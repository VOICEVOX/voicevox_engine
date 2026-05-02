"""
VOICEVOX ENGINE の実行に必要なライブラリのライセンス一覧を作成する。

実行環境にインストールされている Python ライブラリのライセンス一覧を取得する。
一覧に対し、ハードコードされたライセンス一覧を追加する。
ライセンス一覧をファイルとして出力する。
"""

import argparse
import importlib.metadata
import json
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, assert_never

from pydantic import TypeAdapter


def _get_license_text(text_url: str) -> str:
    """URL が指すテキストを取得する。"""
    with urllib.request.urlopen(text_url) as res:
        # NOTE: `urlopen` 返り値の型が貧弱なため型チェックを無視する
        return res.read().decode()  # type: ignore


@dataclass
class _PipLicense:
    """`pip-license` により得られる依存ライブラリの情報"""

    License: str
    Name: str
    URL: str
    Version: str
    LicenseText: str


_pip_licenses_adapter = TypeAdapter(list[_PipLicense])


def _acquire_licenses_of_pip_managed_libraries() -> list[_PipLicense]:
    """Pipで管理されている依存ライブラリのライセンス情報を取得する。"""
    # ライセンス一覧を取得する
    try:
        pip_licenses_json = subprocess.run(
            [
                sys.executable,
                "-m",
                "piplicenses",
                "--from=mixed",
                "--format=json",
                "--with-urls",
                "--with-license-file",
                "--no-license-path",
            ],
            capture_output=True,
            check=True,
        ).stdout.decode()
    except subprocess.CalledProcessError as e:
        raise Exception(f"command output:\n{e.stderr and e.stderr.decode()}") from e
    # ライセンス情報の形式をチェックする
    licenses = _pip_licenses_adapter.validate_json(pip_licenses_json)
    return licenses


class _License:
    def __init__(
        self,
        package_name: str,
        package_version: str | None,
        license_name: str | None,
        license_text: str,
        license_text_type: Literal["raw", "local_address", "remote_address"],
    ):
        self.package_name = package_name
        self.package_version = package_version
        self.license_name = license_name

        match license_text_type:
            case "raw":
                self.license_text = license_text
            case "local_address":
                # ライセンステキストをローカルのライセンスファイルから抽出する
                self.license_text = Path(license_text).read_text(encoding="utf8")
            case "remote_address":
                self.license_text = _get_license_text(license_text)
            case _:
                assert_never(license_text_type)


def _update_licenses(pip_licenses: list[_PipLicense]) -> list[_License]:
    """pip から取得したライセンス情報の抜けを補完する。"""
    package_to_license_url: dict[str, str] = {
        # "package_name": "https://license.adress.com/v0.0.0/LICENSE.txt",
    }

    updated_licenses = []

    for pip_license in pip_licenses:
        package_name = pip_license.Name.lower()

        # ライセンス文が pip から取得できていない場合、pip 外から補う
        if pip_license.LicenseText == "UNKNOWN":
            if package_name not in package_to_license_url:
                # ライセンスがpypiに無い
                raise Exception(f"No License info provided for {package_name}")
            text_url = package_to_license_url[package_name]
            pip_license.LicenseText = _get_license_text(text_url)

        updated_licenses.append(
            _License(
                package_name=pip_license.Name,
                package_version=pip_license.Version,
                license_name=pip_license.License,
                license_text=pip_license.LicenseText,
                license_text_type="raw",
            )
        )

    return updated_licenses


class _LicenseError(Exception):
    """License違反が検出された。"""

    pass


def _validate_license_compliance(licenses: list[_License]) -> None:
    for license in licenses:
        # ライセンスを確認する
        license_names_str = license.license_name or ""
        license_names = license_names_str.split("; ")
        for license_name in license_names:
            if license_name in [
                "GNU General Public License v2 (GPLv2)",
                "GNU General Public License (GPL)",
                "GNU General Public License v3 (GPLv3)",
                "GNU Affero General Public License v3 (AGPL-3)",
            ]:
                raise _LicenseError(
                    f"ライセンス違反: {license.package_name} is {license.license_name}"
                )


def _add_licenses_manually(licenses: list[_License]) -> None:
    python_version = "3.11.9"

    licenses += [
        # https://sourceforge.net/projects/open-jtalk/files/Open%20JTalk/open_jtalk-1.11/
        _License(
            package_name="Open JTalk",
            package_version="1.11",
            license_name="Modified BSD license",
            license_text="tools/licenses/open_jtalk/COPYING",
            license_text_type="local_address",
        ),
        _License(
            package_name="MeCab",
            package_version=None,
            license_name="Modified BSD license",
            license_text="tools/licenses/open_jtalk/mecab/COPYING",
            license_text_type="local_address",
        ),
        _License(
            package_name="NAIST Japanese Dictionary",
            package_version=None,
            license_name="Modified BSD license",
            license_text="tools/licenses//open_jtalk/mecab-naist-jdic/COPYING",
            license_text_type="local_address",
        ),
        _License(
            package_name='HTS Voice "Mei"',
            package_version=None,
            license_name="Creative Commons Attribution 3.0 license",
            license_text="https://raw.githubusercontent.com/r9y9/pyopenjtalk/master/pyopenjtalk/htsvoice/LICENSE_mei_normal.htsvoice",
            license_text_type="remote_address",
        ),
        _License(
            package_name="VOICEVOX CORE",
            package_version=None,
            license_name="MIT license",
            license_text="https://raw.githubusercontent.com/VOICEVOX/voicevox_core/main/LICENSE",
            license_text_type="remote_address",
        ),
        _License(
            package_name="VOICEVOX ENGINE",
            package_version=None,
            license_name="LGPL license",
            license_text="https://raw.githubusercontent.com/VOICEVOX/voicevox_engine/master/LGPL_LICENSE",
            license_text_type="remote_address",
        ),
        _License(
            package_name="world",
            package_version=None,
            license_name="Modified BSD license",
            license_text="https://raw.githubusercontent.com/mmorise/World/master/LICENSE.txt",
            license_text_type="remote_address",
        ),
        _License(
            package_name="PyTorch",
            package_version="1.9.0",
            license_name="BSD-style license",
            license_text="https://raw.githubusercontent.com/pytorch/pytorch/master/LICENSE",
            license_text_type="remote_address",
        ),
        _License(
            package_name="ONNX Runtime",
            package_version="1.17.3",
            license_name="MIT license",
            license_text="https://raw.githubusercontent.com/microsoft/onnxruntime/master/LICENSE",
            license_text_type="remote_address",
        ),
        _License(
            package_name="Python",
            package_version=python_version,
            license_name="Python Software Foundation License",
            license_text=f"https://raw.githubusercontent.com/python/cpython/v{python_version}/LICENSE",
            license_text_type="remote_address",
        ),
        _License(
            package_name="libsndfile-binaries",
            package_version="1.2.2",
            license_name="LGPL-2.1 license",
            license_text="https://raw.githubusercontent.com/bastibe/libsndfile-binaries/refs/tags/1.2.2/COPYING",
            license_text_type="remote_address",
        ),
        _License(
            package_name="libogg",
            package_version="1.3.5",
            license_name="BSD 3-clause license",
            license_text="https://raw.githubusercontent.com/xiph/ogg/v1.3.5/COPYING",
            license_text_type="remote_address",
        ),
        _License(
            package_name="libvorbis",
            package_version="1.3.7",
            license_name="BSD 3-clause license",
            license_text="https://raw.githubusercontent.com/xiph/vorbis/v1.3.7/COPYING",
            license_text_type="remote_address",
        ),
        # libflac
        _License(
            package_name="FLAC",
            package_version="1.4.3",
            license_name="Xiph.org's BSD-like license",
            license_text="https://raw.githubusercontent.com/xiph/flac/1.4.3/COPYING.Xiph",
            license_text_type="remote_address",
        ),
        # libopus
        _License(
            package_name="Opus",
            package_version="1.4",
            license_name="BSD 3-clause license",
            license_text="https://raw.githubusercontent.com/xiph/opus/v1.4/COPYING",
            license_text_type="remote_address",
        ),
        # https://sourceforge.net/projects/mpg123/files/mpg123/1.32.3/
        _License(
            package_name="mpg123",
            package_version="1.32.3",
            license_name="LGPL-2.1 license",
            license_text="tools/licenses/mpg123/COPYING",
            license_text_type="local_address",
        ),
        # liblame
        # https://sourceforge.net/projects/lame/files/lame/3.100/
        _License(
            package_name="lame",
            package_version="3.100",
            license_name="LGPL-2.0 license",
            license_text="https://svn.code.sf.net/p/lame/svn/tags/RELEASE__3_100/lame/COPYING",
            license_text_type="remote_address",
        ),
        # license text from CUDA 12.8.1
        # https://developer.nvidia.com/cuda-12-8-1-download-archive?target_os=Windows&target_arch=x86_64&target_version=10&target_type=exe_local
        # https://developer.download.nvidia.com/compute/cuda/12.8.1/local_installers/cuda_12.8.1_572.61_windows.exe
        # cuda_12.8.1_572.61_windows.exe (cuda_documentation/Doc/EULA.txt)
        _License(
            package_name="CUDA Toolkit",
            package_version="12.8.1",
            license_name=None,
            license_text="tools/licenses/cuda/EULA.txt",
            license_text_type="local_address",
        ),
        # license text from cuDNN v8.9.7 (December 5th, 2023), for CUDA 12.x, cuDNN Library for Windows
        # https://developer.nvidia.com/rdp/cudnn-archive
        # https://developer.download.nvidia.com/compute/cudnn/redist/cudnn/windows-x86_64/cudnn-windows-x86_64-8.9.7.29_cuda12-archive.zip
        # cudnn-windows-x86_64-8.9.7.29_cuda12-archive.zip (cudnn-windows-x86_64-8.9.7.29_cuda12-archive/LICENSE)
        _License(
            package_name="cuDNN",
            package_version="8.9.7",
            license_name=None,
            license_text="tools/licenses/cudnn/LICENSE",
            license_text_type="local_address",
        ),
        # Python-SoXR (`soxr`, https://github.com/dofuuz/python-soxr) が依存するライブラリ
        _License(
            package_name="libsoxr",
            package_version=None,
            license_name="LGPL-2.1 license",
            license_text="https://raw.githubusercontent.com/dofuuz/soxr/master/LICENCE",
            license_text_type="remote_address",
        ),
        _License(
            package_name="PFFFT",
            package_version=None,
            license_name="BSD-like",
            license_text="https://raw.githubusercontent.com/dofuuz/python-soxr/main/cmake/LICENSE-PFFFT.txt",
            license_text_type="remote_address",
        ),
        #
    ]


def _patch_licenses_manually(licenses: list[_License]) -> None:
    """手動でライセンス情報を修正する。"""
    for license in licenses:
        if license.package_name == "kanalizer":
            # kanalizerのwheelをビルドするときに使ったライブラリの情報を追加する
            for p in importlib.metadata.files("kanalizer"):  # type: ignore
                if p.name == "NOTICE.md":
                    notice_md = Path(p.locate())
                    break
            else:
                raise Exception("kanalizerのNOTICE.mdが見つかりませんでした。")
            license.license_text += "\n\n"
            license.license_text += notice_md.read_text(encoding="utf-8")


def _generate_licenses() -> list[_License]:
    pip_licenses = _acquire_licenses_of_pip_managed_libraries()
    licenses = _update_licenses(pip_licenses)
    _validate_license_compliance(licenses)
    _add_licenses_manually(licenses)
    _patch_licenses_manually(licenses)

    return licenses


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output_path", type=str)
    args = parser.parse_args()

    output_path = args.output_path

    licenses = _generate_licenses()

    # dump
    out = Path(output_path).open("w") if output_path else sys.stdout
    json.dump(
        [
            {
                "name": license.package_name,
                "version": license.package_version,
                "license": license.license_name,
                "text": license.license_text,
            }
            for license in licenses
        ],
        out,
    )
