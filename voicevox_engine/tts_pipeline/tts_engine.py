import math
import threading
from typing import List, Optional

import numpy
from numpy import ndarray
from soxr import resample

from ..core_wrapper import CoreWrapper, OldCoreError
from ..model import AccentPhrase, AudioQuery, Mora
from .acoustic_feature_extractor import OjtPhoneme
from .tts_engine_base import TTSEngineBase

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


def count_frame_per_unit(moras: list[Mora]) -> tuple[ndarray, ndarray]:
    """
    音素あたり・モーラあたりのフレーム長を算出する
    Parameters
    ----------
    moras : list[Mora]
        モーラ系列
    Returns
    -------
    frame_per_phoneme : ndarray
        音素あたりのフレーム長。端数丸め。shape = (Phoneme,)
    frame_per_mora : ndarray
        モーラあたりのフレーム長。端数丸め。shape = (Mora,)
    """
    frame_per_phoneme: list[ndarray] = []
    frame_per_mora: list[ndarray] = []
    for mora in moras:
        vowel_frames = _to_frame(mora.vowel_length)
        consonant_frames = _to_frame(mora.consonant_length) if mora.consonant else 0
        mora_frames = vowel_frames + consonant_frames  # 音素ごとにフレーム長を算出し、和をモーラのフレーム長とする

        if mora.consonant:
            frame_per_phoneme += [consonant_frames]
        frame_per_phoneme += [vowel_frames]
        frame_per_mora += [mora_frames]

    frame_per_phoneme = numpy.array(frame_per_phoneme)
    frame_per_mora = numpy.array(frame_per_mora)

    return frame_per_phoneme, frame_per_mora


def _to_frame(sec: float) -> ndarray:
    FRAMERATE = 93.75  # 24000 / 256 [frame/sec]
    # NOTE: `round` は偶数丸め。移植時に取扱い注意。詳細は voicevox_engine#552
    return numpy.round(sec * FRAMERATE).astype(numpy.int32)


def apply_pitch_scale(moras: list[Mora], query: AudioQuery) -> list[Mora]:
    """モーラ系列へ音声合成用のクエリがもつ音高スケール（`pitchScale`）を適用する"""
    for mora in moras:
        mora.pitch *= 2**query.pitchScale
    return moras


def apply_intonation_scale(moras: list[Mora], query: AudioQuery) -> list[Mora]:
    """モーラ系列へ音声合成用のクエリがもつ抑揚スケール（`intonationScale`）を適用する"""
    # 有声音素 (f0>0) の平均値に対する乖離度をスケール
    voiced = list(filter(lambda mora: mora.pitch > 0, moras))
    mean_f0 = numpy.mean(list(map(lambda mora: mora.pitch, voiced))).item()
    if mean_f0 != math.nan:  # 空リスト -> NaN
        for mora in voiced:
            mora.pitch = (mora.pitch - mean_f0) * query.intonationScale + mean_f0
    return moras


def apply_volume_scale(wave: numpy.ndarray, query: AudioQuery) -> numpy.ndarray:
    """音声波形へ音声合成用のクエリがもつ音量スケール（`volumeScale`）を適用する"""
    wave *= query.volumeScale
    return wave


def apply_output_sampling_rate(
    wave: ndarray, sr_wave: int, query: AudioQuery
) -> ndarray:
    """音声波形へ音声合成用のクエリがもつ出力サンプリングレート（`outputSamplingRate`）を適用する"""
    # サンプリングレート一致のときはスルー
    if sr_wave == query.outputSamplingRate:
        return wave
    wave = resample(wave, sr_wave, query.outputSamplingRate)
    return wave


def apply_output_stereo(wave: ndarray, query: AudioQuery) -> ndarray:
    """音声波形へ音声合成用のクエリがもつステレオ出力設定（`outputStereo`）を適用する"""
    if query.outputStereo:
        wave = numpy.array([wave, wave]).T
    return wave


def query_to_decoder_feature(query: AudioQuery) -> tuple[ndarray, ndarray]:
    """音声合成用のクエリからフレームごとの音素 (shape=(フレーム長, 音素数)) と音高 (shape=(フレーム長,)) を得る"""
    moras = to_flatten_moras(query.accent_phrases)

    # 設定を適用する
    moras = apply_prepost_silence(moras, query)
    moras = apply_speed_scale(moras, query)
    moras = apply_pitch_scale(moras, query)
    moras = apply_intonation_scale(moras, query)

    # 表現を変更する（音素クラス → 音素 onehot ベクトル、モーラクラス → 音高スカラ）
    phoneme = numpy.stack([p.onehot for p in to_flatten_phonemes(moras)])
    f0 = numpy.array([mora.pitch for mora in moras], dtype=numpy.float32)

    # 時間スケールを変更する（音素・モーラ → フレーム）
    frame_per_phoneme, frame_per_mora = count_frame_per_unit(moras)
    phoneme = numpy.repeat(phoneme, frame_per_phoneme, axis=0)
    f0 = numpy.repeat(f0, frame_per_mora)

    return phoneme, f0


def raw_wave_to_output_wave(query: AudioQuery, wave: ndarray, sr_wave: int) -> ndarray:
    """生音声波形に音声合成用のクエリを適用して出力音声波形を生成する"""
    wave = apply_volume_scale(wave, query)
    wave = apply_output_sampling_rate(wave, sr_wave, query)
    wave = apply_output_stereo(wave, query)
    return wave


class CoreAdapter:
    """
    コアのアダプター。
    ついでにコア内部で推論している処理をプロセスセーフにする。
    """

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

    def safe_yukarin_s_forward(self, phoneme_list_s: ndarray, style_id: int) -> ndarray:
        # 「指定スタイルを初期化」「mutexによる安全性」「系列長・データ型に関するアダプター」を提供する
        self.initialize_style_id_synthesis(style_id, skip_reinit=True)
        with self.mutex:
            phoneme_length = self.core.yukarin_s_forward(
                length=len(phoneme_list_s),
                phoneme_list=phoneme_list_s,
                style_id=numpy.array(style_id, dtype=numpy.int64).reshape(-1),
            )
        return phoneme_length

    def safe_yukarin_sa_forward(
        self,
        vowel_phoneme_list: ndarray,
        consonant_phoneme_list: ndarray,
        start_accent_list: ndarray,
        end_accent_list: ndarray,
        start_accent_phrase_list: ndarray,
        end_accent_phrase_list: ndarray,
        style_id: int,
    ) -> ndarray:
        # 「指定スタイルを初期化」「mutexによる安全性」「系列長・データ型に関するアダプター」を提供する
        self.initialize_style_id_synthesis(style_id, skip_reinit=True)
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
        return f0_list

    def safe_decode_forward(
        self, phoneme: ndarray, f0: ndarray, style_id: int
    ) -> tuple[ndarray, int]:
        # 「指定スタイルを初期化」「mutexによる安全性」「系列長・データ型に関するアダプター」を提供する
        self.initialize_style_id_synthesis(style_id, skip_reinit=True)
        with self.mutex:
            wave = self.core.decode_forward(
                length=phoneme.shape[0],
                phoneme_size=phoneme.shape[1],
                f0=f0[:, numpy.newaxis],
                phoneme=phoneme,
                style_id=numpy.array(style_id, dtype=numpy.int64).reshape(-1),
            )
        sr_wave = self.default_sampling_rate
        return wave, sr_wave


class TTSEngine(TTSEngineBase):
    """音声合成器（core）の管理/実行/プロキシと音声合成フロー"""

    def __init__(self, core: CoreWrapper):
        super().__init__()
        self.core = CoreAdapter(core)
        # NOTE: self.coreは将来的に消す予定

    @property
    def default_sampling_rate(self) -> int:
        return self.core.default_sampling_rate

    @property
    def speakers(self) -> str:
        return self.core.speakers

    @property
    def supported_devices(self) -> str | None:
        return self.core.supported_devices

    def initialize_style_id_synthesis(self, style_id: int, skip_reinit: bool):
        return self.core.initialize_style_id_synthesis(style_id, skip_reinit)

    def is_initialized_style_id_synthesis(self, style_id: int) -> bool:
        return self.core.is_initialized_style_id_synthesis(style_id)

    def replace_phoneme_length(
        self, accent_phrases: list[AccentPhrase], style_id: int
    ) -> list[AccentPhrase]:
        """アクセント句系列に含まれるモーラの音素長属性をスタイルに合わせて更新する"""
        # モーラ系列を抽出する
        moras = to_flatten_moras(accent_phrases)

        # 音素系列を抽出し前後無音を付加する
        phonemes = to_flatten_phonemes(moras)
        phonemes = [OjtPhoneme("pau")] + phonemes + [OjtPhoneme("pau")]

        # 音素クラスから音素IDスカラへ表現を変換する
        phoneme_ids = numpy.array([p.phoneme_id for p in phonemes], dtype=numpy.int64)

        # コアを用いて音素長を生成する
        phoneme_lengths = self.core.safe_yukarin_s_forward(phoneme_ids, style_id)

        # 生成結果でモーラ内の音素長属性を置換する
        vowel_indexes = [
            i for i, p in enumerate(phonemes) if p.phoneme in mora_phoneme_list
        ]
        for i, mora in enumerate(moras):
            if mora.consonant is None:
                mora.consonant_length = None
            else:
                mora.consonant_length = phoneme_lengths[vowel_indexes[i + 1] - 1]
            mora.vowel_length = phoneme_lengths[vowel_indexes[i + 1]]

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
        f0_list = self.core.safe_yukarin_sa_forward(
            vowel_phoneme_list,
            consonant_phoneme_list,
            start_accent_list,
            end_accent_list,
            start_accent_phrase_list,
            end_accent_phrase_list,
            style_id,
        )

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
        音声合成用のクエリから音声合成に必要な情報を構成し、実際に音声合成を行う
        Parameters
        ----------
        query : AudioQuery
            音声合成用のクエリ
        style_id : int
            スタイルID
        Returns
        -------
        wave : numpy.ndarray
            音声合成結果
        """
        phoneme, f0 = query_to_decoder_feature(query)
        raw_wave, sr_raw_wave = self.core.safe_decode_forward(phoneme, f0, style_id)
        wave = raw_wave_to_output_wave(query, raw_wave, sr_raw_wave)
        return wave
