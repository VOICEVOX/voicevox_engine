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

# assert VOICEVOX_CORE_VERSION >= 0.5.4 (added cpu shared object)
ARG VOICEVOX_CORE_VERSION=0.6.0
ARG VOICEVOX_CORE_LIBRARY_NAME=core_cpu
RUN <<EOF
    wget -nv --show-progress -c -O "./core.zip" "https://github.com/Hiroshiba/voicevox_core/releases/download/${VOICEVOX_CORE_VERSION}/core.zip"
    unzip "./core.zip"
    mv ./core /opt/voicevox_core
    rm ./core.zip
EOF

RUN <<EOF
    # Workaround: remove unused libcore (cpu, gpu)
    # Prevent error: `/sbin/ldconfig.real: /opt/voicevox_core/libcore.so is not a symbolic link`
    set -eux
    if [ "${VOICEVOX_CORE_LIBRARY_NAME}" = "core" ]; then
        rm -f /opt/voicevox_core/libcore_cpu.so
    elif [ "${VOICEVOX_CORE_LIBRARY_NAME}" = "core_cpu" ]; then
        mv /opt/voicevox_core/libcore_cpu.so /opt/voicevox_core/libcore.so
    else
        echo "Invalid VOICEVOX CORE library name: ${VOICEVOX_CORE_LIBRARY_NAME}" >> /dev/stderr
        exit 1
    fi
EOF

RUN <<EOF
    echo "/opt/voicevox_core" > /etc/ld.so.conf.d/voicevox_core.conf
    rm -f /etc/ld.so.cache
    ldconfig
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
        parallel \
        gosu
    apt-get clean
    rm -rf /var/lib/apt/lists/*
EOF

# Copy python env
COPY --from=compile-python-env /opt/python /opt/python

# Copy VOICEVOX Core shared object
COPY --from=download-core-env /etc/ld.so.conf.d/voicevox_core.conf /etc/ld.so.conf.d/voicevox_core.conf
COPY --from=download-core-env /opt/voicevox_core /opt/voicevox_core

# Copy LibTorch
COPY --from=download-libtorch-env /etc/ld.so.conf.d/libtorch.conf /etc/ld.so.conf.d/libtorch.conf
COPY --from=download-libtorch-env /opt/libtorch /opt/libtorch

# Clone VOICEVOX Core example
ARG VOICEVOX_CORE_EXAMPLE_VERSION=0.6.0
RUN <<EOF
    git clone -b "${VOICEVOX_CORE_EXAMPLE_VERSION}" --depth 1 https://github.com/Hiroshiba/voicevox_core.git /opt/voicevox_core_example
    cd /opt/voicevox_core_example/
    cp ./core.h ./example/python/
EOF

# Add local files
# Temporary override PATH for convenience during the image building
# ARG PATH=/opt/python/bin:$PATH
ADD ./requirements.txt /tmp/
ADD ./voicevox_engine /opt/voicevox_engine/voicevox_engine
ADD ./run.py ./check_tts.py ./VERSION.txt ./LICENSE ./LGPL_LICENSE /opt/voicevox_engine/

RUN <<EOF
    # Create a general user
    useradd --create-home user
    # Update ld
    ldconfig

    # Const environment
    export PATH="$PATH:/opt/python/bin/"
    export LIBRARY_PATH="/opt/voicevox_core:$LIBRARY_PATH"

    # Install requirements
    gosu user python3 -m pip install --upgrade pip setuptools wheel
    gosu user pip3 install -r /tmp/requirements.txt

    # Install voicevox_core
    cd /opt/voicevox_core_example/example/python
    gosu user pip3 install .

    # FIXME: remove first execution delay
    # try 5 times, delay 5 seconds before each execution.
    # if all tries are failed, `docker build` will be failed.

    # Download openjtalk dictionary
    parallel --retries 5 --delay 5 --ungroup \
      gosu user python3 -c "import pyopenjtalk; pyopenjtalk._lazy_init()"
EOF

# Create container start shell
ARG USE_GLIBC_229_WORKAROUND=0
COPY --chmod=775 <<EOF /entrypoint.sh
#!/bin/bash
cat /opt/voicevox_core/README.txt > /dev/stderr

# Workaround: ldconfig fail to load LibTorch if glibc <= 2.29.
# For isolating problems and simplifing script, use flag USE_GLIBC_229_WORKAROUND
# instead of implementing version check logic.
if [ "${USE_GLIBC_229_WORKAROUND}" = "1" ]; then
  export LD_LIBRARY_PATH="/opt/libtorch/lib:\${LD_LIBRARY_PATH:-}"
fi

exec "\$@"
EOF

ENTRYPOINT [ "/entrypoint.sh"  ]
CMD [ "gosu", "user", "/opt/python/bin/python3", "./run.py", "--voicevox_dir", "/opt/voicevox_core/", "--voicelib_dir", "/opt/voicevox_core/", "--host", "0.0.0.0" ]

# Enable use_gpu
FROM runtime-env AS runtime-nvidia-env
CMD [ "gosu", "user", "/opt/python/bin/python3", "./run.py", "--use_gpu", "--voicevox_dir", "/opt/voicevox_core/", "--voicelib_dir", "/opt/voicevox_core/", "--host", "0.0.0.0" ]

# Binary build environment (common to CPU, GPU)
FROM runtime-env AS build-env

# Install ccache for Nuitka cache
# chrpath: required for nuitka build; 'RPATH' settings in used shared
RUN <<EOF
    apt-get update
    apt-get install -y \
        ccache \
        chrpath \
        patchelf
    apt-get clean
    rm -rf /var/lib/apt/lists/*
EOF

# Install Python build dependencies
ADD ./requirements-dev.txt /tmp/
RUN <<EOF
    gosu user /opt/python/bin/pip3 install -r /tmp/requirements-dev.txt
EOF

# Create build script
RUN <<EOF
    set -eux

    cat <<EOD > /build.sh
        #!/bin/bash
        set -eux

        # chown general user c.z. mounted directory may be owned by root
        mkdir -p /opt/voicevox_engine_build
        chown -R user:user /opt/voicevox_engine_build

        mkdir -p /home/user/.cache/Nuitka
        chown -R user:user /home/user/.cache/Nuitka

        cd /opt/voicevox_engine_build

        LIBRARY_PATH="/opt/voicevox_core:\${LIBRARY_PATH:-}" \
            gosu user /opt/python/bin/python3 -m nuitka \
                --output-dir=/opt/voicevox_engine_build \
                --standalone \
                --plugin-enable=numpy \
                --follow-import-to=numpy \
                --follow-import-to=aiofiles \
                --include-package=uvicorn \
                --include-package-data=pyopenjtalk \
                --include-package-data=resampy \
                --include-data-file=/opt/voicevox_engine/VERSION.txt=./ \
                --include-data-file=/opt/libtorch/lib/*.so=./ \
                --include-data-file=/opt/libtorch/lib/*.so.*=./ \
                --include-data-file=/opt/voicevox_core/*.so=./ \
                --include-data-file=/opt/voicevox_core/*.bin=./ \
                --include-data-file=/opt/voicevox_core/metas.json=./ \
                --include-data-file=/home/user/.local/lib/python*/site-packages/llvmlite/binding/*.so=./ \
                --follow-imports \
                --no-prefer-source-code \
                /opt/voicevox_engine/run.py

        # replace libcore.so link for libtorch to relative path
        cat <<EOT | xargs -I '%' patchelf --replace-needed "%" "./%" /opt/voicevox_engine_build/run.dist/libcore.so
            libc10.so
            libtorch_cuda.so
            libtorch_cuda_cpp.so
            libtorch_cpu.so
            libtorch_cuda_cu.so
            libtorch.so
EOT

        chmod +x /opt/voicevox_engine_build/run.dist/run
EOD
    chmod +x /build.sh
EOF

CMD [ "bash", "/build.sh" ]
