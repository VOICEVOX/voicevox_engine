# マルチエンジン環境下においては、エンジンのバージョンがエディタのバージョンより
# 古くなる可能性が十分に考えられる。その場合、エディタ側がEngineManifestの情報不足によって
# エラーを吐いて表示が崩壊する可能性がある。これを防止するため、EngineManifest関連の定義を
# 変更する際は、Optionalにする必要があることに留意しなければならない。

from typing import List, Optional

from pydantic import BaseModel, Field


class UpdateInfo(BaseModel):
    """
    エンジンのアップデート情報
    """

    version: str = Field(title="エンジンのバージョン名")
    descriptions: List[str] = Field(title="アップデートの詳細についての説明")
    contributors: Optional[List[str]] = Field(title="貢献者名")


class LicenseInfo(BaseModel):
    """
    依存ライブラリのライセンス情報
    """

    name: str = Field(title="依存ライブラリ名")
    version: Optional[str] = Field(title="依存ライブラリのバージョン")
    license: Optional[str] = Field(title="依存ライブラリのライセンス名")
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
    synthesis_morphing: bool = Field(title="2人の話者でモーフィングした音声を合成")
    manage_library: Optional[bool] = Field(title="音声ライブラリのインストール・アンインストール")


class EngineManifest(BaseModel):
    """
    エンジン自体に関する情報
    """

    manifest_version: str = Field(title="マニフェストのバージョン")
    name: str = Field(title="エンジン名")
    brand_name: str = Field(title="ブランド名")
    uuid: str = Field(title="エンジンのUUID")
    url: str = Field(title="エンジンのURL")
    icon: str = Field(title="エンジンのアイコンをBASE64エンコードしたもの")
    default_sampling_rate: int = Field(title="デフォルトのサンプリング周波数")
    terms_of_service: str = Field(title="エンジンの利用規約")
    update_infos: List[UpdateInfo] = Field(title="エンジンのアップデート情報")
    dependency_licenses: List[LicenseInfo] = Field(title="依存関係のライセンス情報")
    supported_vvlib_manifest_version: Optional[str] = Field(
        title="エンジンが対応するvvlibのバージョン"
    )
    supported_features: SupportedFeatures = Field(title="エンジンが持つ機能")
