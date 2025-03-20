"""
Dockerリポジトリ名、バージョン文字列、カンマ区切りのプレフィックスを受け取り、
バージョン文字列付きのDockerイメージ名を改行区切りで標準出力に出力する

例
$ python3 ./tools/generate_docker_image_names.py \
  --repository "REPO" \
  --version "VER" \
  --prefix ",A,B"
REPO:VER
REPO:A-VER
REPO:B-VER

$ python3 ./tools/generate_docker_image_names.py \
  --repository "REPO" \
  --version "VER" \
  --prefix ""
REPO:VER
"""

from argparse import ArgumentParser


def generate_docker_image_names(
    repository: str,
    version: str,
    comma_separated_prefix: str,
) -> list[str]:
    """
    Dockerリポジトリ名、バージョン文字列、カンマ区切りのプレフィックスを受け取り、
    バージョン文字列付きのDockerイメージ名を配列で返す

    prefixが空文字列でない場合、"{prefix}-{version}"をタグにする

    - 例: repository="REPO", version="VER", prefix="A" -> "REPO:A-VER"

    prefixが空文字列の場合、"{version}"をタグにする

    - 例: repository="REPO", version="VER",  prefix="" -> "REPO:VER"

    Parameters
    ----------
    repository : str
        Dockerリポジトリ名
    version : str
        バージョン文字列
    comma_separated_prefix : str
        カンマ区切りのプレフィックス

    Returns
    -------
    list[str]
        Dockerイメージ名の配列。

    Examples
    --------
    >>> generate_docker_image_names("voicevox/voicevox_engine", "0.22.0", "cpu,cpu-ubuntu22.04")
    ['voicevox/voicevox_engine:0.22.0',
     'voicevox/voicevox_engine:cpu-0.22.0',
     'voicevox/voicevox_engine:cpu-ubuntu22.04-0.22.0']
    """
    # カンマ区切りのタグ名を配列に変換
    prefixes = comma_separated_prefix.split(",")

    # 戻り値の配列
    docker_image_names: list[str] = []

    for prefix in prefixes:
        # プレフィックスが空文字列でない場合、末尾にハイフンを付ける
        if prefix:
            prefix = f"{prefix}-"
        docker_image_names.append(f"{repository}:{prefix}{version}")

    return docker_image_names


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument(
        "--repository",
        type=str,
        required=True,
        help="Dockerリポジトリ名（例: voicevox/voicevox_engine）",
    )
    parser.add_argument(
        "--version",
        type=str,
        default="latest",
        help='バージョン文字列（例: "0.22.0", "latest"）',
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default="",
        help='カンマ区切りのプレフィックス（例: ",cpu,cpu-ubuntu22.04", "nvidia,nvidia-ubuntu22.04"）',
    )

    args = parser.parse_args()

    repository: str = args.repository
    version: str = args.version
    comma_separated_prefix: str = args.prefix

    # Dockerイメージ名を生成
    docker_image_names = generate_docker_image_names(
        repository=repository,
        version=version,
        comma_separated_prefix=comma_separated_prefix,
    )

    # 標準出力に出力
    for docker_image_name in docker_image_names:
        print(docker_image_name)


if __name__ == "__main__":
    main()
