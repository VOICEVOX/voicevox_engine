"""エンジンマニフェスト関連の処理"""

# マルチエンジン環境下においては、エンジンのバージョンがエディタのバージョンより
# 古くなる可能性が十分に考えられる。その場合、エディタ側がEngineManifestの情報不足によって
# エラーを吐いて表示が崩壊する可能性がある。これを防止するため、EngineManifest関連の定義を
# 変更する際は、Optionalにする必要があることに留意しなければならない。

from pathlib import Path
from typing import Self, TypeAlias

from pydantic import BaseModel

EngineName: TypeAlias = str
BrandName: TypeAlias = str


class _FeatureSupportJson(BaseModel):
    """`engine_manifest.json` の機能サポート状況"""

    type: str
    value: bool
    name: str


class _SupportedFeaturesJson(BaseModel):
    """`engine_manifest.json` のサポート機能一覧"""

    adjust_mora_pitch: _FeatureSupportJson
    adjust_phoneme_length: _FeatureSupportJson
    adjust_speed_scale: _FeatureSupportJson
    adjust_pitch_scale: _FeatureSupportJson
    adjust_intonation_scale: _FeatureSupportJson
    adjust_volume_scale: _FeatureSupportJson
    interrogative_upspeak: _FeatureSupportJson
    synthesis_morphing: _FeatureSupportJson
    sing: _FeatureSupportJson
    manage_library: _FeatureSupportJson


class _EngineManifestJson(BaseModel):
    """`engine_manifest.json` のコンテンツ"""

    manifest_version: str
    name: EngineName
    brand_name: BrandName
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
    supported_features: _SupportedFeaturesJson


class EngineManifestInternal(_EngineManifestJson):
    """VOICEVOX ENGINE 内部向けのエンジンマニフェスト"""

    root: Path  # エンジンマニフェストの親ディレクトリのパス。マニフェストの `.icon` 等はここをルートとする相対パスで記述されている。

    @classmethod
    def from_file(cls, manifest_path: Path) -> Self:
        """指定ファイルからインスタンスを生成する。"""
        manifest = _EngineManifestJson.model_validate_json(manifest_path.read_bytes())
        manifest_root = manifest_path.parent
        return cls(root=manifest_root, **manifest.model_dump())


def load_manifest(manifest_path: Path) -> EngineManifestInternal:
    """エンジンマニフェストを指定ファイルから読み込む。"""
    return EngineManifestInternal.from_file(manifest_path)
