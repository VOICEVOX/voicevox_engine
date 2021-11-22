import sys
from itertools import chain
from pathlib import Path
from typing import List, Optional, Tuple

import numpy
import resampy

from voicevox_engine.acoustic_feature_extractor import OjtPhoneme, SamplingData
from voicevox_engine.model import AccentPhrase, AudioQuery, Mora

unvoiced_mora_phoneme_list = ["A", "I", "U", "E", "O", "cl", "pau"]
mora_phoneme_list = ["a", "i", "u", "e", "o", "N"] + unvoiced_mora_phoneme_list


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


class SynthesisEngine:
    def __init__(
        self,
        yukarin_s_forwarder,
        yukarin_sa_forwarder,
        decode_forwarder,
        speakers: str,
    ):
        """
        yukarin_s_forwarder: 音素列から、音素ごとの長さを求める関数
            length: 音素列の長さ
            phoneme_list: 音素列
            speaker_id: 話者番号
            return: 音素ごとの長さ

        yukarin_sa_forwarder: モーラごとの音素列とアクセント情報から、モーラごとの音高を求める関数
            length: モーラ列の長さ
            vowel_phoneme_list: 母音の音素列
            consonant_phoneme_list: 子音の音素列
            start_accent_list: アクセントの開始位置
            end_accent_list: アクセントの終了位置
            start_accent_phrase_list: アクセント句の開始位置
            end_accent_phrase_list: アクセント句の終了位置
            speaker_id: 話者番号
            return: モーラごとの音高

        decode_forwarder: フレームごとの音素と音高から波形を求める関数
            length: フレームの長さ
            phoneme_size: 音素の種類数
            f0: フレームごとの音高
            phoneme: フレームごとの音素
            speaker_id: 話者番号
            return: 音声波形

        speakers: coreから取得したspeakersに関するjsonデータの文字列
        """
        super().__init__()
        self.yukarin_s_forwarder = yukarin_s_forwarder
        self.yukarin_sa_forwarder = yukarin_sa_forwarder
        self.decode_forwarder = decode_forwarder

        self.speakers = speakers
        self.default_sampling_rate = 24000

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
        # Phoneme IDのリスト(phoneme_list_s)をyukarin_s_forwarderにかけ、推論器によって適切な音素の長さを割り当てる
        phoneme_length = self.yukarin_s_forwarder(
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

        # 今までに生成された情報をyukarin_sa_forwarderにかけ、推論器によってモーラごとに適切な音高(ピッチ)を割り当てる
        f0_list = self.yukarin_sa_forwarder(
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

    def replace_mora_data(
        self,
        accent_phrases: List[AccentPhrase],
        speaker_id: int,
    ) -> List[AccentPhrase]:
        return self.replace_mora_pitch(
            accent_phrases=self.replace_phoneme_length(
                accent_phrases=accent_phrases,
                speaker_id=speaker_id,
            ),
            speaker_id=speaker_id,
        )

    def synthesis(self, query: AudioQuery, speaker_id: int):
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

        # TODO: rateを200にする意味がないので、テスト実装後リファクタする
        rate = 200

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
        # floatにキャストし、細かな値を四捨五入する
        phoneme_length = numpy.array(phoneme_length_list, dtype=numpy.float32)
        phoneme_length = numpy.round(phoneme_length * rate) / rate

        # lengthにSpeed Scale(話速)を適用する
        phoneme_length /= query.speedScale

        # TODO: 前の無音を少し長くすると最初のワードが途切れないワークアラウンド実装
        pre_padding_length = 0.4
        phoneme_length[0] += pre_padding_length

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

        # f0とphonemeをそれぞれデコード用にリサンプリングする
        f0 = SamplingData(array=f0, rate=rate).resample(24000 / 256)
        phoneme = SamplingData(array=phoneme, rate=rate).resample(24000 / 256)

        # 今まで生成された情報をdecode_forwarderにかけ、推論器によって音声波形を生成する
        wave = self.decode_forwarder(
            length=phoneme.shape[0],
            phoneme_size=phoneme.shape[1],
            f0=f0[:, numpy.newaxis],
            phoneme=phoneme,
            speaker_id=numpy.array(speaker_id, dtype=numpy.int64).reshape(-1),
        )

        # TODO: 前の無音を少し長くすると最初のワードが途切れないワークアラウンド実装の後処理
        wave = wave[int(self.default_sampling_rate * pre_padding_length) :]

        # volume
        # 音量が1ではないなら、その分を音声波形に適用する
        if query.volumeScale != 1:
            wave *= query.volumeScale

        # 出力サンプリングレートがデフォルト(decode forwarderによるもの、24kHz)でなければ、それを適用する
        if query.outputSamplingRate != self.default_sampling_rate:
            wave = resampy.resample(
                wave,
                self.default_sampling_rate,
                query.outputSamplingRate,
                filter="kaiser_fast",
            )

        # ステレオ変換
        # 出力設定がステレオなのであれば、ステレオ化する
        if query.outputStereo:
            wave = numpy.array([wave, wave]).T

        return wave


def make_synthesis_engine(
    use_gpu: bool,
    voicelib_dir: Path,
    voicevox_dir: Optional[Path] = None,
) -> SynthesisEngine:
    """
    音声ライブラリをロードして、音声合成エンジンを生成

    Parameters
    ----------
    use_gpu: bool
        音声ライブラリに GPU を使わせるか否か
    voicelib_dir: Path
        音声ライブラリ自体があるディレクトリ
    voicevox_dir: Path, optional, default=None
        音声ライブラリの Python モジュールがあるディレクトリ
        None のとき、Python 標準のモジュール検索パスのどれかにあるとする
    """

    # Python モジュール検索パスへ追加
    if voicevox_dir is not None:
        print("Notice: --voicevox_dir is " + voicevox_dir.as_posix(), file=sys.stderr)
        if voicevox_dir.exists():
            sys.path.insert(0, str(voicevox_dir))

    has_voicevox_core = True
    try:
        import core
    except ImportError:
        import traceback

        from voicevox_engine.dev import core

        has_voicevox_core = False

        # 音声ライブラリの Python モジュールをロードできなかった
        traceback.print_exc()
        print(
            "Notice: mock-library will be used. Try re-run with valid --voicevox_dir",  # noqa
            file=sys.stderr,
        )

    core.initialize(voicelib_dir.as_posix() + "/", use_gpu)

    if has_voicevox_core:
        return SynthesisEngine(
            yukarin_s_forwarder=core.yukarin_s_forward,
            yukarin_sa_forwarder=core.yukarin_sa_forward,
            decode_forwarder=core.decode_forward,
            speakers=core.metas(),
        )

    from voicevox_engine.dev.synthesis_engine import (
        SynthesisEngine as mock_synthesis_engine,
    )

    # モックで置き換える
    return mock_synthesis_engine(speakers=core.metas())
