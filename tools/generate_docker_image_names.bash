#!/bin/bash

# Dockerリポジトリ名、バージョン文字列、カンマ区切りのプレフィックスを受け取り、
# バージョン文字列付きのDockerイメージ名を改行区切りで標準出力に出力する
#
# 例1
# $ ./tools/generate_docker_image_names.bash "voicevox/voicevox_engine" "0.22.0" ",cpu,cpu-ubuntu22.04"
# voicevox/voicevox_engine:0.22.0
# voicevox/voicevox_engine:cpu-0.22.0
# voicevox/voicevox_engine:cpu-ubuntu22.04-0.22.0
#
# 例2
# $ ./tools/generate_docker_image_names.bash "voicevox/voicevox_engine" "latest" "nvidia,nvidia-ubuntu22.04"
# voicevox/voicevox_engine:nvidia-latest
# voicevox/voicevox_engine:nvidia-ubuntu22.04-latest
#
# 例3
# $ ./tools/generate_docker_image_names.bash "voicevox/voicevox_engine" "latest" ""
# voicevox/voicevox_engine:latest

set -eux

if [ $# -lt 1 ]; then
  # 引数の数が1未満の場合、ヘルプを標準エラー出力に出力して終了する
  echo "Usage: $0 <repository> [version_or_latest] [comma_separated_prefixes]" 1>&2
  exit 1
fi

repository=$1
version_or_latest=${2:-latest}
comma_separated_prefixes=${3:-}

# カンマ区切りのタグ名を改行区切りに変換して、forループで反復できるようにする
# 例1: "" -> ("")
# 例2: ",cpu,cpu-ubuntu22.04" -> ("" "cpu" "cpu-ubuntu22.04")
# 例3: "nvidia,nvidia-ubuntu22.04" -> ("nvidia" "nvidia-ubuntu22.04")
IFS=',' read -r -a prefixes <<< "${comma_separated_prefixes}"

# prefixesが空（comma_separated_prefixesが空文字列）の場合、prefixesに空文字列を追加する
if [ ${#prefixes[@]} = 0 ]; then
  prefixes+=("")
fi

# バージョン文字列付きのタグ名を改行区切りで出力する
for prefix in "${prefixes[@]}"; do
  if [ -z "${prefix}" ]; then
    # prefixが空文字列の場合、"{バージョン文字列}"をタグにする
    # 例1: prefix="", version="latest" -> "voicevox/voicevox_engine:latest"
    # 例2: prefix="", version="0.22.0" -> "voicevox/voicevox_engine:0.22.0"
    echo "${repository}:${version_or_latest}"
  else
    # prefixが空文字列でない場合、"{prefix}-{バージョン文字列}"をタグにする
    # 例1: prefix="cpu", version="latest" -> "voicevox/voicevox_engine:cpu-latest"
    # 例2: prefix="nvidia-ubuntu22.04", version="0.22.0" -> "voicevox/voicevox_engine:nvidia-ubuntu22.04-0.22.0"
    echo "${repository}:${prefix}-${version_or_latest}"
  fi
done
