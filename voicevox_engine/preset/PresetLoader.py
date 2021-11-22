import yaml
from pydantic import ValidationError
from pathlib import Path

from ..model import Preset


class PresetLoader:
    def __init__(
        self,
        preset_path: Path,
    ):
        self.presets = []
        self.last_modified_time = 0
        self.preset_path = preset_path

    def load_presets(self):
        """
        プリセットのYAMLファイルを読み込む

        Returns
        -------
        ret: tuple[Preset, str]
            プリセットとエラー文のタプル
        """
        _presets = []

        # 設定ファイルのタイムスタンプを確認
        try:
            _last_modified_time = self.preset_path.stat().st_mtime
            if _last_modified_time == self.last_modified_time:
                return self.presets, ""
        except OSError:
            return None, "プリセットの設定ファイルが見つかりません"

        try:
            with open(self.preset_path, encoding="utf-8") as f:
                obj = yaml.safe_load(f)
                if obj is None:
                    raise FileNotFoundError
        except FileNotFoundError:
            return None, "プリセットの設定ファイルが空の内容です"

        for preset in obj:
            try:
                _presets.append(Preset(**preset))
            except ValidationError:
                return None, "プリセットの設定ファイルにミスがあります"

        # idが一意か確認
        if len([preset.id for preset in _presets]) != len(
            {preset.id for preset in _presets}
        ):
            return None, "プリセットのidに重複があります"

        self.presets = _presets
        self.last_modified_time = _last_modified_time
        return self.presets, ""
