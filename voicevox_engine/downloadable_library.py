import json
import zipfile
from io import BytesIO
from pathlib import Path
from typing import List

import requests
from fastapi import HTTPException

from voicevox_engine.model import DownloadableLibrary

__all__ = ["LibraryManager"]

INFO_FILE = "library_info.json"


class LibraryManager:
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        if not self.root_dir.exists():
            self.root_dir.mkdir()

    def downloadable_libraries(self):
        url = "http://localhost:50022"
        response = requests.get(url)
        return list(map(DownloadableLibrary.parse_obj, response.json()))

    def installed_libraries(self) -> List[DownloadableLibrary]:
        library = []
        for library_dir in self.root_dir.iterdir():
            if library_dir.is_dir():
                with open(library_dir / INFO_FILE, encoding="utf-8") as f:
                    library.append(json.load(f))
        return library

    def install_library(self, library_id: str, file: BytesIO):
        library_info = None
        for downloadable_library in self.downloadable_libraries():
            if downloadable_library.uuid == library_id:
                library_info = downloadable_library.dict()
                break
        else:
            raise HTTPException(status_code=404, detail="指定されたライブラリが見つかりません。")
        library_dir = self.root_dir / library_id
        if not library_dir.exists():
            library_dir.mkdir()
        with open(library_dir / INFO_FILE, "w", encoding="utf-8") as f:
            json.dump(library_info, f, indent=4, ensure_ascii=False)
        with zipfile.ZipFile(file) as zf:
            if zf.testzip() is not None:
                raise HTTPException(status_code=422, detail="ZIPファイルが壊れています。")

            zf.extractall(library_dir)
        return library_dir
