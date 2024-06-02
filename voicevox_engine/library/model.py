"""
ライブラリ機能に関して API と ENGINE 内部実装が共有するモデル

「API と ENGINE 内部実装が共有するモデル」については `voicevox_engine/model.py` の module docstring を確認すること。
"""

from pydantic import BaseModel, Field, StrictStr

from voicevox_engine.metas.Metas import Speaker, SpeakerInfo


class LibrarySpeaker(BaseModel):
    """
    音声ライブラリに含まれる話者の情報
    """

    speaker: Speaker = Field(title="話者情報")
    speaker_info: SpeakerInfo = Field(title="話者の追加情報")


class BaseLibraryInfo(BaseModel):
    """
    音声ライブラリの情報
    """

    name: str = Field(title="音声ライブラリの名前")
    uuid: str = Field(title="音声ライブラリのUUID")
    version: str = Field(title="音声ライブラリのバージョン")
    download_url: str = Field(title="音声ライブラリのダウンロードURL")
    bytes: int = Field(title="音声ライブラリのバイト数")
    speakers: list[LibrarySpeaker] = Field(title="音声ライブラリに含まれる話者のリスト")


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

    uninstallable: bool = Field(title="アンインストール可能かどうか")


class VvlibManifest(BaseModel):
    """
    vvlib(VOICEVOX Library)に関する情報
    """

    manifest_version: StrictStr = Field(title="マニフェストバージョン")
    name: StrictStr = Field(title="音声ライブラリ名")
    version: StrictStr = Field(title="音声ライブラリバージョン")
    uuid: StrictStr = Field(title="音声ライブラリのUUID")
    brand_name: StrictStr = Field(title="エンジンのブランド名")
    engine_name: StrictStr = Field(title="エンジン名")
    engine_uuid: StrictStr = Field(title="エンジンのUUID")
