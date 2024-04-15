import json
import os
import subprocess
import urllib.request
from pathlib import Path
from typing import Literal


class LicenseError(Exception):
    # License違反があった場合、このエラーを出します。
    pass


class License:
    def __init__(
        self,
        name: str,  # TODO: `package_name` へリネーム
        version: str | None,  # TODO: `package_version` へリネーム
        license: str | None,  # TODO: `license_name` へリネーム
        text: str,  # TODO: `license_text` へリネーム
        license_text_type: Literal["raw", "local_address", "remote_address"],
    ):
        self.name = name  # TODO: `package_name` へリネーム
        self.version = version  # TODO: `package_version` へリネーム
        self.license = license  # TODO: `license_name` へリネーム

        if license_text_type == "raw":
            self.text = text  # TODO: `license_text` へリネーム
        elif license_text_type == "local_address":
            # ライセンステキストをローカルのライセンスファイルから抽出する
            self.text = Path(text).read_text(encoding="utf8")
        elif license_text_type == "remote_address":
            # ライセンステキストをリモートのライセンスファイルから抽出する
            with urllib.request.urlopen(text) as res:
                license_text: str = res.read().decode()
                self.text = license_text
        else:
            raise Exception("型で保護され実行されないはずのパスが実行されました")


def generate_licenses() -> list[License]:
    licenses: list[License] = []

    # openjtalk
    # https://sourceforge.net/projects/open-jtalk/files/Open%20JTalk/open_jtalk-1.11/
    licenses.append(
        License(
            name="Open JTalk",
            version="1.11",
            license="Modified BSD license",
            text="docs/licenses/open_jtalk/COPYING",
            license_text_type="local_address",
        )
    )
    licenses.append(
        License(
            name="MeCab",
            version=None,
            license="Modified BSD license",
            text="docs/licenses/open_jtalk/mecab/COPYING",
            license_text_type="local_address",
        )
    )
    licenses.append(
        License(
            name="NAIST Japanese Dictionary",
            version=None,
            license="Modified BSD license",
            text="docs/licenses//open_jtalk/mecab-naist-jdic/COPYING",
            license_text_type="local_address",
        )
    )
    licenses.append(
        License(
            name='HTS Voice "Mei"',
            version=None,
            license="Creative Commons Attribution 3.0 license",
            text="https://raw.githubusercontent.com/r9y9/pyopenjtalk/master/pyopenjtalk/htsvoice/LICENSE_mei_normal.htsvoice",  # noqa: B950
            license_text_type="remote_address",
        )
    )

    # VOICEVOX CORE
    licenses.append(
        License(
            name="VOICEVOX CORE",
            version=None,
            license="MIT license",
            text="https://raw.githubusercontent.com/VOICEVOX/voicevox_core/main/LICENSE",
            license_text_type="remote_address",
        )
    )

    # VOICEVOX ENGINE
    licenses.append(
        License(
            name="VOICEVOX ENGINE",
            version=None,
            license="LGPL license",
            text="https://raw.githubusercontent.com/VOICEVOX/voicevox_engine/master/LGPL_LICENSE",
            license_text_type="remote_address",
        )
    )

    # world
    licenses.append(
        License(
            name="world",
            version=None,
            license="Modified BSD license",
            text="https://raw.githubusercontent.com/mmorise/World/master/LICENSE.txt",
            license_text_type="remote_address",
        )
    )

    # pytorch
    licenses.append(
        License(
            name="PyTorch",
            version="1.9.0",
            license="BSD-style license",
            text="https://raw.githubusercontent.com/pytorch/pytorch/master/LICENSE",
            license_text_type="remote_address",
        )
    )

    # onnxruntime
    licenses.append(
        License(
            name="ONNX Runtime",
            version="1.13.1",
            license="MIT license",
            text="https://raw.githubusercontent.com/microsoft/onnxruntime/master/LICENSE",
            license_text_type="remote_address",
        )
    )

    # Python
    python_version = "3.11.3"
    licenses.append(
        License(
            name="Python",
            version=python_version,
            license="Python Software Foundation License",
            text=f"https://raw.githubusercontent.com/python/cpython/v{python_version}/LICENSE",
            license_text_type="remote_address",
        )
    )

    # pip
    try:
        pip_licenses_output = subprocess.run(
            "pip-licenses "
            "--from=mixed "
            "--format=json "
            "--with-urls "
            "--with-license-file "
            "--no-license-path ",
            shell=True,
            capture_output=True,
            check=True,
            env=os.environ,
        ).stdout.decode()
    except subprocess.CalledProcessError as err:
        raise Exception(
            f"command output:\n{err.stderr and err.stderr.decode()}"
        ) from err

    licenses_json = json.loads(pip_licenses_output)
    for license_json in licenses_json:
        license = License(
            name=license_json["Name"],
            version=license_json["Version"],
            license=license_json["License"],
            text=license_json["LicenseText"],
            license_text_type="raw",
        )
        license_names_str = license.license or ""
        license_names = license_names_str.split("; ")
        for license_name in license_names:
            if license_name in [
                "GNU General Public License v2 (GPLv2)",
                "GNU General Public License (GPL)",
                "GNU General Public License v3 (GPLv3)",
                "GNU Affero General Public License v3 (AGPL-3)",
            ]:
                raise LicenseError(
                    f"ライセンス違反: {license.name} is {license.license}"
                )
        # FIXME: assert license type
        if license.text == "UNKNOWN":
            if license.name.lower() == "core" and license.version == "0.0.0":
                continue
            elif license.name.lower() == "future":
                with urllib.request.urlopen(
                    "https://raw.githubusercontent.com/PythonCharmers/python-future/master/LICENSE.txt"  # noqa: B950
                ) as res:
                    license.text = res.read().decode()
            elif license.name.lower() == "pefile":
                with urllib.request.urlopen(
                    "https://raw.githubusercontent.com/erocarrera/pefile/master/LICENSE"  # noqa: B950
                ) as res:
                    license.text = res.read().decode()
            elif license.name.lower() == "pyopenjtalk":
                with urllib.request.urlopen(
                    "https://raw.githubusercontent.com/r9y9/pyopenjtalk/master/LICENSE.md"
                ) as res:
                    license.text = res.read().decode()
            elif license.name.lower() == "python-multipart":
                with urllib.request.urlopen(
                    "https://raw.githubusercontent.com/andrew-d/python-multipart/master/LICENSE.txt"  # noqa: B950
                ) as res:
                    license.text = res.read().decode()
            elif license.name.lower() == "romkan":
                with urllib.request.urlopen(
                    "https://raw.githubusercontent.com/soimort/python-romkan/master/LICENSE"
                ) as res:
                    license.text = res.read().decode()
            elif license.name.lower() == "distlib":
                with urllib.request.urlopen(
                    "https://bitbucket.org/pypa/distlib/raw/7d93712134b28401407da27382f2b6236c87623a/LICENSE.txt"  # noqa: B950
                ) as res:
                    license.text = res.read().decode()
            elif license.name.lower() == "jsonschema":
                with urllib.request.urlopen(
                    "https://raw.githubusercontent.com/python-jsonschema/jsonschema/dbc398245a583cb2366795dc529ae042d10c1577/COPYING"
                ) as res:
                    license.text = res.read().decode()
            elif license.name.lower() == "lockfile":
                with urllib.request.urlopen(
                    "https://opendev.org/openstack/pylockfile/raw/tag/0.12.2/LICENSE"
                ) as res:
                    license.text = res.read().decode()
            elif license.name.lower() == "platformdirs":
                with urllib.request.urlopen(
                    "https://raw.githubusercontent.com/platformdirs/platformdirs/aa671aaa97913c7b948567f4d9c77d4f98bfa134/LICENSE"
                ) as res:
                    license.text = res.read().decode()
            elif license.name.lower() == "webencodings":
                with urllib.request.urlopen(
                    "https://raw.githubusercontent.com/gsnedders/python-webencodings/fa2cb5d75ab41e63ace691bc0825d3432ba7d694/LICENSE"
                ) as res:
                    license.text = res.read().decode()
            else:
                # ライセンスがpypiに無い
                raise Exception(f"No License info provided for {license.name}")

        # soxr
        if license.name.lower() == "soxr":
            with urllib.request.urlopen(
                "https://raw.githubusercontent.com/dofuuz/python-soxr/v0.3.6/LICENSE.txt"
            ) as res:
                license.text = res.read().decode()

        licenses.append(license)

    # OpenBLAS
    licenses.append(
        License(
            name="OpenBLAS",
            version=None,
            license="BSD 3-clause license",
            text="https://raw.githubusercontent.com/xianyi/OpenBLAS/develop/LICENSE",
            license_text_type="remote_address",
        )
    )

    # libsndfile-binaries
    licenses.append(
        License(
            name="libsndfile-binaries",
            version="1.2.0",
            license="LGPL-2.1 license",
            text="https://raw.githubusercontent.com/bastibe/libsndfile-binaries/d9887ef926bb11cf1a2526be4ab6f9dc690234c0/COPYING",  # noqa: B950
            license_text_type="remote_address",
        )
    )

    # libogg
    licenses.append(
        License(
            name="libogg",
            version="1.3.5",
            license="BSD 3-clause license",
            text="https://raw.githubusercontent.com/xiph/ogg/v1.3.5/COPYING",
            license_text_type="remote_address",
        )
    )

    # libvorbis
    licenses.append(
        License(
            name="libvorbis",
            version="1.3.7",
            license="BSD 3-clause license",
            text="https://raw.githubusercontent.com/xiph/vorbis/v1.3.7/COPYING",
            license_text_type="remote_address",
        )
    )

    # libflac
    licenses.append(
        License(
            name="FLAC",
            version="1.4.2",
            license="Xiph.org's BSD-like license",
            text="https://raw.githubusercontent.com/xiph/flac/1.4.2/COPYING.Xiph",
            license_text_type="remote_address",
        )
    )

    # libopus
    licenses.append(
        License(
            name="Opus",
            version="1.3.1",
            license="BSD 3-clause license",
            text="https://raw.githubusercontent.com/xiph/opus/v1.3.1/COPYING",
            license_text_type="remote_address",
        )
    )

    # mpg123
    # https://sourceforge.net/projects/mpg123/files/mpg123/1.30.2/
    licenses.append(
        License(
            name="mpg123",
            version="1.30.2",
            license="LGPL-2.1 license",
            text="docs/licenses/mpg123/COPYING",
            license_text_type="local_address",
        )
    )

    # liblame
    # https://sourceforge.net/projects/lame/files/lame/3.100/
    licenses.append(
        License(
            name="lame",
            version="3.100",
            license="LGPL-2.0 license",
            text="https://svn.code.sf.net/p/lame/svn/tags/RELEASE__3_100/lame/COPYING",
            license_text_type="remote_address",
        )
    )

    # cuda
    # license text from CUDA 11.8.0
    # https://developer.nvidia.com/cuda-11-8-0-download-archive?target_os=Windows&target_arch=x86_64&target_version=10&target_type=exe_local # noqa: B950
    # https://developer.download.nvidia.com/compute/cuda/11.8.0/local_installers/cuda_11.8.0_522.06_windows.exe # noqa: B950
    # cuda_11.8.0_522.06_windows.exe (cuda_documentation/Doc/EULA.txt)
    licenses.append(
        License(
            name="CUDA Toolkit",
            version="11.8.0",
            license=None,
            text="docs/licenses/cuda/EULA.txt",
            license_text_type="local_address",
        )
    )
    # cudnn
    # license text from
    # cuDNN v8.9.2 (June 1st, 2023), for CUDA 11.x, cuDNN Library for Windows
    # https://developer.nvidia.com/rdp/cudnn-archive # noqa: B950
    # https://developer.download.nvidia.com/compute/cudnn/redist/cudnn/windows-x86_64/cudnn-windows-x86_64-8.9.2.26_cuda11-archive.zip # noqa: B950
    # cudnn-windows-x86_64-8.9.2.26_cuda11-archive.zip (cudnn-windows-x86_64-8.9.2.26_cuda11-archive/LICENSE) # noqa: B950
    licenses.append(
        License(
            name="cuDNN",
            version="8.9.2",
            license=None,
            text="docs/licenses/cudnn/LICENSE",
            license_text_type="local_address",
        )
    )

    return licenses


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output_path", type=str)
    args = parser.parse_args()

    output_path = args.output_path

    licenses = generate_licenses()

    # dump
    out = Path(output_path).open("w") if output_path else sys.stdout
    json.dump(
        [
            {
                "name": license.name,
                "version": license.version,
                "license": license.license,
                "text": license.text,
            }
            for license in licenses
        ],
        out,
    )
