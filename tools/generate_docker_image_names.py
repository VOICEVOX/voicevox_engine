"""
# Dockerリポジトリ名、バージョン文字列、カンマ区切りのプレフィックスを受け取り、
# バージョン文字列付きのDockerイメージ名を改行区切りで標準出力に出力する
#
# 例1
# $ python3 ./tools/generate_docker_image_names.py \
#   --repository "voicevox/voicevox_engine" \
#   --version "0.22.0" \
#   --prefix ",cpu,cpu-ubuntu22.04"
# voicevox/voicevox_engine:0.22.0
# voicevox/voicevox_engine:cpu-0.22.0
# voicevox/voicevox_engine:cpu-ubuntu22.04-0.22.0
#
# 例2
# $ python3 ./tools/generate_docker_image_names.py \
#   --repository "voicevox/voicevox_engine" \
#   --version "latest" \
#   --prefix "nvidia,nvidia-ubuntu22.04"
# voicevox/voicevox_engine:nvidia-latest
# voicevox/voicevox_engine:nvidia-ubuntu22.04-latest
#
# 例3
# $ python3 ./tools/generate_docker_image_names.py \
#   --repository "voicevox/voicevox_engine" \
#   --version "latest" \
#   --prefix ""
# voicevox/voicevox_engine:latest
"""

from argparse import ArgumentParser


def generate_docker_image_names(
    repository: str, version: str, comma_separated_prefix: str
) -> list[str]:
    """
    Dockerリポジトリ名、バージョン文字列、カンマ区切りのプレフィックスを受け取り、
    バージョン文字列付きのDockerイメージ名を配列で返す

    prefixが空文字列でない場合、"{prefix}-{バージョン文字列}"をタグにする
    - 例1: prefix="cpu", version="latest" -> "voicevox/voicevox_engine:cpu-latest"
    - 例2: prefix="nvidia-ubuntu22.04", version="0.22.0" -> "voicevox/voicevox_engine:nvidia-ubuntu22.04-0.22.0"

    prefixが空文字列の場合、"{バージョン文字列}"をタグにする

    - 例1: prefix="", version="latest" -> "voicevox/voicevox_engine:latest"
    - 例2: prefix="", version="0.22.0" -> "voicevox/voicevox_engine:0.22.0"

    Parameters
    ----------
    repository : str
        Dockerリポジトリ名（例: "voicevox/voicevox_engine"）
    version : str
        バージョン文字列（例: "0.22.0", "latest"）
    comma_separated_prefix : str
        カンマ区切りのプレフィックス（例: ",cpu,cpu-ubuntu22.04", "nvidia,nvidia-ubuntu22.04"

    Returns
    -------
    list[str]
        Dockerイメージ名の配列（例: ["voicevox/voicevox_engine:0.22.0", "voicevox/voicevox_engine:cpu-0.22.0", "voicevox/voicevox_engine:cpu-ubuntu22.04-0.22.0"]）
    """
    # カンマ区切りのタグ名を配列に変換
    # 例1: "" -> [""]
    # 例2: ",cpu,cpu-ubuntu22.04" -> ["", "cpu", "cpu-ubuntu22.04"]
    # 例3: "nvidia,nvidia-ubuntu22.04" -> ["nvidia", "nvidia-ubuntu22.04"]
    prefixes = comma_separated_prefix.split(",")

    # 戻り値の配列
    docker_image_names: list[str] = []

    for prefix in prefixes:
        if prefix:
            # プレフィックスが空文字でない場合、末尾にハイフンを付ける
            # 例: prefix="cpu" -> prefix="cpu-"
            prefix = f"{prefix}-"

        docker_image_names.append(f"{repository}:{prefix}{version}")

    return docker_image_names


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument(
        "--repository",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--version",
        type=str,
        default="latest",
        help="バージョン文字列。デフォルトブランチの場合、latest。",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default="",
        help="Dockerイメージのタグのカンマ区切りのプレフィックス",
    )

    args = parser.parse_args()

    repository: str = args.repository
    version: str = args.version
    comma_separated_prefix: str = args.prefix

    # Dockerイメージ名を生成
    docker_image_names = generate_docker_image_names(
        repository, version, comma_separated_prefix
    )

    # 標準出力に出力
    for docker_image_name in docker_image_names:
        print(docker_image_name)


if __name__ == "__main__":
    main()
