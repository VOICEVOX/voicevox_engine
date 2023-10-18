# syntax=docker/dockerfile:1.4

ARG BASE_IMAGE=ubuntu:20.04
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

# assert VOICEVOX_CORE_VERSION >= 0.11.0 (ONNX)
ARG TARGETPLATFORM
ARG USE_GPU=false
ARG VOICEVOX_CORE_VERSION=0.14.5

RUN <<EOF
    set -eux

    # Processing Switch
    if [ "${USE_GPU}" = "true" ]; then
        VOICEVOX_CORE_ASSET_ASSET_PROCESSING="gpu"
    else
        VOICEVOX_CORE_ASSET_ASSET_PROCESSING="cpu"
    fi

    # TARGETARCH Switch
    if [ "${TARGETPLATFORM}" = "linux/amd64" ]; then
        VOICEVOX_CORE_ASSET_TARGETARCH="x64"
    else
        VOICEVOX_CORE_ASSET_TARGETARCH="arm64"
    fi

    VOICEVOX_CORE_ASSET_PREFIX="voicevox_core-linux-${VOICEVOX_CORE_ASSET_TARGETARCH}-${VOICEVOX_CORE_ASSET_ASSET_PROCESSING}"

    # Download Core
    VOICEVOX_CORE_ASSET_NAME=${VOICEVOX_CORE_ASSET_PREFIX}-${VOICEVOX_CORE_VERSION}
    wget -nv --show-progress -c -O "./${VOICEVOX_CORE_ASSET_NAME}.zip" "https://github.com/VOICEVOX/voicevox_core/releases/download/${VOICEVOX_CORE_VERSION}/${VOICEVOX_CORE_ASSET_NAME}.zip"
    unzip "./${VOICEVOX_CORE_ASSET_NAME}.zip"
    mkdir -p core
    mv "${VOICEVOX_CORE_ASSET_NAME}"/* core
    rm -rf $VOICEVOX_CORE_ASSET_NAME
    rm "./${VOICEVOX_CORE_ASSET_NAME}.zip"

    # Move Core to /opt/voicevox_core/
    mkdir /opt/voicevox_core
    mv ./core/* /opt/voicevox_core/

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

ARG TARGETPLATFORM
ARG USE_GPU=false
ARG ONNXRUNTIME_VERSION=1.13.1
RUN <<EOF
    set -eux

    # Processing Switch
    if [ "${USE_GPU}" = "true" ]; then
        ONNXRUNTIME_PROCESSING="gpu-"
    else
        ONNXRUNTIME_PROCESSING=""
    fi

    # TARGETARCH Switch
    if [ "${TARGETPLATFORM}" = "linux/amd64" ]; then
        ONNXRUNTIME_TARGETARCH=x64
    else
        ONNXRUNTIME_TARGETARCH=aarch64
    fi
    
    ONNXRUNTIME_URL="https://github.com/microsoft/onnxruntime/releases/download/v${ONNXRUNTIME_VERSION}/onnxruntime-linux-${ONNXRUNTIME_TARGETARCH}-${ONNXRUNTIME_PROCESSING}${ONNXRUNTIME_VERSION}.tgz"

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
        curl \
        libncursesw5-dev \
        xz-utils \
        tk-dev \
        libxml2-dev \
        libxmlsec1-dev \
        libffi-dev \
        liblzma-dev \
        git
    apt-get clean
    rm -rf /var/lib/apt/lists/*
EOF

ARG PYTHON_VERSION=3.11.3
ARG PYENV_VERSION=v2.3.17
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

# ca-certificates: pyopenjtalk dictionary download
# build-essential: pyopenjtalk local build
RUN <<EOF
    set -eux

    apt-get update
    apt-get install -y \
        git \
        wget \
        cmake \
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
    gosu user /opt/python/bin/pip3 install -r /tmp/requirements.txt
EOF

# Copy VOICEVOX Core release
# COPY --from=download-core-env /etc/ld.so.conf.d/voicevox_core.conf /etc/ld.so.conf.d/voicevox_core.conf
COPY --from=download-core-env /opt/voicevox_core /opt/voicevox_core

# Copy ONNX Runtime
# COPY --from=download-onnxruntime-env /etc/ld.so.conf.d/onnxruntime.conf /etc/ld.so.conf.d/onnxruntime.conf
COPY --from=download-onnxruntime-env /opt/onnxruntime /opt/onnxruntime

# Add local files
ADD ./voicevox_engine /opt/voicevox_engine/voicevox_engine
ADD ./docs /opt/voicevox_engine/docs
ADD ./run.py ./generate_licenses.py ./presets.yaml ./default.csv ./default_setting.yml ./engine_manifest.json /opt/voicevox_engine/
ADD ./speaker_info /opt/voicevox_engine/speaker_info
ADD ./ui_template /opt/voicevox_engine/ui_template
ADD ./engine_manifest_assets /opt/voicevox_engine/engine_manifest_assets

# Replace version
ARG VOICEVOX_ENGINE_VERSION=latest
RUN sed -i "s/__version__ = \"latest\"/__version__ = \"${VOICEVOX_ENGINE_VERSION}\"/" /opt/voicevox_engine/voicevox_engine/__init__.py
RUN sed -i "s/\"version\": \"999\\.999\\.999\"/\"version\": \"${VOICEVOX_ENGINE_VERSION}\"/" /opt/voicevox_engine/engine_manifest.json

# Generate licenses.json
ADD ./requirements-license.txt /tmp/
RUN <<EOF
    set -eux

    cd /opt/voicevox_engine

    # Define temporary env vars
    # /home/user/.local/bin is required to use the commands installed by pip
    export PATH="/home/user/.local/bin:${PATH:-}"

    gosu user /opt/python/bin/pip3 install -r /tmp/requirements-license.txt
    gosu user /opt/python/bin/python3 generate_licenses.py > /opt/voicevox_engine/engine_manifest_assets/dependency_licenses.json
    cp /opt/voicevox_engine/engine_manifest_assets/dependency_licenses.json /opt/voicevox_engine/licenses.json
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

# Download Resource
ARG VOICEVOX_RESOURCE_VERSION=0.14.4
RUN <<EOF
    set -eux

    # README
    wget -nv --show-progress -c -O "/opt/voicevox_engine/README.md" "https://raw.githubusercontent.com/VOICEVOX/voicevox_resource/${VOICEVOX_RESOURCE_VERSION}/engine/README.md"
EOF

# Create container start shell
COPY --chmod=775 <<EOF /entrypoint.sh
#!/bin/bash
set -eux

# Display README for engine
cat /opt/voicevox_engine/README.md > /dev/stderr

exec "\$@"
EOF

ENTRYPOINT [ "/entrypoint.sh"  ]
CMD [ "gosu", "user", "/opt/python/bin/python3", "./run.py", "--voicelib_dir", "/opt/voicevox_core/", "--runtime_dir", "/opt/onnxruntime/lib", "--host", "0.0.0.0" ]

# Enable use_gpu
FROM runtime-env AS runtime-nvidia-env
CMD [ "gosu", "user", "/opt/python/bin/python3", "./run.py", "--use_gpu", "--voicelib_dir", "/opt/voicevox_core/", "--runtime_dir", "/opt/onnxruntime/lib", "--host", "0.0.0.0" ]
