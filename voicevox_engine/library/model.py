"""
ライブラリ機能に関して API と ENGINE 内部実装が共有するモデル（データ構造）

モデルの注意点は `voicevox_engine/model.py` の module docstring を確認すること。
"""

from pydantic import BaseModel, Field, StrictStr

from voicevox_engine.metas.Metas import Speaker, SpeakerInfo


class LibrarySpeaker(BaseModel):
    """
    音声ライブラリに含まれるキャラクターの情報
    """

    speaker: Speaker = Field(description="キャラクター情報")
    speaker_info: SpeakerInfo = Field(description="キャラクターの追加情報")


class BaseLibraryInfo(BaseModel):
    """
    音声ライブラリの情報
    """

    name: str = Field(description="音声ライブラリの名前")
    uuid: str = Field(description="音声ライブラリのUUID")
    version: str = Field(description="音声ライブラリのバージョン")
    download_url: str = Field(description="音声ライブラリのダウンロードURL")
    bytes: int = Field(description="音声ライブラリのバイト数")
    speakers: list[LibrarySpeaker] = Field(
        description="音声ライブラリに含まれるキャラクターのリスト"
    )


# 今後InstalledLibraryInfo同様に拡張する可能性を考え、モデルを分けている
class DownloadableLibraryInfo(BaseLibraryInfo):
    """
    ダウンロード可能な音声ライブラリの情報
    """

    pass


class InstalledLibraryInfo(BaseLibraryInfo):
    """
    インストール済み音声ライブラリの情報
    """

    uninstallable: bool = Field(description="アンインストール可能かどうか")


class VvlibManifest(BaseModel):
    """
    vvlib(VOICEVOX Library)に関する情報
    """

    manifest_version: StrictStr = Field(description="マニフェストバージョン")
    name: StrictStr = Field(description="音声ライブラリ名")
    version: StrictStr = Field(description="音声ライブラリバージョン")
    uuid: StrictStr = Field(description="音声ライブラリのUUID")
    brand_name: StrictStr = Field(description="エンジンのブランド名")
    engine_name: StrictStr = Field(description="エンジン名")
    engine_uuid: StrictStr = Field(description="エンジンのUUID")
