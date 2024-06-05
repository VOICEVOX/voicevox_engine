import base64
import json
from hashlib import sha256
from pathlib import Path
from typing import Literal


def b64encode_str(s: bytes) -> str:
    return base64.b64encode(s).decode("utf-8")


class ResourceManager:
    def __init__(self, is_development: bool) -> None:
        self._is_development = is_development
        self._path_to_hash: dict[Path, str] = {}
        self._hash_to_path: dict[str, Path] = {}

    def register_dir(self, resource_dir: Path) -> None:
        filemap_json = resource_dir / "filemap.json"
        if filemap_json.exists():
            data: dict[str, str] = json.loads(filemap_json.read_bytes())
            self._path_to_hash |= {resource_dir / k: v for k, v in data.items()}
        else:
            if self._is_development:
                self._path_to_hash |= {
                    i: sha256(i.read_bytes()).digest().hex()
                    for i in resource_dir.glob("**/*")
                    if i.is_file()
                }
            else:
                raise Exception(f"{filemap_json}が見つかりません")
        self._hash_to_path |= {v: k for k, v in self._path_to_hash.items()}

    def resource_str(
        self,
        resource_path: Path,
        base_url: str,
        resource_format: Literal["base64", "url"],
    ) -> str:
        if resource_format == "base64":
            return b64encode_str(resource_path.read_bytes())
        return f"{base_url}/{self._path_to_hash[resource_path]}"

    def resource_path(self, filehash: str) -> Path | None:
        return self._hash_to_path.get(filehash)
