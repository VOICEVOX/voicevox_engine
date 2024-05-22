# マルチエンジン環境下においては、エンジンのバージョンがエディタのバージョンより
# 古くなる可能性が十分に考えられる。その場合、エディタ側がEngineManifestの情報不足によって
# エラーを吐いて表示が崩壊する可能性がある。これを防止するため、EngineManifest関連の定義を
# 変更する際は、Optionalにする必要があることに留意しなければならない。

import json
from base64 import b64encode
from pathlib import Path
from typing import TypeAlias

from pydantic import BaseModel, Field


class UpdateInfo(BaseModel):
    """
    エンジンのアップデート情報
    """

    version: str = Field(title="エンジンのバージョン名")
    descriptions: list[str] = Field(title="アップデートの詳細についての説明")
    contributors: list[str] | None = Field(title="貢献者名")


class LicenseInfo(BaseModel):
    """
    依存ライブラリのライセンス情報
    """

    name: str = Field(title="依存ライブラリ名")
    version: str | None = Field(title="依存ライブラリのバージョン")
    license: str | None = Field(title="依存ライブラリのライセンス名")
    text: str = Field(title="依存ライブラリのライセンス本文")


class SupportedFeatures(BaseModel):
    """
    エンジンが持つ機能の一覧
    """

    adjust_mora_pitch: bool = Field(title="モーラごとの音高の調整")
    adjust_phoneme_length: bool = Field(title="音素ごとの長さの調整")
    adjust_speed_scale: bool = Field(title="全体の話速の調整")
    adjust_pitch_scale: bool = Field(title="全体の音高の調整")
    adjust_intonation_scale: bool = Field(title="全体の抑揚の調整")
    adjust_volume_scale: bool = Field(title="全体の音量の調整")
    interrogative_upspeak: bool = Field(title="疑問文の自動調整")
    synthesis_morphing: bool = Field(
        title="2種類のスタイルでモーフィングした音声を合成"
    )
    sing: bool | None = Field(title="歌唱音声合成")
    manage_library: bool | None = Field(
        title="音声ライブラリのインストール・アンインストール"
    )


EngineName: TypeAlias = str
BrandName: TypeAlias = str


class EngineManifest(BaseModel):
    """
    エンジン自体に関する情報
    """

    manifest_version: str = Field(title="マニフェストのバージョン")
    name: EngineName = Field(title="エンジン名")
    brand_name: BrandName = Field(title="ブランド名")
    uuid: str = Field(title="エンジンのUUID")
    url: str = Field(title="エンジンのURL")
    icon: str = Field(title="エンジンのアイコンをBASE64エンコードしたもの")
    default_sampling_rate: int = Field(title="デフォルトのサンプリング周波数")
    frame_rate: float = Field(title="エンジンのフレームレート")
    terms_of_service: str = Field(title="エンジンの利用規約")
    update_infos: list[UpdateInfo] = Field(title="エンジンのアップデート情報")
    dependency_licenses: list[LicenseInfo] = Field(title="依存関係のライセンス情報")
    supported_vvlib_manifest_version: str | None = Field(
        title="エンジンが対応するvvlibのバージョン"
    )
    supported_features: SupportedFeatures = Field(title="エンジンが持つ機能")


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
