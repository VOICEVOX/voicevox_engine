# syntax=docker/dockerfile:1.3-labs

ARG BASE_IMAGE=ubuntu:focal
ARG BASE_RUNTIME_IMAGE=ubuntu:focal

# Download VOICEVOX Core shared object
FROM ${BASE_IMAGE} AS download-core-env
ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /work

RUN <<EOF
    apt-get update
    apt-get install -y \
        wget \
        unzip
    apt-get clean
    rm -rf /var/lib/apt/lists/*
EOF

ARG VOICEVOX_CORE_VERSION=0.5.2
RUN <<EOF
    wget -nv --show-progress -c -O "./core.zip" "https://github.com/Hiroshiba/voicevox_core/releases/download/${VOICEVOX_CORE_VERSION}/core.zip"
    unzip "./core.zip"
    mv ./core /opt/voicevox_core
    rm ./core.zip
EOF

RUN <<EOF
    echo "/opt/voicevox_core" > /etc/ld.so.conf.d/voicevox_core.conf
    rm -f /etc/ld.so.cache
    ldconfig
EOF

# Temporary workaround: modify libcore link for cpu
# Remove CUDA/LibTorchGPU dependencies from libcore
ARG INFERENCE_DEVICE=cpu
RUN <<EOF
    if [ "${INFERENCE_DEVICE}" = "cpu" ]; then
        apt-get update
        apt-get install -y \
            patchelf
        apt-get clean
        rm -rf /var/lib/apt/lists/*
    fi
EOF

RUN <<EOF
    if [ "${INFERENCE_DEVICE}" = "cpu" ]; then
        cd /opt/voicevox_core/

        patchelf --remove-needed libtorch_cuda.so libcore.so
        patchelf --remove-needed libtorch_cuda_cpp.so libcore.so
        patchelf --remove-needed libtorch_cuda_cu.so libcore.so
        patchelf --remove-needed libnvToolsExt.so.1 libcore.so
        patchelf --remove-needed libcudart.so.11.0 libcore.so
    fi
EOF


# Download LibTorch
FROM ${BASE_IMAGE} AS download-libtorch-env
ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /work

RUN <<EOF
    apt-get update
    apt-get install -y \
        wget \
        unzip
    apt-get clean
    rm -rf /var/lib/apt/lists/*
EOF

ARG LIBTORCH_URL=https://download.pytorch.org/libtorch/cpu/libtorch-cxx11-abi-shared-with-deps-1.9.0%2Bcpu.zip
RUN <<EOF
    wget -nv --show-progress -c -O "./libtorch.zip" "${LIBTORCH_URL}"
    unzip "./libtorch.zip"
    mv ./libtorch /opt/libtorch
    rm ./libtorch.zip
EOF

RUN <<EOF
    echo "/opt/libtorch/lib" > /etc/ld.so.conf.d/libtorch.conf
    rm -f /etc/ld.so.cache
    ldconfig
EOF


# Compile Python (version locked)
FROM ${BASE_IMAGE} AS compile-python-env

ARG DEBIAN_FRONTEND=noninteractive

RUN <<EOF
    apt-get update
    apt-get install -y \
        build-essential \
        libssl-dev \
        zlib1g-dev \
        libbz2-dev \
        libreadline-dev \
        libsqlite3-dev \
        wget \
        curl \
        llvm \
        libncurses5-dev \
        libncursesw5-dev \
        xz-utils \
        tk-dev \
        libffi-dev \
        liblzma-dev \
        python-openssl \
        git
    apt-get clean
    rm -rf /var/lib/apt/lists/*
EOF

ARG PYTHON_VERSION=3.7.12
# FIXME: Lock pyenv version with git tag
# 90d0d20508a91e7ea1e609e8aa9f9d1a28bb563e (including 3.7.12) not released yet (2021-09-12)
ARG PYENV_VERSION=master
ARG PYENV_ROOT=/tmp/.pyenv
ARG PYBUILD_ROOT=/tmp/python-build
RUN <<EOF
    set -e
    git clone -b "${PYENV_VERSION}" https://github.com/pyenv/pyenv.git "$PYENV_ROOT"
    PREFIX="$PYBUILD_ROOT" "$PYENV_ROOT"/plugins/python-build/install.sh
    "$PYBUILD_ROOT/bin/python-build" -v "$PYTHON_VERSION" /opt/python
    rm -rf "$PYBUILD_ROOT" "$PYENV_ROOT"
EOF

# FIXME: add /opt/python to PATH
# not working: /etc/profile read only on login shell
# not working: /etc/environment is the same
# not suitable: `ENV` is ignored by docker-compose
# RUN <<EOF
#     echo "export PATH=/opt/python/bin:\$PATH" > /etc/profile.d/python-path.sh
#     echo "export LD_LIBRARY_PATH=/opt/python/lib:\$LD_LIBRARY_PATH" >> /etc/profile.d/python-path.sh
#     echo "export C_INCLUDE_PATH=/opt/python/include:\$C_INCLUDE_PATH" >> /etc/profile.d/python-path.sh
#
#     rm -f /etc/ld.so.cache
#     ldconfig
# EOF


# Runtime
FROM ${BASE_RUNTIME_IMAGE} AS runtime-env
ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /opt/voicevox_engine

# libsndfile1: soundfile shared object
# ca-certificates: pyopenjtalk dictionary download
# build-essential: pyopenjtalk local build
# parallel: retry download pyopenjtalk dictionary
RUN <<EOF
    apt-get update
    apt-get install -y \
        git \
        cmake \
        libsndfile1 \
        ca-certificates \
        build-essential \
        parallel
    apt-get clean
    rm -rf /var/lib/apt/lists/*
EOF

# gosu: general user execution
ARG GOSU_VERSION=1.14
ADD "https://github.com/tianon/gosu/releases/download/${GOSU_VERSION}/gosu-amd64" /usr/local/bin/gosu
RUN <<EOF
    chmod +x /usr/local/bin/gosu
EOF

# Create a general user
RUN <<EOF
    useradd --create-home user
EOF

COPY --from=compile-python-env /opt/python /opt/python

# Temporary override PATH for convenience during the image building
# ARG PATH=/opt/python/bin:$PATH
ADD ./requirements.txt /tmp/
RUN <<EOF
    gosu user /opt/python/bin/python3 -m pip install --upgrade pip setuptools wheel
    gosu user /opt/python/bin/pip3 install -r /tmp/requirements.txt
EOF

# Copy VOICEVOX Core shared object
COPY --from=download-core-env /etc/ld.so.conf.d/voicevox_core.conf /etc/ld.so.conf.d/voicevox_core.conf
COPY --from=download-core-env /opt/voicevox_core /opt/voicevox_core

# Copy LibTorch
COPY --from=download-libtorch-env /etc/ld.so.conf.d/libtorch.conf /etc/ld.so.conf.d/libtorch.conf
COPY --from=download-libtorch-env /opt/libtorch /opt/libtorch

ARG VOICEVOX_CORE_EXAMPLE_VERSION=0.5.2
RUN <<EOF
    git clone -b "${VOICEVOX_CORE_EXAMPLE_VERSION}" --depth 1 https://github.com/Hiroshiba/voicevox_core.git /opt/voicevox_core_example
    cd /opt/voicevox_core_example
    cp ./core.h ./example/python/
    cd example/python
    LIBRARY_PATH="/opt/voicevox_core:$LIBRARY_PATH" gosu user /opt/python/bin/pip3 install .
EOF

ADD ./voicevox_engine /opt/voicevox_engine/voicevox_engine
ADD ./run.py ./check_tts.py ./VERSION.txt ./LICENSE ./LGPL_LICENSE /opt/voicevox_engine/

# Download openjtalk dictionary
RUN <<EOF
    # FIXME: remove first execution delay
    # try 5 times, delay 5 seconds before each execution.
    # if all tries are failed, `docker build` will be failed.
    parallel --retries 5 --delay 5 --ungroup <<EOT
        gosu user /opt/python/bin/python3 -c "import pyopenjtalk; pyopenjtalk._lazy_init()"
EOT
EOF

# Update ldconfig on container start
RUN <<EOF
    cat <<EOT > /entrypoint.sh
        #!/bin/bash
        cat /opt/voicevox_core/README.txt > /dev/stderr

        rm -f /etc/ld.so.cache
        ldconfig

        exec "\$@"
EOT
    chmod +x /entrypoint.sh
EOF

ENTRYPOINT [ "bash", "/entrypoint.sh"  ]
CMD [ "gosu", "user", "/opt/python/bin/python3", "./run.py", "--voicevox_dir", "/opt/voicevox_core/", "--voicelib_dir", "/opt/voicevox_core/", "--host", "0.0.0.0" ]

# Enable use_gpu
FROM runtime-env AS runtime-nvidia-env
CMD [ "gosu", "user", "/opt/python/bin/python3", "./run.py", "--use_gpu", "--voicevox_dir", "/opt/voicevox_core/", "--voicelib_dir", "/opt/voicevox_core/", "--host", "0.0.0.0" ]
