import base64
from os.path import basename
from pathlib import Path

import pytest

from voicevox_engine.resource_manager import ResourceManager, ResourceManagerError

with_filemap_dir = Path(__file__).parent / "with_filemap"
without_filemap_dir = Path(__file__).parent / "without_filemap"

dummy_base_url = "http://localhost"


def b64encode_str(s: bytes) -> str:
    return base64.b64encode(s).decode("utf-8")


def test_with_filemap() -> None:
    manager = ResourceManager(False)
    manager.register_dir(with_filemap_dir)
    png_path = with_filemap_dir / "dummy.png"
    png_bytes = png_path.read_bytes()

    assert manager.resource_str(png_path, dummy_base_url, "base64") == b64encode_str(
        png_bytes
    )
    png_filehash = basename(manager.resource_str(png_path, dummy_base_url, "url"))
    png_res_path = manager.resource_path(png_filehash)
    assert png_res_path is not None
    assert png_res_path.read_bytes() == png_bytes

    wav_path = with_filemap_dir / "dummy.wav"
    wav_bytes = wav_path.read_bytes()

    assert manager.resource_str(wav_path, dummy_base_url, "base64") == b64encode_str(
        wav_bytes
    )
    wav_filehash = basename(manager.resource_str(wav_path, dummy_base_url, "url"))
    wav_res_path = manager.resource_path(wav_filehash)
    assert wav_res_path is not None
    assert wav_res_path.read_bytes() == wav_bytes

    txt_path = with_filemap_dir / "dummy.txt"
    with pytest.raises(ResourceManagerError) as _:
        manager.resource_str(txt_path, dummy_base_url, "base64")
    with pytest.raises(ResourceManagerError) as _:
        manager.resource_str(txt_path, dummy_base_url, "url")

    assert manager.resource_path("BAD_HASH") is None


def test_without_filemap_when_production() -> None:
    manager = ResourceManager(False)
    with pytest.raises(ResourceManagerError) as _:
        manager.register_dir(without_filemap_dir)


def test_without_filemap() -> None:
    manager = ResourceManager(True)
    manager.register_dir(without_filemap_dir)
    png_path = without_filemap_dir / "dummy.png"
    png_bytes = png_path.read_bytes()

    assert manager.resource_str(png_path, dummy_base_url, "base64") == b64encode_str(
        png_bytes
    )
    png_filehash = basename(manager.resource_str(png_path, dummy_base_url, "url"))
    png_res_path = manager.resource_path(png_filehash)
    assert png_res_path is not None
    assert png_res_path.read_bytes() == png_bytes

    wav_path = without_filemap_dir / "dummy.wav"
    wav_bytes = wav_path.read_bytes()

    assert manager.resource_str(wav_path, dummy_base_url, "base64") == b64encode_str(
        wav_bytes
    )
    wav_filehash = basename(manager.resource_str(wav_path, dummy_base_url, "url"))
    wav_res_path = manager.resource_path(wav_filehash)
    assert wav_res_path is not None
    assert wav_res_path.read_bytes() == wav_bytes

    txt_path = without_filemap_dir / "dummy.txt"
    txt_bytes = txt_path.read_bytes()

    assert manager.resource_str(txt_path, dummy_base_url, "base64") == b64encode_str(
        txt_bytes
    )
    txt_filehash = basename(manager.resource_str(txt_path, dummy_base_url, "url"))
    txt_res_path = manager.resource_path(txt_filehash)
    assert txt_res_path is not None
    assert txt_res_path.read_bytes() == txt_bytes

    assert manager.resource_path("BAD_HASH") is None
