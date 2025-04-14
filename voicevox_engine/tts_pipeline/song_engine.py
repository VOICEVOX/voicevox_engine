"""歌声音声合成エンジン"""

from typing import Any, Final, Literal, TypeAlias

import numpy as np
from numpy.typing import NDArray

from voicevox_engine.utility.core_version_utility import get_latest_version

from ..core.core_adapter import CoreAdapter, DeviceSupport
from ..core.core_initializer import MOCK_VER, CoreManager
from ..core.core_wrapper import CoreWrapper
from ..metas.Metas import StyleId
from .audio_postprocessing import raw_wave_to_output_wave
from .model import (
    FrameAudioQuery,
    FramePhoneme,
    Note,
    NoteId,
    Score,
)
from .mora_mapping import mora_kana_to_mora_phonemes
from .phoneme import Phoneme


class SongInvalidInputError(Exception):
    """Sing の不正な入力エラー"""

    pass


def _frame_query_to_sf_decoder_feature(
    query: FrameAudioQuery,
) -> tuple[NDArray[np.int64], NDArray[np.float32], NDArray[np.float32]]:
    """歌声合成用のクエリからフレームごとの音素・音高・音量を得る"""
    # 各データを分解・numpy配列に変換する
    phonemes = []
    phoneme_lengths = []

    for phoneme in query.phonemes:
        if phoneme.phoneme not in Phoneme._PHONEME_LIST:
            msg = f"phoneme {phoneme.phoneme} is not valid"
            raise SongInvalidInputError(msg)

        phonemes.append(Phoneme(phoneme.phoneme).id)
        phoneme_lengths.append(phoneme.frame_length)

    phonemes_array = np.array(phonemes, dtype=np.int64)
    phoneme_lengths_array = np.array(phoneme_lengths, dtype=np.int64)

    frame_phonemes = np.repeat(phonemes_array, phoneme_lengths_array)
    f0s = np.array(query.f0, dtype=np.float32)
    volumes = np.array(query.volume, dtype=np.float32)

    return frame_phonemes, f0s, volumes


def _notes_to_keys_and_phonemes(
    notes: list[Note],
) -> tuple[
    NDArray[np.int64],
    NDArray[np.int64],
    NDArray[np.int64],
    NDArray[np.int64],
    NDArray[np.int64],
    list[NoteId | None],
]:
    """
    ノート単位の長さ・モーラ情報や、音素列・音素ごとのキー列を作成する

    Parameters
    ----------
    notes : list[Note]
        ノート列

    Returns
    -------
    note_lengths : NDArray[np.int64]
        ノートの長さ列
    note_consonants : NDArray[np.int64]
        ノートの子音ID列
    note_vowels : NDArray[np.int64]
        ノートの母音ID列
    phonemes : NDArray[np.int64]
        音素列
    phoneme_keys : NDArray[np.int64]
        音素ごとのキー列
    phoneme_note_ids : list[NoteId]
        音素ごとのノートID列
    """
    note_lengths: list[int] = []
    note_consonants: list[int] = []
    note_vowels: list[int] = []
    phonemes: list[int] = []
    phoneme_keys: list[int] = []
    phoneme_note_ids: list[NoteId | None] = []

    for note in notes:
        if note.lyric == "":
            if note.key is not None:
                msg = "lyricが空文字列の場合、keyはnullである必要があります。"
                raise SongInvalidInputError(msg)
            note_lengths.append(note.frame_length)
            note_consonants.append(-1)
            note_vowels.append(0)  # pau
            phonemes.append(0)  # pau
            phoneme_keys.append(-1)
            phoneme_note_ids.append(note.id)
        else:
            if note.key is None:
                msg = "keyがnullの場合、lyricは空文字列である必要があります。"
                raise SongInvalidInputError(msg)

            # TODO: 1ノートに複数のモーラがある場合の処理
            mora_phonemes = mora_kana_to_mora_phonemes.get(
                note.lyric  # type: ignore
            ) or mora_kana_to_mora_phonemes.get(
                _hira_to_kana(note.lyric)  # type: ignore
            )
            if mora_phonemes is None:
                msg = f"lyricが不正です: {note.lyric}"
                raise SongInvalidInputError(msg)

            consonant, vowel = mora_phonemes
            if consonant is None:
                consonant_id = -1
            else:
                consonant_id = Phoneme(consonant).id
            vowel_id = Phoneme(vowel).id

            note_lengths.append(note.frame_length)
            note_consonants.append(consonant_id)
            note_vowels.append(vowel_id)
            if consonant_id != -1:
                phonemes.append(consonant_id)
                phoneme_keys.append(note.key)
                phoneme_note_ids.append(note.id)
            phonemes.append(vowel_id)
            phoneme_keys.append(note.key)
            phoneme_note_ids.append(note.id)

    # 各データをnumpy配列に変換する
    note_lengths_array = np.array(note_lengths, dtype=np.int64)
    note_consonants_array = np.array(note_consonants, dtype=np.int64)
    note_vowels_array = np.array(note_vowels, dtype=np.int64)
    phonemes_array = np.array(phonemes, dtype=np.int64)
    phoneme_keys_array = np.array(phoneme_keys, dtype=np.int64)

    return (
        note_lengths_array,
        note_consonants_array,
        note_vowels_array,
        phonemes_array,
        phoneme_keys_array,
        phoneme_note_ids,
    )


def _hira_to_kana(text: str) -> str:
    """ひらがなをカタカナに変換する"""
    return "".join(chr(ord(c) + 96) if "ぁ" <= c <= "ゔ" else c for c in text)


def _calc_phoneme_lengths(
    consonant_lengths: NDArray[np.int64],
    note_durations: NDArray[np.int64],
) -> NDArray[np.int64]:
    """
    子音長と音符長から音素長を計算する。

    母音はノートの頭にくるようにするため、予測された子音長は前のノートの長さを超えないように調整される。
    """
    phoneme_durations = []
    for i in range(len(consonant_lengths)):
        if i < len(consonant_lengths) - 1:
            # 最初のノートは子音長が0の、pauである必要がある
            if i == 0 and consonant_lengths[i] != 0:
                msg = f"consonant_lengths[0] must be 0, but {consonant_lengths[0]}"
                raise SongInvalidInputError(msg)

            next_consonant_length = consonant_lengths[i + 1]
            note_duration = note_durations[i]

            # もし、次のノートの子音長が負になる場合、現在のノートの半分にする
            # NOTE: 将来的にコアは非負になるのでこの処理は不要になる
            if next_consonant_length < 0:
                next_consonant_length = consonant_lengths[i + 1] = note_duration // 2
            vowel_length = note_duration - next_consonant_length

            # もし、現在のノートの母音長が負になる場合、
            # 次のノートの子音長を現在のノートの半分にする
            if vowel_length < 0:
                next_consonant_length = consonant_lengths[i + 1] = note_duration // 2
                vowel_length = note_duration - next_consonant_length

            phoneme_durations.append(vowel_length)
            if next_consonant_length > 0:
                phoneme_durations.append(next_consonant_length)
        else:
            vowel_length = note_durations[i]
            phoneme_durations.append(vowel_length)

    phoneme_durations_array = np.array(phoneme_durations, dtype=np.int64)
    return phoneme_durations_array


class SongEngine:
    """音声合成器（core）の管理/実行/プロキシと音声合成フロー"""

    def __init__(self, core: CoreWrapper):
        super().__init__()
        self._core = CoreAdapter(core)

    @property
    def default_sampling_rate(self) -> int:
        """合成される音声波形のデフォルトサンプリングレートを取得する。"""
        return self._core.default_sampling_rate

    @property
    def supported_devices(self) -> DeviceSupport | None:
        """合成時に各デバイスが利用可能か否かの一覧を取得する。"""
        return self._core.supported_devices

    def create_phoneme_and_f0_and_volume(
        self,
        score: Score,
        style_id: StyleId,
    ) -> tuple[list[FramePhoneme], list[float], list[float]]:
        """歌声合成用の楽譜・スタイルIDに基づいてフレームごとの音素・音高・音量を生成する"""
        notes = score.notes

        (
            note_lengths_array,
            note_consonants_array,
            note_vowels_array,
            phonemes_array,
            phoneme_keys_array,
            phoneme_note_ids,
        ) = _notes_to_keys_and_phonemes(notes)

        # コアを用いて子音長を生成する
        consonant_lengths = self._core.safe_predict_sing_consonant_length_forward(
            note_consonants_array, note_vowels_array, note_lengths_array, style_id
        )

        # 予測した子音長を元に、すべての音素長を計算する
        phoneme_lengths = _calc_phoneme_lengths(consonant_lengths, note_lengths_array)

        # 時間スケールを変更する（音素 → フレーム）
        frame_phonemes = np.repeat(phonemes_array, phoneme_lengths)
        frame_keys = np.repeat(phoneme_keys_array, phoneme_lengths)

        # コアを用いて音高を生成する
        f0s = self._core.safe_predict_sing_f0_forward(
            frame_phonemes, frame_keys, style_id
        )

        # コアを用いて音量を生成する
        # FIXME: 変数名のsいらない？
        volumes = self._core.safe_predict_sing_volume_forward(
            frame_phonemes, frame_keys, f0s, style_id
        )

        phoneme_data_list = [
            FramePhoneme(
                phoneme=Phoneme._PHONEME_LIST[phoneme_id],
                frame_length=phoneme_duration,
                note_id=phoneme_note_id,
            )
            for phoneme_id, phoneme_duration, phoneme_note_id in zip(
                phonemes_array, phoneme_lengths, phoneme_note_ids, strict=True
            )
        ]

        # mypyの型チェックを通すために明示的に型を付ける
        f0_list: list[float] = f0s.tolist()  # type: ignore
        volume_list: list[float] = volumes.tolist()  # type: ignore

        return phoneme_data_list, f0_list, volume_list

    def create_f0_from_phoneme(
        self,
        score: Score,
        phonemes: list[FramePhoneme],
        style_id: StyleId,
    ) -> list[float]:
        """歌声合成用の音素・スタイルIDに基づいて基本周波数を生成する"""
        notes = score.notes

        (
            _,
            _,
            _,
            phonemes_array_from_notes,
            phoneme_keys_array,
            _,
        ) = _notes_to_keys_and_phonemes(notes)

        phonemes_array = np.array(
            [Phoneme(p.phoneme).id for p in phonemes], dtype=np.int64
        )
        phoneme_lengths = np.array([p.frame_length for p in phonemes], dtype=np.int64)

        # notesから生成した音素系列と、FrameAudioQueryが持つ音素系列が一致しているか確認
        # この確認によって、phoneme_keys_arrayが使用可能かを間接的に確認する
        try:
            all_equals = np.all(phonemes_array == phonemes_array_from_notes)
        except ValueError:
            # 長さが異なる場合はValueErrorが発生するので、Falseとする
            # mypyを通すためにnp.bool_でラップする
            all_equals = np.bool_(False)

        if not all_equals:
            msg = "Scoreから抽出した音素列とFrameAudioQueryから抽出した音素列が一致しません。"
            raise SongInvalidInputError(msg)

        # 時間スケールを変更する（音素 → フレーム）
        frame_phonemes = np.repeat(phonemes_array, phoneme_lengths)
        frame_keys = np.repeat(phoneme_keys_array, phoneme_lengths)

        # コアを用いて音高を生成する
        f0s = self._core.safe_predict_sing_f0_forward(
            frame_phonemes, frame_keys, style_id
        )

        # mypyの型チェックを通すために明示的に型を付ける
        f0_list: list[float] = f0s.tolist()  # type: ignore

        return f0_list

    def create_volume_from_phoneme_and_f0(
        self,
        score: Score,
        phonemes: list[FramePhoneme],
        f0s: list[float],
        style_id: StyleId,
    ) -> list[float]:
        """歌声合成用の音素・音高・スタイルIDに基づいて音量を生成する"""
        notes = score.notes

        (
            _,
            _,
            _,
            phonemes_array_from_notes,
            phoneme_keys_array,
            _,
        ) = _notes_to_keys_and_phonemes(notes)

        phonemes_array = np.array(
            [Phoneme(p.phoneme).id for p in phonemes], dtype=np.int64
        )
        phoneme_lengths = np.array([p.frame_length for p in phonemes], dtype=np.int64)
        f0_array = np.array(f0s, dtype=np.float32)

        # notesから生成した音素系列と、FrameAudioQueryが持つ音素系列が一致しているか確認
        # この確認によって、phoneme_keys_arrayが使用可能かを間接的に確認する
        try:
            all_equals = np.all(phonemes_array == phonemes_array_from_notes)
        except ValueError:
            # 長さが異なる場合はValueErrorが発生するので、Falseとする
            # mypyを通すためにnp.bool_でラップする
            all_equals = np.bool_(False)

        if not all_equals:
            msg = "Scoreから抽出した音素列とFrameAudioQueryから抽出した音素列が一致しません。"
            raise SongInvalidInputError(msg)

        # 時間スケールを変更する（音素 → フレーム）
        frame_phonemes = np.repeat(phonemes_array, phoneme_lengths)
        frame_keys = np.repeat(phoneme_keys_array, phoneme_lengths)

        # コアを用いて音量を生成する
        volumes = self._core.safe_predict_sing_volume_forward(
            frame_phonemes, frame_keys, f0_array, style_id
        )

        # mypyの型チェックを通すために明示的に型を付ける
        volume_list: list[float] = volumes.tolist()  # type: ignore

        return volume_list

    def frame_synthesize_wave(
        self,
        query: FrameAudioQuery,
        style_id: StyleId,
    ) -> NDArray[np.float32]:
        """歌声合成用のクエリ・スタイルIDに基づいて音声波形を生成する"""
        phoneme, f0, volume = _frame_query_to_sf_decoder_feature(query)
        raw_wave, sr_raw_wave = self._core.safe_sf_decode_forward(
            phoneme, f0, volume, style_id
        )
        wave = raw_wave_to_output_wave(query, raw_wave, sr_raw_wave)
        return wave


class SongEngineNotFound(Exception):
    """SongEngine が見つからないエラー"""

    def __init__(self, *args: list[Any], version: str, **kwargs: dict[str, Any]):
        """SongEngine のバージョン番号を用いてインスタンス化する。"""
        super().__init__(*args, **kwargs)
        self.version = version


class MockSongEngineNotFound(Exception):
    """モック SongEngine が見つからないエラー"""


LatestVersion: TypeAlias = Literal["LATEST_VERSION"]
LATEST_VERSION: Final[LatestVersion] = "LATEST_VERSION"


class SongEngineManager:
    """Song エンジンの集まりを一括管理するマネージャー"""

    def __init__(self) -> None:
        self._engines: dict[str, SongEngine] = {}

    def versions(self) -> list[str]:
        """登録されたエンジンのバージョン一覧を取得する。"""
        return list(self._engines.keys())

    def _latest_version(self) -> str:
        return get_latest_version(self.versions())

    def register_engine(self, engine: SongEngine, version: str) -> None:
        """エンジンを登録する。"""
        self._engines[version] = engine

    def get_song_engine(self, version: str | LatestVersion) -> SongEngine:
        """指定バージョンのエンジンを取得する。"""
        if version == LATEST_VERSION:
            return self._engines[self._latest_version()]
        elif version in self._engines:
            return self._engines[version]
        elif version == MOCK_VER:
            raise MockSongEngineNotFound()
        else:
            raise SongEngineNotFound(version=version)


def make_song_engines_from_cores(core_manager: CoreManager) -> SongEngineManager:
    """コア一覧からSongエンジン一覧を生成する"""
    # FIXME: `MOCK_VER` を循環 import 無しに `initialize_cores()` 関連モジュールから import する
    MOCK_VER = "0.0.0"
    song_engines = SongEngineManager()
    for ver, core in core_manager.items():
        if ver == MOCK_VER:
            from ..dev.song_engine.mock import MockSongEngine

            song_engines.register_engine(MockSongEngine(), ver)
        else:
            song_engines.register_engine(SongEngine(core.core), ver)
    return song_engines
