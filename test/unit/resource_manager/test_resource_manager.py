import base64
from pathlib import Path

import pytest

from voicevox_engine.resource_manager import ResourceManager, ResourceManagerError

with_filemap_dir = Path(__file__).parent / "with_filemap"
without_filemap_dir = Path(__file__).parent / "without_filemap"


def b64encode_str(s: bytes) -> str:
    return base64.b64encode(s).decode("utf-8")


def _assert_resource(manager: ResourceManager, input_path: Path) -> None:
    """
    `input_path`で指定したファイルから正しくbase64が取得できるか確認する
    また、ハッシュを取得し、対応するファイルから同じバイト列が取得できるか確認する
    """
    true_bytes = input_path.read_bytes()

    assert manager.resource_str(input_path, "base64") == b64encode_str(true_bytes)

    result_filehash = manager.resource_str(input_path, "hash")
    result_path = manager.resource_path(result_filehash)
    assert result_path.read_bytes() == true_bytes


def test_with_filemap() -> None:
    """
    "filemap.json"があるディレクトリでのテスト
    （fimemapの生成コマンド）
    `python tools/generate_filemap.py --target_dir test/unit/resource_manager/with_filemap`
    """
    manager = ResourceManager(False)
    manager.register_dir(with_filemap_dir)

    png_path = with_filemap_dir / "dummy.png"
    _assert_resource(manager, png_path)

    wav_path = with_filemap_dir / "dummy.wav"
    _assert_resource(manager, wav_path)

    # 同じバイナリがある場合のテスト
    same_wav_path = with_filemap_dir / "dummy_same_binary.wav"
    assert wav_path.read_bytes() == same_wav_path.read_bytes()
    _assert_resource(manager, same_wav_path)

    # filemap.jsonに含まれないものはエラー
    # NOTE: 通常、テキストはResourceManagerで管理しない
    txt_path = with_filemap_dir / "dummy.txt"
    with pytest.raises(ResourceManagerError):
        manager.resource_str(txt_path, "base64")
    with pytest.raises(ResourceManagerError):
        manager.resource_str(txt_path, "hash")

    # 登録されていないハッシュが渡された場合エラー
    with pytest.raises(ResourceManagerError):
        manager.resource_path("NOT_EXIST_HASH")


def test_without_filemap_when_production() -> None:
    """
    "create_filemap_if_not_exist"がFalseで"filemap.json"が無い場合エラーにする
    """
    manager = ResourceManager(False)
    with pytest.raises(ResourceManagerError):
        manager.register_dir(without_filemap_dir)


def test_without_filemap() -> None:
    """
    "create_filemap_if_not_exist"がTrueで"filemap.json"が無い場合は登録時にfilemapを生成する
    """
    manager = ResourceManager(True)
    manager.register_dir(without_filemap_dir)

    # 全てのファイルが管理される
    png_path = without_filemap_dir / "dummy.png"
    _assert_resource(manager, png_path)

    wav_path = without_filemap_dir / "dummy.wav"
    _assert_resource(manager, wav_path)

    txt_path = without_filemap_dir / "dummy.txt"
    _assert_resource(manager, txt_path)

    # 同じバイナリがある場合のテスト
    same_wav_path = without_filemap_dir / "dummy_same_binary.wav"
    assert wav_path.read_bytes() == same_wav_path.read_bytes()
    _assert_resource(manager, same_wav_path)

    # 登録されていないハッシュが渡された場合エラー
    with pytest.raises(ResourceManagerError):
        manager.resource_path("NOT_EXIST_HASH")
