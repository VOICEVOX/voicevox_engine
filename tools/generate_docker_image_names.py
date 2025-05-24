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

$ uv run ./tools/generate_docker_image_names.py \
  --repository "REPO" \
  --version "VER" \
  --prefix ",A,B" \
  --with_latest
REPO:VER
REPO:latest
REPO:A-VER
REPO:A-latest
REPO:B-VER
REPO:B-latest

$ uv run ./tools/generate_docker_image_names.py \
  --repository "REPO" \
  --version "VER" \
  --prefix "" \
  --with_latest
REPO:VER
REPO:latest
"""

from argparse import ArgumentParser


def _generate_docker_image_tags(
    version: str,
    comma_separated_prefix: str,
    with_latest: bool,
) -> set[str]:
    """
    Dockerイメージタグを生成する。

    バージョン、カンマ区切りのプレフィックスを受け取り、タグをセットで返す。

    prefixが空文字列でない場合、"{prefix}-{version}"をタグにする

    - 例: version="VER", prefix="A" -> "A-VER"

    prefixが空文字列の場合、"{version}"をタグにする

    - 例: version="VER",  prefix="" -> "VER"

    Parameters
    ----------
    version : str
        バージョン
    comma_separated_prefix : str
        カンマ区切りのプレフィックス
    with_latest : bool
        バージョンをlatestに置き換えたタグを追加する

    Returns
    -------
    set[str]
        Dockerイメージタグのセット。

    Examples
    --------
    >>> _generate_docker_image_tags(
    ...     version="0.22.0-preview.1",
    ...     comma_separated_prefix=",cpu,cpu-ubuntu22.04",
    ...     with_latest=False,
    ... )
    {'0.22.0-preview.1',
     'cpu-0.22.0-preview.1',
     'cpu-ubuntu22.04-0.22.0-preview.1'}
    >>> _generate_docker_image_tags(
    ...     version="0.22.0",
    ...     comma_separated_prefix=",cpu,cpu-ubuntu22.04",
    ...     with_latest=True,
    ... )
    {'0.22.0',
     'latest',
     'cpu-0.22.0',
     'cpu-latest',
     'cpu-ubuntu22.04-0.22.0',
     'cpu-ubuntu22.04-latest'}
    """
    # カンマ区切りのタグ名を配列に変換
    prefixes = comma_separated_prefix.split(",")

    # 戻り値のセット
    tags: set[str] = set()

    for prefix in prefixes:
        # プレフィックスが空文字列でない場合、末尾にハイフンを付ける
        if prefix:
            prefix = f"{prefix}-"
        tags.add(f"{prefix}{version}")

        if with_latest:
            tags.add(f"{prefix}latest")

    return tags


def _create_docker_image_names(
    repository: str,
    tags: list[str],
) -> list[str]:
    """
    Dockerイメージ名を作成する。

    Dockerリポジトリ名、Dockerタグ名のリストを受け取り、Dockerイメージ名を配列で返す。

    Parameters
    ----------
    repository : str
        Dockerリポジトリ名
    tags : list[str]
        Dockerイメージタグのリスト

    Returns
    -------
    list[str]
        Dockerイメージ名の配列。

    Examples
    --------
    >>> _create_docker_image_names(
    ...     repository="voicevox/voicevox_engine",
    ...     tags=[
    ...         "0.22.0-preview.1",
    ...         "cpu-0.22.0-preview.1",
    ...         "cpu-ubuntu22.04-0.22.0-preview.1",
    ...     ],
    ... )
    ['voicevox/voicevox_engine:0.22.0-preview.1',
     'voicevox/voicevox_engine:cpu-0.22.0-preview.1',
     'voicevox/voicevox_engine:cpu-ubuntu22.04-0.22.0-preview.1']
    """
    # 戻り値の配列
    docker_image_names: list[str] = []

    for tag in tags:
        # Dockerイメージ名を生成
        docker_image_name = f"{repository}:{tag}"
        docker_image_names.append(docker_image_name)

    return docker_image_names


def _generate_docker_image_names(
    repository: str,
    version: str,
    comma_separated_prefix: str,
    with_latest: bool,
) -> set[str]:
    """
    Dockerイメージ名を生成する。

    Dockerリポジトリ名、バージョン、カンマ区切りのプレフィックスを受け取り、Dockerイメージ名をセットで返す。

    Parameters
    ----------
    repository : str
        Dockerリポジトリ名
    version : str
        バージョン
    comma_separated_prefix : str
        カンマ区切りのプレフィックス
    with_latest : bool
        バージョンをlatestに置き換えたタグを追加する

    Returns
    -------
    set[str]
        Dockerイメージ名のセット。
    """
    tags = _generate_docker_image_tags(
        version=version,
        comma_separated_prefix=comma_separated_prefix,
        with_latest=with_latest,
    )
    return set(
        _create_docker_image_names(
            repository=repository,
            tags=list(tags),
        )
    )


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
    parser.add_argument(
        "--with_latest",
        action="store_true",
        help="バージョンをlatestに置き換えたタグを追加する",
    )

    args = parser.parse_args()

    repository: str = args.repository
    version: str = args.version
    comma_separated_prefix: str = args.prefix
    with_latest: bool = args.with_latest

    # Dockerイメージ名を生成
    docker_image_names = _generate_docker_image_names(
        repository=repository,
        version=version,
        comma_separated_prefix=comma_separated_prefix,
        with_latest=with_latest,
    )

    # 標準出力に出力
    for docker_image_name in docker_image_names:
        print(docker_image_name)


if __name__ == "__main__":
    main()
