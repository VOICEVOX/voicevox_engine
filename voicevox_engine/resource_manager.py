"""
URLから取得可能なリソースの管理

アップデートでリソースの変更が反映されるようにURLはハッシュ値から生成する
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
        self._create_filemap_if_not_exist = create_filemap_if_not_exist
        self._path_to_hash: dict[Path, str] = {}
        self._hash_to_path: dict[str, Path] = {}

    def register_dir(self, resource_dir: Path) -> None:
        """ディレクトリをfilemapに登録する"""
        filemap_json = resource_dir / "filemap.json"
        if filemap_json.exists():
            data: dict[str, str] = json.loads(filemap_json.read_bytes())
            self._path_to_hash |= {resource_dir / k: v for k, v in data.items()}
        else:
            if self._create_filemap_if_not_exist:
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
        base_url: str,
        resource_format: Literal["base64", "url"],
    ) -> str:
        filehash = self._path_to_hash.get(resource_path)
        if filehash is not None:
            if resource_format == "base64":
                return b64encode_str(resource_path.read_bytes())
            return f"{base_url}/{filehash}"
        raise ResourceManagerError(f"{resource_path}がfilemapに登録されていません")

    def resource_path(self, filehash: str) -> Path | None:
        return self._hash_to_path.get(filehash)
