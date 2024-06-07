from os import remove
from pathlib import Path
from shutil import copyfile

import pytest

from voicevox_engine.preset.model import Preset
from voicevox_engine.preset.preset_manager import (
    PresetInputError,
    PresetInternalError,
    PresetManager,
)

presets_test_1_yaml_path = Path("test/unit/preset/presets-test-1.yaml")
presets_test_2_yaml_path = Path("test/unit/preset/presets-test-2.yaml")
presets_test_3_yaml_path = Path("test/unit/preset/presets-test-3.yaml")
presets_test_4_yaml_path = Path("test/unit/preset/presets-test-4.yaml")


def test_validation() -> None:
    preset_manager = PresetManager(preset_path=presets_test_1_yaml_path)
    presets = preset_manager.load_presets()
    assert presets is not None


def test_validation_same() -> None:
    preset_manager = PresetManager(preset_path=presets_test_1_yaml_path)
    presets = preset_manager.load_presets()
    presets2 = preset_manager.load_presets()
    assert presets is not None
    assert presets == presets2


def test_validation_2() -> None:
    preset_manager = PresetManager(preset_path=presets_test_2_yaml_path)
    true_msg = "プリセットの設定ファイルにミスがあります"
    with pytest.raises(PresetInternalError, match=true_msg):
        preset_manager.load_presets()


def test_preset_id() -> None:
    preset_manager = PresetManager(preset_path=presets_test_3_yaml_path)
    true_msg = "プリセットのidに重複があります"
    with pytest.raises(PresetInternalError, match=true_msg):
        preset_manager.load_presets()


def test_empty_file() -> None:
    preset_manager = PresetManager(preset_path=presets_test_4_yaml_path)
    true_msg = "プリセットの設定ファイルが空の内容です"
    with pytest.raises(PresetInternalError, match=true_msg):
        preset_manager.load_presets()


def test_not_exist_file() -> None:
    preset_manager = PresetManager(preset_path=Path("test/presets-dummy.yaml"))
    true_msg = "プリセットの設定ファイルが見つかりません"
    with pytest.raises(PresetInternalError, match=true_msg):
        preset_manager.load_presets()


def test_add_preset(tmp_path: Path) -> None:
    preset_path = tmp_path / "presets.yaml"
    copyfile(presets_test_1_yaml_path, preset_path)
    preset_manager = PresetManager(preset_path=preset_path)
    preset = Preset(
        **{
            "id": 10,
            "name": "test10",
            "speaker_uuid": "7ffcb7ce-00ec-4bdc-82cd-45a8889e43ff",
            "style_id": 2,
            "speedScale": 1,
            "pitchScale": 1,
            "intonationScale": 0.5,
            "volumeScale": 1,
            "prePhonemeLength": 0.1,
            "postPhonemeLength": 0.1,
            "pauseLength": None,
            "pauseLengthScale": 1.0,
        }
    )
    id = preset_manager.add_preset(preset)
    assert id == 10
    assert len(preset_manager.presets) == 3
    for _preset in preset_manager.presets:
        if _preset.id == id:
            assert _preset == preset
    remove(preset_path)


def test_add_preset_load_failure() -> None:
    preset_manager = PresetManager(preset_path=presets_test_2_yaml_path)
    true_msg = "プリセットの設定ファイルにミスがあります"
    with pytest.raises(PresetInternalError, match=true_msg):
        preset_manager.add_preset(
            Preset(
                **{
                    "id": 1,
                    "name": "",
                    "speaker_uuid": "",
                    "style_id": 0,
                    "speedScale": 0,
                    "pitchScale": 0,
                    "intonationScale": 0,
                    "volumeScale": 0,
                    "prePhonemeLength": 0,
                    "postPhonemeLength": 0,
                    "pauseLength": 0,
                    "pauseLengthScale": 0,
                }
            )
        )


def test_add_preset_conflict_id(tmp_path: Path) -> None:
    preset_path = tmp_path / "presets.yaml"
    copyfile(presets_test_1_yaml_path, preset_path)
    preset_manager = PresetManager(preset_path=preset_path)
    preset = Preset(
        **{
            "id": 2,
            "name": "test3",
            "speaker_uuid": "7ffcb7ce-00ec-4bdc-82cd-45a8889e43ff",
            "style_id": 2,
            "speedScale": 1,
            "pitchScale": 1,
            "intonationScale": 0.5,
            "volumeScale": 1,
            "prePhonemeLength": 0.1,
            "postPhonemeLength": 0.1,
            "pauseLength": None,
            "pauseLengthScale": 1.0,
        }
    )
    id = preset_manager.add_preset(preset)
    assert id == 3
    assert len(preset_manager.presets) == 3
    for _preset in preset_manager.presets:
        if _preset.id == id:
            assert _preset == preset
    remove(preset_path)


def test_add_preset_conflict_id2(tmp_path: Path) -> None:
    preset_path = tmp_path / "presets.yaml"
    copyfile(presets_test_1_yaml_path, preset_path)
    preset_manager = PresetManager(preset_path=preset_path)
    preset = Preset(
        **{
            "id": -1,
            "name": "test3",
            "speaker_uuid": "7ffcb7ce-00ec-4bdc-82cd-45a8889e43ff",
            "style_id": 2,
            "speedScale": 1,
            "pitchScale": 1,
            "intonationScale": 0.5,
            "volumeScale": 1,
            "prePhonemeLength": 0.1,
            "postPhonemeLength": 0.1,
            "pauseLength": None,
            "pauseLengthScale": 1.0,
        }
    )
    id = preset_manager.add_preset(preset)
    assert id == 3
    assert len(preset_manager.presets) == 3
    for _preset in preset_manager.presets:
        if _preset.id == id:
            assert _preset == preset
    remove(preset_path)


def test_add_preset_write_failure(tmp_path: Path) -> None:
    preset_path = tmp_path / "presets.yaml"
    copyfile(presets_test_1_yaml_path, preset_path)
    preset_manager = PresetManager(preset_path=preset_path)
    preset = Preset(
        **{
            "id": 10,
            "name": "test10",
            "speaker_uuid": "7ffcb7ce-00ec-4bdc-82cd-45a8889e43ff",
            "style_id": 2,
            "speedScale": 1,
            "pitchScale": 1,
            "intonationScale": 0.5,
            "volumeScale": 1,
            "prePhonemeLength": 0.1,
            "postPhonemeLength": 0.1,
            "pauseLength": None,
            "pauseLengthScale": 1.0,
        }
    )
    preset_manager.load_presets()
    preset_manager._refresh_cache = lambda: None  # type:ignore[method-assign]
    preset_manager.preset_path = ""  # type: ignore[assignment]
    true_msg = "プリセットの設定ファイルが見つかりません"
    with pytest.raises(PresetInternalError, match=true_msg):
        preset_manager.add_preset(preset)
    assert len(preset_manager.presets) == 2
    remove(preset_path)


def test_update_preset(tmp_path: Path) -> None:
    preset_path = tmp_path / "presets.yaml"
    copyfile(presets_test_1_yaml_path, preset_path)
    preset_manager = PresetManager(preset_path=preset_path)
    preset = Preset(
        **{
            "id": 1,
            "name": "test1 new",
            "speaker_uuid": "7ffcb7ce-00ec-4bdc-82cd-45a8889e43ff",
            "style_id": 2,
            "speedScale": 1,
            "pitchScale": 1,
            "intonationScale": 0.5,
            "volumeScale": 1,
            "prePhonemeLength": 0.1,
            "postPhonemeLength": 0.1,
            "pauseLength": None,
            "pauseLengthScale": 1.0,
        }
    )
    id = preset_manager.update_preset(preset)
    assert id == 1
    assert len(preset_manager.presets) == 2
    for _preset in preset_manager.presets:
        if _preset.id == id:
            assert _preset == preset
    remove(preset_path)


def test_update_preset_load_failure() -> None:
    preset_manager = PresetManager(preset_path=presets_test_2_yaml_path)
    true_msg = "プリセットの設定ファイルにミスがあります"
    with pytest.raises(PresetInternalError, match=true_msg):
        preset_manager.update_preset(
            Preset(
                **{
                    "id": 1,
                    "name": "",
                    "speaker_uuid": "",
                    "style_id": 0,
                    "speedScale": 0,
                    "pitchScale": 0,
                    "intonationScale": 0,
                    "volumeScale": 0,
                    "prePhonemeLength": 0,
                    "postPhonemeLength": 0,
                    "pauseLength": 0,
                    "pauseLengthScale": 0,
                }
            )
        )


def test_update_preset_not_found(tmp_path: Path) -> None:
    preset_path = tmp_path / "presets.yaml"
    copyfile(presets_test_1_yaml_path, preset_path)
    preset_manager = PresetManager(preset_path=preset_path)
    preset = Preset(
        **{
            "id": 10,
            "name": "test1 new",
            "speaker_uuid": "7ffcb7ce-00ec-4bdc-82cd-45a8889e43ff",
            "style_id": 2,
            "speedScale": 1,
            "pitchScale": 1,
            "intonationScale": 0.5,
            "volumeScale": 1,
            "prePhonemeLength": 0.1,
            "postPhonemeLength": 0.1,
            "pauseLength": None,
            "pauseLengthScale": 1.0,
        }
    )
    true_msg = "更新先のプリセットが存在しません"
    with pytest.raises(PresetInputError, match=true_msg):
        preset_manager.update_preset(preset)
    assert len(preset_manager.presets) == 2
    remove(preset_path)


def test_update_preset_write_failure(tmp_path: Path) -> None:
    preset_path = tmp_path / "presets.yaml"
    copyfile(presets_test_1_yaml_path, preset_path)
    preset_manager = PresetManager(preset_path=preset_path)
    preset = Preset(
        **{
            "id": 1,
            "name": "test1 new",
            "speaker_uuid": "7ffcb7ce-00ec-4bdc-82cd-45a8889e43ff",
            "style_id": 2,
            "speedScale": 1,
            "pitchScale": 1,
            "intonationScale": 0.5,
            "volumeScale": 1,
            "prePhonemeLength": 0.1,
            "postPhonemeLength": 0.1,
            "pauseLength": None,
            "pauseLengthScale": 1.0,
        }
    )
    preset_manager.load_presets()
    preset_manager._refresh_cache = lambda: None  # type:ignore[method-assign]
    preset_manager.preset_path = ""  # type: ignore[assignment]
    true_msg = "プリセットの設定ファイルが見つかりません"
    with pytest.raises(PresetInternalError, match=true_msg):
        preset_manager.update_preset(preset)
    assert len(preset_manager.presets) == 2
    assert preset_manager.presets[0].name == "test"
    remove(preset_path)


def test_delete_preset(tmp_path: Path) -> None:
    preset_path = tmp_path / "presets.yaml"
    copyfile(presets_test_1_yaml_path, preset_path)
    preset_manager = PresetManager(preset_path=preset_path)
    id = preset_manager.delete_preset(1)
    assert id == 1
    assert len(preset_manager.presets) == 1
    remove(preset_path)


def test_delete_preset_load_failure() -> None:
    preset_manager = PresetManager(preset_path=presets_test_2_yaml_path)
    true_msg = "プリセットの設定ファイルにミスがあります"
    with pytest.raises(PresetInternalError, match=true_msg):
        preset_manager.delete_preset(10)


def test_delete_preset_not_found(tmp_path: Path) -> None:
    preset_path = tmp_path / "presets.yaml"
    copyfile(presets_test_1_yaml_path, preset_path)
    preset_manager = PresetManager(preset_path=preset_path)
    true_msg = "削除対象のプリセットが存在しません"
    with pytest.raises(PresetInputError, match=true_msg):
        preset_manager.delete_preset(10)
    assert len(preset_manager.presets) == 2
    remove(preset_path)


def test_delete_preset_write_failure(tmp_path: Path) -> None:
    preset_path = tmp_path / "presets.yaml"
    copyfile(presets_test_1_yaml_path, preset_path)
    preset_manager = PresetManager(preset_path=preset_path)
    preset_manager.load_presets()
    preset_manager._refresh_cache = lambda: None  # type:ignore[method-assign]
    preset_manager.preset_path = ""  # type: ignore[assignment]
    true_msg = "プリセットの設定ファイルが見つかりません"
    with pytest.raises(PresetInternalError, match=true_msg):
        preset_manager.delete_preset(1)
    assert len(preset_manager.presets) == 2
    remove(preset_path)
