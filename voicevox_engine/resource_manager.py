"""
リソースファイルを管理する。
"""

import base64
import json
from hashlib import sha256
from pathlib import Path
from typing import Literal


class ResourceManagerError(Exception):
    def __init__(self, message: str):
        self.message = message


def b64encode_str(s: bytes) -> str:
    return base64.b64encode(s).decode("utf-8")


class ResourceManager:
    """
    リソースファイルのパスと、一意なハッシュ値の対応(filemap)を管理する。

    APIでリソースファイルを一意なURLとして返すときに使う。
    ついでにファイルをbase64文字列に変換することもできる。
    """

    def __init__(self, create_filemap_if_not_exist: bool) -> None:
        """
        Parameters
        ----------
        create_filemap_if_not_exist : bool
            `filemap.json`がない場合でも登録時にfilemapを生成するか(開発時を想定)
        """
        self._create_filemap_if_not_exist = create_filemap_if_not_exist
        self._path_to_hash: dict[Path, str] = {}
        self._hash_to_path: dict[str, Path] = {}

    def register_dir(self, resource_dir: Path) -> None:
        """ディレクトリをfilemapに登録する"""
        filemap_json = resource_dir / "filemap.json"
        if filemap_json.exists():
            data: dict[str, str] = json.loads(filemap_json.read_bytes())
            self._path_to_hash |= {resource_dir / k: v for k, v in data.items()}
        elif self._create_filemap_if_not_exist:
            self._path_to_hash |= {
                i: sha256(i.read_bytes()).digest().hex()
                for i in resource_dir.rglob("*")
                if i.is_file()
            }
        else:
            raise ResourceManagerError(f"{filemap_json}が見つかりません")

        self._hash_to_path |= {v: k for k, v in self._path_to_hash.items()}

    def resource_str(
        self,
        resource_path: Path,
        resource_format: Literal["base64", "hash"],
    ) -> str:
        """指定したリソースファイルのbase64文字列やハッシュ値を返す。"""
        # NOTE: 意図しないパスのファイルの結果を返さないようにする
        filehash = self._path_to_hash.get(resource_path)
        if filehash is None:
            raise ResourceManagerError(f"{resource_path}がfilemapに登録されていません")

        if resource_format == "base64":
            return b64encode_str(resource_path.read_bytes())
        return filehash

    def resource_path(self, filehash: str) -> Path:
        """指定したハッシュ値を持つリソースファイルのパスを返す。"""
        resource_path = self._hash_to_path.get(filehash)

        if resource_path is None:
            raise ResourceManagerError(f"'{filehash}'に対応するリソースがありません")
        return resource_path
