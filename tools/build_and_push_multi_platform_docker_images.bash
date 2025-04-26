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
multi_platform_image_tags=$(
    uv run "${script_dir}/generate_docker_image_names.py" \
        --repository "${PUSH_IMAGE_REPOSITORY}" \
        --version "${VERSION_OR_LATEST}" \
        --prefix "${PUSH_MULTI_PLATFORM_IMAGE_PREFIXES}"
)

# AMD64のDockerイメージ名
amd64_image_tag=$(
    uv run "${script_dir}/generate_docker_image_names.py" \
        --repository "${PULL_IMAGE_REPOSITORY}" \
        --version "${VERSION_OR_LATEST}" \
        --prefix "${PULL_AMD64_IMAGE_PREFIX}"
)

# ARM64のDockerイメージ名
arm64_image_tag=$(
    uv run "${script_dir}/generate_docker_image_names.py" \
        --repository "${PULL_IMAGE_REPOSITORY}" \
        --version "${VERSION_OR_LATEST}" \
        --prefix "${PULL_ARM64_IMAGE_PREFIX}"
)

# タグを除くイメージ名
amd64_image_name=$(echo "${amd64_image_tag}" | cut -d: -f1)
arm64_image_name=$(echo "${arm64_image_tag}" | cut -d: -f1)

# 単一プラットフォームイメージのダイジェスト
amd64_image_digest=$(
    docker manifest inspect "${amd64_image_tag}" |
        jq -r '.manifests[] | select(.platform.architecture=="amd64") | .digest'
)
if [ -z "${amd64_image_digest}" ]; then
    echo "::error::AMD64イメージのダイジェストを取得できませんでした"
    exit 1
fi

arm64_image_digest=$(
    docker manifest inspect "${arm64_image_tag}" |
        jq -r '.manifests[] | select(.platform.architecture=="arm64") | .digest'
)
if [ -z "${arm64_image_digest}" ]; then
    echo "::error::ARM64イメージのダイジェストを取得できませんでした"
    exit 1
fi

# マルチプラットフォームイメージのマニフェストリストを作成
(
    IFS=$'\n'
    for multi_platform_image_tag in $multi_platform_image_tags; do
        # マニフェストリストを作成
        docker manifest create \
            "${multi_platform_image_tag}" \
            "${amd64_image_name}@${amd64_image_digest}" \
            "${arm64_image_name}@${arm64_image_digest}"

        # プラットフォーム情報を追加
        docker manifest annotate \
            "${multi_platform_image_tag}" \
            "${amd64_image_name}@${amd64_image_digest}" \
            --os linux \
            --arch amd64

        docker manifest annotate \
            "${multi_platform_image_tag}" \
            "${arm64_image_name}@${arm64_image_digest}" \
            --os linux \
            --arch arm64 \
            --variant v8
    done
)

# push
(
    IFS=$'\n'
    for multi_platform_image_tag in ${multi_platform_image_tags}; do
        docker manifest push "${multi_platform_image_tag}"
    done
)
