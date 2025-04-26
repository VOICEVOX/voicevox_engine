#!/bin/bash

# 事前にビルドされた単一プラットフォームDockerイメージを組み合わせて、
# マルチプラットフォームDockerイメージを作成してpushする
# NOTE: 単一プラットフォームイメージはマニフェストリストである必要がある

set -eu

if [ ! -v PULL_IMAGE_REPOSITORY ]; then # pullするDockerイメージリポジトリ
    echo "::error::PULL_IMAGE_REPOSITORYが未定義です"
    exit 1
fi

if [ ! -v PUSH_IMAGE_REPOSITORY ]; then # pushするDockerイメージリポジトリ
    echo "::error::PUSH_IMAGE_REPOSITORYが未定義です"
    exit 1
fi

if [ ! -v VERSION_OR_LATEST ]; then # バージョンまたはlatest
    echo "::error::VERSION_OR_LATESTが未定義です"
    exit 1
fi

if [ ! -v PULL_AMD64_IMAGE_PREFIX ]; then # pullするAMD64イメージのプレフィックス
    echo "::error::PULL_AMD64_IMAGE_PREFIXが未定義です"
    exit 1
fi

if [ ! -v PULL_ARM64_IMAGE_PREFIX ]; then # pullするARM64イメージのプレフィックス
    echo "::error::PULL_ARM64_IMAGE_PREFIXが未定義です"
    exit 1
fi

if [ ! -v PUSH_MULTI_PLATFORM_IMAGE_PREFIXES ]; then # pushするマルチプラットフォームイメージのプレフィックス（カンマ区切り）
    echo "::error::PUSH_MULTI_PLATFORM_IMAGE_PREFIXESが未定義です"
    exit 1
fi

script_dir=$(dirname "${0}")

# ビルドするマルチプラットフォームDockerイメージ名のリスト
push_multi_platform_image_tags=$(
    uv run "${script_dir}/generate_docker_image_names.py" \
        --repository "${PUSH_IMAGE_REPOSITORY}" \
        --version "${VERSION_OR_LATEST}" \
        --prefix "${PUSH_MULTI_PLATFORM_IMAGE_PREFIXES}"
)

# AMD64のDockerイメージ名
pull_amd64_image_tag=$(
    uv run "${script_dir}/generate_docker_image_names.py" \
        --repository "${PULL_IMAGE_REPOSITORY}" \
        --version "${VERSION_OR_LATEST}" \
        --prefix "${PULL_AMD64_IMAGE_PREFIX}"
)

# ARM64のDockerイメージ名
pull_arm64_image_tag=$(
    uv run "${script_dir}/generate_docker_image_names.py" \
        --repository "${PULL_IMAGE_REPOSITORY}" \
        --version "${VERSION_OR_LATEST}" \
        --prefix "${PULL_ARM64_IMAGE_PREFIX}"
)

# Dockerリポジトリ名（タグを除くイメージ名）
pull_amd64_repository=$(echo "${pull_amd64_image_tag}" | cut -d: -f1)
pull_arm64_repository=$(echo "${pull_arm64_image_tag}" | cut -d: -f1)

# 単一プラットフォームイメージのダイジェスト
pull_amd64_image_digest=$(
    docker manifest inspect "${pull_amd64_image_tag}" |
        jq -r '.manifests[] | select(.platform.architecture=="amd64") | .digest'
)
if [ -z "${pull_amd64_image_digest}" ]; then
    echo "::error::AMD64イメージのダイジェストを取得できませんでした"
    exit 1
fi

pull_arm64_image_digest=$(
    docker manifest inspect "${pull_arm64_image_tag}" |
        jq -r '.manifests[] | select(.platform.architecture=="arm64") | .digest'
)
if [ -z "${pull_arm64_image_digest}" ]; then
    echo "::error::ARM64イメージのダイジェストを取得できませんでした"
    exit 1
fi

# レジストリ名・レジストリを除くリポジトリ名
# NOTE: スラッシュ数が1つ以下の場合、レジストリはDocker Hub
pull_amd64_repository_slash_count=$(grep --only-matching "/" <<< "${pull_amd64_repository}" | wc -l)
if [ "${pull_amd64_repository_slash_count}" -le 1 ]; then
    pull_amd64_image_registry=docker.io
else
    pull_amd64_image_registry=$(echo "${pull_amd64_repository}" | cut -d/ -f1)
fi

pull_arm64_repository_slash_count=$(grep --only-matching "/" <<< "${pull_arm64_repository}" | wc -l)
if [ "${pull_arm64_repository_slash_count}" -le 1 ]; then
    pull_arm64_image_registry=docker.io
else
    pull_arm64_image_registry=$(echo "${pull_arm64_repository}" | cut -d/ -f1)
fi

push_image_repository_slash_count=$(grep --only-matching "/" <<< "${PUSH_IMAGE_REPOSITORY}" | wc -l)
if [ "${push_image_repository_slash_count}" -le 1 ]; then
    push_image_registry=docker.io
    push_image_repository_without_registry="${PUSH_IMAGE_REPOSITORY}"
else
    push_image_registry=$(echo "${PUSH_IMAGE_REPOSITORY}" | cut -d/ -f1)
    push_image_repository_without_registry=$(echo "${PUSH_IMAGE_REPOSITORY}" | cut -d/ -f2-)
fi

# 仮のイメージ名を作成
# NOTE: レジストリが異なるイメージをマニフェストリストに追加することはできないため、
# レジストリが異なる場合、push先のリポジトリに仮のタグを作成する
push_amd64_image_name="${push_image_registry}/${push_image_repository_without_registry}:temp-amd64"
if [ "${pull_amd64_image_registry}" != "${push_image_registry}" ]; then
    docker pull "${pull_amd64_image_tag}"
    docker tag "${pull_amd64_image_tag}" "${push_amd64_image_name}"
fi

push_arm64_image_name="${push_image_registry}/${push_image_repository_without_registry}:temp-arm64"
if [ "${pull_arm64_image_registry}" != "${push_image_registry}" ]; then
    docker pull "${pull_arm64_image_tag}"
    docker tag "${pull_arm64_image_tag}" "${push_arm64_image_name}"
fi

# マルチプラットフォームイメージのマニフェストリストを作成してpush
(
    IFS=$'\n'
    for push_multi_platform_image_tag in $push_multi_platform_image_tags; do
        # マニフェストリストを作成
        docker manifest create "${push_multi_platform_image_tag}" \
            "${push_amd64_image_name}" \
            "${push_arm64_image_name}"

        # プラットフォーム情報を追加
        docker manifest annotate \
            "${push_multi_platform_image_tag}" \
            "${push_amd64_image_name}" \
            --os linux \
            --arch amd64

        docker manifest annotate \
            "${push_multi_platform_image_tag}" \
            "${push_arm64_image_name}" \
            --os linux \
            --arch arm64 \
            --variant v8

        docker manifest push "${push_multi_platform_image_tag}"
    done
)
