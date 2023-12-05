import threading
from itertools import chain
from typing import List, Optional, Tuple

import numpy
from soxr import resample

from ..acoustic_feature_extractor import OjtPhoneme
from ..model import AccentPhrase, AudioQuery, Mora
from .core_wrapper import CoreWrapper, OldCoreError
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
        モーラ時系列（前後の無音含まない）
    phoneme_data_list : List[OjtPhoneme]
        音素時系列（前後の無音含む）
    """
    flatten_moras = to_flatten_moras(accent_phrases)

    phoneme_each_mora = [
        ([mora.consonant] if mora.consonant is not None else []) + [mora.vowel]
        for mora in flatten_moras
    ]
    phoneme_str_list = list(chain.from_iterable(phoneme_each_mora))
    phoneme_str_list = ["pau"] + phoneme_str_list + ["pau"]

    phoneme_data_list = [
        OjtPhoneme(phoneme=p, start=i, end=i + 1)
        for i, p in enumerate(phoneme_str_list)
    ]

    return flatten_moras, phoneme_data_list


def silence_mora(length: float) -> Mora:
    """無音モーラの生成"""
    return Mora(text=" ", vowel="sil", vowel_length=length, pitch=0.0)


def change_silence(moras: list[Mora], query: AudioQuery) -> list[Mora]:
    """モーラ列の先頭/最後尾へqueryに基づいた無音モーラを追加
    Parameters
    ----------
    moras : List[Mora]
        モーラ時系列
    query : AudioQuery
        音声合成クエリ
    Returns
    -------
    moras : List[Mora]
        前後無音が付加されたモーラ時系列
    """
    silence_moras_head = [silence_mora(query.prePhonemeLength)]
    silence_moras_tail = [silence_mora(query.postPhonemeLength)]
    moras = silence_moras_head + moras + silence_moras_tail
    return moras


def calc_frame_per_phoneme(query: AudioQuery, moras: List[Mora]):
    """
    音素あたりのフレーム長を算出
    Parameters
    ----------
    query : AudioQuery
        音声合成クエリ
    moras : List[Mora]
        モーラ列
    Returns
    -------
    frame_per_phoneme : NDArray[]
        音素あたりのフレーム長。端数丸め。
    """
    # 音素あたりの継続長
    sec_per_phoneme = numpy.array(
        [
            length
            for mora in moras
            for length in (
                [mora.consonant_length] if mora.consonant is not None else []
            )
            + [mora.vowel_length]
        ],
        dtype=numpy.float32,
    )

    # 話速による継続長の補正
    sec_per_phoneme /= query.speedScale

    # 音素あたりのフレーム長。端数丸め。
    framerate = 24000 / 256  # framerate 93.75 [frame/sec]
    frame_per_phoneme = numpy.round(sec_per_phoneme * framerate).astype(numpy.int32)

    return frame_per_phoneme


def calc_frame_pitch(
    query: AudioQuery,
    moras: List[Mora],
    phonemes: List[OjtPhoneme],
    frame_per_phoneme: numpy.ndarray,
):
    """
    フレームごとのピッチの生成
    Parameters
    ----------
    query : AudioQuery
        音声合成クエリ
    moras : List[Mora]
        モーラ列
    phonemes : List[OjtPhoneme]
        音素列
    frame_per_phoneme: NDArray
        音素あたりのフレーム長。端数丸め。
    Returns
    -------
    frame_f0 : NDArray[]
        フレームごとの基本周波数系列
    """
    # TODO: Better function name (c.f. VOICEVOX/voicevox_engine#790)
    # モーラごとの基本周波数
    f0 = numpy.array([mora.pitch for mora in moras], dtype=numpy.float32)

    # 音高スケールによる補正
    f0 *= 2**query.pitchScale

    # 抑揚スケールによる補正。有声音素 (f0>0) の平均値に対する乖離度をスケール
    voiced = f0 > 0
    mean_f0 = f0[voiced].mean()
    if not numpy.isnan(mean_f0):
        f0[voiced] = (f0[voiced] - mean_f0) * query.intonationScale + mean_f0

    # フレームごとのピッチ化
    # 母音インデックスに基づき "音素あたりのフレーム長" を "モーラあたりのフレーム長" に集約
    vowel_indexes = numpy.array(split_mora(phonemes)[2])
    frame_per_mora = [
        a.sum() for a in numpy.split(frame_per_phoneme, vowel_indexes[:-1] + 1)
    ]
    # モーラの基本周波数を子音・母音に割当てフレーム化
    frame_f0 = numpy.repeat(f0, frame_per_mora)
    return frame_f0


def calc_frame_phoneme(phonemes: List[OjtPhoneme], frame_per_phoneme: numpy.ndarray):
    """
    フレームごとの音素列の生成
    Parameters
    ----------
    phonemes : List[OjtPhoneme]
        音素列
    frame_per_phoneme: NDArray
        音素あたりのフレーム長。端数丸め。
    Returns
    -------
    frame_phoneme : NDArray[]
        フレームごとの音素系列
    """
    # TODO: Better function name (c.f. VOICEVOX/voicevox_engine#790)
    # Index化
    phoneme_ids = numpy.array([p.phoneme_id for p in phonemes], dtype=numpy.int64)

    # フレームごとの音素化
    frame_phoneme = numpy.repeat(phoneme_ids, frame_per_phoneme)

    # Onehot化
    array = numpy.zeros(
        (len(frame_phoneme), OjtPhoneme.num_phoneme), dtype=numpy.float32
    )
    array[numpy.arange(len(frame_phoneme)), frame_phoneme] = 1
    frame_phoneme = array

    return frame_phoneme


class SynthesisEngine(SynthesisEngineBase):
    """音声合成器（core）の管理/実行/プロキシと音声合成フロー"""

    def __init__(self, core: CoreWrapper):
        super().__init__()
        self.core = core
        self.mutex = threading.Lock()
        self.default_sampling_rate = 24000

    @property
    def speakers(self) -> str:
        """話者情報（json文字列）"""
        # Coreプロキシ
        return self.core.metas()

    @property
    def supported_devices(self) -> str | None:
        """デバイスサポート情報"""
        # Coreプロキシ
        try:
            supported_devices = self.core.supported_devices()
        except OldCoreError:
            supported_devices = None
        return supported_devices

    def initialize_style_id_synthesis(self, style_id: int, skip_reinit: bool):
        # Core管理
        try:
            with self.mutex:
                # 以下の条件のいずれかを満たす場合, 初期化を実行する
                # 1. 引数 skip_reinit が False の場合
                # 2. 話者が初期化されていない場合
                if (not skip_reinit) or (not self.core.is_model_loaded(style_id)):
                    self.core.load_model(style_id)
        except OldCoreError:
            pass  # コアが古い場合はどうしようもないので何もしない

    def is_initialized_style_id_synthesis(self, style_id: int) -> bool:
        # Coreプロキシ
        try:
            return self.core.is_model_loaded(style_id)
        except OldCoreError:
            return True  # コアが古い場合はどうしようもないのでTrueを返す

    def replace_phoneme_length(
        self, accent_phrases: List[AccentPhrase], style_id: int
    ) -> List[AccentPhrase]:
        """
        accent_phrasesの母音・子音の長さを設定する
        Parameters
        ----------
        accent_phrases : List[AccentPhrase]
            アクセント句モデルのリスト
        style_id : int
            スタイルID
        Returns
        -------
        accent_phrases : List[AccentPhrase]
            母音・子音の長さが設定されたアクセント句モデルのリスト
        """
        # モデルがロードされていない場合はロードする
        self.initialize_style_id_synthesis(style_id, skip_reinit=True)
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
        with self.mutex:
            phoneme_length = self.core.yukarin_s_forward(
                length=len(phoneme_list_s),
                phoneme_list=phoneme_list_s,
                style_id=numpy.array(style_id, dtype=numpy.int64).reshape(-1),
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
        self, accent_phrases: List[AccentPhrase], style_id: int
    ) -> List[AccentPhrase]:
        """
        accent_phrasesの音高(ピッチ)を設定する
        Parameters
        ----------
        accent_phrases : List[AccentPhrase]
            アクセント句モデルのリスト
        style_id : int
            スタイルID
        Returns
        -------
        accent_phrases : List[AccentPhrase]
            音高(ピッチ)が設定されたアクセント句モデルのリスト
        """
        # モデルがロードされていない場合はロードする
        self.initialize_style_id_synthesis(style_id, skip_reinit=True)
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
        with self.mutex:
            f0_list = self.core.yukarin_sa_forward(
                length=vowel_phoneme_list.shape[0],
                vowel_phoneme_list=vowel_phoneme_list[numpy.newaxis],
                consonant_phoneme_list=consonant_phoneme_list[numpy.newaxis],
                start_accent_list=start_accent_list[numpy.newaxis],
                end_accent_list=end_accent_list[numpy.newaxis],
                start_accent_phrase_list=start_accent_phrase_list[numpy.newaxis],
                end_accent_phrase_list=end_accent_phrase_list[numpy.newaxis],
                style_id=numpy.array(style_id, dtype=numpy.int64).reshape(-1),
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

    def _synthesis_impl(self, query: AudioQuery, style_id: int):
        """
        音声合成クエリから音声合成に必要な情報を構成し、実際に音声合成を行う
        Parameters
        ----------
        query : AudioQuery
            音声合成クエリ
        style_id : int
            スタイルID
        Returns
        -------
        wave : numpy.ndarray
            音声合成結果
        """
        # モデルがロードされていない場合はロードする
        self.initialize_style_id_synthesis(style_id, skip_reinit=True)
        # phoneme
        # AccentPhraseをすべてMoraおよびOjtPhonemeの形に分解し、処理可能な形にする
        flatten_moras, phoneme_data_list = pre_process(query.accent_phrases)

        flatten_moras = change_silence(flatten_moras, query)
        frame_per_phoneme = calc_frame_per_phoneme(query, flatten_moras)
        f0 = calc_frame_pitch(
            query, flatten_moras, phoneme_data_list, frame_per_phoneme
        )
        phoneme = calc_frame_phoneme(phoneme_data_list, frame_per_phoneme)

        # 今まで生成された情報をdecode_forwardにかけ、推論器によって音声波形を生成する
        with self.mutex:
            wave = self.core.decode_forward(
                length=phoneme.shape[0],
                phoneme_size=phoneme.shape[1],
                f0=f0[:, numpy.newaxis],
                phoneme=phoneme,
                style_id=numpy.array(style_id, dtype=numpy.int64).reshape(-1),
            )

        # volume: ゲイン適用
        wave *= query.volumeScale

        # 出力サンプリングレートがデフォルト(decode forwarderによるもの、24kHz)でなければ、それを適用する
        if query.outputSamplingRate != self.default_sampling_rate:
            wave = resample(
                wave,
                self.default_sampling_rate,
                query.outputSamplingRate,
            )

        # ステレオ変換
        # 出力設定がステレオなのであれば、ステレオ化する
        if query.outputStereo:
            wave = numpy.array([wave, wave]).T

        return wave
