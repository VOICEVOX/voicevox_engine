import json
from base64 import b64encode
from pathlib import Path

from pydantic import BaseModel

from .EngineManifest import EngineManifest, LicenseInfo, UpdateInfo


class FeatureSupportJson(BaseModel):
    """`engine_manifest.json` の機能サポート状況"""

    type: str
    value: bool
    name: str


class SupportedFeaturesJson(BaseModel):
    """`engine_manifest.json` のサポート機能一覧"""

    adjust_mora_pitch: FeatureSupportJson
    adjust_phoneme_length: FeatureSupportJson
    adjust_speed_scale: FeatureSupportJson
    adjust_pitch_scale: FeatureSupportJson
    adjust_intonation_scale: FeatureSupportJson
    adjust_volume_scale: FeatureSupportJson
    interrogative_upspeak: FeatureSupportJson
    synthesis_morphing: FeatureSupportJson
    sing: FeatureSupportJson
    manage_library: FeatureSupportJson


class EngineManifestJson(BaseModel):
    """`engine_manifest.json` のコンテンツ"""

    manifest_version: str
    name: str
    brand_name: str
    uuid: str
    version: str
    url: str
    command: str
    port: int
    icon: str
    default_sampling_rate: int
    frame_rate: float
    terms_of_service: str
    update_infos: str
    dependency_licenses: str
    supported_features: SupportedFeaturesJson


def load_manifest(manifest_path: Path) -> EngineManifest:
    """エンジンマニフェストを指定ファイルから読み込む。"""

    root_dir = manifest_path.parent
    manifest = EngineManifestJson.parse_file(manifest_path).dict()
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
