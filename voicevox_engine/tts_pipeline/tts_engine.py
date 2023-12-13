import math
import threading
from typing import List, Optional

import numpy
from numpy import ndarray
from soxr import resample

from ..core_wrapper import CoreWrapper, OldCoreError
from ..model import AccentPhrase, AudioQuery, Mora
from .acoustic_feature_extractor import OjtPhoneme
from .tts_engine_base import SynthesisEngineBase

unvoiced_mora_phoneme_list = ["A", "I", "U", "E", "O", "cl", "pau"]
mora_phoneme_list = ["a", "i", "u", "e", "o", "N"] + unvoiced_mora_phoneme_list


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


def to_flatten_phonemes(moras: list[Mora]) -> list[OjtPhoneme]:
    """
    モーラ系列に含まれる音素の抽出
    Parameters
    ----------
    moras : list[Mora]
        モーラ系列
    Returns
    -------
    phonemes : list[OjtPhoneme]
        音素系列
    """
    phonemes: list[OjtPhoneme] = []
    for mora in moras:
        if mora.consonant:
            phonemes += [OjtPhoneme(mora.consonant)]
        phonemes += [(OjtPhoneme(mora.vowel))]
    return phonemes


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
    accent_phrases: list[AccentPhrase],
) -> tuple[list[Mora], list[OjtPhoneme]]:
    """
    AccentPhraseモデルのリストを整形し、処理に必要なデータの原型を作り出す
    Parameters
    ----------
    accent_phrases : List[AccentPhrase]
        AccentPhraseモデルのリスト
    Returns
    -------
    flatten_moras : List[Mora]
        モーラ列（前後の無音含まない）
    phonemes : List[OjtPhoneme]
        音素列（前後の無音含む）
    """
    flatten_moras = to_flatten_moras(accent_phrases)
    phonemes = to_flatten_phonemes(flatten_moras)

    # 前後無音の追加
    phonemes = [OjtPhoneme("pau")] + phonemes + [OjtPhoneme("pau")]

    return flatten_moras, phonemes


def generate_silence_mora(length: float) -> Mora:
    """無音モーラの生成"""
    return Mora(text="　", vowel="sil", vowel_length=length, pitch=0.0)


def apply_prepost_silence(moras: list[Mora], query: AudioQuery) -> list[Mora]:
    """
    前後無音（`prePhonemeLength` & `postPhonemeLength`）の適用
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
    pre_silence_moras = [generate_silence_mora(query.prePhonemeLength)]
    post_silence_moras = [generate_silence_mora(query.postPhonemeLength)]
    moras = pre_silence_moras + moras + post_silence_moras
    return moras


def apply_speed_scale(moras: list[Mora], query: AudioQuery) -> list[Mora]:
    """
    話速スケール（`speedScale`）の適用
    Parameters
    ----------
    moras : list[Mora]
        モーラ系列
    query : AudioQuery
        音声合成クエリ
    Returns
    -------
    moras : list[Mora]
        話速スケールが適用されたモーラ系列
    """
    for mora in moras:
        mora.vowel_length /= query.speedScale
        if mora.consonant_length:
            mora.consonant_length /= query.speedScale
    return moras


def calc_frame_per_phoneme(moras: List[Mora]):
    """
    音素あたりのフレーム長を算出
    Parameters
    ----------
    moras : List[Mora]
        モーラ列
    Returns
    -------
    frame_per_phoneme : NDArray[]
        音素あたりのフレーム長。端数丸め。
    """
    frame_per_phoneme: list[ndarray] = []
    for mora in moras:
        if mora.consonant:
            frame_per_phoneme.append(_to_frame(mora.consonant_length))
        frame_per_phoneme.append(_to_frame(mora.vowel_length))
    frame_per_phoneme = numpy.array(frame_per_phoneme)
    return frame_per_phoneme


def _to_frame(sec: float) -> ndarray:
    FRAMERATE = 93.75  # 24000 / 256 [frame/sec]
    # NOTE: `round` は偶数丸め。移植時に取扱い注意。詳細は voicevox_engine#552
    return numpy.round(sec * FRAMERATE).astype(numpy.int32)


def calc_frame_per_mora(mora: Mora) -> ndarray:
    """
    モーラあたりのフレーム長を算出
    Parameters
    ----------
    mora : Mora
        モーラ
    Returns
    -------
    frame_per_mora : NDArray[]
        モーラあたりのフレーム長。端数丸め。
    """
    # 音素ごとにフレーム長を算出し、和をモーラのフレーム長とする
    vowel_frames = _to_frame(mora.vowel_length)
    consonant_frames = _to_frame(mora.consonant_length) if mora.consonant else 0
    return vowel_frames + consonant_frames


def apply_pitch_scale(moras: list[Mora], query: AudioQuery) -> list[Mora]:
    """
    音高スケール（`pitchScale`）の適用
    Parameters
    ----------
    moras : list[Mora]
        モーラ系列
    query : AudioQuery
        音声合成クエリ
    Returns
    -------
    moras : list[Mora]
        音高スケールが適用されたモーラ系列
    """
    for mora in moras:
        mora.pitch *= 2**query.pitchScale
    return moras


def apply_intonation_scale(moras: list[Mora], query: AudioQuery) -> list[Mora]:
    """
    抑揚スケール（`intonationScale`）の適用
    Parameters
    ----------
    moras : list[Mora]
        モーラ系列
    query : AudioQuery
        音声合成クエリ
    Returns
    -------
    moras : list[Mora]
        抑揚スケールが適用されたモーラ系列
    """
    # 有声音素 (f0>0) の平均値に対する乖離度をスケール
    voiced = list(filter(lambda mora: mora.pitch > 0, moras))
    mean_f0 = numpy.mean(list(map(lambda mora: mora.pitch, voiced))).item()
    if mean_f0 != math.nan:  # 空リスト -> NaN
        for mora in voiced:
            mora.pitch = (mora.pitch - mean_f0) * query.intonationScale + mean_f0
    return moras


def calc_frame_pitch(moras: list[Mora]) -> ndarray:
    """
    フレームごとのピッチの生成
    Parameters
    ----------
    moras : List[Mora]
        モーラ列
    Returns
    -------
    frame_f0 : NDArray[]
        フレームごとの基本周波数系列
    """
    # TODO: Better function name (c.f. VOICEVOX/voicevox_engine#790)
    # モーラごとの基本周波数
    f0 = numpy.array([mora.pitch for mora in moras], dtype=numpy.float32)

    # Rescale: 時間スケールの変更（モーラ -> フレーム）
    # 母音インデックスに基づき "音素あたりのフレーム長" を "モーラあたりのフレーム長" に集約
    frame_per_mora = numpy.array(list(map(calc_frame_per_mora, moras)))
    frame_f0 = numpy.repeat(f0, frame_per_mora)
    return frame_f0


def apply_volume_scale(wave: numpy.ndarray, query: AudioQuery) -> numpy.ndarray:
    """
    音量スケール（`volumeScale`）の適用
    Parameters
    ----------
    wave : numpy.ndarray
        音声波形
    query : AudioQuery
        音声合成クエリ
    Returns
    -------
    wave : numpy.ndarray
        音量スケールが適用された音声波形
    """
    wave *= query.volumeScale
    return wave


def calc_frame_phoneme(phonemes: List[OjtPhoneme], frame_per_phoneme: numpy.ndarray):
    """
    フレームごとの音素列の生成（onehot化 + フレーム化）
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
    # Convert: Core入力形式への変換（onehotベクトル系列）
    onehot_phoneme = numpy.stack([p.onehot for p in phonemes])

    # Rescale: 時間スケールの変更（音素 -> フレーム）
    frame_phoneme = numpy.repeat(onehot_phoneme, frame_per_phoneme, axis=0)
    return frame_phoneme


def apply_output_sampling_rate(
    wave: ndarray, sr_wave: int, query: AudioQuery
) -> ndarray:
    """
    出力サンプリングレート（`outputSamplingRate`）の適用
    Parameters
    ----------
    wave : ndarray
        音声波形
    sr_wave : int
        `wave`のサンプリングレート
    query : AudioQuery
        音声合成クエリ
    Returns
    -------
    wave : ndarray
        出力サンプリングレートが適用された音声波形
    """
    # サンプリングレート一致のときはスルー
    if sr_wave == query.outputSamplingRate:
        return wave

    wave = resample(wave, sr_wave, query.outputSamplingRate)
    return wave


def apply_output_stereo(wave: ndarray, query: AudioQuery) -> ndarray:
    """
    ステレオ出力（`outputStereo`）の適用
    Parameters
    ----------
    wave : ndarray
        音声波形
    query : AudioQuery
        音声合成クエリ
    Returns
    -------
    wave : ndarray
        ステレオ出力設定が適用された音声波形
    """
    if query.outputStereo:
        wave = numpy.array([wave, wave]).T
    return wave


class SynthesisEngine(SynthesisEngineBase):
    """音声合成器（core）の管理/実行/プロキシと音声合成フロー"""

    def __init__(self, core: CoreWrapper):
        super().__init__()
        self.core = core
        self.mutex = threading.Lock()

    @property
    def default_sampling_rate(self) -> int:
        return self.core.default_sampling_rate

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

        flatten_moras = to_flatten_moras(query.accent_phrases)
        flatten_moras = apply_prepost_silence(flatten_moras, query)
        flatten_moras = apply_speed_scale(flatten_moras, query)
        flatten_moras = apply_pitch_scale(flatten_moras, query)
        flatten_moras = apply_intonation_scale(flatten_moras, query)

        phoneme_data_list = to_flatten_phonemes(flatten_moras)

        frame_per_phoneme = calc_frame_per_phoneme(flatten_moras)
        f0 = calc_frame_pitch(flatten_moras)
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
            sr_wave = self.default_sampling_rate

        wave = apply_volume_scale(wave, query)
        wave = apply_output_sampling_rate(wave, sr_wave, query)
        wave = apply_output_stereo(wave, query)

        return wave
