"""
Dockerイメージ名を生成する。

Dockerリポジトリ名、バージョン、カンマ区切りのプレフィックスを受け取り、Dockerイメージ名を改行区切りで標準出力に出力する。

例
$ uv run ./tools/generate_docker_image_names.py \
  --repository "REPO" \
  --version "VER" \
  --prefix ",A,B"
REPO:VER
REPO:A-VER
REPO:B-VER

$ uv run ./tools/generate_docker_image_names.py \
  --repository "REPO" \
  --version "VER" \
  --prefix ""
REPO:VER
"""

from argparse import ArgumentParser


def _generate_docker_image_names(
    repository: str,
    version: str,
    comma_separated_prefix: str,
) -> set[str]:
    """
    Dockerイメージ名を生成する。

    Dockerリポジトリ名、バージョン、カンマ区切りのプレフィックスを受け取り、Dockerイメージ名をセットで返す。

    prefixが空文字列でない場合、"{prefix}-{version}"をタグにする

    - 例: repository="REPO", version="VER", prefix="A" -> "REPO:A-VER"

    prefixが空文字列の場合、"{version}"をタグにする

    - 例: repository="REPO", version="VER",  prefix="" -> "REPO:VER"

    Parameters
    ----------
    repository : str
        Dockerリポジトリ名
    version : str
        バージョン
    comma_separated_prefix : str
        カンマ区切りのプレフィックス

    Returns
    -------
    set[str]
        Dockerイメージ名のセット。

    Examples
    --------
    >>> _generate_docker_image_names(
    ...     repository="voicevox/voicevox_engine",
    ...     version="0.22.0-preview.1",
    ...     comma_separated_prefix=",cpu,cpu-ubuntu22.04",
    ... )
    {'voicevox/voicevox_engine:0.22.0-preview.1',
     'voicevox/voicevox_engine:cpu-0.22.0-preview.1',
     'voicevox/voicevox_engine:cpu-ubuntu22.04-0.22.0-preview.1'}
    """
    # カンマ区切りのタグ名を配列に変換
    prefixes = comma_separated_prefix.split(",")

    # 戻り値のセット
    docker_image_names: set[str] = set()

    for prefix in prefixes:
        # プレフィックスが空文字列でない場合、末尾にハイフンを付ける
        if prefix:
            prefix = f"{prefix}-"
        docker_image_names.add(f"{repository}:{prefix}{version}")

    return docker_image_names


def main() -> None:
    """コマンドライン引数からDockerイメージ名を生成し標準出力へ出力する。"""
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
        required=True,
        help='バージョン（例: "0.22.0-preview.1", "0.22.0"）',
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
    docker_image_names = _generate_docker_image_names(
        repository=repository,
        version=version,
        comma_separated_prefix=comma_separated_prefix,
    )

    # 標準出力に出力
    for docker_image_name in docker_image_names:
        print(docker_image_name)


if __name__ == "__main__":
    main()
