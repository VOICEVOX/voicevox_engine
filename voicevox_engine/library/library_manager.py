"""音声ライブラリの管理"""

import base64
import json
import os
import shutil
import zipfile
from pathlib import Path
from typing import BinaryIO

from pydantic import ValidationError
from semver.version import Version

from voicevox_engine.library.model import (
    DownloadableLibraryInfo,
    InstalledLibraryInfo,
    VvlibManifest,
)

__all__ = ["LibraryManager"]

INFO_FILE = "metas.json"


class LibraryNotFoundError(Exception):
    pass


class LibraryFormatInvalidError(Exception):
    pass


class LibraryUnsupportedError(Exception):
    pass


class LibraryOperationUnauthorizedError(Exception):
    pass


class LibraryInternalError(Exception):
    pass


class LibraryManager:
    """音声ライブラリ (`.vvlib`) の管理"""

    def __init__(
        self,
        library_root_dir: Path,
        supported_vvlib_version: str | None,
        brand_name: str,
        engine_name: str,
        engine_uuid: str,
    ):
        self.library_root_dir = library_root_dir
        self.library_root_dir.mkdir(exist_ok=True)
        if supported_vvlib_version is not None:
            self.supported_vvlib_version = Version.parse(supported_vvlib_version)
        else:
            # supported_vvlib_versionがNoneの時は0.0.0として扱う
            self.supported_vvlib_version = Version.parse("0.0.0")
        self.engine_brand_name = brand_name
        self.engine_name = engine_name
        self.engine_uuid = engine_uuid

    def downloadable_libraries(self) -> list[DownloadableLibraryInfo]:
        """ダウンロード可能音声ライブラリ情報の一覧を取得する。"""
        # == ダウンロード情報をネットワーク上から取得する場合
        # url = "https://example.com/downloadable_libraries.json"
        # response = requests.get(url)
        # return list(map(DownloadableLibrary.parse_obj, response.json()))

        # == ダウンロード情報をjsonファイルから取得する場合
        # with open(
        #     self.root_dir / "resources" / "engine_manifest_assets" / "downloadable_libraries.json", # noqa: B950
        #     encoding="utf-8",
        # ) as f:
        #     return list(map(DownloadableLibrary.parse_obj, json.load(f)))

        # ダミーとして、speaker_infoのアセットを読み込む
        with open(
            "./resources/engine_manifest_assets/downloadable_libraries.json",
            encoding="utf-8",
        ) as f:
            libraries = json.load(f)
            speaker_info = libraries[0]["speakers"][0]["speaker_info"]
            mock_root_dir = Path(
                "./resources/character_info/7ffcb7ce-00ec-4bdc-82cd-45a8889e43ff"
            )
            speaker_info["policy"] = (mock_root_dir / "policy.md").read_text()
            speaker_info["portrait"] = base64.b64encode(
                (mock_root_dir / "portrait.png").read_bytes()
            )
            for style_info in speaker_info["style_infos"]:
                style_id = style_info["id"]
                style_info["icon"] = base64.b64encode(
                    (mock_root_dir / "icons" / f"{style_id}.png").read_bytes()
                )
                style_info["voice_samples"] = [
                    base64.b64encode(
                        (
                            mock_root_dir / "voice_samples" / f"{style_id}_{i:0>3}.wav"
                        ).read_bytes()
                    )
                    for i in range(1, 4)
                ]
            return list(map(DownloadableLibraryInfo.model_validate, libraries))

    def installed_libraries(self) -> dict[str, InstalledLibraryInfo]:
        """インストール済み音声ライブラリ情報の一覧を取得する。"""
        library: dict[str, InstalledLibraryInfo] = {}
        for library_dir in self.library_root_dir.iterdir():
            if library_dir.is_dir():
                # ライブラリ情報の取得 from `library_root_dir / f"{library_uuid}" / "metas.json"`
                library_uuid = os.path.basename(library_dir)
                with open(library_dir / INFO_FILE, encoding="utf-8") as f:
                    info = json.load(f)
                # アンインストール出来ないライブラリを作る場合、何かしらの条件でFalseを設定する
                library[library_uuid] = InstalledLibraryInfo(**info, uninstallable=True)
        return library

    def install_library(self, library_id: str, file: BinaryIO) -> Path:
        """
        音声ライブラリ (`.vvlib`) をインストールする。
        Parameters
        ----------
        library_id : str
            インストール対象ライブラリID
        file : BytesIO
            ライブラリファイルBlob
        Returns
        -------
        library_dir : Path
            インストール済みライブラリの情報
        """
        for downloadable_library in self.downloadable_libraries():
            if downloadable_library.uuid == library_id:
                library_info = downloadable_library.model_dump_json(indent=4)
                break
        else:
            msg = f"音声ライブラリ {library_id} が見つかりません。"
            raise LibraryNotFoundError(msg)

        # ライブラリディレクトリを生成する
        library_dir = self.library_root_dir / library_id
        library_dir.mkdir(exist_ok=True)

        # metas.jsonを生成する
        with open(library_dir / INFO_FILE, "w", encoding="utf-8") as f:
            f.write(library_info)

        # ZIP 形式ではないファイルはライブラリでないためインストールを拒否する
        if not zipfile.is_zipfile(file):
            msg = f"音声ライブラリ {library_id} は不正なファイル形式です。"
            raise LibraryFormatInvalidError(msg)

        with zipfile.ZipFile(file) as zf:
            if zf.testzip() is not None:
                msg = f"音声ライブラリ {library_id} は不正なファイルです。"
                raise LibraryFormatInvalidError(msg)

            vvlib_manifest = None
            try:
                vvlib_manifest = json.loads(
                    zf.read("vvlib_manifest.json").decode("utf-8")
                )
            # マニフェストファイルをもたないライブラリはインストールを拒否する
            except KeyError:
                msg = (
                    f"音声ライブラリ {library_id} にvvlib_manifest.jsonが存在しません。"
                )
                raise LibraryFormatInvalidError(msg)
            except Exception:
                msg = f"音声ライブラリ {library_id} のvvlib_manifest.jsonは不正です。"
                raise LibraryFormatInvalidError(msg)

            # 不正な形式のマニフェストファイルをもつライブラリはインストールを拒否する
            try:
                VvlibManifest.model_validate(vvlib_manifest)
            except ValidationError:
                msg = f"音声ライブラリ {library_id} のvvlib_manifest.jsonが不正な形式です。"
                raise LibraryFormatInvalidError(msg)

            # 不正な `version` 形式のマニフェストファイルもつライブラリはインストールを拒否する
            if not Version.is_valid(vvlib_manifest["version"]):
                msg = f"音声ライブラリ {library_id} のversion形式が不正です。"
                raise LibraryFormatInvalidError(msg)

            # 不正な形式あるいは対応範囲外のマニフェストバージョンをもつライブラリはインストールを拒否する
            try:
                manifest_version = Version.parse(vvlib_manifest["manifest_version"])
            except ValueError:
                msg = f"音声ライブラリ {library_id} のmanifest_version形式が不正です。"
                raise LibraryFormatInvalidError(msg)
            if manifest_version > self.supported_vvlib_version:
                msg = f"音声ライブラリ {library_id} は未対応です。"
                raise LibraryUnsupportedError(msg)

            # このエンジン向けでないライブラリはインストールを拒否する
            if vvlib_manifest["engine_uuid"] != self.engine_uuid:
                msg = f"音声ライブラリ {library_id} は{self.engine_name}向けではありません。"
                raise LibraryUnsupportedError(msg)

            # インストールする
            # NOTE: 当該ライブラリ用のディレクトリ下へ展開してインストールする
            zf.extractall(library_dir)

        return library_dir

    def uninstall_library(self, library_id: str) -> None:
        """ID で指定されたインストール済み音声ライブラリをアンインストールする。"""

        # 未インストールライブラリのアンインストールは不可能なので拒否する
        if library_id not in self.installed_libraries().keys():
            msg = f"音声ライブラリ {library_id} はインストールされていません。"
            raise LibraryNotFoundError(msg)

        # アンインストール不許可ライブラリはアンインストールを拒否する
        if not self.installed_libraries()[library_id].uninstallable:
            msg = f"音声ライブラリ {library_id} はアンインストールが禁止されています。"
            raise LibraryOperationUnauthorizedError(msg)

        # アンインストールする
        try:
            # NOTE: 当該ライブラリのディレクトリを削除してアンインストールする
            shutil.rmtree(self.library_root_dir / library_id)
        except Exception:
            msg = f"音声ライブラリ {library_id} の削除に失敗しました。"
            raise LibraryInternalError(msg)
