#!/bin/bash

set -eu

if [ ! -v IMAGE_NAME ]; then # Dockerイメージ名
    echo "IMAGE_NAMEが未定義です"
    exit 1
fi

if [ ! -v VERSION_OR_LATEST ]; then # バージョンまたはlatest
    echo "VERSION_OR_LATESTが未定義です"
    exit 1
fi

if [ ! -v MANIFEST_LIST_PREFIXES ]; then # pushするマルチプラットフォームマニフェストリストのプレフィックス（カンマ区切り）
    echo "MANIFEST_LIST_PREFIXESが未定義です"
    exit 1
fi

if [ ! -v AMD64_MANIFEST_PREFIX ]; then # pullするAMD64マニフェストのプレフィックス
    echo "AMD64_MANIFEST_PREFIXが未定義です"
    exit 1
fi

if [ ! -v ARM64_MANIFEST_PREFIX ]; then # pullするARM64マニフェストのプレフィックス
    echo "ARM64_MANIFEST_PREFIXが未定義です"
    exit 1
fi

is_signed

script_dir=$(dirname "${0}")

# ビルドするマルチプラットフォームDockerイメージ名のリスト
manifest_list_tags=$(
  python3 "${script_dir}/generate_docker_image_names.py" \
    --repository "${IMAGE_NAME}" \
    --version "${VERSION_OR_LATEST}" \
    --prefix "${MANIFEST_LIST_PREFIXES}"
)

# AMD64のDockerイメージ名
amd64_image_tag=$(
  python3 "${script_dir}/generate_docker_image_names.py" \
    --repository "${IMAGE_NAME}" \
    --version "${VERSION_OR_LATEST}" \
    --prefix "${AMD64_MANIFEST_PREFIX}"
)

# ARM64のDockerイメージ名
arm64_image_tag=$(
  python3 "${script_dir}/generate_docker_image_names.py" \
    --repository "${IMAGE_NAME}" \
    --version "${VERSION_OR_LATEST}" \
    --prefix "${ARM64_MANIFEST_PREFIX}"
)

# タグを除くイメージ名
amd64_image_name=$(echo "${amd64_image_tag}" | cut -d: -f1)
arm64_image_name=$(echo "${arm64_image_tag}" | cut -d: -f1)

# 単一プラットフォームイメージのダイジェスト（sha256:digest 形式）
amd64_image_digest=$(
  docker manifest inspect "${amd64_image_tag}" \
  | jq -r '.manifests[] | select(.platform.architecture=="amd64") | .digest'
)
if [ -z "${amd64_image_digest}" ]; then
  echo "::error::AMD64イメージのダイジェストを取得できませんでした"
  exit 1
fi

arm64_image_digest=$(
  docker manifest inspect "${arm64_image_tag}" \
  | jq -r '.manifests[] | select(.platform.architecture=="arm64") | .digest'
)
if [ -z "${arm64_image_digest}" ]; then
  echo "::error::ARM64イメージのダイジェストを取得できませんでした"
  exit 1
fi

IFS=$'\n'
for manifest_list_tag in $manifest_list_tags; do
  # イメージ名とダイジェストを指定して、新規のマニフェストリストを作成
  docker manifest create \
    "${manifest_list_tag}" \
    "${amd64_image_name}@${amd64_image_digest}" \
    "${arm64_image_name}@${arm64_image_digest}"

  # マニフェストにプラットフォーム情報を追加
  docker manifest annotate \
    "${manifest_list_tag}" \
    "${amd64_image_name}@${amd64_image_digest}" \
    --os linux \
    --arch amd64

  docker manifest annotate \
    "${manifest_list_tag}" \
    "${arm64_image_name}@${arm64_image_digest}" \
    --os linux \
    --arch arm64 \
    --variant v8
done

# マニフェストリストをpushする
IFS=$'\n'
for manifest_list_tag in ${manifest_list_tags}; do
  docker manifest push "${manifest_list_tag}"
done
