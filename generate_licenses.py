import json
import os
import subprocess
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class License:
    name: str
    version: Optional[str]
    license: Optional[str]
    text: str


def generate_licenses() -> List[License]:
    licenses: List[License] = []

    # openjtalk
    # https://sourceforge.net/projects/open-jtalk/files/Open%20JTalk/open_jtalk-1.11/
    licenses.append(
        License(
            name="Open JTalk",
            version="1.11",
            license="Modified BSD license",
            text=Path("docs/licenses/open_jtalk/COPYING").read_text(),
        )
    )
    licenses.append(
        License(
            name="MeCab",
            version=None,
            license="Modified BSD license",
            text=Path("docs/licenses/open_jtalk/mecab/COPYING").read_text(),
        )
    )
    licenses.append(
        License(
            name="NAIST Japanese Dictionary",
            version=None,
            license="Modified BSD license",
            text=Path("docs/licenses//open_jtalk/mecab-naist-jdic/COPYING").read_text(),
        )
    )
    with urllib.request.urlopen(
        "https://raw.githubusercontent.com/r9y9/pyopenjtalk/master/pyopenjtalk/htsvoice/LICENSE_mei_normal.htsvoice"  # noqa: B950
    ) as res:
        licenses.append(
            License(
                name='HTS Voice "Mei"',
                version=None,
                license="Creative Commons Attribution 3.0 license",
                text=res.read().decode(),
            )
        )

    # world
    with urllib.request.urlopen(
        "https://raw.githubusercontent.com/mmorise/World/master/LICENSE.txt"
    ) as res:
        licenses.append(
            License(
                name="world",
                version=None,
                license="Modified BSD license",
                text=res.read().decode(),
            )
        )

    # pytorch
    with urllib.request.urlopen(
        "https://raw.githubusercontent.com/pytorch/pytorch/master/LICENSE"
    ) as res:
        licenses.append(
            License(
                name="PyTorch",
                version="1.9.0",
                license="BSD-style license",
                text=res.read().decode(),
            )
        )

    # Python
    python_version = "3.7.12"
    with urllib.request.urlopen(
        f"https://raw.githubusercontent.com/python/cpython/v{python_version}/LICENSE"
    ) as res:
        licenses.append(
            License(
                name="Python",
                version=python_version,
                license="Python Software Foundation License",
                text=res.read().decode(),
            )
        )

    # pip
    licenses_json = json.loads(
        subprocess.run(
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
    )
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
            elif license.name.lower() == "nuitka":
                with urllib.request.urlopen(
                    "https://raw.githubusercontent.com/Nuitka/Nuitka/develop/LICENSE.txt"
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
            elif license.name.lower() == "resampy":
                with urllib.request.urlopen(
                    "https://raw.githubusercontent.com/bmcfee/resampy/master/LICENSE"
                ) as res:
                    license.text = res.read().decode()
            else:
                # ライセンスがpypiに無い
                raise Exception(f"No License info provided for {license.name}")
        licenses.append(license)

    # OpenBLAS
    with urllib.request.urlopen(
        "https://raw.githubusercontent.com/xianyi/OpenBLAS/develop/LICENSE"
    ) as res:
        licenses.append(
            License(
                name="OpenBLAS",
                version=None,
                license="BSD 3-clause license",
                text=res.read().decode(),
            )
        )

    # libsndfile-binaries
    with urllib.request.urlopen(
        "https://raw.githubusercontent.com/bastibe/libsndfile-binaries/84cb164928f17c7ca0c1e5c40342c20ce2b90e8c/COPYING"  # noqa: B950
    ) as res:
        licenses.append(
            License(
                name="libsndfile-binaries",
                version="1.0.28",
                license="LGPL-2.1 license",
                text=res.read().decode(),
            )
        )

    # libogg
    with urllib.request.urlopen(
        "https://raw.githubusercontent.com/xiph/ogg/v1.3.2/COPYING"
    ) as res:
        licenses.append(
            License(
                name="libogg",
                version="1.3.2",
                license="BSD 3-clause license",
                text=res.read().decode(),
            )
        )

    # libvorbis
    with urllib.request.urlopen(
        "https://raw.githubusercontent.com/xiph/vorbis/v1.3.5/COPYING"
    ) as res:
        licenses.append(
            License(
                name="libvorbis",
                version="1.3.5",
                license="BSD 3-clause license",
                text=res.read().decode(),
            )
        )

    # libflac
    with urllib.request.urlopen(
        "https://raw.githubusercontent.com/xiph/flac/1.3.2/COPYING.Xiph"
    ) as res:
        licenses.append(
            License(
                name="FLAC",
                version="1.3.2",
                license="Xiph.org's BSD-like license",
                text=res.read().decode(),
            )
        )

    # cuda
    # license text from CUDA 11.1.1
    # https://developer.nvidia.com/cuda-11.1.1-download-archive?target_os=Windows&target_arch=x86_64&target_version=10&target_type=exelocal # noqa: B950
    # https://developer.download.nvidia.com/compute/cuda/11.4.2/local_installers/cuda_11.4.2_471.41_win10.exe # noqa: B950
    # cuda_11.1.1_456.81_win10.exe (cuda_documentation/Doc/EULA.txt)
    licenses.append(
        License(
            name="CUDA Toolkit",
            version="11.1.1",
            license=None,
            text=Path("docs/licenses/cuda/EULA.txt").read_text(encoding="utf8"),
        )
    )
    # cudnn
    # license text from
    # cuDNN v7.6.5 (November 18th, 2019), for CUDA 10.2, cuDNN Library for Windows 10
    # https://developer.nvidia.com/rdp/cudnn-archive # noqa: B950
    # https://developer.nvidia.com/compute/machine-learning/cudnn/secure/7.6.5.32/Production/10.2_20191118/cudnn-10.2-windows10-x64-v7.6.5.32.zip # noqa: B950
    # cudnn-10.2-windows10-x64-v7.6.5.32.zip (cuda/NVIDIA_SLA_cuDNN_Support.txt)
    licenses.append(
        License(
            name="cuDNN",
            version="7.6.5",
            license=None,
            text=Path("docs/licenses/cuda/NVIDIA_SLA_cuDNN_Support.txt").read_text(
                encoding="utf8"
            ),
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
        [asdict(license) for license in licenses],
        out,
    )
