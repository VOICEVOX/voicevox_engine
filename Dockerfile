# syntax=docker/dockerfile:1

# TODO: build-arg と target のドキュメントをこのファイルに書く

ARG BASE_IMAGE=mirror.gcr.io/ubuntu:22.04

# Download VOICEVOX ENGINE
FROM ${BASE_IMAGE} AS download-engine-env
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

# Runtime
FROM ${BASE_IMAGE} AS runtime-env
ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /opt/voicevox_engine

# ca-certificates: pyopenjtalk dictionary download
# build-essential: pyopenjtalk local build
# ref: https://github.com/VOICEVOX/voicevox_engine/issues/770
RUN <<EOF
    set -eux

    apt-get update
    apt-get install -y \
        curl \
        gosu
    apt-get clean
    rm -rf /var/lib/apt/lists/*

    # Create a general user
    useradd --create-home user
EOF

# Copy VOICEVOX ENGINE
COPY --from=download-engine-env /opt/voicevox_engine /opt/voicevox_engine

# Download Resource
ARG VOICEVOX_RESOURCE_VERSION=0.24.1
RUN <<EOF
    set -eux

    # README
    curl -fLo "/opt/voicevox_engine/README.md" --retry 3 --retry-delay 5 "https://raw.githubusercontent.com/VOICEVOX/voicevox_resource/${VOICEVOX_RESOURCE_VERSION}/engine/README.md"
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
CMD [ "gosu", "user", "/opt/voicevox_engine/run", "--host", "0.0.0.0" ]

# Enable use_gpu
FROM runtime-env AS runtime-nvidia-env
CMD [ "gosu", "user", "/opt/voicevox_engine/run", "--use_gpu", "--host", "0.0.0.0" ]
