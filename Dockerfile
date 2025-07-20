# syntax=docker/dockerfile:1

ARG BASE_IMAGE=mirror.gcr.io/ubuntu:22.04

# === ダウンロードフェーズ ===
FROM ${BASE_IMAGE} AS download-engine-env
ARG DEBIAN_FRONTEND=noninteractive
WORKDIR /work

RUN apt-get update && apt-get install -y \
    curl \
    p7zip-full \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

ARG VOICEVOX_ENGINE_REPOSITORY
ARG VOICEVOX_ENGINE_VERSION
ARG VOICEVOX_ENGINE_TARGET

RUN set -eux; \
    LIST_NAME=voicevox_engine-${VOICEVOX_ENGINE_TARGET}-${VOICEVOX_ENGINE_VERSION}.7z.txt; \
    curl -fLO --retry 3 --retry-delay 5 "https://github.com/${VOICEVOX_ENGINE_REPOSITORY}/releases/download/${VOICEVOX_ENGINE_VERSION}/${LIST_NAME}"; \
    awk -v "repo=${VOICEVOX_ENGINE_REPOSITORY}" -v "tag=${VOICEVOX_ENGINE_VERSION}" \
        '{ print "url = \"https://github.com/" repo "/releases/download/" tag "/" $0 "\"\noutput = \"" $0 "\"" }' \
        "${LIST_NAME}" > ./curl.txt; \
    curl -fL --retry 3 --retry-delay 5 --parallel --config ./curl.txt; \
    7zr x "$(head -1 "./${LIST_NAME}")"; \
    mv ./${VOICEVOX_ENGINE_TARGET} /opt/voicevox_engine; \
    rm -rf ./*

# === ランタイムフェーズ ===
FROM ${BASE_IMAGE} AS runtime-env
ARG DEBIAN_FRONTEND=noninteractive
WORKDIR /opt/voicevox_engine

RUN apt-get update && apt-get install -y \
    curl \
    gosu \
    git \
    cmake \
    build-essential \
    python3-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 一般ユーザー作成（gosu用）
RUN useradd --create-home user

# VOICEVOX ENGINE 本体
COPY --from=download-engine-env /opt/voicevox_engine /opt/voicevox_engine

# コアライブラリ（libcore.so）をコピー（必要に応じてパス調整）
COPY ./voicevox_engine/core/bin/linux/libcore.so ./voicevox_engine/core/libcore.so

# READMEを取得
ARG VOICEVOX_RESOURCE_VERSION=0.24.1
RUN curl -fLo "/opt/voicevox_engine/README.md" --retry 3 --retry-delay 5 \
    "https://raw.githubusercontent.com/VOICEVOX/voicevox_resource/${VOICEVOX_RESOURCE_VERSION}/engine/README.md"

# Pythonパッケージインストール（requirements.txtは同じディレクトリにある想定）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 起動スクリプト
COPY --chmod=775 <<EOF /entrypoint.sh
#!/bin/bash
set -eux
cat /opt/voicevox_engine/README.md > /dev/stderr
exec "\$@"
EOF

ENTRYPOINT [ "/entrypoint.sh" ]
CMD [ "gosu", "user", "/opt/voicevox_engine/run", "--host", "0.0.0.0" ]

# === GPU対応バージョン（必要に応じて使用） ===
FROM runtime-env AS runtime-nvidia-env
CMD [ "gosu", "user", "/opt/voicevox_engine/run", "--use_gpu", "--host", "0.0.0.0" ]
