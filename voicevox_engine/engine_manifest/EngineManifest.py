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


class EngineManifest(BaseModel):
    """
    エンジン自体に関する情報
    """

    manifest_version: str = Field(title="マニフェストのバージョン")
    name: str = Field(title="エンジン名")
    uuid: str = Field(title="エンジンのUUID")
    url: str = Field(title="エンジンのURL")
    icon: str = Field(title="エンジンのアイコンをBASE64エンコードしたもの")
    default_sampling_rate: int = Field(title="デフォルトのサンプリング周波数")
    terms_of_service: str = Field(title="エンジンの利用規約")
    update_infos: List[UpdateInfo] = Field(title="エンジンのアップデート情報")
    dependency_licenses: List[LicenseInfo] = Field(title="依存関係のライセンス情報")
    downloadable_libraries_path: Optional[str] = Field(
        title="ダウンロード可能な音声ライブラリ情報を取得するためのローカルjsonパス"
    )
    downloadable_libraries_url: Optional[str] = Field(
        title="ダウンロード可能な音声ライブラリ情報を取得するためのAPIのURL"
    )
