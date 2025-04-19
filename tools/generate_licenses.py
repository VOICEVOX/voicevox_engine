"""
VOICEVOX ENGINE の実行に必要なライブラリのライセンス一覧を作成する。

このスクリプトの実行環境にインストールされている Python ライブラリのライセンス一覧を取得する。
その一覧に対し、このスクリプトにハードコードされたライセンス一覧を追加する。
このライセンス一覧をファイルとして出力する。
"""

import json
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, assert_never

from pydantic import TypeAdapter


class _LicenseError(Exception):
    # License違反があった場合、このエラーを出します。
    pass


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
                assert_never("型で保護され実行されないはずのパスが実行されました")


def _get_license_text(text_url: str) -> str:
    """URL が指すテキストを取得する。"""
    with urllib.request.urlopen(text_url) as res:
        # NOTE: `urlopen` 返り値の型が貧弱なため型チェックを無視する
        return res.read().decode()  # type: ignore


def _generate_licenses() -> list[_License]:
    raw_licenses = _acquire_licenses_of_pip_managed_libraries()
    licenses = _update_licenses(raw_licenses)
    _validate_license_compliance(licenses)
    _add_licenses_manually(licenses)

    return licenses


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


def _update_licenses(raw_licenses: list[_PipLicense]) -> list[_License]:
    """pip から取得したライセンス情報を更新する。"""
    package_to_license_url = {
        "distlib": "https://bitbucket.org/pypa/distlib/raw/7d93712134b28401407da27382f2b6236c87623a/LICENSE.txt",
        "future": "https://raw.githubusercontent.com/PythonCharmers/python-future/master/LICENSE.txt",
        "jsonschema": "https://raw.githubusercontent.com/python-jsonschema/jsonschema/dbc398245a583cb2366795dc529ae042d10c1577/COPYING",
        "lockfile": "https://opendev.org/openstack/pylockfile/raw/tag/0.12.2/LICENSE",
        "pefile": "https://raw.githubusercontent.com/erocarrera/pefile/master/LICENSE",
        "platformdirs": "https://raw.githubusercontent.com/platformdirs/platformdirs/aa671aaa97913c7b948567f4d9c77d4f98bfa134/LICENSE",
        "pyopenjtalk": "https://raw.githubusercontent.com/r9y9/pyopenjtalk/master/LICENSE.md",
        "python-multipart": "https://raw.githubusercontent.com/andrew-d/python-multipart/master/LICENSE.txt",
        "romkan": "https://raw.githubusercontent.com/soimort/python-romkan/master/LICENSE",
        "webencodings": "https://raw.githubusercontent.com/gsnedders/python-webencodings/fa2cb5d75ab41e63ace691bc0825d3432ba7d694/LICENSE",
    }

    updated_licenses = []

    for raw_license in raw_licenses:
        package_name = raw_license.Name.lower()

        # ライセンス文が pip から取得できていない場合、pip 外から補う
        if raw_license.LicenseText == "UNKNOWN":
            if package_name == "core" and raw_license.Version == "0.0.0":
                continue
            if package_name not in package_to_license_url:
                # ライセンスがpypiに無い
                raise Exception(f"No License info provided for {package_name}")
            text_url = package_to_license_url[package_name]
            raw_license.LicenseText = _get_license_text(text_url)

        # soxr
        if package_name == "soxr":
            text_url = "https://raw.githubusercontent.com/dofuuz/python-soxr/v0.3.6/LICENSE.txt"
            raw_license.LicenseText = _get_license_text(text_url)

        updated_licenses.append(
            _License(
                package_name=raw_license.Name,
                package_version=raw_license.Version,
                license_name=raw_license.License,
                license_text=raw_license.LicenseText,
                license_text_type="raw",
            )
        )

    return updated_licenses


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
            package_version="1.13.1",
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
            package_version="1.2.0",
            license_name="LGPL-2.1 license",
            license_text="https://raw.githubusercontent.com/bastibe/libsndfile-binaries/d9887ef926bb11cf1a2526be4ab6f9dc690234c0/COPYING",
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
            package_version="1.4.2",
            license_name="Xiph.org's BSD-like license",
            license_text="https://raw.githubusercontent.com/xiph/flac/1.4.2/COPYING.Xiph",
            license_text_type="remote_address",
        ),
        # libopus
        _License(
            package_name="Opus",
            package_version="1.3.1",
            license_name="BSD 3-clause license",
            license_text="https://raw.githubusercontent.com/xiph/opus/v1.3.1/COPYING",
            license_text_type="remote_address",
        ),
        # https://sourceforge.net/projects/mpg123/files/mpg123/1.30.2/
        _License(
            package_name="mpg123",
            package_version="1.30.2",
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
        # license text from CUDA 11.8.0
        # https://developer.nvidia.com/cuda-11-8-0-download-archive?target_os=Windows&target_arch=x86_64&target_version=10&target_type=exe_local
        # https://developer.download.nvidia.com/compute/cuda/11.8.0/local_installers/cuda_11.8.0_522.06_windows.exe
        # cuda_11.8.0_522.06_windows.exe (cuda_documentation/Doc/EULA.txt)
        _License(
            package_name="CUDA Toolkit",
            package_version="11.8.0",
            license_name=None,
            license_text="tools/licenses/cuda/EULA.txt",
            license_text_type="local_address",
        ),
        # license text from cuDNN v8.9.2 (June 1st, 2023), for CUDA 11.x, cuDNN Library for Windows
        # https://developer.nvidia.com/rdp/cudnn-archive
        # https://developer.download.nvidia.com/compute/cudnn/redist/cudnn/windows-x86_64/cudnn-windows-x86_64-8.9.2.26_cuda11-archive.zip
        # cudnn-windows-x86_64-8.9.2.26_cuda11-archive.zip (cudnn-windows-x86_64-8.9.2.26_cuda11-archive/LICENSE)
        _License(
            package_name="cuDNN",
            package_version="8.9.2",
            license_name=None,
            license_text="tools/licenses/cudnn/LICENSE",
            license_text_type="local_address",
        ),
    ]


if __name__ == "__main__":
    import argparse

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
