"""音声合成エンジン"""

import copy
import math
from typing import Final, Literal, TypeAlias

import numpy as np
from fastapi import HTTPException
from numpy.typing import NDArray
from soxr import resample

from voicevox_engine.utility.core_version_utility import get_latest_version

from ..core.core_adapter import CoreAdapter, DeviceSupport
from ..core.core_initializer import CoreManager
from ..core.core_wrapper import CoreWrapper
from ..metas.Metas import StyleId
from ..model import AudioQuery
from .kana_converter import parse_kana
from .model import AccentPhrase, FrameAudioQuery, FramePhoneme, Mora, Note, Score
from .mora_mapping import mora_kana_to_mora_phonemes, mora_phonemes_to_mora_kana
from .phoneme import Phoneme
from .text_analyzer import text_to_accent_phrases

# 疑問文語尾定数
UPSPEAK_LENGTH = 0.15
UPSPEAK_PITCH_ADD = 0.3
UPSPEAK_PITCH_MAX = 6.5


class TalkSingInvalidInputError(Exception):
    """Talk と Sing の不正な入力エラー"""

    pass


def to_flatten_moras(accent_phrases: list[AccentPhrase]) -> list[Mora]:
    """アクセント句系列からモーラ系列を抽出する。"""
    moras: list[Mora] = []
    for accent_phrase in accent_phrases:
        moras += accent_phrase.moras
        if accent_phrase.pause_mora:
            moras += [accent_phrase.pause_mora]
    return moras


def _to_flatten_phonemes(moras: list[Mora]) -> list[Phoneme]:
    """モーラ系列から音素系列を抽出する"""
    phonemes: list[Phoneme] = []
    for mora in moras:
        if mora.consonant:
            phonemes += [Phoneme(mora.consonant)]
        phonemes += [(Phoneme(mora.vowel))]
    return phonemes


def _create_one_hot(accent_phrase: AccentPhrase, index: int) -> NDArray[np.int64]:
    """
    アクセント句から指定インデックスのみが 1 の配列 (onehot) を生成する。
    長さ `len(moras)` な配列の指定インデックスを 1 とし、pause_mora を含む場合は末尾に 0 が付加される。
    """
    onehot = np.zeros(len(accent_phrase.moras))
    onehot[index] = 1
    onehot = np.append(onehot, [0] if accent_phrase.pause_mora else [])
    return onehot.astype(np.int64)


def _generate_silence_mora(length: float) -> Mora:
    """無音モーラの生成"""
    return Mora(text="　", vowel="sil", vowel_length=length, pitch=0.0)


def _apply_interrogative_upspeak(
    accent_phrases: list[AccentPhrase], enable_interrogative_upspeak: bool
) -> list[AccentPhrase]:
    """必要に応じて各アクセント句の末尾へ疑問形モーラ（同一母音・継続長 0.15秒・音高↑）を付与する"""
    # NOTE: 将来的にAudioQueryインスタンスを引数にする予定
    if not enable_interrogative_upspeak:
        return accent_phrases

    for accent_phrase in accent_phrases:
        moras = accent_phrase.moras
        if len(moras) == 0:
            continue
        # 疑問形補正条件: 疑問形アクセント句 & 末尾有声モーラ
        if accent_phrase.is_interrogative and moras[-1].pitch > 0:
            last_mora = copy.deepcopy(moras[-1])
            upspeak_mora = Mora(
                text=mora_phonemes_to_mora_kana[last_mora.vowel],
                consonant=None,
                consonant_length=None,
                vowel=last_mora.vowel,
                vowel_length=UPSPEAK_LENGTH,
                pitch=min(last_mora.pitch + UPSPEAK_PITCH_ADD, UPSPEAK_PITCH_MAX),
            )
            accent_phrase.moras += [upspeak_mora]
    return accent_phrases


def _apply_prepost_silence(moras: list[Mora], query: AudioQuery) -> list[Mora]:
    """モーラ系列へ音声合成用のクエリがもつ前後無音（`prePhonemeLength` & `postPhonemeLength`）を付加する"""
    pre_silence_moras = [_generate_silence_mora(query.prePhonemeLength)]
    post_silence_moras = [_generate_silence_mora(query.postPhonemeLength)]
    moras = pre_silence_moras + moras + post_silence_moras
    return moras


def _apply_speed_scale(moras: list[Mora], query: AudioQuery) -> list[Mora]:
    """モーラ系列へ音声合成用のクエリがもつ話速スケール（`speedScale`）を適用する"""
    for mora in moras:
        mora.vowel_length /= query.speedScale
        if mora.consonant_length:
            mora.consonant_length /= query.speedScale
    return moras


def _count_frame_per_unit(
    moras: list[Mora],
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """
    音素あたり・モーラあたりのフレーム長を算出する
    Parameters
    ----------
    moras : list[Mora]
        モーラ系列
    Returns
    -------
    frame_per_phoneme : NDArray[np.int64]
        音素あたりのフレーム長。端数丸め。shape = (Phoneme,)
    frame_per_mora : NDArray[np.int64]
        モーラあたりのフレーム長。端数丸め。shape = (Mora,)
    """
    frame_per_phoneme: list[int] = []
    frame_per_mora: list[int] = []
    for mora in moras:
        vowel_frames = _to_frame(mora.vowel_length)
        consonant_frames = (
            _to_frame(mora.consonant_length) if mora.consonant_length is not None else 0
        )
        mora_frames = (
            vowel_frames + consonant_frames
        )  # 音素ごとにフレーム長を算出し、和をモーラのフレーム長とする

        if mora.consonant:
            frame_per_phoneme += [consonant_frames]
        frame_per_phoneme += [vowel_frames]
        frame_per_mora += [mora_frames]

    return (
        np.array(frame_per_phoneme, dtype=np.int64),
        np.array(frame_per_mora, dtype=np.int64),
    )


def _to_frame(sec: float) -> int:
    FRAMERATE = 93.75  # 24000 / 256 [frame/sec]
    # NOTE: `round` は偶数丸め。移植時に取扱い注意。詳細は voicevox_engine#552
    sec_rounded: NDArray[np.float64] = np.round(sec * FRAMERATE)
    return sec_rounded.astype(np.int32).item()


def _apply_pitch_scale(moras: list[Mora], query: AudioQuery) -> list[Mora]:
    """モーラ系列へ音声合成用のクエリがもつ音高スケール（`pitchScale`）を適用する"""
    for mora in moras:
        mora.pitch *= 2**query.pitchScale
    return moras


def _apply_pause_length(moras: list[Mora], query: AudioQuery) -> list[Mora]:
    """モーラ系列へ音声合成用のクエリがもつ無音時間（`pauseLength`）を適用する"""
    if query.pauseLength is not None:
        for mora in moras:
            if mora.vowel == "pau":
                mora.vowel_length = query.pauseLength
    return moras


def _apply_pause_length_scale(moras: list[Mora], query: AudioQuery) -> list[Mora]:
    """モーラ系列へ音声合成用のクエリがもつ無音時間スケール（`pauseLengthScale`）を適用する"""
    for mora in moras:
        if mora.vowel == "pau":
            mora.vowel_length *= query.pauseLengthScale
    return moras


def _apply_intonation_scale(moras: list[Mora], query: AudioQuery) -> list[Mora]:
    """モーラ系列へ音声合成用のクエリがもつ抑揚スケール（`intonationScale`）を適用する"""
    # 有声音素 (f0>0) の平均値に対する乖離度をスケール
    voiced = list(filter(lambda mora: mora.pitch > 0, moras))
    mean_f0 = np.mean(list(map(lambda mora: mora.pitch, voiced))).item()
    if mean_f0 != math.nan:  # 空リスト -> NaN
        for mora in voiced:
            mora.pitch = (mora.pitch - mean_f0) * query.intonationScale + mean_f0
    return moras


def _apply_volume_scale(
    wave: NDArray[np.float32], query: AudioQuery | FrameAudioQuery
) -> NDArray[np.float32]:
    """音声波形へ音声合成用のクエリがもつ音量スケール（`volumeScale`）を適用する"""
    return wave * query.volumeScale


def _apply_output_sampling_rate(
    wave: NDArray[np.float32], sr_wave: float, query: AudioQuery | FrameAudioQuery
) -> NDArray[np.float32]:
    """音声波形へ音声合成用のクエリがもつ出力サンプリングレート（`outputSamplingRate`）を適用する"""
    # サンプリングレート一致のときはスルー
    if sr_wave == query.outputSamplingRate:
        return wave
    wave = resample(wave, sr_wave, query.outputSamplingRate)
    return wave


def _apply_output_stereo(
    wave: NDArray[np.float32], query: AudioQuery | FrameAudioQuery
) -> NDArray[np.float32]:
    """音声波形へ音声合成用のクエリがもつステレオ出力設定（`outputStereo`）を適用する"""
    if query.outputStereo:
        wave = np.array([wave, wave]).T
    return wave


def _query_to_decoder_feature(
    query: AudioQuery,
) -> tuple[NDArray[np.float32], NDArray[np.float32]]:
    """音声合成用のクエリからフレームごとの音素 (shape=(フレーム長, 音素数)) と音高 (shape=(フレーム長,)) を得る"""
    moras = to_flatten_moras(query.accent_phrases)

    # 設定を適用する
    moras = _apply_prepost_silence(moras, query)
    moras = _apply_pause_length(moras, query)
    moras = _apply_pause_length_scale(moras, query)
    moras = _apply_speed_scale(moras, query)
    moras = _apply_pitch_scale(moras, query)
    moras = _apply_intonation_scale(moras, query)

    # 表現を変更する（音素クラス → 音素 onehot ベクトル、モーラクラス → 音高スカラ）
    phoneme = np.stack([p.onehot for p in _to_flatten_phonemes(moras)])
    f0 = np.array([mora.pitch for mora in moras], dtype=np.float32)

    # 時間スケールを変更する（音素・モーラ → フレーム）
    frame_per_phoneme, frame_per_mora = _count_frame_per_unit(moras)
    phoneme = np.repeat(phoneme, frame_per_phoneme, axis=0)
    f0 = np.repeat(f0, frame_per_mora)

    return phoneme, f0


def raw_wave_to_output_wave(
    query: AudioQuery | FrameAudioQuery, wave: NDArray[np.float32], sr_wave: int
) -> NDArray[np.float32]:
    """生音声波形に音声合成用のクエリを適用して出力音声波形を生成する"""
    wave = _apply_volume_scale(wave, query)
    wave = _apply_output_sampling_rate(wave, sr_wave, query)
    wave = _apply_output_stereo(wave, query)
    return wave


def _hira_to_kana(text: str) -> str:
    """ひらがなをカタカナに変換する"""
    return "".join(chr(ord(c) + 96) if "ぁ" <= c <= "ゔ" else c for c in text)


def _calc_phoneme_lengths(
    consonant_lengths: NDArray[np.int64],
    note_durations: NDArray[np.int64],
) -> NDArray[np.int64]:
    """
    子音長と音符長から音素長を計算する
    ただし、母音はノートの頭にくるようにするため、
    予測された子音長は前のノートの長さを超えないように調整される
    """
    phoneme_durations = []
    for i in range(len(consonant_lengths)):
        if i < len(consonant_lengths) - 1:
            # 最初のノートは子音長が0の、pauである必要がある
            if i == 0 and consonant_lengths[i] != 0:
                msg = f"consonant_lengths[0] must be 0, but {consonant_lengths[0]}"
                raise TalkSingInvalidInputError(msg)

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


def _notes_to_keys_and_phonemes(
    notes: list[Note],
) -> tuple[
    NDArray[np.int64],
    NDArray[np.int64],
    NDArray[np.int64],
    NDArray[np.int64],
    NDArray[np.int64],
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
    """

    note_lengths: list[int] = []
    note_consonants: list[int] = []
    note_vowels: list[int] = []
    phonemes: list[int] = []
    phoneme_keys: list[int] = []

    for note in notes:
        if note.lyric == "":
            if note.key is not None:
                msg = "lyricが空文字列の場合、keyはnullである必要があります。"
                raise TalkSingInvalidInputError(msg)
            note_lengths.append(note.frame_length)
            note_consonants.append(-1)
            note_vowels.append(0)  # pau
            phonemes.append(0)  # pau
            phoneme_keys.append(-1)
        else:
            if note.key is None:
                msg = "keyがnullの場合、lyricは空文字列である必要があります。"
                raise TalkSingInvalidInputError(msg)

            # TODO: 1ノートに複数のモーラがある場合の処理
            mora_phonemes = mora_kana_to_mora_phonemes.get(
                note.lyric  # type: ignore
            ) or mora_kana_to_mora_phonemes.get(
                _hira_to_kana(note.lyric)  # type: ignore
            )
            if mora_phonemes is None:
                msg = f"lyricが不正です: {note.lyric}"
                raise TalkSingInvalidInputError(msg)

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
            phonemes.append(vowel_id)
            phoneme_keys.append(note.key)

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
    )


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
            raise TalkSingInvalidInputError(msg)

        phonemes.append(Phoneme(phoneme.phoneme).id)
        phoneme_lengths.append(phoneme.frame_length)

    phonemes_array = np.array(phonemes, dtype=np.int64)
    phoneme_lengths_array = np.array(phoneme_lengths, dtype=np.int64)

    frame_phonemes = np.repeat(phonemes_array, phoneme_lengths_array)
    f0s = np.array(query.f0, dtype=np.float32)
    volumes = np.array(query.volume, dtype=np.float32)

    return frame_phonemes, f0s, volumes


class TTSEngine:
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

    def update_length(
        self, accent_phrases: list[AccentPhrase], style_id: StyleId
    ) -> list[AccentPhrase]:
        """アクセント句系列に含まれるモーラの音素長属性をスタイルに合わせて更新する"""
        # モーラ系列を抽出する
        moras = to_flatten_moras(accent_phrases)

        # 音素系列を抽出する
        phonemes = _to_flatten_phonemes(moras)

        # 音素クラスから音素IDスカラへ表現を変換する
        phoneme_ids = np.array([p.id for p in phonemes], dtype=np.int64)

        # コアを用いて音素長を生成する
        phoneme_lengths = self._core.safe_yukarin_s_forward(phoneme_ids, style_id)

        # 生成結果でモーラ内の音素長属性を置換する
        vowel_indexes = [i for i, p in enumerate(phonemes) if p.is_mora_tail()]
        for i, mora in enumerate(moras):
            if mora.consonant is None:
                mora.consonant_length = None
            else:
                mora.consonant_length = phoneme_lengths[vowel_indexes[i] - 1]
            mora.vowel_length = phoneme_lengths[vowel_indexes[i]]

        return accent_phrases

    def update_pitch(
        self, accent_phrases: list[AccentPhrase], style_id: StyleId
    ) -> list[AccentPhrase]:
        """アクセント句系列に含まれるモーラの音高属性をスタイルに合わせて更新する"""
        # 後続のnumpy.concatenateが空リストだとエラーになるので別処理
        if len(accent_phrases) == 0:
            return []

        # アクセントの開始/終了位置リストを作る
        start_accent_list = np.concatenate(
            [
                # accentはプログラミング言語におけるindexのように0始まりではなく1始まりなので、
                # accentが1の場合は0番目を指定している
                # accentが1ではない場合、accentはend_accent_listに用いられる
                _create_one_hot(accent_phrase, 0 if accent_phrase.accent == 1 else 1)
                for accent_phrase in accent_phrases
            ]
        )
        end_accent_list = np.concatenate(
            [
                # accentはプログラミング言語におけるindexのように0始まりではなく1始まりなので、1を引いている
                _create_one_hot(accent_phrase, accent_phrase.accent - 1)
                for accent_phrase in accent_phrases
            ]
        )

        # アクセント句の開始/終了位置リストを作る
        start_accent_phrase_list = np.concatenate(
            [_create_one_hot(accent_phrase, 0) for accent_phrase in accent_phrases]
        )
        end_accent_phrase_list = np.concatenate(
            [_create_one_hot(accent_phrase, -1) for accent_phrase in accent_phrases]
        )

        # アクセント句系列からモーラ系列と音素系列を抽出する
        moras = to_flatten_moras(accent_phrases)

        # モーラ系列から子音ID系列・母音ID系列を抽出する
        consonant_id_ints = [
            Phoneme(mora.consonant).id if mora.consonant else -1 for mora in moras
        ]
        consonant_ids = np.array(consonant_id_ints, dtype=np.int64)
        vowels = [Phoneme(mora.vowel) for mora in moras]
        vowel_ids = np.array([p.id for p in vowels], dtype=np.int64)

        # コアを用いてモーラ音高を生成する
        f0 = self._core.safe_yukarin_sa_forward(
            vowel_ids,
            consonant_ids,
            start_accent_list,
            end_accent_list,
            start_accent_phrase_list,
            end_accent_phrase_list,
            style_id,
        )

        # 母音が無声であるモーラは音高を 0 とする
        for i, p in enumerate(vowels):
            if p.is_unvoiced_mora_tail():
                f0[i] = 0

        # 更新する
        for i, mora in enumerate(moras):
            mora.pitch = f0[i]

        return accent_phrases

    def update_length_and_pitch(
        self, accent_phrases: list[AccentPhrase], style_id: StyleId
    ) -> list[AccentPhrase]:
        """アクセント句系列の音素長・モーラ音高をスタイルIDに基づいて更新する"""
        accent_phrases = self.update_length(accent_phrases, style_id)
        accent_phrases = self.update_pitch(accent_phrases, style_id)
        return accent_phrases

    def create_accent_phrases(self, text: str, style_id: StyleId) -> list[AccentPhrase]:
        """テキストからアクセント句系列を生成し、スタイルIDに基づいてその音素長・モーラ音高を更新する"""
        accent_phrases = text_to_accent_phrases(text)
        accent_phrases = self.update_length_and_pitch(accent_phrases, style_id)
        return accent_phrases

    def create_accent_phrases_from_kana(
        self, kana: str, style_id: StyleId
    ) -> list[AccentPhrase]:
        """AquesTalk 風記法テキストからアクセント句系列を生成し、スタイルIDに基づいてその音素長・モーラ音高を更新する"""
        accent_phrases = parse_kana(kana)
        accent_phrases = self.update_length_and_pitch(accent_phrases, style_id)
        return accent_phrases

    def synthesize_wave(
        self,
        query: AudioQuery,
        style_id: StyleId,
        enable_interrogative_upspeak: bool = True,
    ) -> NDArray[np.float32]:
        """音声合成用のクエリ・スタイルID・疑問文語尾自動調整フラグに基づいて音声波形を生成する"""
        # モーフィング時などに同一参照のqueryで複数回呼ばれる可能性があるので、元の引数のqueryに破壊的変更を行わない
        query = copy.deepcopy(query)
        query.accent_phrases = _apply_interrogative_upspeak(
            query.accent_phrases, enable_interrogative_upspeak
        )

        phoneme, f0 = _query_to_decoder_feature(query)
        raw_wave, sr_raw_wave = self._core.safe_decode_forward(phoneme, f0, style_id)
        wave = raw_wave_to_output_wave(query, raw_wave, sr_raw_wave)
        return wave

    def initialize_synthesis(self, style_id: StyleId, skip_reinit: bool) -> None:
        """指定されたスタイル ID に関する合成機能を初期化する。既に初期化されていた場合は引数に応じて再初期化する。"""
        self._core.initialize_style_id_synthesis(style_id, skip_reinit=skip_reinit)

    def is_synthesis_initialized(self, style_id: StyleId) -> bool:
        """指定されたスタイル ID に関する合成機能が初期化済みか否かを取得する。"""
        return self._core.is_initialized_style_id_synthesis(style_id)

    # FIXME: sing用のエンジンに移すかクラス名変える
    # 返す値の総称を考え、関数名を変更する
    def create_sing_phoneme_and_f0_and_volume(
        self,
        score: Score,
        style_id: StyleId,
    ) -> tuple[list[FramePhoneme], list[float], list[float]]:
        """歌声合成用のスコア・スタイルIDに基づいてフレームごとの音素・音高・音量を生成する"""
        notes = score.notes

        (
            note_lengths_array,
            note_consonants_array,
            note_vowels_array,
            phonemes_array,
            phoneme_keys_array,
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
            )
            for phoneme_id, phoneme_duration in zip(phonemes_array, phoneme_lengths)
        ]

        return phoneme_data_list, f0s.tolist(), volumes.tolist()

    def create_sing_volume_from_phoneme_and_f0(
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
            raise TalkSingInvalidInputError(msg)

        # 時間スケールを変更する（音素 → フレーム）
        frame_phonemes = np.repeat(phonemes_array, phoneme_lengths)
        frame_keys = np.repeat(phoneme_keys_array, phoneme_lengths)

        # コアを用いて音量を生成する
        volumes = self._core.safe_predict_sing_volume_forward(
            frame_phonemes, frame_keys, f0_array, style_id
        )

        # mypyの型チェックを通すために明示的に型を付ける
        volume_list: list[float] = volumes.tolist()

        return volume_list

    def frame_synthsize_wave(
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


LatestVersion: TypeAlias = Literal["LATEST_VERSION"]
LATEST_VERSION: Final[LatestVersion] = "LATEST_VERSION"


class TTSEngineManager:
    """TTS エンジンの集まりを一括管理するマネージャー"""

    def __init__(self) -> None:
        self._engines: dict[str, TTSEngine] = {}

    def versions(self) -> list[str]:
        """登録されたエンジンのバージョン一覧を取得する。"""
        return list(self._engines.keys())

    def _latest_version(self) -> str:
        return get_latest_version(self.versions())

    def register_engine(self, engine: TTSEngine, version: str) -> None:
        """エンジンを登録する。"""
        self._engines[version] = engine

    def get_engine(self, version: str | LatestVersion) -> TTSEngine:
        """指定バージョンのエンジンを取得する。"""
        if version == LATEST_VERSION:
            return self._engines[self._latest_version()]
        elif version in self._engines:
            return self._engines[version]

        raise HTTPException(status_code=422, detail="不明なバージョンです")


def make_tts_engines_from_cores(core_manager: CoreManager) -> TTSEngineManager:
    """コア一覧からTTSエンジン一覧を生成する"""
    # FIXME: `MOCK_VER` を循環 import 無しに `initialize_cores()` 関連モジュールから import する
    MOCK_VER = "0.0.0"
    tts_engines = TTSEngineManager()
    for ver, core in core_manager.items():
        if ver == MOCK_VER:
            from ..dev.tts_engine.mock import MockTTSEngine

            tts_engines.register_engine(MockTTSEngine(), ver)
        else:
            tts_engines.register_engine(TTSEngine(core.core), ver)
    return tts_engines
