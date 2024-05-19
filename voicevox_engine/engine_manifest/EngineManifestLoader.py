"""エンジンマニフェストの読み込み"""

import json
from base64 import b64encode
from pathlib import Path

from .EngineManifest import EngineManifest, LicenseInfo, UpdateInfo


def load_manifest(manifest_path: Path) -> EngineManifest:
    """エンジンマニフェストを指定ファイルから読み込む。"""

    root_dir = manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return EngineManifest(
        manifest_version=manifest["manifest_version"],
        name=manifest["name"],
        brand_name=manifest["brand_name"],
        uuid=manifest["uuid"],
        url=manifest["url"],
        default_sampling_rate=manifest["default_sampling_rate"],
        frame_rate=manifest["frame_rate"],
        icon=b64encode((root_dir / manifest["icon"]).read_bytes()).decode("utf-8"),
        terms_of_service=(root_dir / manifest["terms_of_service"]).read_text("utf-8"),
        update_infos=[
            UpdateInfo(**update_info)
            for update_info in json.loads(
                (root_dir / manifest["update_infos"]).read_text("utf-8")
            )
        ],
        # supported_vvlib_manifest_versionを持たないengine_manifestのために
        # キーが存在しない場合はNoneを返すgetを使う
        supported_vvlib_manifest_version=manifest.get(
            "supported_vvlib_manifest_version"
        ),
        dependency_licenses=[
            LicenseInfo(**license_info)
            for license_info in json.loads(
                (root_dir / manifest["dependency_licenses"]).read_text("utf-8")
            )
        ],
        supported_features={
            key: item["value"] for key, item in manifest["supported_features"].items()
        },
    )
