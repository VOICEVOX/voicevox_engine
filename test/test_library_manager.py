import copy
import glob
import json
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest import TestCase
from zipfile import ZipFile

from fastapi import HTTPException

from voicevox_engine.library_manager import LibraryManager

vvlib_manifest_name = "vvlib_manifest.json"


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
        with open("test/vvlib_manifest.json") as f:
            self.vvlib_manifest = json.loads(f.read())
            self.library_uuid = self.vvlib_manifest["uuid"]
        with ZipFile(self.library_filename, "w") as zf:
            speaker_infos = glob.glob("speaker_info/**", recursive=True)
            for info in speaker_infos:
                zf.write(info)
            zf.writestr(vvlib_manifest_name, json.dumps(self.vvlib_manifest))
        self.library_file = open(self.library_filename, "br")

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()
        self.library_file.close()
        self.library_filename.unlink()

    def create_vvlib_without_manifest(self, filename: str) -> None:
        with (
            ZipFile(filename, "w") as zf_out,
            ZipFile(self.library_filename, "r") as zf_in,
        ):
            for file in zf_in.infolist():
                buffer = zf_in.read(file.filename)
                if file.filename != vvlib_manifest_name:
                    zf_out.writestr(file, buffer)

    def create_vvlib_manifest(self, **kwargs: Any) -> dict[str, Any]:
        vvlib_manifest = copy.deepcopy(self.vvlib_manifest)
        return {**vvlib_manifest, **kwargs}

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
        with self.assertRaises(HTTPException) as e:
            self.library_manger.install_library(invalid_uuid, self.library_file)
        self.assertEqual(
            e.exception.detail,
            f"音声ライブラリ {invalid_uuid} が見つかりません。",
        )

    def test_install_non_zip_file(self) -> None:
        """非 ZIP ファイルは音声ライブラリとしてインストールできない。"""
        with self.assertRaises(HTTPException) as e:
            self.library_manger.install_library(self.library_uuid, BytesIO())
        self.assertEqual(
            e.exception.detail,
            f"音声ライブラリ {self.library_uuid} は不正なファイル形式（非 ZIP ファイル）です。",
        )

    def test_install_manifest_less_library(self) -> None:
        """マニフェストの無い ZIP ファイルは音声ライブラリとしてインストールできない。"""
        invalid_vvlib_name = "test/invalid.vvlib"
        self.create_vvlib_without_manifest(invalid_vvlib_name)
        with open(invalid_vvlib_name, "br") as f, self.assertRaises(HTTPException) as e:
            self.library_manger.install_library(self.library_uuid, f)
        self.assertEqual(
            e.exception.detail,
            f"音声ライブラリ {self.library_uuid} にvvlib_manifest.jsonが存在しません。",
        )

    def test_install_broken_manifest_library(self) -> None:
        """不正な形式の vvlib_manifest.json をもつ ZIP ファイルは音声ライブラリとしてインストールできない。"""

        # vvlib_manifestのパースのテスト
        # Duplicate name: 'vvlib_manifest.json'とWarningを吐かれるので、毎回作り直す
        invalid_vvlib_name = "test/invalid.vvlib"
        self.create_vvlib_without_manifest(invalid_vvlib_name)
        with ZipFile(invalid_vvlib_name, "a") as zf:
            zf.writestr(vvlib_manifest_name, "test")

        with open(invalid_vvlib_name, "br") as f, self.assertRaises(HTTPException) as e:
            self.library_manger.install_library(self.library_uuid, f)
        self.assertEqual(
            e.exception.detail,
            f"音声ライブラリ {self.library_uuid} のvvlib_manifest.jsonは不正です。",
        )

    def test_install_invalid_type_manifest_library(self) -> None:
        """不正な形式の vvlib_manifest.json をもつ ZIP ファイルは音声ライブラリとしてインストールできない。"""
        # vvlib_manifestのパースのテスト
        invalid_vvlib_name = "test/invalid.vvlib"
        invalid_vvlib_manifest = self.create_vvlib_manifest(version=10)
        self.create_vvlib_without_manifest(invalid_vvlib_name)
        with ZipFile(invalid_vvlib_name, "a") as zf:
            zf.writestr(vvlib_manifest_name, json.dumps(invalid_vvlib_manifest))

        with open(invalid_vvlib_name, "br") as f, self.assertRaises(HTTPException) as e:
            self.library_manger.install_library(self.library_uuid, f)
        self.assertEqual(
            e.exception.detail,
            f"音声ライブラリ {self.library_uuid} のvvlib_manifest.jsonが不正な形式です。",
        )

    def test_install_invalid_version_manifest_library(self) -> None:
        # vvlib_manifestの不正なversionのテスト
        invalid_vvlib_name = "test/invalid.vvlib"
        invalid_vvlib_manifest = self.create_vvlib_manifest(version="10")
        self.create_vvlib_without_manifest(invalid_vvlib_name)
        with ZipFile(invalid_vvlib_name, "a") as zf:
            zf.writestr(vvlib_manifest_name, json.dumps(invalid_vvlib_manifest))

        with open(invalid_vvlib_name, "br") as f, self.assertRaises(HTTPException) as e:
            self.library_manger.install_library(self.library_uuid, f)
        self.assertEqual(
            e.exception.detail,
            f"音声ライブラリ {self.library_uuid} のversion形式が不正です。",
        )

    def test_install_invalid_manifest_version_library(self) -> None:
        # vvlib_manifestの不正なmanifest_versionのテスト
        invalid_vvlib_name = "test/invalid.vvlib"
        invalid_vvlib_manifest = self.create_vvlib_manifest(manifest_version="10")
        self.create_vvlib_without_manifest(invalid_vvlib_name)
        with ZipFile(invalid_vvlib_name, "a") as zf:
            zf.writestr(vvlib_manifest_name, json.dumps(invalid_vvlib_manifest))

        with open(invalid_vvlib_name, "br") as f, self.assertRaises(HTTPException) as e:
            self.library_manger.install_library(self.library_uuid, f)
        self.assertEqual(
            e.exception.detail,
            f"音声ライブラリ {self.library_uuid} のmanifest_version形式が不正です。",
        )

    def test_install_invalid_manifest_version_library_2(self) -> None:
        # vvlib_manifestの未対応のmanifest_versionのテスト
        invalid_vvlib_name = "test/invalid.vvlib"
        invalid_vvlib_manifest = self.create_vvlib_manifest(
            manifest_version="999.999.999"
        )
        self.create_vvlib_without_manifest(invalid_vvlib_name)
        with ZipFile(invalid_vvlib_name, "a") as zf:
            zf.writestr(vvlib_manifest_name, json.dumps(invalid_vvlib_manifest))

        with open(invalid_vvlib_name, "br") as f, self.assertRaises(HTTPException) as e:
            self.library_manger.install_library(self.library_uuid, f)
        self.assertEqual(
            e.exception.detail,
            f"音声ライブラリ {self.library_uuid} はエンジンが未対応です。",
        )

    def test_install_non_target_engine_library(self) -> None:
        # vvlib_manifestのインストール先エンジンの検証のテスト
        invalid_vvlib_name = "test/invalid.vvlib"
        invalid_vvlib_manifest = self.create_vvlib_manifest(
            engine_uuid="26f7823b-20c6-40c5-bf86-6dd5d9d45c18"
        )
        self.create_vvlib_without_manifest(invalid_vvlib_name)
        with ZipFile(invalid_vvlib_name, "a") as zf:
            zf.writestr(vvlib_manifest_name, json.dumps(invalid_vvlib_manifest))

        with open(invalid_vvlib_name, "br") as f, self.assertRaises(HTTPException) as e:
            self.library_manger.install_library(self.library_uuid, f)
        self.assertEqual(
            e.exception.detail,
            f"音声ライブラリ {self.library_uuid} は{self.engine_name}向けではありません。",
        )

    def test_install(self) -> None:
        # 正しいライブラリをインストールして問題が起きないか
        library_path = self.library_manger.install_library(
            self.library_uuid, self.library_file
        )
        self.assertEqual(self.tmp_dir_path / self.library_uuid, library_path)

        self.library_manger.uninstall_library(self.library_uuid)

    def test_uninstall_library(self) -> None:
        # TODO: アンインストール出来ないライブラリをテストできるようにしたい
        with self.assertRaises(HTTPException) as e:
            self.library_manger.uninstall_library(self.library_uuid)
        self.assertEqual(
            e.exception.detail,
            f"音声ライブラリ {self.library_uuid} はインストールされていません。",
        )

        self.library_manger.install_library(self.library_uuid, self.library_file)
        self.library_manger.uninstall_library(self.library_uuid)
