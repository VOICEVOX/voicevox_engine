# syntax=docker/dockerfile:1

# TODO: build-arg と target のドキュメントをこのファイルに書く

ARG BASE_IMAGE=mirror.gcr.io/ubuntu:22.04

FROM ${BASE_IMAGE} AS download-env
ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /work

RUN <<EOF
    set -eux

    apt-get update
    apt-get install -y \
        curl \
        p7zip
    apt-get clean
    rm -rf /var/lib/apt/lists/*
EOF

# Download VOICEVOX ENGINE
ARG VOICEVOX_ENGINE_REPOSITORY
ARG VOICEVOX_ENGINE_VERSION
ARG VOICEVOX_ENGINE_TARGET

RUN <<EOF
    set -eux

    LIST_NAME=voicevox_engine-$VOICEVOX_ENGINE_TARGET-$VOICEVOX_ENGINE_VERSION.7z.txt

    curl -fLO --retry 3 --retry-delay 5 "https://github.com/$VOICEVOX_ENGINE_REPOSITORY/releases/download/$VOICEVOX_ENGINE_VERSION/$LIST_NAME"

    awk \
        -v "repo=$VOICEVOX_ENGINE_REPOSITORY" \
        -v "tag=$VOICEVOX_ENGINE_VERSION" \
        '{
             print \
                 "url = \"https://github.com/" repo "/releases/download/" tag "/" $0 "\"\n" \
                 "output = \"" $0 "\""
        }' \
        "$LIST_NAME" \
        > ./curl.txt

    curl -fL --retry 3 --retry-delay 5 --parallel --config ./curl.txt

    7zr x "$(head -1 "./$LIST_NAME")"

    mv ./$VOICEVOX_ENGINE_TARGET /opt/voicevox_engine
    rm ./*
EOF

# Download Resource
ARG VOICEVOX_RESOURCE_VERSION=0.26.0-preview.0
RUN <<EOF
    set -eux

    # README
    curl -fLo "/work/README.md" --retry 3 --retry-delay 5 "https://raw.githubusercontent.com/VOICEVOX/voicevox_resource/${VOICEVOX_RESOURCE_VERSION}/engine/README.md"
EOF

# Runtime
FROM ${BASE_IMAGE} AS runtime-env
ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /opt/voicevox_engine

RUN <<EOF
    set -eux

    apt-get update
    apt-get install -y \
        gosu
    apt-get clean
    rm -rf /var/lib/apt/lists/*

    # Create a general user
    useradd --create-home user
EOF

# Copy VOICEVOX ENGINE
COPY --from=download-env /opt/voicevox_engine /opt/voicevox_engine

# Copy Resource
COPY --from=download-env /work/README.md /opt/voicevox_engine/README.md

# Create container start shell
COPY --chmod=775 <<EOF /entrypoint.sh
#!/bin/bash
set -eux

# Display README for engine
cat /opt/voicevox_engine/README.md > /dev/stderr

exec gosu user /opt/voicevox_engine/run "\$@"
EOF

ENV VV_HOST=0.0.0.0

ENTRYPOINT [ "/entrypoint.sh" ]

# Enable use_gpu
FROM runtime-env AS runtime-nvidia-env

ENV VV_USE_GPU=1
