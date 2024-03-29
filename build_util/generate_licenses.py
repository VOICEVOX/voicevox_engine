"""依存パッケージ/ライブラリのライセンス情報を収集・定型化・保存する。"""

import json
import os
import subprocess
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, Optional, TypeAlias


@dataclass
class License:
    name: str
    version: Optional[str]
    license: Optional[str]
    text: str


# ライセンス情報: (place_type, name, version, license_type, place)
LicenseInfo: TypeAlias = tuple[
    Literal["local", "remote"], str, str | None, str | None, str
]


def generate_licenses() -> list[License]:
    """依存パッケージ/ライブラリのライセンス情報を収集し、定型化する。"""

    licenses: list[License] = []

    python_ver = "3.11.3"

    # fmt: off
    license_infos: list[LicenseInfo] = [
        # https://sourceforge.net/projects/open-jtalk/files/Open%20JTalk/open_jtalk-1.11/
        ("local",  "Open JTalk",                "1.11",     "Modified BSD license",                     "docs/licenses/open_jtalk/COPYING"),                                                                            # noqa: B950,E241
        ("local",  "MeCab",                     None,       "Modified BSD license",                     "docs/licenses/open_jtalk/mecab/COPYING"),                                                                      # noqa: B950,E241
        ("local",  "NAIST Japanese Dictionary", None,       "Modified BSD license",                     "docs/licenses//open_jtalk/mecab-naist-jdic/COPYING"),                                                          # noqa: B950,E241
        ("remote", 'HTS Voice "Mei"',           None,       "Creative Commons Attribution 3.0 license", "https://raw.githubusercontent.com/r9y9/pyopenjtalk/master/pyopenjtalk/htsvoice/LICENSE_mei_normal.htsvoice"),  # noqa: B950,E241
        ("remote", "VOICEVOX CORE",             None,       "MIT license",                              "https://raw.githubusercontent.com/VOICEVOX/voicevox_core/main/LICENSE"),                                       # noqa: B950,E241
        ("remote", "VOICEVOX ENGINE",           None,       "LGPL license",                             "https://raw.githubusercontent.com/VOICEVOX/voicevox_engine/master/LGPL_LICENSE"),                              # noqa: B950,E241
        ("remote", "world",                     None,       "Modified BSD license",                     "https://raw.githubusercontent.com/mmorise/World/master/LICENSE.txt"),                                          # noqa: B950,E241
        ("remote", "PyTorch",                   "1.9.0",    "BSD-style license",                        "https://raw.githubusercontent.com/pytorch/pytorch/master/LICENSE"),                                            # noqa: B950,E241
        ("remote", "ONNX Runtime",              "1.13.1",   "MIT license",                              "https://raw.githubusercontent.com/microsoft/onnxruntime/master/LICENSE"),                                      # noqa: B950,E241
        ("remote", "Python",                    python_ver, "Python Software Foundation License",       f"https://raw.githubusercontent.com/python/cpython/v{python_ver}/LICENSE"),                                     # noqa: B950,E241
    ]
    # fmt: on

    for info in license_infos:
        # ローカルに事前保存されたライセンス情報を登録する
        if info[0] == "local":
            licenses.append(
                License(
                    name=info[1],
                    version=info[2],
                    license=info[3],
                    text=Path(info[4]).read_text(),
                )
            )
        # リモートに存在するライセンス情報を登録する
        elif info[0] == "remote":
            with urllib.request.urlopen(info[4]) as res:
                licenses.append(
                    License(
                        name=info[1],
                        version=info[2],
                        license=info[3],
                        text=res.read().decode(),
                    )
                )
        else:
            raise Exception("Never occur")

    # `pip install` されたパッケージのライセンス情報を登録する
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
    # /pip

    # fmt: off
    license_infos = [
        ("remote", "OpenBLAS",            None,     "BSD 3-clause license",        "https://raw.githubusercontent.com/xianyi/OpenBLAS/develop/LICENSE"),                                               # noqa: B950,E241
        ("remote", "libsndfile-binaries", "1.2.0",  "LGPL-2.1 license",            "https://raw.githubusercontent.com/bastibe/libsndfile-binaries/d9887ef926bb11cf1a2526be4ab6f9dc690234c0/COPYING"),  # noqa: B950,E241
        ("remote", "libogg",              "1.3.5",  "BSD 3-clause license",        "https://raw.githubusercontent.com/xiph/ogg/v1.3.5/COPYING"),                                                       # noqa: B950,E241
        ("remote", "libvorbis",           "1.3.7",  "BSD 3-clause license",        "https://raw.githubusercontent.com/xiph/vorbis/v1.3.7/COPYING"),                                                    # noqa: B950,E241
        ("remote", "FLAC",                "1.4.2",  "Xiph.org's BSD-like license", "https://raw.githubusercontent.com/xiph/flac/1.4.2/COPYING.Xiph"),                                                  # noqa: B950,E241
        ("remote", "Opus",                "1.3.1",  "BSD 3-clause license",        "https://raw.githubusercontent.com/xiph/opus/v1.3.1/COPYING"),                                                      # noqa: B950,E241
        # https://sourceforge.net/projects/mpg123/files/mpg123/1.30.2/                                                                                                                                 # noqa: B950,E241
        ("local",  "mpg123",              "1.30.2", "LGPL-2.1 license",            "docs/licenses/mpg123/COPYING"),                                                                                    # noqa: B950,E241
        # https://sourceforge.net/projects/lame/files/lame/3.100/                                                                                                                                      # noqa: B950,E241
        ("remote", "lame",                "3.100",  "LGPL-2.0 license",            "https://svn.code.sf.net/p/lame/svn/tags/RELEASE__3_100/lame/COPYING"),                                             # noqa: B950,E241
        # https://developer.nvidia.com/cuda-11-8-0-download-archive?target_os=Windows&target_arch=x86_64&target_version=10&target_type=exe_local                                                       # noqa: B950,E241
        # https://developer.download.nvidia.com/compute/cuda/11.8.0/local_installers/cuda_11.8.0_522.06_windows.exe                                                                                    # noqa: B950,E241
        # cuda_11.8.0_522.06_windows.exe (cuda_documentation/Doc/EULA.txt)                                                                                                                             # noqa: B950,E241
        ("local",  "CUDA Toolkit",        "11.8.0", None,                          "docs/licenses/cuda/EULA.txt"),                                                                                     # noqa: B950,E241
        # cuDNN v8.9.2 (June 1st, 2023), for CUDA 11.x, cuDNN Library for Windows                                                                                                                      # noqa: B950,E241
        # https://developer.nvidia.com/rdp/cudnn-archive                                                                                                                                               # noqa: B950,E241
        # https://developer.download.nvidia.com/compute/cudnn/redist/cudnn/windows-x86_64/cudnn-windows-x86_64-8.9.2.26_cuda11-archive.zip                                                             # noqa: B950,E241
        # cudnn-windows-x86_64-8.9.2.26_cuda11-archive.zip (cudnn-windows-x86_64-8.9.2.26_cuda11-archive/LICENSE)                                                                                      # noqa: B950,E241
        ("local",  "cuDNN",               "8.9.2",  None,                          "docs/licenses/cudnn/LICENSE"),                                                                                     # noqa: B950,E241
    ]
    # fmt: on

    for info in license_infos:
        # ローカルに事前保存されたライセンス情報を登録する
        if info[0] == "local":
            licenses.append(
                License(
                    name=info[1],
                    version=info[2],
                    license=info[3],
                    text=Path(info[4]).read_text(),
                )
            )
        # リモートに存在するライセンス情報を登録する
        elif info[0] == "remote":
            with urllib.request.urlopen(info[4]) as res:
                licenses.append(
                    License(
                        name=info[1],
                        version=info[2],
                        license=info[3],
                        text=res.read().decode(),
                    )
                )
        else:
            raise Exception("Never occur")

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
        [asdict(license) for license in licenses],
        out,
    )
