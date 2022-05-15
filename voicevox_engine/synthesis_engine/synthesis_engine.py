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

from ..acoustic_feature_extractor import OjtPhoneme
from ..kana_parser import create_kana
from ..model import AccentPhrase, AudioQuery, Mora
from .core_wrapper import CoreWrapper
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


def to_phoneme_data_list(phoneme_str_list: List[str]):
    """
    phoneme文字列のリストを、OjtPhonemeクラスのリストに変換する
    Parameters
    ----------
    phoneme_str_list : List[str]
        phoneme文字列のリスト
    Returns
    -------
    phoneme_list : List[OjtPhoneme]
        変換されたOjtPhonemeクラスのリスト
    """
    phoneme_data_list = [
        OjtPhoneme(phoneme=p, start=i, end=i + 1)
        for i, p in enumerate(phoneme_str_list)
    ]
    phoneme_data_list = OjtPhoneme.convert(phoneme_data_list)
    return phoneme_data_list


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
) -> Tuple[List[Mora], List[OjtPhoneme]]:
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
    phoneme_data_list : List[OjtPhoneme]
        flatten_morasから取り出したすべてのPhonemeをOjtPhonemeに変換したものを返す
    """
    flatten_moras = to_flatten_moras(accent_phrases)

    phoneme_each_mora = [
        ([mora.consonant] if mora.consonant is not None else []) + [mora.vowel]
        for mora in flatten_moras
    ]
    phoneme_str_list = list(chain.from_iterable(phoneme_each_mora))
    phoneme_str_list = ["pau"] + phoneme_str_list + ["pau"]

    phoneme_data_list = to_phoneme_data_list(phoneme_str_list)

    return flatten_moras, phoneme_data_list


class SynthesisEngine(SynthesisEngineBase):
    def __init__(
        self,
        core: CoreWrapper,
    ):
        """
        core.yukarin_s_forward: 音素列から、音素ごとの長さを求める関数
            length: 音素列の長さ
            phoneme_list: 音素列
            speaker_id: 話者番号
            return: 音素ごとの長さ

        core.yukarin_sa_forward: モーラごとの音素列とアクセント情報から、モーラごとの音高を求める関数
            length: モーラ列の長さ
            vowel_phoneme_list: 母音の音素列
            consonant_phoneme_list: 子音の音素列
            start_accent_list: アクセントの開始位置
            end_accent_list: アクセントの終了位置
            start_accent_phrase_list: アクセント句の開始位置
            end_accent_phrase_list: アクセント句の終了位置
            speaker_id: 話者番号
            return: モーラごとの音高

        core.decode_forward: フレームごとの音素と音高から波形を求める関数
            length: フレームの長さ
            phoneme_size: 音素の種類数
            f0: フレームごとの音高
            phoneme: フレームごとの音素
            speaker_id: 話者番号
            return: 音声波形

        speakers: coreから取得したspeakersに関するjsonデータの文字列

        supported_devices:
            coreから取得した対応デバイスに関するjsonデータの文字列
            Noneの場合はコアが情報の取得に対応していないため、対応デバイスは不明
        """
        super().__init__()
        self.core = core
        self._speakers = self.core.metas()
        try:
            self._supported_devices = self.core.supported_devices()
        except NameError:
            self._supported_devices = None
        self.default_sampling_rate = 24000

    @property
    def speakers(self) -> str:
        return self._speakers

    @property
    def supported_devices(self) -> Optional[str]:
        return self._supported_devices

    def _lazy_init(self, speaker_id: int):
        try:
            is_model_loaded = self.core.is_model_loaded(speaker_id)
        except NameError:
            return
        if not is_model_loaded:
            self.core.load_model(speaker_id)

    def replace_phoneme_length(
        self, accent_phrases: List[AccentPhrase], speaker_id: int
    ) -> List[AccentPhrase]:
        """
        accent_phrasesの母音・子音の長さを設定する
        Parameters
        ----------
        accent_phrases : List[AccentPhrase]
            アクセント句モデルのリスト
        speaker_id : int
            話者ID
        Returns
        -------
        accent_phrases : List[AccentPhrase]
            母音・子音の長さが設定されたアクセント句モデルのリスト
        """
        # モデルがロードされていない場合はロードする
        self._lazy_init(speaker_id)
        # phoneme
        # AccentPhraseをすべてMoraおよびOjtPhonemeの形に分解し、処理可能な形にする
        flatten_moras, phoneme_data_list = pre_process(accent_phrases)
        # OjtPhonemeの形に分解されたもの(phoneme_data_list)から、vowel(母音)の位置を抜き出す
        _, _, vowel_indexes_data = split_mora(phoneme_data_list)

        # yukarin_s
        # OjtPhonemeのリストからOjtPhonemeのPhoneme ID(OpenJTalkにおける音素のID)のリストを作る
        phoneme_list_s = numpy.array(
            [p.phoneme_id for p in phoneme_data_list], dtype=numpy.int64
        )
        # Phoneme IDのリスト(phoneme_list_s)をyukarin_s_forwardにかけ、推論器によって適切な音素の長さを割り当てる
        phoneme_length = self.core.yukarin_s_forward(
            length=len(phoneme_list_s),
            phoneme_list=phoneme_list_s,
            speaker_id=numpy.array(speaker_id, dtype=numpy.int64).reshape(-1),
        )

        # yukarin_s_forwarderの結果をaccent_phrasesに反映する
        # flatten_moras変数に展開された値を変更することでコード量を削減しつつaccent_phrases内のデータを書き換えている
        for i, mora in enumerate(flatten_moras):
            mora.consonant_length = (
                phoneme_length[vowel_indexes_data[i + 1] - 1]
                if mora.consonant is not None
                else None
            )
            mora.vowel_length = phoneme_length[vowel_indexes_data[i + 1]]

        return accent_phrases

    def replace_mora_pitch(
        self, accent_phrases: List[AccentPhrase], speaker_id: int
    ) -> List[AccentPhrase]:
        """
        accent_phrasesの音高(ピッチ)を設定する
        Parameters
        ----------
        accent_phrases : List[AccentPhrase]
            アクセント句モデルのリスト
        speaker_id : int
            話者ID
        Returns
        -------
        accent_phrases : List[AccentPhrase]
            音高(ピッチ)が設定されたアクセント句モデルのリスト
        """
        # モデルがロードされていない場合はロードする
        self._lazy_init(speaker_id)
        # numpy.concatenateが空リストだとエラーを返すのでチェック
        if len(accent_phrases) == 0:
            return []

        # phoneme
        # AccentPhraseをすべてMoraおよびOjtPhonemeの形に分解し、処理可能な形にする
        flatten_moras, phoneme_data_list = pre_process(accent_phrases)

        # accent
        def _create_one_hot(accent_phrase: AccentPhrase, position: int):
            """
            単位行列(numpy.eye)を応用し、accent_phrase内でone hotな配列(リスト)を作る
            例えば、accent_phraseのmorasの長さが12、positionが1なら
            [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            morasの長さが同じく12、positionが-1なら
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
            のような配列を生成する
            accent_phraseがpause_moraを含む場合はさらに後ろに0が足される
            Parameters
            ----------
            accent_phrase : AccentPhrase
                アクセント句モデル
            position : int
                one hotにするindex
            Returns
            -------
            one_hot : numpy.ndarray
                one hotな配列(リスト)
            """
            return numpy.r_[
                numpy.eye(len(accent_phrase.moras))[position],
                (0 if accent_phrase.pause_mora is not None else []),
            ]

        # accent_phrasesから、アクセントの開始位置のリストを作る
        start_accent_list = numpy.concatenate(
            [
                # accentはプログラミング言語におけるindexのように0始まりではなく1始まりなので、
                # accentが1の場合は0番目を指定している
                # accentが1ではない場合、accentはend_accent_listに用いられる
                _create_one_hot(accent_phrase, 0 if accent_phrase.accent == 1 else 1)
                for accent_phrase in accent_phrases
            ]
        )

        # accent_phrasesから、アクセントの終了位置のリストを作る
        end_accent_list = numpy.concatenate(
            [
                # accentはプログラミング言語におけるindexのように0始まりではなく1始まりなので、1を引いている
                _create_one_hot(accent_phrase, accent_phrase.accent - 1)
                for accent_phrase in accent_phrases
            ]
        )

        # accent_phrasesから、アクセント句の開始位置のリストを作る
        # これによって、yukarin_sa_forwarder内でアクセント句を区別できる
        start_accent_phrase_list = numpy.concatenate(
            [_create_one_hot(accent_phrase, 0) for accent_phrase in accent_phrases]
        )

        # accent_phrasesから、アクセント句の終了位置のリストを作る
        end_accent_phrase_list = numpy.concatenate(
            [_create_one_hot(accent_phrase, -1) for accent_phrase in accent_phrases]
        )

        # 最初と最後に0を付け加える。これによってpau(前後の無音のためのもの)を付け加えたことになる
        start_accent_list = numpy.r_[0, start_accent_list, 0]
        end_accent_list = numpy.r_[0, end_accent_list, 0]
        start_accent_phrase_list = numpy.r_[0, start_accent_phrase_list, 0]
        end_accent_phrase_list = numpy.r_[0, end_accent_phrase_list, 0]

        # アクセント・アクセント句関連のデータをyukarin_sa_forwarderに渡すための最終処理、リスト内のデータをint64に変換する
        start_accent_list = numpy.array(start_accent_list, dtype=numpy.int64)
        end_accent_list = numpy.array(end_accent_list, dtype=numpy.int64)
        start_accent_phrase_list = numpy.array(
            start_accent_phrase_list, dtype=numpy.int64
        )
        end_accent_phrase_list = numpy.array(end_accent_phrase_list, dtype=numpy.int64)

        # phonemeに関するデータを取得(変換)する
        (
            consonant_phoneme_data_list,
            vowel_phoneme_data_list,
            _,
        ) = split_mora(phoneme_data_list)

        # yukarin_sa
        # Phoneme関連のデータをyukarin_sa_forwarderに渡すための最終処理、リスト内のデータをint64に変換する
        vowel_phoneme_list = numpy.array(
            [p.phoneme_id for p in vowel_phoneme_data_list], dtype=numpy.int64
        )
        consonant_phoneme_list = numpy.array(
            [
                p.phoneme_id if p is not None else -1
                for p in consonant_phoneme_data_list
            ],
            dtype=numpy.int64,
        )

        # 今までに生成された情報をyukarin_sa_forwardにかけ、推論器によってモーラごとに適切な音高(ピッチ)を割り当てる
        f0_list = self.core.yukarin_sa_forward(
            length=vowel_phoneme_list.shape[0],
            vowel_phoneme_list=vowel_phoneme_list[numpy.newaxis],
            consonant_phoneme_list=consonant_phoneme_list[numpy.newaxis],
            start_accent_list=start_accent_list[numpy.newaxis],
            end_accent_list=end_accent_list[numpy.newaxis],
            start_accent_phrase_list=start_accent_phrase_list[numpy.newaxis],
            end_accent_phrase_list=end_accent_phrase_list[numpy.newaxis],
            speaker_id=numpy.array(speaker_id, dtype=numpy.int64).reshape(-1),
        )[0]

        # 無声母音を含むMoraに関しては、音高(ピッチ)を0にする
        for i, p in enumerate(vowel_phoneme_data_list):
            if p.phoneme in unvoiced_mora_phoneme_list:
                f0_list[i] = 0

        # yukarin_sa_forwarderの結果をaccent_phrasesに反映する
        # flatten_moras変数に展開された値を変更することでコード量を削減しつつaccent_phrases内のデータを書き換えている
        for i, mora in enumerate(flatten_moras):
            mora.pitch = f0_list[i + 1]

        return accent_phrases

    def _synthesis_impl(self, query: AudioQuery, speaker_id: int):
        """
        音声合成クエリから音声合成に必要な情報を構成し、実際に音声合成を行う
        Parameters
        ----------
        query : AudioQuery
            音声合成クエリ
        speaker_id : int
            話者ID
        Returns
        -------
        wave : numpy.ndarray
            音声合成結果
        """
        # モデルがロードされていない場合はロードする
        self._lazy_init(speaker_id)
        # phoneme
        # AccentPhraseをすべてMoraおよびOjtPhonemeの形に分解し、処理可能な形にする
        flatten_moras, phoneme_data_list = pre_process(query.accent_phrases)

        # OjtPhonemeのリストからOjtPhonemeのPhoneme ID(OpenJTalkにおける音素のID)のリストを作る
        phoneme_list_s = numpy.array(
            [p.phoneme_id for p in phoneme_data_list], dtype=numpy.int64
        )

        # length
        # 音素の長さをリストに展開・結合する。ここには前後の無音時間も含まれる
        phoneme_length_list = (
            [query.prePhonemeLength]
            + [
                length
                for mora in flatten_moras
                for length in (
                    [mora.consonant_length] if mora.consonant is not None else []
                )
                + [mora.vowel_length]
            ]
            + [query.postPhonemeLength]
        )
        # floatにキャスト
        phoneme_length = numpy.array(phoneme_length_list, dtype=numpy.float32)

        # lengthにSpeed Scale(話速)を適用する
        phoneme_length /= query.speedScale

        # pitch
        # モーラの音高(ピッチ)を展開・結合し、floatにキャストする
        f0_list = [0] + [mora.pitch for mora in flatten_moras] + [0]
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

        # OjtPhonemeの形に分解された音素リストから、vowel(母音)の位置を抜き出し、numpyのarrayにする
        _, _, vowel_indexes_data = split_mora(phoneme_data_list)
        vowel_indexes = numpy.array(vowel_indexes_data)

        # forward decode
        # 音素の長さにrateを掛け、intにキャストする
        rate = 24000 / 256
        phoneme_bin_num = numpy.round(phoneme_length * rate).astype(numpy.int32)

        # Phoneme IDを音素の長さ分繰り返す
        phoneme = numpy.repeat(phoneme_list_s, phoneme_bin_num)
        # f0を母音と子音の長さの合計分繰り返す
        f0 = numpy.repeat(
            f0,
            [a.sum() for a in numpy.split(phoneme_bin_num, vowel_indexes[:-1] + 1)],
        )

        # phonemeの長さとOjtPhonemeのnum_phoneme(45)分の0で初期化された2次元配列を用意する
        array = numpy.zeros((len(phoneme), OjtPhoneme.num_phoneme), dtype=numpy.float32)
        # 初期化された2次元配列の各行をone hotにする
        array[numpy.arange(len(phoneme)), phoneme] = 1
        phoneme = array

        # 今まで生成された情報をdecode_forwardにかけ、推論器によって音声波形を生成する
        wave = self.core.decode_forward(
            length=phoneme.shape[0],
            phoneme_size=phoneme.shape[1],
            f0=f0[:, numpy.newaxis],
            phoneme=phoneme,
            speaker_id=numpy.array(speaker_id, dtype=numpy.int64).reshape(-1),
        )

        # volume: ゲイン適用
        wave *= query.volumeScale

        # 出力サンプリングレートがデフォルト(decode forwarderによるもの、24kHz)でなければ、それを適用する
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
        self._lazy_init(speaker)
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

        wave = self.core.decode_forward(
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
