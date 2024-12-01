"""プリセット関連の処理"""

import shutil
import warnings
from pathlib import Path

import yaml
from pydantic import TypeAdapter, ValidationError

from ..utility.path_utility import engine_root
from .model import Preset


class PresetInputError(Exception):
    """受け入れ不可能な入力値に起因するエラー"""

    pass


class PresetInternalError(Exception):
    """プリセットマネージャーに起因するエラー"""

    pass


class PresetManager:
    """
    プリセットの管理

    プリセットはAudioQuery全体パラメータ（話速・音高・抑揚・音量・無音長）のデフォルト値セットである。
    YAMLファイルをSSoTとする簡易データベース方式により、プリセットの管理をおこなう。
    """

    def __init__(self, preset_path: Path):
        """プリセットマネージャーを生成する。プリセットファイルが存在しない場合は新規作成する。"""

        self.presets: list[Preset] = []  # 全プリセットのキャッシュ
        self.last_modified_time = 0.0
        self.preset_path = preset_path
        if not self.preset_path.exists():
            # エンジンのディレクトリ内に`presets.yaml`があった場合、マイグレーションする
            old_preset_path = engine_root() / "presets.yaml"
            if old_preset_path.exists():
                try:
                    shutil.move(old_preset_path, self.preset_path)
                except OSError:
                    warnings.warn(
                        "プリセットファイルのマイグレーションに失敗しました",
                        stacklevel=1,
                    )
                    self.preset_path.write_text("[]")
            else:
                self.preset_path.write_text("[]")

    def _refresh_cache(self) -> None:
        """プリセットの設定ファイルの最新状態をキャッシュへ反映する"""

        # データベース更新の確認（タイムスタンプベース）
        try:
            _last_modified_time = self.preset_path.stat().st_mtime
            if _last_modified_time == self.last_modified_time:
                # 更新無し
                return

            # データベースの読み込み
            with open(self.preset_path, mode="r", encoding="utf-8") as f:
                obj = yaml.safe_load(f)
        except OSError:
            raise PresetInternalError("プリセットの読み込みに失敗しました")
        except yaml.YAMLError:
            raise PresetInternalError("プリセットのパースに失敗しました")
        if obj is None:
            raise PresetInternalError("プリセットの設定ファイルが空の内容です")

        try:
            preset_list_adapter = TypeAdapter(list[Preset])
            _presets = preset_list_adapter.validate_python(obj)
        except ValidationError:
            raise PresetInternalError("プリセットの設定ファイルにミスがあります")

        # 全idの一意性をバリデーション
        if len([preset.id for preset in _presets]) != len(
            {preset.id for preset in _presets}
        ):
            raise PresetInternalError("プリセットのidに重複があります")

        # キャッシュを更新する
        self.presets = _presets
        self.last_modified_time = _last_modified_time

    def add_preset(self, preset: Preset) -> int:
        """新規プリセットを追加し、その ID を取得する。"""

        # データベース更新の反映
        self._refresh_cache()

        # 新規プリセットID の発行。IDが0未満、または存在するIDなら新規IDを発行
        if preset.id < 0 or preset.id in {preset.id for preset in self.presets}:
            preset.id = max([preset.id for preset in self.presets]) + 1
        # 新規プリセットの追加
        self.presets.append(preset)

        # 変更の反映。失敗時はリバート。
        try:
            self._write_on_file()
        except Exception as err:
            self.presets.pop()
            if isinstance(err, OSError):
                raise PresetInternalError("プリセットの書き込みに失敗しました")
            else:
                raise err

        return preset.id

    def load_presets(self) -> list[Preset]:
        """全てのプリセットを取得する"""

        # データベース更新の反映
        self._refresh_cache()

        return self.presets

    def update_preset(self, preset: Preset) -> int:
        """指定されたプリセットを更新し、その ID を取得する。"""

        # データベース更新の反映
        self._refresh_cache()

        # 対象プリセットの検索
        prev_preset: tuple[int, Preset | None] = (-1, None)
        for i in range(len(self.presets)):
            if self.presets[i].id == preset.id:
                prev_preset = (i, self.presets[i])
                self.presets[i] = preset
                break
        else:
            raise PresetInputError("更新先のプリセットが存在しません")

        # 変更の反映。失敗時はリバート。
        try:
            self._write_on_file()
        except Exception as err:
            self.presets[prev_preset[0]] = prev_preset[1]
            if isinstance(err, OSError):
                raise PresetInternalError("プリセットの書き込みに失敗しました")
            else:
                raise err

        return preset.id

    def delete_preset(self, id: int) -> int:
        """ID で指定されたプリセットを削除し、その ID を取得する。"""

        # データベース更新の反映
        self._refresh_cache()

        # 対象プリセットの検索
        buf = None
        buf_index = -1
        for i in range(len(self.presets)):
            if self.presets[i].id == id:
                buf = self.presets.pop(i)
                buf_index = i
                break
        else:
            raise PresetInputError("削除対象のプリセットが存在しません")

        # 変更の反映。失敗時はリバート。
        try:
            self._write_on_file()
        except OSError:
            self.presets.insert(buf_index, buf)
            raise PresetInternalError("プリセットの書き込みに失敗しました")

        return id

    def _write_on_file(self) -> None:
        """プリセット情報のファイル（簡易データベース）書き込み"""
        with open(self.preset_path, mode="w", encoding="utf-8") as f:
            yaml.safe_dump(
                [preset.model_dump() for preset in self.presets],
                f,
                allow_unicode=True,
                sort_keys=False,
            )
