import copy
import math

import numpy
from numpy import ndarray
from soxr import resample

from ..core_adapter import CoreAdapter
from ..core_wrapper import CoreWrapper
from ..metas.Metas import StyleId
from ..model import AccentPhrase, AudioQuery, Mora
from .acoustic_feature_extractor import Phoneme
from .mora_list import openjtalk_mora2text
from .text_analyzer import text_to_accent_phrases

unvoiced_mora_phoneme_list = ["A", "I", "U", "E", "O", "cl", "pau"]
mora_phoneme_list = ["a", "i", "u", "e", "o", "N"] + unvoiced_mora_phoneme_list

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


def split_mora(
    phoneme_list: list[Phoneme],
) -> tuple[list[Phoneme | None], list[Phoneme], list[int]]:
    """音素系列から子音系列・母音系列・母音位置を抽出する"""
    vowel_indexes = [
        i for i, p in enumerate(phoneme_list) if p.phoneme in mora_phoneme_list
    ]
    vowel_phoneme_list = [phoneme_list[i] for i in vowel_indexes]
    # postとprevのvowel_indexの差として考えられる値は1か2
    # 理由としてはphoneme_listは、consonant、vowelの組み合わせか、vowel一つの連続であるから
    # 1の場合はconsonant(子音)が存在しない=母音のみ(a/i/u/e/o/N/cl/pau)で構成されるモーラ(音)である
    # 2の場合はconsonantが存在するモーラである
    # なので、2の場合(else)でphonemeを取り出している
    consonant_phoneme_list = [None] + [
        None if post - prev == 1 else phoneme_list[post - 1]
        for prev, post in zip(vowel_indexes[:-1], vowel_indexes[1:])
    ]
    return consonant_phoneme_list, vowel_phoneme_list, vowel_indexes


def pre_process(
    accent_phrases: list[AccentPhrase],
) -> tuple[list[Mora], list[Phoneme]]:
    """アクセント句系列から（前後の無音含まない）モーラ系列と（前後の無音含む）音素系列を抽出する"""
    flatten_moras = to_flatten_moras(accent_phrases)
    phonemes = to_flatten_phonemes(flatten_moras)

    # 前後無音の追加
    phonemes = [Phoneme("pau")] + phonemes + [Phoneme("pau")]

    return flatten_moras, phonemes


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
                text=openjtalk_mora2text[last_mora.vowel],
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

    return numpy.array(frame_per_phoneme), numpy.array(frame_per_mora)


def _to_frame(sec: float) -> int:
    FRAMERATE = 93.75  # 24000 / 256 [frame/sec]
    # NOTE: `round` は偶数丸め。移植時に取扱い注意。詳細は voicevox_engine#552
    return numpy.round(sec * FRAMERATE).astype(numpy.int32).item()


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


class TTSEngine:
    """音声合成器（core）の管理/実行/プロキシと音声合成フロー"""

    def __init__(self, core: CoreWrapper):
        super().__init__()
        self._core = CoreAdapter(core)
        # NOTE: self._coreは将来的に消す予定

    def replace_phoneme_length(
        self, accent_phrases: list[AccentPhrase], style_id: StyleId
    ) -> list[AccentPhrase]:
        """アクセント句系列に含まれるモーラの音素長属性をスタイルに合わせて更新する"""
        # モーラ系列を抽出する
        moras = to_flatten_moras(accent_phrases)

        # 音素系列を抽出し前後無音を付加する
        phonemes = to_flatten_phonemes(moras)
        phonemes = [Phoneme("pau")] + phonemes + [Phoneme("pau")]

        # 音素クラスから音素IDスカラへ表現を変換する
        phoneme_ids = numpy.array([p.phoneme_id for p in phonemes], dtype=numpy.int64)

        # コアを用いて音素長を生成する
        phoneme_lengths = self._core.safe_yukarin_s_forward(phoneme_ids, style_id)

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
        self, accent_phrases: list[AccentPhrase], style_id: StyleId
    ) -> list[AccentPhrase]:
        """
        accent_phrasesの音高(ピッチ)を設定する
        Parameters
        ----------
        accent_phrases : List[AccentPhrase]
            アクセント句モデルのリスト
        style_id : StyleId
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
        # AccentPhraseをすべてMoraおよびPhonemeの形に分解し、処理可能な形にする
        flatten_moras, phoneme_data_list = pre_process(accent_phrases)

        # accent
        def _create_one_hot(accent_phrase: AccentPhrase, position: int) -> ndarray:
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
        f0_list = self._core.safe_yukarin_sa_forward(
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

    def replace_mora_data(
        self, accent_phrases: list[AccentPhrase], style_id: StyleId
    ) -> list[AccentPhrase]:
        """アクセント句系列の音素長・モーラ音高をスタイルIDに基づいて更新する"""
        return self.replace_mora_pitch(
            accent_phrases=self.replace_phoneme_length(
                accent_phrases=accent_phrases, style_id=style_id
            ),
            style_id=style_id,
        )

    def create_accent_phrases(self, text: str, style_id: StyleId) -> list[AccentPhrase]:
        """テキストからアクセント句系列を生成し、スタイルIDに基づいてその音素長・モーラ音高を更新する"""
        # 音素とアクセントの推定
        accent_phrases = text_to_accent_phrases(text)

        # 音素長・モーラ音高の推定と更新
        accent_phrases = self.replace_mora_data(
            accent_phrases=accent_phrases,
            style_id=style_id,
        )
        return accent_phrases

    def synthesis(
        self,
        query: AudioQuery,
        style_id: StyleId,
        enable_interrogative_upspeak: bool = True,
    ) -> ndarray:
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
