import copy
import math

import numpy as np
from fastapi import HTTPException
from numpy.typing import NDArray
from soxr import resample

from ..core.core_adapter import CoreAdapter
from ..core.core_wrapper import CoreWrapper
from ..metas.Metas import StyleId
from ..model import AccentPhrase, AudioQuery, FrameAudioQuery, FramePhoneme, Mora, Score
from .acoustic_feature_extractor import Phoneme
from .kana_converter import parse_kana
from .mora_list import mora_kana_to_mora_phonemes, mora_phonemes_to_mora_kana
from .text_analyzer import text_to_accent_phrases

# 疑問文語尾定数
UPSPEAK_LENGTH = 0.15
UPSPEAK_PITCH_ADD = 0.3
UPSPEAK_PITCH_MAX = 6.5


# TODO: move mora utility to mora module
def to_flatten_moras(accent_phrases: list[AccentPhrase]) -> list[Mora]:
    """
    アクセント句系列に含まれるモーラの抽出
    Parameters
    ----------
    accent_phrases : list[AccentPhrase]
        アクセント句系列
    Returns
    -------
    moras : list[Mora]
        モーラ系列。ポーズモーラを含む。
    """
    moras: list[Mora] = []
    for accent_phrase in accent_phrases:
        moras += accent_phrase.moras
        if accent_phrase.pause_mora:
            moras += [accent_phrase.pause_mora]
    return moras


def to_flatten_phonemes(moras: list[Mora]) -> list[Phoneme]:
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


def generate_silence_mora(length: float) -> Mora:
    """無音モーラの生成"""
    return Mora(text="　", vowel="sil", vowel_length=length, pitch=0.0)


def apply_interrogative_upspeak(
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


def apply_prepost_silence(moras: list[Mora], query: AudioQuery) -> list[Mora]:
    """モーラ系列へ音声合成用のクエリがもつ前後無音（`prePhonemeLength` & `postPhonemeLength`）を付加する"""
    pre_silence_moras = [generate_silence_mora(query.prePhonemeLength)]
    post_silence_moras = [generate_silence_mora(query.postPhonemeLength)]
    moras = pre_silence_moras + moras + post_silence_moras
    return moras


def apply_speed_scale(moras: list[Mora], query: AudioQuery) -> list[Mora]:
    """モーラ系列へ音声合成用のクエリがもつ話速スケール（`speedScale`）を適用する"""
    for mora in moras:
        mora.vowel_length /= query.speedScale
        if mora.consonant_length:
            mora.consonant_length /= query.speedScale
    return moras


def count_frame_per_unit(
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
        mora_frames = vowel_frames + consonant_frames  # 音素ごとにフレーム長を算出し、和をモーラのフレーム長とする

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
    return np.round(sec * FRAMERATE).astype(np.int32).item()


def apply_pitch_scale(moras: list[Mora], query: AudioQuery) -> list[Mora]:
    """モーラ系列へ音声合成用のクエリがもつ音高スケール（`pitchScale`）を適用する"""
    for mora in moras:
        mora.pitch *= 2**query.pitchScale
    return moras


def apply_intonation_scale(moras: list[Mora], query: AudioQuery) -> list[Mora]:
    """モーラ系列へ音声合成用のクエリがもつ抑揚スケール（`intonationScale`）を適用する"""
    # 有声音素 (f0>0) の平均値に対する乖離度をスケール
    voiced = list(filter(lambda mora: mora.pitch > 0, moras))
    mean_f0 = np.mean(list(map(lambda mora: mora.pitch, voiced))).item()
    if mean_f0 != math.nan:  # 空リスト -> NaN
        for mora in voiced:
            mora.pitch = (mora.pitch - mean_f0) * query.intonationScale + mean_f0
    return moras


def apply_volume_scale(
    wave: NDArray[np.float32], query: AudioQuery | FrameAudioQuery
) -> NDArray[np.float32]:
    """音声波形へ音声合成用のクエリがもつ音量スケール（`volumeScale`）を適用する"""
    return wave * query.volumeScale


def apply_output_sampling_rate(
    wave: NDArray[np.float32], sr_wave: float, query: AudioQuery | FrameAudioQuery
) -> NDArray[np.float32]:
    """音声波形へ音声合成用のクエリがもつ出力サンプリングレート（`outputSamplingRate`）を適用する"""
    # サンプリングレート一致のときはスルー
    if sr_wave == query.outputSamplingRate:
        return wave
    wave = resample(wave, sr_wave, query.outputSamplingRate)
    return wave


def apply_output_stereo(
    wave: NDArray[np.float32], query: AudioQuery | FrameAudioQuery
) -> NDArray[np.float32]:
    """音声波形へ音声合成用のクエリがもつステレオ出力設定（`outputStereo`）を適用する"""
    if query.outputStereo:
        wave = np.array([wave, wave]).T
    return wave


def query_to_decoder_feature(
    query: AudioQuery,
) -> tuple[NDArray[np.float32], NDArray[np.float32]]:
    """音声合成用のクエリからフレームごとの音素 (shape=(フレーム長, 音素数)) と音高 (shape=(フレーム長,)) を得る"""
    moras = to_flatten_moras(query.accent_phrases)

    # 設定を適用する
    moras = apply_prepost_silence(moras, query)
    moras = apply_speed_scale(moras, query)
    moras = apply_pitch_scale(moras, query)
    moras = apply_intonation_scale(moras, query)

    # 表現を変更する（音素クラス → 音素 onehot ベクトル、モーラクラス → 音高スカラ）
    phoneme = np.stack([p.onehot for p in to_flatten_phonemes(moras)])
    f0 = np.array([mora.pitch for mora in moras], dtype=np.float32)

    # 時間スケールを変更する（音素・モーラ → フレーム）
    frame_per_phoneme, frame_per_mora = count_frame_per_unit(moras)
    phoneme = np.repeat(phoneme, frame_per_phoneme, axis=0)
    f0 = np.repeat(f0, frame_per_mora)

    return phoneme, f0


def raw_wave_to_output_wave(
    query: AudioQuery | FrameAudioQuery, wave: NDArray[np.float32], sr_wave: int
) -> NDArray[np.float32]:
    """生音声波形に音声合成用のクエリを適用して出力音声波形を生成する"""
    wave = apply_volume_scale(wave, query)
    wave = apply_output_sampling_rate(wave, sr_wave, query)
    wave = apply_output_stereo(wave, query)
    return wave


def _hira_to_kana(text: str) -> str:
    """ひらがなをカタカナに変換する"""
    return "".join(chr(ord(c) + 96) if "ぁ" <= c <= "ゔ" else c for c in text)


def calc_phoneme_lengths(
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
                raise HTTPException(
                    status_code=400,
                    detail=f"consonant_lengths[0] must be 0, but {consonant_lengths[0]}",
                )

            next_consonant_length = consonant_lengths[i + 1]
            note_duration = note_durations[i]

            # もし、次のノートの子音長が負になる場合、現在のノートの半分にする
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


class TTSEngine:
    """音声合成器（core）の管理/実行/プロキシと音声合成フロー"""

    def __init__(self, core: CoreWrapper):
        super().__init__()
        self._core = CoreAdapter(core)
        # NOTE: self._coreは将来的に消す予定

    def update_length(
        self, accent_phrases: list[AccentPhrase], style_id: StyleId
    ) -> list[AccentPhrase]:
        """アクセント句系列に含まれるモーラの音素長属性をスタイルに合わせて更新する"""
        # モーラ系列を抽出する
        moras = to_flatten_moras(accent_phrases)

        # 音素系列を抽出する
        phonemes = to_flatten_phonemes(moras)

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
        query.accent_phrases = apply_interrogative_upspeak(
            query.accent_phrases, enable_interrogative_upspeak
        )

        phoneme, f0 = query_to_decoder_feature(query)
        raw_wave, sr_raw_wave = self._core.safe_decode_forward(phoneme, f0, style_id)
        wave = raw_wave_to_output_wave(query, raw_wave, sr_raw_wave)
        return wave

    # FIXME: sing用のエンジンに移すかクラス名変える
    # 返す値の総称を考え、関数名を変更する
    def create_sing_phoneme_and_f0_and_volume(
        self,
        score: Score,
        style_id: StyleId,
    ) -> tuple[list[FramePhoneme], list[float], list[float]]:
        """歌声合成用のスコア・スタイルIDに基づいてフレームごとの音素・音高・音量を生成する"""
        notes = score.notes

        # Scoreを分解し、ノート単位のデータ、音素単位のデータを作成する
        note_lengths: list[int] = []
        note_consonants: list[int] = []
        note_vowels: list[int] = []
        phonemes: list[int] = []
        phoneme_keys: list[int] = []

        for note in notes:
            if note.lyric == "":
                if note.key is not None:
                    raise HTTPException(
                        status_code=400,
                        detail="lyricが空文字列の場合、keyはnullである必要があります。",
                    )
                note_lengths.append(note.frame_length)
                note_consonants.append(-1)
                note_vowels.append(0)  # pau
                phonemes.append(0)  # pau
                phoneme_keys.append(-1)
            else:
                if note.key is None:
                    raise HTTPException(
                        status_code=400,
                        detail="keyがnullの場合、lyricは空文字列である必要があります。",
                    )

                # TODO: 1ノートに複数のモーラがある場合の処理
                mora_phonemes = mora_kana_to_mora_phonemes.get(
                    note.lyric  # type: ignore
                ) or mora_kana_to_mora_phonemes.get(
                    _hira_to_kana(note.lyric)  # type: ignore
                )
                if mora_phonemes is None:
                    raise HTTPException(
                        status_code=400,
                        detail=f"lyricが不正です: {note.lyric}",
                    )

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

        # コアを用いて子音長を生成する
        consonant_lengths = self._core.safe_predict_sing_consonant_length_forward(
            note_consonants_array, note_vowels_array, note_lengths_array, style_id
        )

        # 予測した子音長を元に、すべての音素長を計算する
        phoneme_lengths = calc_phoneme_lengths(consonant_lengths, note_lengths_array)

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
            for phoneme_id, phoneme_duration in zip(phonemes, phoneme_lengths)
        ]

        return phoneme_data_list, f0s.tolist(), volumes.tolist()

    def frame_synthsize_wave(
        self,
        frame_audio_query: FrameAudioQuery,
        style_id: StyleId,
    ) -> NDArray[np.float32]:
        """歌声合成用のクエリ・スタイルIDに基づいて音声波形を生成する"""

        # 各データを分解・numpy配列に変換する
        phonemes = []
        phoneme_lengths = []

        for phoneme in frame_audio_query.phonemes:
            if phoneme.phoneme not in Phoneme._PHONEME_LIST:
                raise HTTPException(
                    status_code=400,
                    detail=f"phoneme {phoneme.phoneme} is not valid",
                )

            phonemes.append(Phoneme(phoneme.phoneme).id)
            phoneme_lengths.append(phoneme.frame_length)

        phonemes_array = np.array(phonemes, dtype=np.int64)
        phoneme_lengths_array = np.array(phoneme_lengths, dtype=np.int64)

        frame_phonemes = np.repeat(phonemes_array, phoneme_lengths_array)
        f0s = np.array(frame_audio_query.f0, dtype=np.float32)
        volumes = np.array(frame_audio_query.volume, dtype=np.float32)

        # コアを用いて音声を生成する
        raw_wave, sr_raw_wave = self._core.safe_sf_decode_forward(
            frame_phonemes, f0s, volumes, style_id
        )

        wave = raw_wave_to_output_wave(frame_audio_query, raw_wave, sr_raw_wave)
        return wave


def make_tts_engines_from_cores(cores: dict[str, CoreAdapter]) -> dict[str, TTSEngine]:
    """コア一覧からTTSエンジン一覧を生成する"""
    # FIXME: `MOCK_VER` を循環 import 無しに `initialize_cores()` 関連モジュールから import する
    MOCK_VER = "0.0.0"
    tts_engines: dict[str, TTSEngine] = {}
    for ver, core in cores.items():
        if ver == MOCK_VER:
            from ..dev.tts_engine import MockTTSEngine

            tts_engines[ver] = MockTTSEngine()
        else:
            tts_engines[ver] = TTSEngine(core.core)
    return tts_engines
