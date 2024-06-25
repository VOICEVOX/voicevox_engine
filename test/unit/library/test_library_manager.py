import copy
import glob
import json
import os
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest import TestCase
from zipfile import ZipFile

from voicevox_engine.library.library_manager import (
    LibraryFormatInvalidError,
    LibraryManager,
    LibraryNotFoundError,
    LibraryUnsupportedError,
)

VVLIB_MANIFEST_NAME = "vvlib_manifest.json"


def create_vvlib_manifest(template_vvlib: Any, **kwargs: Any) -> dict[str, Any]:
    """テンプレートの vvlib から指定の属性を追加・上書きした、新たな vvlib オブジェクトを生成する。"""
    vvlib_manifest = copy.deepcopy(template_vvlib)
    return {**vvlib_manifest, **kwargs}


def create_vvlib_without_manifest(filename: str, template_vvlib_path: Path) -> None:
    """テンプレートの vvlib からマニフェストファイルを削除した、新たな vvlib ファイルを指定パスに生成する。"""
    with (
        ZipFile(filename, "w") as zf_out,
        ZipFile(template_vvlib_path, "r") as zf_in,
    ):
        for file in zf_in.infolist():
            buffer = zf_in.read(file.filename)
            if file.filename != VVLIB_MANIFEST_NAME:
                zf_out.writestr(file, buffer)


def append_any_as_manifest_to_vvlib(obj: Any, vvlib_path: str) -> None:
    """指定 vvlib へ任意の Python オブジェクトをマニフェストファイルとして追加する。"""
    with ZipFile(vvlib_path, "a") as zf:
        if isinstance(obj, str):
            obj_str = obj
        else:
            obj_str = json.dumps(obj)
        zf.writestr(VVLIB_MANIFEST_NAME, obj_str)


class TestLibraryManager(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.tmp_dir = TemporaryDirectory()
        self.tmp_dir_path = Path(self.tmp_dir.name)
        self.engine_name = "Test Engine"
        self.library_manger = LibraryManager(
            self.tmp_dir_path,
            "0.15.0",
            "Test",
            self.engine_name,
            "c7b58856-bd56-4aa1-afb7-b8415f824b06",
        )
        self.library_filename = Path("test/test.vvlib")
        with open("test/unit/library/vvlib_manifest.json") as f:
            self.vvlib_manifest = json.loads(f.read())
            self.library_uuid = self.vvlib_manifest["uuid"]
        with ZipFile(self.library_filename, "w") as zf:
            character_infos = glob.glob("resources/character_info/**", recursive=True)
            for info in character_infos:
                zf.write(info)
            zf.writestr(VVLIB_MANIFEST_NAME, json.dumps(self.vvlib_manifest))
        self.library_file = open(self.library_filename, "br")

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()
        self.library_file.close()
        self.library_filename.unlink()

    def test_installed_libraries(self) -> None:
        self.assertEqual(self.library_manger.installed_libraries(), {})

        self.library_manger.install_library(
            self.library_uuid,
            self.library_file,
        )
        # 内容はdownloadable_library.jsonを元に生成されるので、内容は確認しない
        self.assertEqual(
            list(self.library_manger.installed_libraries().keys())[0], self.library_uuid
        )

        self.library_manger.uninstall_library(self.library_uuid)
        self.assertEqual(self.library_manger.installed_libraries(), {})

    def test_install_unauthorized_library(self) -> None:
        """エンジンの受け入れリストに ID の無い音声ライブラリはインストールできない。"""
        invalid_uuid = "52398bd5-3cc3-406c-a159-dfec5ace4bab"
        with self.assertRaises(LibraryNotFoundError):
            self.library_manger.install_library(invalid_uuid, self.library_file)

    def test_install_non_zip_file(self) -> None:
        """非 ZIP ファイルは音声ライブラリとしてインストールできない。"""
        with self.assertRaises(LibraryFormatInvalidError):
            self.library_manger.install_library(self.library_uuid, BytesIO())

    def test_install_manifest_less_library(self) -> None:
        """マニフェストの無い ZIP ファイルは音声ライブラリとしてインストールできない。"""
        invalid_vvlib_name = "test/invalid.vvlib"
        create_vvlib_without_manifest(invalid_vvlib_name, self.library_filename)
        with (
            open(invalid_vvlib_name, "br") as f,
            self.assertRaises(LibraryFormatInvalidError),
        ):
            self.library_manger.install_library(self.library_uuid, f)

        # Teardown
        # TODO: tmp ファイルを用いた自動削除、あるいは、共通 teardown による削除へ実装し直す
        os.remove(invalid_vvlib_name)

    def test_install_broken_manifest_library(self) -> None:
        """不正な形式の vvlib_manifest.json をもつ ZIP ファイルは音声ライブラリとしてインストールできない。"""

        # Inputs
        invalid_vvlib_name = "test/invalid.vvlib"
        invalid_vvlib_manifest = "test"
        create_vvlib_without_manifest(invalid_vvlib_name, self.library_filename)
        append_any_as_manifest_to_vvlib(invalid_vvlib_manifest, invalid_vvlib_name)

        with (
            open(invalid_vvlib_name, "br") as f,
            self.assertRaises(LibraryFormatInvalidError),
        ):
            self.library_manger.install_library(self.library_uuid, f)

        # Teardown
        os.remove(invalid_vvlib_name)

    def test_install_invalid_type_manifest_library(self) -> None:
        """不正な形式の vvlib_manifest.json をもつ ZIP ファイルは音声ライブラリとしてインストールできない。"""

        # Inputs
        invalid_vvlib_name = "test/invalid.vvlib"
        invalid_vvlib_manifest = create_vvlib_manifest(
            template_vvlib=self.vvlib_manifest, version=10
        )
        create_vvlib_without_manifest(invalid_vvlib_name, self.library_filename)
        append_any_as_manifest_to_vvlib(invalid_vvlib_manifest, invalid_vvlib_name)

        # Tests
        with (
            open(invalid_vvlib_name, "br") as f,
            self.assertRaises(LibraryFormatInvalidError),
        ):
            self.library_manger.install_library(self.library_uuid, f)

        # Teardown
        os.remove(invalid_vvlib_name)

    def test_install_invalid_version_manifest_library(self) -> None:
        # vvlib_manifestの不正なversionのテスト

        # Inputs
        invalid_vvlib_name = "test/invalid.vvlib"
        invalid_vvlib_manifest = create_vvlib_manifest(
            template_vvlib=self.vvlib_manifest, version="10"
        )
        create_vvlib_without_manifest(invalid_vvlib_name, self.library_filename)
        append_any_as_manifest_to_vvlib(invalid_vvlib_manifest, invalid_vvlib_name)

        # Tests
        with (
            open(invalid_vvlib_name, "br") as f,
            self.assertRaises(LibraryFormatInvalidError),
        ):
            self.library_manger.install_library(self.library_uuid, f)

        # Teardown
        os.remove(invalid_vvlib_name)

    def test_install_invalid_manifest_version_library(self) -> None:
        # vvlib_manifestの不正なmanifest_versionのテスト

        # Inputs
        invalid_vvlib_name = "test/invalid.vvlib"
        invalid_vvlib_manifest = create_vvlib_manifest(
            template_vvlib=self.vvlib_manifest, manifest_version="10"
        )
        create_vvlib_without_manifest(invalid_vvlib_name, self.library_filename)
        append_any_as_manifest_to_vvlib(invalid_vvlib_manifest, invalid_vvlib_name)

        # Tests
        with (
            open(invalid_vvlib_name, "br") as f,
            self.assertRaises(LibraryFormatInvalidError),
        ):
            self.library_manger.install_library(self.library_uuid, f)

        # Teardown
        os.remove(invalid_vvlib_name)

    def test_install_invalid_manifest_version_library_2(self) -> None:
        # vvlib_manifestの未対応のmanifest_versionのテスト

        # Inputs
        invalid_vvlib_name = "test/invalid.vvlib"
        invalid_vvlib_manifest = create_vvlib_manifest(
            template_vvlib=self.vvlib_manifest, manifest_version="999.999.999"
        )
        create_vvlib_without_manifest(invalid_vvlib_name, self.library_filename)
        append_any_as_manifest_to_vvlib(invalid_vvlib_manifest, invalid_vvlib_name)

        # Tests
        with (
            open(invalid_vvlib_name, "br") as f,
            self.assertRaises(LibraryUnsupportedError),
        ):
            self.library_manger.install_library(self.library_uuid, f)

        # Teardown
        os.remove(invalid_vvlib_name)

    def test_install_non_target_engine_library(self) -> None:
        # vvlib_manifestのインストール先エンジンの検証のテスト

        # Inputs
        invalid_vvlib_name = "test/invalid.vvlib"
        invalid_vvlib_manifest = create_vvlib_manifest(
            template_vvlib=self.vvlib_manifest,
            engine_uuid="26f7823b-20c6-40c5-bf86-6dd5d9d45c18",
        )
        create_vvlib_without_manifest(invalid_vvlib_name, self.library_filename)
        append_any_as_manifest_to_vvlib(invalid_vvlib_manifest, invalid_vvlib_name)

        # Tests
        with (
            open(invalid_vvlib_name, "br") as f,
            self.assertRaises(LibraryUnsupportedError),
        ):
            self.library_manger.install_library(self.library_uuid, f)

        # Teardown
        os.remove(invalid_vvlib_name)

    def test_install(self) -> None:
        # 正しいライブラリをインストールして問題が起きないか
        library_path = self.library_manger.install_library(
            self.library_uuid, self.library_file
        )
        self.assertEqual(self.tmp_dir_path / self.library_uuid, library_path)

        self.library_manger.uninstall_library(self.library_uuid)

    def test_uninstall_library(self) -> None:
        # TODO: アンインストール出来ないライブラリをテストできるようにしたい
        with self.assertRaises(LibraryNotFoundError):
            self.library_manger.uninstall_library(self.library_uuid)

        self.library_manger.install_library(self.library_uuid, self.library_file)
        self.library_manger.uninstall_library(self.library_uuid)
