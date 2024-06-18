import base64
from pathlib import Path

import pytest

from voicevox_engine.resource_manager import ResourceManager, ResourceManagerError

with_filemap_dir = Path(__file__).parent / "with_filemap"
without_filemap_dir = Path(__file__).parent / "without_filemap"


def b64encode_str(s: bytes) -> str:
    return base64.b64encode(s).decode("utf-8")


def _assert_resource(manager: ResourceManager, test_path: Path) -> None:
    """
    `test_path`で指定したファイルが正しくbase64とハッシュが取得できるか確認する
    また、取得したハッシュから取得したファイルから同じバイト列が取得できるか確認する
    """
    test_bytes = test_path.read_bytes()

    assert manager.resource_str(test_path, "base64") == b64encode_str(test_bytes)

    test_filehash = manager.resource_str(test_path, "hash")
    test_res_path = manager.resource_path(test_filehash)
    assert test_res_path is not None
    assert test_res_path.read_bytes() == test_bytes


def test_with_filemap() -> None:
    manager = ResourceManager(False)
    manager.register_dir(with_filemap_dir)

    png_path = with_filemap_dir / "dummy.png"
    _assert_resource(manager, png_path)

    wav_path = with_filemap_dir / "dummy.wav"
    _assert_resource(manager, wav_path)

    # テキストは通常エンコードせずにJSONに含めるためResourceManagerでは管理しない
    txt_path = with_filemap_dir / "dummy.txt"
    with pytest.raises(ResourceManagerError) as _:
        manager.resource_str(txt_path, "base64")
    with pytest.raises(ResourceManagerError) as _:
        manager.resource_str(txt_path, "hash")

    assert manager.resource_path("NOT_EXIST_HASH") is None


def test_without_filemap_when_production() -> None:
    # "create_filemap_if_not_exist"がFalseで"filemap.json"が無い場合エラーにする
    manager = ResourceManager(False)
    with pytest.raises(ResourceManagerError) as _:
        manager.register_dir(without_filemap_dir)


def test_without_filemap() -> None:
    manager = ResourceManager(True)
    manager.register_dir(without_filemap_dir)

    png_path = without_filemap_dir / "dummy.png"
    _assert_resource(manager, png_path)

    wav_path = without_filemap_dir / "dummy.wav"
    _assert_resource(manager, wav_path)

    # "filemap.json"がない場合、全てのファイルが公開される
    txt_path = without_filemap_dir / "dummy.txt"
    _assert_resource(manager, txt_path)

    assert manager.resource_path("NOT_EXIST_HASH") is None
