# First version by @Hiroshiba https://github.com/Hiroshiba/voicevox/issues/219#issuecomment-927917044

import json
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


licenses: List[License] = []

# openjtalk
licenses.append(
    License(
        name="Open JTalk",
        version="1.11",
        license="Modified BSD license",
        text=Path("/path/to/open_jtalk/COPYING").read_text(),
    )
)
licenses.append(
    License(
        name="MeCab",
        version=None,
        license="Modified BSD license",
        text=Path("/path/to/open_jtalk/mecab/COPYING").read_text(),
    )
)
licenses.append(
    License(
        name="NAIST Japanese Dictionary",
        version=None,
        license="Modified BSD license",
        text=Path(
            "/path/to/open_jtalk/mecab-naist-jdic/COPYING"
        ).read_text(),
    )
)
with urllib.request.urlopen(
    "https://raw.githubusercontent.com/r9y9/pyopenjtalk/master/pyopenjtalk/htsvoice/LICENSE_mei_normal.htsvoice"
) as res:
    licenses.append(
        License(
            name='HTS Voice "Mei"',
            version=None,
            license="Creative Commons Attribution 3.0 license",
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
licenses.append(
    License(
        name="Python",
        version="3.7.11",
        license="Python Software Foundation License",
        text=Path("downloaded/Python 3.7.11.txt").read_text(encoding="utf8"),
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
        "--no-license-path "
        "--ignore-packages each-cpp-forwarder",
        shell=True,
        capture_output=True,
        check=True,
    ).stdout.decode()
)
for license_json in licenses_json:
    license = License(
        name=license_json["Name"],
        version=license_json["Version"],
        license=license_json["License"],
        text=license_json["LicenseText"],
    )
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
                "https://raw.githubusercontent.com/andrew-d/python-multipart/master/LICENSE.txt"
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
            raise Exception(license.name)
    licenses.append(license)


# npm
npm_custom_path = (
    Path("/patu/to/voicevox").expanduser().joinpath("license-custom.json")
)
npm_custom_path.write_text(
    '{ "name": "", "version": "", "description": "", "licenses": "", "copyright": "",'
    '"licenseFile": "none", "licenseText": "none", "licenseModified": "no" }'
)
licenses_json = json.loads(
    subprocess.run(
        "license-checker "
        "--production "
        "--excludePrivatePackages "
        "--json "
        "--customPath license-custom.json",
        shell=True,
        capture_output=True,
        check=True,
        cwd=Path("/patu/to/voicevox").expanduser(),
    ).stdout.decode()
)
npm_custom_path.unlink()
for license_json in licenses_json.values():
    assert "licenseFile" in license_json
    licenses.append(
        License(
            name=license_json["name"],
            version=license_json["version"],
            license=license_json["licenses"],
            text=license_json["licenseText"],
        )
    )

# cuda
licenses.append(
    License(
        name="CUDA Toolkit",
        version="11.1.1",
        license=None,
        text=Path("downloaded/CUDA Toolkit v11.1.1.txt").read_text(encoding="utf8"),
    )
)
licenses.append(
    License(
        name="cuDNN",
        version="7.6.5",
        license=None,
        text=Path("downloaded/NVIDIA cuDNN.txt").read_text(encoding="utf8"),
    )
)

# dump
json.dump(
    [asdict(license) for license in licenses],
    Path("/patu/to/voicevox")
    .expanduser()
    .joinpath("public/licenses.json")
    .open("w"),
)
