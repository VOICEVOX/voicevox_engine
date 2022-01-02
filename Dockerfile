# syntax=docker/dockerfile:1.3-labs

ARG BASE_IMAGE=ubuntu:focal
ARG BASE_RUNTIME_IMAGE=$BASE_IMAGE

# Download VOICEVOX Core shared object
FROM ${BASE_IMAGE} AS download-core-env
ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /work

RUN <<EOF
    set -eux

    apt-get update
    apt-get install -y \
        wget \
        unzip
    apt-get clean
    rm -rf /var/lib/apt/lists/*
EOF

# assert VOICEVOX_CORE_VERSION >= 0.10.preview.0 (ONNX)
ARG VOICEVOX_CORE_VERSION=0.10.preview.0
ARG VOICEVOX_CORE_LIBRARY_NAME=libcore_cpu_x64.so
RUN <<EOF
    set -eux

    # Download Core
    wget -nv --show-progress -c -O "./core.zip" "https://github.com/VOICEVOX/voicevox_core/releases/download/${VOICEVOX_CORE_VERSION}/core.zip"
    unzip "./core.zip"
    rm ./core.zip

    # Move Core Library to /opt/voicevox_core/
    mkdir /opt/voicevox_core
    mv "./core/${VOICEVOX_CORE_LIBRARY_NAME}" /opt/voicevox_core/

    if [ "${VOICEVOX_CORE_LIBRARY_NAME}" != "libcore.so" ]; then
        # Create relative symbolic link
        cd /opt/voicevox_core
        ln -sf "${VOICEVOX_CORE_LIBRARY_NAME}" libcore.so
        cd -
    fi

    # Move Voice Library to /opt/voicevox_core/
    mv ./core/*.bin ./core/core.h ./core/metas.json /opt/voicevox_core/

    # Move documents to /opt/voicevox_core/
    mv ./core/README.txt ./core/VERSION /opt/voicevox_core/

    rm -rf ./core

    # Add /opt/voicevox_core to dynamic library search path
    echo "/opt/voicevox_core" > /etc/ld.so.conf.d/voicevox_core.conf

    # Update dynamic library search cache
    ldconfig
EOF


# Download ONNX Runtime
FROM ${BASE_IMAGE} AS download-onnxruntime-env
ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /work

RUN <<EOF
    set -eux

    apt-get update
    apt-get install -y \
        wget \
        tar
    apt-get clean
    rm -rf /var/lib/apt/lists/*
EOF

ARG ONNXRUNTIME_URL=https://github.com/microsoft/onnxruntime/releases/download/v1.9.0/onnxruntime-linux-x64-1.9.0.tgz
RUN <<EOF
    set -eux

    # Download ONNX Runtime
    wget -nv --show-progress -c -O "./onnxruntime.tgz" "${ONNXRUNTIME_URL}"

    # Extract ONNX Runtime to /opt/onnxruntime
    mkdir -p /opt/onnxruntime
    tar xf "./onnxruntime.tgz" -C "/opt/onnxruntime" --strip-components 1
    rm ./onnxruntime.tgz

    # Add /opt/onnxruntime/lib to dynamic library search path
    echo "/opt/onnxruntime/lib" > /etc/ld.so.conf.d/onnxruntime.conf

    # Update dynamic library search cache
    ldconfig
EOF


# Compile Python (version locked)
FROM ${BASE_IMAGE} AS compile-python-env

ARG DEBIAN_FRONTEND=noninteractive

RUN <<EOF
    set -eux
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

ARG PYTHON_VERSION=3.8.10
# FIXME: Lock pyenv version with git tag
# 90d0d20508a91e7ea1e609e8aa9f9d1a28bb563e (including 3.7.12) not released yet (2021-09-12)
ARG PYENV_VERSION=master
ARG PYENV_ROOT=/tmp/.pyenv
ARG PYBUILD_ROOT=/tmp/python-build
RUN <<EOF
    set -eux

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
#     set -eux
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
RUN <<EOF
    set -eux

    apt-get update
    apt-get install -y \
        git \
        cmake \
        libsndfile1 \
        ca-certificates \
        build-essential \
        gosu
    apt-get clean
    rm -rf /var/lib/apt/lists/*

    # Create a general user
    useradd --create-home user
EOF

# Copy python env
COPY --from=compile-python-env /opt/python /opt/python

# Install Python dependencies
ADD ./requirements.txt /tmp/
RUN <<EOF
    # Install requirements
    gosu user /opt/python/bin/python3 -m pip install --upgrade pip setuptools wheel
    gosu user /opt/python/bin/pip3 install -r /tmp/requirements.txt
EOF

# Copy VOICEVOX Core release
# COPY --from=download-core-env /etc/ld.so.conf.d/voicevox_core.conf /etc/ld.so.conf.d/voicevox_core.conf
COPY --from=download-core-env /opt/voicevox_core /opt/voicevox_core

# Copy ONNX Runtime
# COPY --from=download-onnxruntime-env /etc/ld.so.conf.d/onnxruntime.conf /etc/ld.so.conf.d/onnxruntime.conf
COPY --from=download-onnxruntime-env /opt/onnxruntime /opt/onnxruntime

# Install VOICEVOX Core Python module
ARG VOICEVOX_CORE_SOURCE_VERSION=0.10.preview.0
RUN <<EOF
    set -eux

    git clone -b "${VOICEVOX_CORE_SOURCE_VERSION}" --depth 1 https://github.com/VOICEVOX/voicevox_core.git /tmp/voicevox_core_source

    # Copy shared libraries to repo to be packed in core package
    # ONNX Runtime: included
    # CUDA/cuDNN: not included

    mkdir -p /tmp/voicevox_core_source/core/lib
    cp /opt/voicevox_core/libcore.so /tmp/voicevox_core_source/core/lib/

    # Copy versioned shared library only (setup.py will copy package data as real file on install)
    cd /opt/onnxruntime/lib
    find . -name 'libonnxruntime.so.*' -or -name 'libonnxruntime_*.so' | xargs -I% cp -v % /tmp/voicevox_core_source/core/lib/
    cd -

    # Duplicate core.h in repo
    cp /tmp/voicevox_core_source/core/src/core.h /tmp/voicevox_core_source/core/lib/

    # Install voicevox_core Python module
    # Files will be generated at build time, so chown for general user
    chown -R user:user /tmp/voicevox_core_source

    cd /tmp/voicevox_core_source

    gosu user /opt/python/bin/pip3 install .

    # remove cloned repository before layer end to reduce image size
    rm -rf /tmp/voicevox_core_source
EOF

# Add local files
ADD ./voicevox_engine /opt/voicevox_engine/voicevox_engine
ADD ./docs /opt/voicevox_engine/docs
ADD ./run.py ./generate_licenses.py ./check_tts.py ./presets.yaml ./VERSION.txt ./user.dic /opt/voicevox_engine/
ADD ./speaker_info /opt/voicevox_engine/speaker_info

# Generate licenses.json
RUN <<EOF
    set -eux

    cd /opt/voicevox_engine

    # Define temporary env vars
    # /home/user/.local/bin is required to use the commands installed by pip
    export PATH="/home/user/.local/bin:${PATH:-}"

    gosu user /opt/python/bin/pip3 install pip-licenses
    gosu user /opt/python/bin/python3 generate_licenses.py > /opt/voicevox_engine/licenses.json
EOF

# Keep this layer separated to use layer cache on download failed in local build
RUN <<EOF
    set -eux

    # Download openjtalk dictionary
    # try 5 times, sleep 5 seconds before retry
    for i in $(seq 5); do
        EXIT_CODE=0
        gosu user /opt/python/bin/python3 -c "import pyopenjtalk; pyopenjtalk._lazy_init()" || EXIT_CODE=$?
        if [ "$EXIT_CODE" = "0" ]; then
            break
        fi
        sleep 5
    done

    if [ "$EXIT_CODE" != "0" ]; then
        exit "$EXIT_CODE"
    fi
EOF

# Create container start shell
COPY --chmod=775 <<EOF /entrypoint.sh
#!/bin/bash
set -eux

cat /opt/voicevox_core/README.txt > /dev/stderr

exec "\$@"
EOF

ENTRYPOINT [ "/entrypoint.sh"  ]
CMD [ "gosu", "user", "/opt/python/bin/python3", "./run.py", "--voicelib_dir", "/opt/voicevox_core/", "--host", "0.0.0.0" ]

# Enable use_gpu
FROM runtime-env AS runtime-nvidia-env
CMD [ "gosu", "user", "/opt/python/bin/python3", "./run.py", "--use_gpu", "--voicelib_dir", "/opt/voicevox_core/", "--host", "0.0.0.0" ]

# Binary build environment (common to CPU, GPU)
FROM runtime-env AS build-env

# Install ccache for Nuitka cache
# chrpath: required for nuitka build; 'RPATH' settings in used shared
RUN <<EOF
    set -eux

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
    set -eux

    gosu user /opt/python/bin/pip3 install -r /tmp/requirements-dev.txt
EOF

# Generate licenses.json with build dependencies
RUN <<EOF
    set -eux

    cd /opt/voicevox_engine

    # Define temporary env vars
    # /home/user/.local/bin is required to use the commands installed by pip
    export PATH="/home/user/.local/bin:${PATH:-}"

    gosu user /opt/python/bin/pip3 install pip-licenses
    gosu user /opt/python/bin/python3 generate_licenses.py > /opt/voicevox_engine/licenses.json
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

        gosu user /opt/python/bin/python3 -m nuitka \
            --output-dir=/opt/voicevox_engine_build \
            --standalone \
            --plugin-enable=numpy \
            --follow-import-to=numpy \
            --follow-import-to=aiofiles \
            --include-package=uvicorn \
            --include-package=anyio \
            --include-package-data=pyopenjtalk \
            --include-package-data=scipy \
            --include-data-file=/opt/voicevox_engine/VERSION.txt=./ \
            --include-data-file=/opt/voicevox_engine/licenses.json=./ \
            --include-data-file=/opt/voicevox_engine/presets.yaml=./ \
            --include-data-file=/opt/voicevox_engine/user.dic=./ \
            --include-data-file=/opt/voicevox_core/*.bin=./ \
            --include-data-file=/opt/voicevox_core/metas.json=./ \
            --include-data-dir=/opt/voicevox_engine/speaker_info=./speaker_info \
            --follow-imports \
            --no-prefer-source-code \
            /opt/voicevox_engine/run.py

        # Copy libonnxruntime_providers_cuda.so and dependencies (CUDA/cuDNN)
        if [ -f "/opt/onnxruntime/lib/libonnxruntime_providers_cuda.so" ]; then
            mkdir -p /tmp/coredeps

            # Copy provider libraries (libonnxruntime.so.{version} is copied by Nuitka)
            cd /opt/onnxruntime/lib
            cp libonnxruntime_*.so /tmp/coredeps/
            cd -

            # assert nvidia/cuda base image
            cd /usr/local/cuda/lib64
            cp libcublas.so.* libcublasLt.so.* libcudart.so.* libcufft.so.* libcurand.so.* /tmp/coredeps/
            cd -

            # remove unneed full version libraries
            cd /tmp/coredeps
            rm -f libcublas.so.*.* libcublasLt.so.*.* libcufft.so.*.* libcurand.so.*.*
            rm -f libcudart.so.*.*.*
            cd -

            # assert nvidia/cuda base image
            cd /usr/lib/x86_64-linux-gnu
            cp libcudnn.so.* libcudnn_*_infer.so.* /tmp/coredeps/
            cd -

            # remove unneed full version libraries
            cd /tmp/coredeps
            rm -f libcudnn.so.*.* libcudnn_*_infer.so.*.*
            cd -

            mv /tmp/coredeps/* /opt/voicevox_engine_build/run.dist/
            rm -rf /tmp/coredeps
        fi

        chmod +x /opt/voicevox_engine_build/run.dist/run
EOD
    chmod +x /build.sh
EOF

CMD [ "bash", "/build.sh" ]
