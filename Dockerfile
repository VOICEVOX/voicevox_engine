# syntax=docker/dockerfile:1

# TODO: build-arg と target のドキュメントをこのファイルに書く

# --- Download ---
FROM mirror.gcr.io/ubuntu:22.04 AS download-env
ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /work

RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && \
    apt-get install -y  curl p7zip

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
ARG VOICEVOX_RESOURCE_VERSION=0.25.0
RUN <<EOF
    set -eux

    # README
    curl -fLo "/work/README.md" --retry 3 --retry-delay 5 "https://raw.githubusercontent.com/VOICEVOX/voicevox_resource/${VOICEVOX_RESOURCE_VERSION}/engine/README.md"
EOF

# -- Download Additional Packages ---
FROM mirror.gcr.io/ubuntu:22.04 AS download-additional-packages

# Download Additional Packages
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && \
    apt-get install -y zlib1g

# --- Runtime ---
FROM gcr.io/distroless/base-debian12 AS runtime-env
ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /opt/voicevox_engine

# Copy busybox
COPY --from=busybox:musl /bin/busybox /usr/local/bin/busybox
SHELL ["/usr/local/bin/busybox", "sh", "-c"]

# Copy gosu
COPY --from=tianon/gosu /gosu /usr/local/bin/

# Add non-root user
RUN <<EOF
    set -eux
    busybox addgroup -S user
    busybox adduser -S -G user user
    busybox chown -R user:user /opt/voicevox_engine
EOF

# Install Packages
COPY --from=download-env /usr/lib/x86_64-linux-gnu/libz.so.1 /usr/lib/x86_64-linux-gnu/libz.so.1

# Copy VOICEVOX ENGINE
COPY --from=download-env /opt/voicevox_engine /opt/voicevox_engine

# Copy Resource
COPY --from=download-env /work/README.md /opt/voicevox_engine/README.md

# Create container start shell
COPY --chmod=775 <<'EOF' /opt/entrypoint.sh
#!/usr/local/bin/busybox sh
set -eux

# Display README for engine
busybox cat /opt/voicevox_engine/README.md > /dev/stderr

exec gosu user /opt/voicevox_engine/run "$@"
EOF

ENTRYPOINT [ "/opt/entrypoint.sh" ]
CMD [ "--host", "0.0.0.0" ]

# Enable use_gpu
FROM runtime-env AS runtime-nvidia-env
CMD [ "--use_gpu", "--host", "0.0.0.0" ]
