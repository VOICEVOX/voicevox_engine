import json
from base64 import b64encode
from pathlib import Path

from .EngineManifest import EngineManifest, LicenseInfo, UpdateInfo


class EngineManifestLoader:
    def __init__(self, assets_dir: Path):
        self.assets_dir = assets_dir

    def load_manifest(self) -> EngineManifest:
        manifest = json.loads(
            (self.assets_dir / "manifest.json").read_text(encoding="utf-8")
        )

        manifest = EngineManifest(
            manifest_version=manifest["manifest_version"],
            name=manifest["name"],
            uuid=manifest["uuid"],
            url=manifest["url"],
            default_sampling_rate=manifest["default_sampling_rate"],
            icon=b64encode((self.assets_dir / manifest["icon"]).read_bytes()).decode(
                "utf-8"
            ),
            terms_of_service=(self.assets_dir / manifest["terms_of_service"]).read_text(
                "utf-8"
            ),
            update_infos=[
                UpdateInfo(**update_info)
                for update_info in json.loads(
                    (self.assets_dir / manifest["update_infos"]).read_text("utf-8")
                )
            ],
            dependency_licenses=[
                LicenseInfo(**license_info)
                for license_info in json.loads(
                    (self.assets_dir / manifest["dependency_licenses"]).read_text(
                        "utf-8"
                    )
                )
            ],
        )
        return manifest
