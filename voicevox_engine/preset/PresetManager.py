from pathlib import Path
from typing import List

import yaml  # type: ignore[import-untyped]
from pydantic import ValidationError, parse_obj_as

from .Preset import Preset
from .PresetError import PresetError


class PresetManager:
    """
    プリセットの管理

    プリセットはAudioQuery全体パラメータ（話速・音高・抑揚・音量・無音長）のデフォルト値セットである。
    YAMLファイルをSSoTとする簡易データベース方式により、プリセットの管理をおこなう。
    """

    def __init__(self, preset_path: Path):
        """
        Parameters
        ----------
        preset_path : Path
            プリセット情報を一元管理するYAMLファイルへのパス
        """
        self.presets: list[Preset] = []
        self.last_modified_time = 0.0
        self.preset_path = preset_path

    def load_presets(self) -> list[Preset]:
        """
        既存プリセットの読み込み
        Returns
        -------
        ret: list[Preset]
            読み込まれたプリセットのリスト
        """

        # データベース更新の確認（タイムスタンプベース）
        try:
            _last_modified_time = self.preset_path.stat().st_mtime
            if _last_modified_time == self.last_modified_time:
                # 更新無し、キャッシュを返す
                return self.presets
        except OSError:
            raise PresetError("プリセットの設定ファイルが見つかりません")

        # データベースの読み込み
        with open(self.preset_path, mode="r", encoding="utf-8") as f:
            obj = yaml.safe_load(f)
            if obj is None:
                raise PresetError("プリセットの設定ファイルが空の内容です")
        try:
            _presets = parse_obj_as(List[Preset], obj)
        except ValidationError:
            raise PresetError("プリセットの設定ファイルにミスがあります")

        # 全idの一意性をバリデーション
        if len([preset.id for preset in _presets]) != len(
            {preset.id for preset in _presets}
        ):
            raise PresetError("プリセットのidに重複があります")

        self.presets = _presets
        self.last_modified_time = _last_modified_time

        return self.presets

    def add_preset(self, preset: Preset) -> int:
        """
        新規プリセットの追加
        Parameters
        ----------
        preset : Preset
            新規プリセット
        Returns
        -------
        ret: int
            追加されたプリセットのID
        """

        # データベース更新の反映
        self.load_presets()

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
            if isinstance(err, FileNotFoundError):
                raise PresetError("プリセットの設定ファイルに書き込み失敗しました")
            else:
                raise err

        return preset.id

    def update_preset(self, preset: Preset) -> int:
        """
        既存プリセットの更新
        Parameters
        ----------
        preset : Preset
            新しい既存プリセット
        Returns
        -------
        ret: int
            更新されたプリセットのID
        """

        # データベース更新の反映
        self.load_presets()

        # 対象プリセットの検索
        prev_preset: tuple[int, Preset | None] = (-1, None)
        for i in range(len(self.presets)):
            if self.presets[i].id == preset.id:
                prev_preset = (i, self.presets[i])
                self.presets[i] = preset
                break
        else:
            raise PresetError("更新先のプリセットが存在しません")

        # 変更の反映。失敗時はリバート。
        try:
            self._write_on_file()
        except Exception as err:
            self.presets[prev_preset[0]] = prev_preset[1]
            if isinstance(err, FileNotFoundError):
                raise PresetError("プリセットの設定ファイルに書き込み失敗しました")
            else:
                raise err

        return preset.id

    def delete_preset(self, id: int) -> int:
        """
        指定したIDのプリセットの削除
        Parameters
        ----------
        id: int
            削除対象プリセットのID
        Returns
        -------
        ret: int
            削除されたプリセットのID
        """

        # データベース更新の反映
        self.load_presets()

        # 対象プリセットの検索
        buf = None
        buf_index = -1
        for i in range(len(self.presets)):
            if self.presets[i].id == id:
                buf = self.presets.pop(i)
                buf_index = i
                break
        else:
            raise PresetError("削除対象のプリセットが存在しません")

        # 変更の反映。失敗時はリバート。
        try:
            self._write_on_file()
        except FileNotFoundError:
            self.presets.insert(buf_index, buf)
            raise PresetError("プリセットの設定ファイルに書き込み失敗しました")

        return id

    def _write_on_file(self):
        """プリセット情報のファイル（簡易データベース）書き込み"""
        with open(self.preset_path, mode="w", encoding="utf-8") as f:
            yaml.safe_dump(
                [preset.dict() for preset in self.presets],
                f,
                allow_unicode=True,
                sort_keys=False,
            )
