# syntax=docker/dockerfile:1.11

# TODO: build-arg と target のドキュメントをこのファイルに書く

ARG BASE_IMAGE=mirror.gcr.io/ubuntu:20.04
ARG BASE_RUNTIME_IMAGE=$BASE_IMAGE

# Download VOICEVOX ENGINE
FROM ${BASE_IMAGE} AS download-engine-env
ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /work

RUN <<EOF
    set -eux

    apt-get update
    apt-get install -y \
        gh \
        wget \
        curl \
        p7zip
    apt-get clean
    rm -rf /var/lib/apt/lists/*
EOF

ARG TARGETPLATFORM
ARG VOICEVOX_ENGINE_VERSION=latest
ARG USE_GPU=false

RUN --mount=type=secret,id=gh-token,env=GH_TOKEN <<EOF
    set -eux

    case "$USE_GPU" in
        true)
            TARGET=linux-nvidia ;;
        false)
            case "$TARGETPLATFORM" in
                linux/amd64)
                    TARGET=linux-cpu-x64 ;;
                linux/arm64)
                    TARGET=linux-cpu-arm64 ;;
                *)
                    # shellcheck disable=SC2016
                    echo 'Unexpected value for `$TARGETPLATFORM`' >&2
                    exit 1
            esac ;;
        *)
            # shellcheck disable=SC2016
            echo 'Invalid value for `$USE_GPU`' >&2
            exit 1
    esac

    if [ "$VOICEVOX_ENGINE_VERSION" = latest ]; then
        tag=$(gh release view -R VOICEVOX/voicevox_engine --json tagName -q .tagName)
    else
        tag=$VOICEVOX_ENGINE_VERSION
    fi

    list_name=voicevox_engine-$TARGET-$tag.7z.txt

    wget -nv --show-progress "https://github.com/VOICEVOX/voicevox_engine/releases/download/$tag/$list_name"

    awk \
        -v "tag=$tag" \
        '{
             print \
                 "url = \"https://github.com/VOICEVOX/voicevox_engine/releases/download/" tag "/" $0 "\"\n" \
                 "output = \"" $0 "\""
        }' \
        "$list_name" \
        > ./curl.txt

    curl -fL --parallel --config ./curl.txt

    7zr x "$(head -1 "./$list_name")"

    mv ./$TARGET /opt/voicevox_engine
    rm ./*
EOF

# Runtime
FROM ${BASE_RUNTIME_IMAGE} AS runtime-env
ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /opt/voicevox_engine

# ca-certificates: pyopenjtalk dictionary download
# build-essential: pyopenjtalk local build
# ref: https://github.com/VOICEVOX/voicevox_engine/issues/770
RUN <<EOF
    set -eux

    apt-get update
    apt-get install -y \
        wget \
        gosu
    apt-get clean
    rm -rf /var/lib/apt/lists/*

    # Create a general user
    useradd --create-home user
EOF

# Copy VOICEVOX ENGINE
COPY --from=download-engine-env /opt/voicevox_engine /opt/voicevox_engine

# Download Resource
ARG VOICEVOX_RESOURCE_VERSION=0.23.0
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
CMD [ "gosu", "user", "/opt/voicevox_engine/run", "--host", "0.0.0.0" ]

# Enable use_gpu
FROM runtime-env AS runtime-nvidia-env
CMD [ "gosu", "user", "/opt/voicevox_engine/run", "--use_gpu", "--host", "0.0.0.0" ]
