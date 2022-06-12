from copy import deepcopy
from itertools import chain
from typing import List, Optional, Tuple

import numpy
from scipy.signal import resample

from voicevox_engine.experimental.guided_extractor import (
    PhraseInfo,
    extract_guided_feature,
    get_normalize_diff,
    resample_ts,
)
from voicevox_engine.experimental.julius4seg.sp_inserter import frame_to_second

from ..acoustic_feature_extractor import Accent, OjtPhoneme
from ..kana_parser import create_kana
from ..model import AccentPhrase, AudioQuery, Mora
from .synthesis_engine_base import SynthesisEngineBase

unvoiced_mora_phoneme_list = ["A", "I", "U", "E", "O", "cl", "pau"]
mora_phoneme_list = ["a", "i", "u", "e", "o", "N"] + unvoiced_mora_phoneme_list


# TODO: move mora utility to mora module
def to_flatten_moras(accent_phrases: List[AccentPhrase]) -> List[Mora]:
    """
    accent_phrasesに含まれるMora(とpause_moraがあればそれも)を
    すべて一つのリストに結合する
    Parameters
    ----------
    accent_phrases : List[AccentPhrase]
        AccentPhraseのリスト
    Returns
    -------
    moras : List[Mora]
        結合されたMoraのリストを返す
    """
    return list(
        chain.from_iterable(
            accent_phrase.moras
            + (
                [accent_phrase.pause_mora]
                if accent_phrase.pause_mora is not None
                else []
            )
            for accent_phrase in accent_phrases
        )
    )


def to_phoneme_id_list(phoneme_str_list: List[str]):
    """
    phoneme文字列のリストを、phoneme idのリストに変換する
    Parameters
    ----------
    phoneme_str_list : List[str]
        phoneme文字列のリスト
    Returns
    -------
    phoneme_list : List[int]
        変換されたphoneme idのリスト
    """
    phoneme_data_list = [
        OjtPhoneme(phoneme=p, start=i, end=i + 1)
        for i, p in enumerate(phoneme_str_list)
    ]
    phoneme_data_list = OjtPhoneme.convert(phoneme_data_list)
    phoneme_id_list = [p.phoneme_id for p in phoneme_data_list]
    return phoneme_id_list


def to_accent_id_list(accent_str_list: List[str]):
    """
    accent文字列のリストを、accent idのリストに変換する
    Parameters
    ----------
    accent_str_list : List[str]
        accent文字列のリスト
    Returns
    -------
    accent_list : List[int]
        変換されたaccent idのリスト
    """
    accent_id_list = [Accent(accent=s).accent_id for s in accent_str_list]
    return accent_id_list


def split_mora(phoneme_list: List[OjtPhoneme]):
    """
    OjtPhonemeのリストから、
    母音の位置(vowel_indexes)
    母音の音素列(vowel_phoneme_list)
    子音の音素列(consonant_phoneme_list)
    を生成し、返す
    Parameters
    ----------
    phoneme_list : List[OjtPhoneme]
        phonemeクラスのリスト
    Returns
    -------
    consonant_phoneme_list : List[OjtPhoneme]
        子音の音素列
    vowel_phoneme_list : List[OjtPhoneme]
        母音の音素列
    vowel_indexes : : List[int]
        母音の位置
    """
    vowel_indexes = [
        i for i, p in enumerate(phoneme_list) if p.phoneme in mora_phoneme_list
    ]
    vowel_phoneme_list = [phoneme_list[i] for i in vowel_indexes]
    # postとprevのvowel_indexの差として考えられる値は1か2
    # 理由としてはphoneme_listは、consonant、vowelの組み合わせか、vowel一つの連続であるから
    # 1の場合はconsonant(子音)が存在しない=母音のみ(a/i/u/e/o/N/cl/pau)で構成されるモーラ(音)である
    # 2の場合はconsonantが存在するモーラである
    # なので、2の場合(else)でphonemeを取り出している
    consonant_phoneme_list: List[Optional[OjtPhoneme]] = [None] + [
        None if post - prev == 1 else phoneme_list[post - 1]
        for prev, post in zip(vowel_indexes[:-1], vowel_indexes[1:])
    ]
    return consonant_phoneme_list, vowel_phoneme_list, vowel_indexes


def pre_process(
    accent_phrases: List[AccentPhrase],
) -> Tuple[List[Mora], numpy.ndarray, numpy.ndarray]:
    """
    AccentPhraseモデルのリストを整形し、処理に必要なデータの原型を作り出す
    Parameters
    ----------
    accent_phrases : List[AccentPhrase]
        AccentPhraseモデルのリスト
    Returns
    -------
    flatten_moras : List[Mora]
        AccentPhraseモデルのリスト内に含まれるすべてのMoraをリスト化したものを返す
    phoneme_id_list : numpy.ndarray
        flatten_morasから取り出したすべてのPhonemeをphoneme idに変換したものを返す
    accent_id_list: numpy.ndarray
        accent_phrasesから取り出したアクセントを元に生成されたアクセント列を返す
    """
    flatten_moras = to_flatten_moras(accent_phrases)

    phoneme_each_mora = [
        ([mora.consonant] if mora.consonant is not None else []) + [mora.vowel]
        for mora in flatten_moras
    ]
    phoneme_str_list = list(chain.from_iterable(phoneme_each_mora))

    phoneme_id_list = numpy.array(to_phoneme_id_list(phoneme_str_list), dtype=numpy.int64)

    accent_str_list = []
    for accent_phrase in accent_phrases:
        for i, mora in enumerate(accent_phrase.moras):
            if i + 1 == accent_phrase.accent and len(accent_phrase.moras) != accent_phrase.accent:
                if mora.consonant is not None:
                    accent_str_list.append("_")
                accent_str_list.append("]")
            else:
                if mora.consonant is not None:
                    accent_str_list.append("_")
                if i == 0:
                    accent_str_list.append("[")
                else:
                    accent_str_list.append("_")
        if accent_phrase.pause_mora is not None:
            accent_str_list.append("_")
        accent_str_list[-1] = "?" if accent_phrase.is_interrogative else "#"
    accent_id_list = numpy.array(to_accent_id_list(accent_str_list), dtype=numpy.int64)

    return flatten_moras, phoneme_id_list, accent_id_list


class SynthesisEngine(SynthesisEngineBase):
    def __init__(
        self,
        variance_forwarder,
        decode_forwarder,
        speakers: str,
        supported_devices: Optional[str] = None,
    ):
        """
        variance_forwarder: 音素ごとの音高と長さを求める関数
            length: 音素列の長さ
            phonemes: 音素列
            accents: アクセント列
            speaker_id: 話者番号
            return: 音素ごとの音高・長さ

        decode_forwarder: フレームごとの音素と音高から波形を求める関数
            length: フレームの長さ
            phonemes: 音素列
            pitches: 音素ごとの音高
            durations: 音素ごとの長さ
            speaker_id: 話者番号
            return: 音声波形

        speakers: coreから取得したspeakersに関するjsonデータの文字列

        supported_devices:
            coreから取得した対応デバイスに関するjsonデータの文字列
            Noneの場合はコアが情報の取得に対応していないため、対応デバイスは不明
        """
        super().__init__()
        self.variance_forwarder = variance_forwarder
        self.decode_forwarder = decode_forwarder

        self._speakers = speakers
        self._supported_devices = supported_devices
        self.default_sampling_rate = 48000

    @property
    def speakers(self) -> str:
        return self._speakers

    @property
    def supported_devices(self) -> Optional[str]:
        return self._supported_devices

    def replace_phoneme_length(
        self, accent_phrases: List[AccentPhrase], speaker_id: str
    ) -> Tuple[List[AccentPhrase], numpy.ndarray]:
        """
        accent_phrasesの母音・子音の長さを設定する
        Parameters
        ----------
        accent_phrases : List[AccentPhrase]
            アクセント句モデルのリスト
        speaker_id : str
            話者ID
        Returns
        -------
        accent_phrases : List[AccentPhrase]
            母音・子音の長さが設定されたアクセント句モデルのリスト
        """
        # phoneme
        # AccentPhraseをすべてMoraおよびOjtPhonemeの形に分解し、処理可能な形にする
        flatten_moras, phoneme_id_list, accent_id_list = pre_process(accent_phrases)

        # Phoneme IDのリスト(phoneme_id_list)とAccent IDのリスト(accent_id_list)をvariance_forwarderにかけ、
        # 推論器によって適切な音素ごとの音高・音素長を割り当てる
        pitches: numpy.ndarray
        durations: numpy.ndarray
        pitches, durations = self.variance_forwarder(
            length=len(phoneme_id_list),
            phonemes=phoneme_id_list,
            accents=accent_id_list,
            speaker_id=speaker_id,
        )

        # variance_forwarderの結果をaccent_phrasesに反映する
        # flatten_moras変数に展開された値を変更することでコード量を削減しつつaccent_phrases内のデータを書き換えている
        index = 0
        for mora in flatten_moras:
            if mora.consonant is not None:
                mora.consonant_length = durations[index]
                index += 1
            else:
                mora.consonant_length = None
            mora.vowel_length = durations[index]
            index += 1

        return accent_phrases, pitches

    def replace_mora_pitch(
        self, accent_phrases: List[AccentPhrase], speaker_id: str, pitches: Optional[numpy.ndarray] = None
    ) -> List[AccentPhrase]:
        """
        accent_phrasesの音高(ピッチ)を設定する
        Parameters
        ----------
        accent_phrases : List[AccentPhrase]
            アクセント句モデルのリスト
        speaker_id : str
            話者ID
        pitches : Optional[numpy.ndarray]
            ピッチを取得済みの場合、そのピッチを入力
        Returns
        -------
        accent_phrases : List[AccentPhrase]
            音高(ピッチ)が設定されたアクセント句モデルのリスト
        """
        # numpy.concatenateが空リストだとエラーを返すのでチェック
        if len(accent_phrases) == 0:
            return []

        # phoneme
        # AccentPhraseをすべてMoraおよびOjtPhonemeの形に分解し、処理可能な形にする
        flatten_moras, phoneme_id_list, accent_id_list = pre_process(accent_phrases)

        # pitchesを取得していない場合のみ、推論を行う
        if pitches is None:
            # Phoneme IDのリスト(phoneme_id_list)とAccent IDのリスト(accent_id_list)をvariance_forwarderにかけ、
            # 推論器によって適切な音素ごとの音高・音素長を割り当てる
            pitches, _ = self.variance_forwarder(
                length=len(phoneme_id_list),
                phonemes=phoneme_id_list,
                accents=accent_id_list,
                speaker_id=speaker_id,
            )

        # variance_forwarderの結果をaccent_phrasesに反映する
        # flatten_moras変数に展開された値を変更することでコード量を削減しつつaccent_phrases内のデータを書き換えている
        index = 0
        for mora in flatten_moras:
            if mora.consonant is not None:
                index += 1
            if mora.vowel in unvoiced_mora_phoneme_list:
                mora.pitch = 0.0
            else:
                mora.pitch = pitches[index]
            index += 1

        return accent_phrases

    def _synthesis_impl(self, query: AudioQuery, speaker_id: str):
        """
        音声合成クエリから音声合成に必要な情報を構成し、実際に音声合成を行う
        Parameters
        ----------
        query : AudioQuery
            音声合成クエリ
        speaker_id : str
            話者ID
        Returns
        -------
        wave : numpy.ndarray
            音声合成結果
        """

        # phoneme
        # AccentPhraseをすべてMoraおよびOjtPhonemeの形に分解し、処理可能な形にする
        flatten_moras, phoneme_id_list, _ = pre_process(query.accent_phrases)

        # length
        # 音素の長さをリストに展開・結合する。
        phoneme_length_list = [
            length
            for mora in flatten_moras
            for length in (
                [mora.consonant_length] if mora.consonant is not None else []
            )
            + [mora.vowel_length]
        ]
        # floatにキャスト
        durations = numpy.array(phoneme_length_list, dtype=numpy.float32)

        # lengthにSpeed Scale(話速)を適用する
        durations /= query.speedScale

        # pitch
        # モーラの音高(ピッチ)を展開・結合し、floatにキャストする
        f0_list = [
            pitch
            for mora in flatten_moras
            for pitch in (
                  [mora.pitch] if mora.consonant is not None else []
              )
              + [mora.pitch]
        ]
        f0 = numpy.array(f0_list, dtype=numpy.float32)
        # 音高(ピッチ)の調節を適用する(2のPitch Scale乗を掛ける)
        f0 *= 2 ** query.pitchScale

        # 有声音素(音高(ピッチ)が0より大きいもの)か否かを抽出する
        voiced = f0 > 0
        # 有声音素の音高(ピッチ)の平均値を求める
        mean_f0 = f0[voiced].mean()
        # 平均値がNaNではないとき、抑揚を適用する
        # 抑揚は音高と音高の平均値の差に抑揚を掛けたもの((f0 - mean_f0) * Intonation Scale)に抑揚の平均値(mean_f0)を足したもの
        if not numpy.isnan(mean_f0):
            f0[voiced] = (f0[voiced] - mean_f0) * query.intonationScale + mean_f0

        # 今まで生成された情報をdecode_forwarderにかけ、推論器によって音声波形を生成する
        wave = self.decode_forwarder(
            length=phoneme_id_list.shape[0],
            phonemes=phoneme_id_list,
            pitches=f0,
            durations=durations,
            speaker_id=speaker_id,
        )

        # volume: ゲイン適用
        wave *= query.volumeScale

        # add sil
        if query.prePhonemeLength != 0 or query.postPhonemeLength != 0:
            pre_pause = numpy.zeros(int(self.default_sampling_rate * query.prePhonemeLength))
            post_pause = numpy.zeros(int(self.default_sampling_rate * query.postPhonemeLength))
            wave = numpy.concatenate([pre_pause, wave, post_pause], 0)

        # 出力サンプリングレートがデフォルト(decode forwarderによるもの、48kHz)でなければ、それを適用する
        if query.outputSamplingRate != self.default_sampling_rate:
            wave = resample(
                wave,
                query.outputSamplingRate * len(wave) // self.default_sampling_rate,
            )

        # ステレオ変換
        # 出力設定がステレオなのであれば、ステレオ化する
        if query.outputStereo:
            wave = numpy.array([wave, wave]).T

        return wave

    def guided_synthesis(
        self,
        query: AudioQuery,
        speaker: int,
        audio_path: str,
        normalize: bool,
        core_version: Optional[str] = None,
    ):
        kana = create_kana(query.accent_phrases)
        f0, phonemes = extract_guided_feature(audio_path, kana)

        phone_list = numpy.zeros((len(f0), OjtPhoneme.num_phoneme), dtype=numpy.float32)

        for s, e, p in phonemes:
            s, e = (resample_ts(v) for v in (s, e))
            if p == "silB":
                f0[:e] = 0.0
                s += 1
                p = "pau"
            elif p == "silE":
                f0[s:] = 0.0
                p = "pau"
            elif p == "sp":
                f0[s:e] = 0.0
                p = "pau"
            elif p == "q":
                p = "cl"
            phone_list[s - 1 : e] = OjtPhoneme(start=s, end=e, phoneme=p).onehot

        if normalize:
            f0 += get_normalize_diff(engine=self, kana=kana, f0=f0, speaker_id=speaker)

        f0 *= 2 ** query.pitchScale

        f0 = resample(f0, int(len(f0) / query.speedScale))
        phone_list = resample(phone_list, int(len(phone_list) / query.speedScale))

        wave = self.decode_forwarder(
            length=phone_list.shape[0],
            phoneme_size=phone_list.shape[1],
            f0=f0[:, numpy.newaxis].astype(numpy.float32),
            phoneme=phone_list,
            speaker_id=numpy.array([speaker], dtype=numpy.int64).reshape(-1),
        )

        if query.volumeScale != 1:
            wave *= query.volumeScale

        if query.outputSamplingRate != self.default_sampling_rate:
            wave = resample(
                wave,
                query.outputSamplingRate * len(wave) // self.default_sampling_rate,
            )

        if query.outputStereo:
            wave = numpy.array([wave, wave]).T

        return wave

    def guided_accent_phrases(
        self,
        query: AudioQuery,
        speaker: int,
        audio_path: str,
        normalize: bool,
    ) -> List[AccentPhrase]:
        kana = create_kana(query.accent_phrases)
        f0, phonemes = extract_guided_feature(audio_path, kana)
        timed_phonemes = frame_to_second(deepcopy(phonemes))

        phrase_info = []
        for ((s, e, p), (ts, te, _tp)) in zip(phonemes, timed_phonemes):
            if p not in unvoiced_mora_phoneme_list:
                clip = f0[resample_ts(s) : resample_ts(e)]
                clip = clip[clip != 0]
                pitch = numpy.average(clip) if len(clip) != 0 else 0
            else:
                pitch = 0
            pitch = 0 if numpy.isnan(pitch) else pitch
            length = float(te) - float(ts)
            phrase_info.append(PhraseInfo(pitch, length, p))

        if normalize:
            normalize_diff = get_normalize_diff(
                engine=self, kana=kana, f0=f0, speaker_id=speaker
            )
            for p in phrase_info:
                if p.pitch != 0:
                    p.pitch += normalize_diff

        idx = 1
        for phrase in query.accent_phrases:
            phrase.pause_mora = None
            for mora in phrase.moras:
                if mora.consonant is not None:
                    mora.pitch = (
                        phrase_info[idx].pitch + phrase_info[idx + 1].pitch
                    ) / 2
                    mora.consonant_length = phrase_info[idx].length
                    mora.vowel_length = phrase_info[idx + 1].length
                    idx += 2
                else:
                    mora.pitch = phrase_info[idx].pitch
                    mora.vowel_length = phrase_info[idx].length
                    idx += 1
                if mora.vowel in unvoiced_mora_phoneme_list:
                    mora.pitch = 0
            if phrase_info[idx].phoneme == "sp":
                phrase.pause_mora = Mora(
                    text="、",
                    consonant=None,
                    consonant_length=None,
                    vowel="pau",
                    vowel_length=phrase_info[idx].length,
                    pitch=0,
                )
                idx += 1

        return query.accent_phrases
