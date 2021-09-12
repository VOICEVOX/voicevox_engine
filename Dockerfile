# syntax=docker/dockerfile:1.3-labs

ARG BASE_RUNTIME_IMAGE=ubuntu:focal

FROM ubuntu:focal AS download-core-env
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
    mkdir -p /etc/ld.conf.so.d
    echo "/opt/voicevox_core" > /etc/ld.conf.so.d/voicevox_core.conf
EOF


FROM ${BASE_RUNTIME_IMAGE} AS runtime-env
ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /opt/voicevox_engine

# libsndfile1: soundfile shared object
# ca-certificates: pyopenjtalk dictionary download
RUN <<EOF
    apt-get update
    apt-get install -y \
        python3 \
        python3-pip \
        git \
        cmake \
        libsndfile1 \
        ca-certificates
    apt-get clean
    rm -rf /var/lib/apt/lists/*
EOF

ADD ./requirements.txt ./requirements-dev.txt /tmp/
RUN <<EOF
    python -m pip install --upgrade pip setuptools wheel
    pip install -r /tmp/requirements-dev.txt
EOF

COPY --from=download-core-env /opt/voicevox_core /opt/voicevox_core

RUN mkdir -p /etc/ld.conf.so.d
COPY --from=download-core-env /etc/ld.conf.so.d/voicevox_core.conf /etc/ld.conf.so.d/voicevox_core.conf

ADD ./voicevox_engine /opt/voicevox_engine/voicevox_engine
ADD ./run.py ./check_tts.py ./VERSION.txt ./speakers.json ./LICENSE ./LGPL_LICENSE /opt/voicevox_engine/

# Download openjtalk dictionary
RUN python3 -c "import pyopenjtalk; pyopenjtalk._lazy_init()"

CMD [ "python3", "./run.py", "--voicevox_dir", "/opt/voicevox_core", "--host", "0.0.0.0" ]
