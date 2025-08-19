"""テキスト音声合成エンジン"""

import copy
import math
from typing import Any, Final, Literal, TypeAlias

import numpy as np
from numpy.typing import NDArray

from ..core.core_adapter import CoreAdapter, DeviceSupport
from ..core.core_initializer import CoreManager
from ..core.core_wrapper import CoreWrapper
from ..metas.metas import StyleId
from ..model import AudioQuery
from ..utility.core_version_utility import MOCK_CORE_VERSION, get_latest_version
from .audio_postprocessing import raw_wave_to_output_wave
from .kana_converter import parse_kana
from .model import (
    AccentPhrase,
    Mora,
)
from .mora_mapping import mora_phonemes_to_mora_kana
from .njd_feature_processor import text_to_full_context_labels
from .phoneme import Phoneme
from .text_analyzer import full_context_labels_to_accent_phrases

# 疑問文語尾定数
UPSPEAK_LENGTH = 0.15
UPSPEAK_PITCH_ADD = 0.3
UPSPEAK_PITCH_MAX = 6.5


class TalkInvalidInputError(Exception):
    """Talk の不正な入力エラー"""

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
        phonemes += [Phoneme(mora.vowel)]
    return phonemes


def _create_one_hot(accent_phrase: AccentPhrase, index: int) -> NDArray[np.int64]:
    """
    アクセント句から指定インデックスのみが 1 の配列 (onehot) を生成する。

    長さ `len(moras)` な配列の指定インデックスを 1 とし、pause_mora を含む場合は末尾に 0 が付加される。
    """
    accent_onehot = np.zeros(len(accent_phrase.moras))
    accent_onehot[index] = 1
    onehot = np.append(accent_onehot, [0] if accent_phrase.pause_mora else [])
    return onehot.astype(np.int64)


def _generate_silence_mora(length: float) -> Mora:
    """音の長さを指定して無音モーラを生成する。"""
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
        """アクセント句系列に含まれる音素の長さをスタイルに合わせて更新する。"""
        # モーラ系列を抽出する
        moras = to_flatten_moras(accent_phrases)

        # 音素系列を抽出する
        phonemes = _to_flatten_phonemes(moras)

        # 音素クラスから音素IDスカラへ表現を変換する
        phoneme_ids = np.array([p.id for p in phonemes], dtype=np.int64)

        # 音素ごとの長さを生成する
        phoneme_lengths = self._core.safe_yukarin_s_forward(phoneme_ids, style_id)

        # 生成された音素長でモーラの音素長を更新する
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
        """アクセント句系列に含まれるモーラの音高をスタイルに合わせて更新する。"""
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
        """アクセント句系列に含まれる音素の長さとモーラの音高をスタイルに合わせて更新する。"""
        accent_phrases = self.update_length(accent_phrases, style_id)
        accent_phrases = self.update_pitch(accent_phrases, style_id)
        return accent_phrases

    def create_accent_phrases(
        self,
        text: str,
        style_id: StyleId,
        enable_katakana_english: bool,
    ) -> list[AccentPhrase]:
        """テキストからアクセント句系列を生成し、スタイルIDに基づいてその音素長・モーラ音高を更新する"""
        full_context_labels = text_to_full_context_labels(
            text, enable_katakana_english=enable_katakana_english
        )
        accent_phrases = full_context_labels_to_accent_phrases(full_context_labels)
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
        enable_interrogative_upspeak: bool,
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


class TTSEngineNotFound(Exception):
    """TTSEngine が見つからないエラー"""

    def __init__(self, *args: list[Any], version: str, **kwargs: dict[str, Any]):
        """TTSEngine のバージョン番号を用いてインスタンス化する。"""
        super().__init__(*args, **kwargs)
        self.version = version


class MockTTSEngineNotFound(Exception):
    """モック TTSEngine が見つからないエラー"""


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

    def get_tts_engine(self, version: str | LatestVersion) -> TTSEngine:
        """指定バージョンのエンジンを取得する。"""
        if version == LATEST_VERSION:
            return self._engines[self._latest_version()]
        elif version in self._engines:
            return self._engines[version]
        elif version == MOCK_CORE_VERSION:
            raise MockTTSEngineNotFound()
        else:
            raise TTSEngineNotFound(version=version)


def make_tts_engines_from_cores(core_manager: CoreManager) -> TTSEngineManager:
    """コア一覧からTTSエンジン一覧を生成する"""
    tts_engines = TTSEngineManager()
    for ver, core in core_manager.items():
        if ver == MOCK_CORE_VERSION:
            from ..dev.tts_engine.mock import MockTTSEngine

            tts_engines.register_engine(MockTTSEngine(), ver)
        else:
            tts_engines.register_engine(TTSEngine(core.core), ver)
    return tts_engines
