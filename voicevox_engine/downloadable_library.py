import base64
import json
import shutil
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Dict

from fastapi import HTTPException

from voicevox_engine.model import DownloadableLibrary, InstalledLibrary

__all__ = ["LibraryManager"]

INFO_FILE = "metas.json"


class LibraryManager:
    def __init__(self, library_root_dir: Path):
        self.library_root_dir = library_root_dir
        self.library_root_dir.mkdir(exist_ok=True)

    def downloadable_libraries(self):
        # == ダウンロード情報をネットワーク上から取得する場合
        # url = "https://example.com/downloadable_libraries.json"
        # response = requests.get(url)
        # return list(map(DownloadableLibrary.parse_obj, response.json()))

        # == ダウンロード情報をjsonファイルから取得する場合
        # with open(
        #     self.root_dir / "engine_manifest_assets" / "downloadable_libraries.json",
        #     encoding="utf-8",
        # ) as f:
        #     return list(map(DownloadableLibrary.parse_obj, json.load(f)))

        # ダミーとして、speaker_infoのアセットを読み込む
        with open(
            "./engine_manifest_assets/downloadable_libraries.json",
            encoding="utf-8",
        ) as f:
            libraries = json.load(f)
            speaker_info = libraries[0]["speakers"][0]["speaker_info"]
            mock_root_dir = Path("./speaker_info/7ffcb7ce-00ec-4bdc-82cd-45a8889e43ff")
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
            return list(map(DownloadableLibrary.parse_obj, libraries))

    def installed_libraries(self) -> Dict[str, InstalledLibrary]:
        library = {}
        for library_dir in self.library_root_dir.iterdir():
            if library_dir.is_dir():
                with open(library_dir / INFO_FILE, encoding="utf-8") as f:
                    library[library_dir] = json.load(f)
                    # アンインストール出来ないライブラリを作る場合、何かしらの条件でFalseを設定する
                    library[library_dir]["uninstallable"] = True
        return library

    def install_library(self, library_id: str, file: BytesIO):
        for downloadable_library in self.downloadable_libraries():
            if downloadable_library.uuid == library_id:
                library_info = downloadable_library.dict()
                break
        else:
            raise HTTPException(status_code=404, detail="指定された音声ライブラリが見つかりません。")
        library_dir = self.library_root_dir / library_id
        library_dir.mkdir(exist_ok=True)
        with open(library_dir / INFO_FILE, "w", encoding="utf-8") as f:
            json.dump(library_info, f, indent=4, ensure_ascii=False)
        with zipfile.ZipFile(file) as zf:
            if zf.testzip() is not None:
                raise HTTPException(status_code=422, detail="不正なZIPファイルです。")

            zf.extractall(library_dir)
        return library_dir

    def uninstall_library(self, library_id: str):
        installed_libraries = self.installed_libraries()
        if library_id not in installed_libraries.keys():
            raise HTTPException(status_code=404, detail="指定された音声ライブラリはインストールされていません。")

        if not installed_libraries[library_id]["uninstallable"]:
            raise HTTPException(status_code=403, detail="指定された音声ライブラリはアンインストールできません。")

        try:
            shutil.rmtree(self.library_root_dir / library_id)
        except Exception:
            raise HTTPException(status_code=500, detail="ライブラリの削除に失敗しました。")
