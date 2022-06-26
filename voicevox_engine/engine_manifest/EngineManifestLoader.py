import json
from base64 import b64encode
from pathlib import Path

from .EngineManifest import EngineManifest, LicenseInfo, UpdateInfo


class EngineManifestLoader:
    def __init__(self, assets_dir: Path):
        self.assets_dir = assets_dir

    def load_manifest(self) -> EngineManifest:
        manifest = EngineManifest(
            **json.load((self.assets_dir / "manifest.json").open(encoding="utf-8")),
            icon=b64encode((self.assets_dir / "icon.png").read_bytes()).decode("utf-8"),
            terms_of_service=(self.assets_dir / "terms_of_service.md").read_text(
                encoding="utf-8"
            ),
            update_infos=[
                UpdateInfo(**update_info)
                for update_info in json.load(
                    (self.assets_dir / "update_infos.json").open(encoding="utf-8")
                )
            ],
            dependency_licenses=[
                LicenseInfo(**license_info)
                for license_info in json.load(
                    (self.assets_dir / "dependency_licenses.json").open(
                        encoding="utf-8"
                    )
                )
            ],
        )
        return manifest
