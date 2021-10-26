from itertools import chain
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


def accent_phrases_shaping(
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
        # Step1. まず、AccentPhraseをすべてMoraおよびOjtPhonemeの形に分解し、処理可能な形にする
        flatten_moras, phoneme_data_list = accent_phrases_shaping(accent_phrases)
        # Step2. 次にOjtPhonemeの形に分解されたもの(phoneme_data_list)から、vowel(母音)の位置を抜き出す
        _, _, vowel_indexes_data = split_mora(phoneme_data_list)

        # yukarin_s
        # Step3. OjtPhonemeのリストからOjtPhonemeのPhoneme ID(OpenJTalkにおける音素のID)のリストを作る
        phoneme_list_s = numpy.array(
            [p.phoneme_id for p in phoneme_data_list], dtype=numpy.int64
        )
        # Step4. Step3.で作られたPhoneme IDのリストをyukarin_s_forwarderにかけ、推論器によって適切な音素の長さを割り当てる
        phoneme_length = self.yukarin_s_forwarder(
            length=len(phoneme_list_s),
            phoneme_list=phoneme_list_s,
            speaker_id=numpy.array(speaker_id, dtype=numpy.int64).reshape(-1),
        )

        # Step5. yukarin_s_forwarderの結果をaccent_phrasesに反映する
        # PythonにおけるObject(class)はイミュータブルであるため、
        # flatten_moras変数に展開された値を変更することで間接的にaccent_phrases内のデータを書き換えることができる
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
        # Step1. まず、AccentPhraseをすべてMoraおよびOjtPhonemeの形に分解し、処理可能な形にする
        flatten_moras, phoneme_data_list = accent_phrases_shaping(accent_phrases)

        # accent
        def _repeat_with_mora(array: numpy.ndarray, accent_phrase: AccentPhrase):
            """
            moraの数だけあるarrayの要素数をphonemeの数まで増やす(変換する)
            Parameters
            ----------
            array : numpy.ndarray
                moraの数だけ要素数があるarray
            accent_phrase : AccentPhrase
                アクセント句モデル
            Returns
            -------
            array : numpy.ndarray
                phonemeの数まで拡張されたarrayを返す
            """
            return numpy.repeat(
                array,
                [
                    1 if mora.consonant is None else 2
                    for mora in accent_phrase.moras
                    + (
                        [accent_phrase.pause_mora]
                        if accent_phrase.pause_mora is not None
                        else []
                    )
                ],
            )

        # Step2. accent_phrasesから、アクセントの開始位置のリストを作る
        # 単位行列(numpy.eye)を応用し、accent_listを作っている
        start_accent_list = numpy.concatenate(
            [
                _repeat_with_mora(
                    numpy.r_[
                        numpy.eye(len(accent_phrase.moras))[
                            # accentはプログラミング言語におけるindexのように0始まりではなく1始まりなので、
                            # accentが1の場合は0番目を指定している
                            # accentが1ではない場合、accentはend_accent_listに用いられる
                            0
                            if accent_phrase.accent == 1
                            else 1
                        ],
                        (0 if accent_phrase.pause_mora is not None else []),
                    ],
                    accent_phrase=accent_phrase,
                )
                for accent_phrase in accent_phrases
            ]
        )

        # Step3. accent_phrasesから、アクセントの終了位置のリストを作る
        end_accent_list = numpy.concatenate(
            [
                _repeat_with_mora(
                    numpy.r_[
                        # accentはプログラミング言語におけるindexのように0始まりではなく1始まりなので、1を引いている
                        numpy.eye(len(accent_phrase.moras))[accent_phrase.accent - 1],
                        (0 if accent_phrase.pause_mora is not None else []),
                    ],
                    accent_phrase=accent_phrase,
                )
                for accent_phrase in accent_phrases
            ]
        )

        # Step4. accent_phrasesから、アクセント句の開始位置のリストを作る
        # これによって、yukarin_sa_forwarder内でアクセント句を区別できる
        start_accent_phrase_list = numpy.concatenate(
            [
                _repeat_with_mora(
                    numpy.r_[
                        # フレーズの長さ分の単位行列の0番目([1, 0, 0, 0, 0,....])を取り出す
                        numpy.eye(len(accent_phrase.moras))[0],
                        (0 if accent_phrase.pause_mora is not None else []),
                    ],
                    accent_phrase=accent_phrase,
                )
                for accent_phrase in accent_phrases
            ]
        )

        # Step5. accent_phrasesから、アクセント句の終了位置のリストを作る
        end_accent_phrase_list = numpy.concatenate(
            [
                _repeat_with_mora(
                    numpy.r_[
                        # フレーズの長さ分の単位行列の最後([....0, 0, 0, 0, 1])を取り出す
                        numpy.eye(len(accent_phrase.moras))[-1],
                        (0 if accent_phrase.pause_mora is not None else []),
                    ],
                    accent_phrase=accent_phrase,
                )
                for accent_phrase in accent_phrases
            ]
        )

        # Step6. 最初と最後に0を付け加える。これによってpau(前後の無音のためのもの)を付け加えたことになる
        start_accent_list = numpy.r_[0, start_accent_list, 0]
        end_accent_list = numpy.r_[0, end_accent_list, 0]
        start_accent_phrase_list = numpy.r_[0, start_accent_phrase_list, 0]
        end_accent_phrase_list = numpy.r_[0, end_accent_phrase_list, 0]

        # Step7. アクセント・アクセント句関連のデータをyukarin_sa_forwarderに渡すための最終処理、リスト内のデータをint64に変換する
        start_accent_list = numpy.array(start_accent_list, dtype=numpy.int64)
        end_accent_list = numpy.array(end_accent_list, dtype=numpy.int64)
        start_accent_phrase_list = numpy.array(
            start_accent_phrase_list, dtype=numpy.int64
        )
        end_accent_phrase_list = numpy.array(end_accent_phrase_list, dtype=numpy.int64)

        # Step8. phonemeに関するデータを取得(変換)する
        (
            consonant_phoneme_data_list,
            vowel_phoneme_data_list,
            vowel_indexes_data,
        ) = split_mora(phoneme_data_list)

        # yukarin_sa
        # Step9. Phoneme関連のデータをyukarin_sa_forwarderに渡すための最終処理、リスト内のデータをint64に変換する
        vowel_indexes = numpy.array(vowel_indexes_data, dtype=numpy.int64)

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

        # Step10. Step7.およびStep9.で作られたデータをyukarin_sa_forwarderにかけ、推論器によってモーラごとに適切な音高(ピッチ)を割り当てる
        f0_list = self.yukarin_sa_forwarder(
            length=vowel_phoneme_list.shape[0],
            vowel_phoneme_list=vowel_phoneme_list[numpy.newaxis],
            consonant_phoneme_list=consonant_phoneme_list[numpy.newaxis],
            start_accent_list=start_accent_list[vowel_indexes][numpy.newaxis],
            end_accent_list=end_accent_list[vowel_indexes][numpy.newaxis],
            start_accent_phrase_list=start_accent_phrase_list[vowel_indexes][
                numpy.newaxis
            ],
            end_accent_phrase_list=end_accent_phrase_list[vowel_indexes][numpy.newaxis],
            speaker_id=numpy.array(speaker_id, dtype=numpy.int64).reshape(-1),
        )[0]

        # Step11. 無声母音を含むMoraに関しては、音高(ピッチ)を0にする
        for i, p in enumerate(vowel_phoneme_data_list):
            if p.phoneme in unvoiced_mora_phoneme_list:
                f0_list[i] = 0

        # Step12. yukarin_sa_forwarderの結果をaccent_phrasesに反映する
        # PythonにおけるObject(class)はイミュータブルであるため、
        # flatten_moras変数に展開された値を変更することで間接的にaccent_phrases内のデータを書き換えることができる
        for i, mora in enumerate(flatten_moras):
            mora.pitch = f0_list[i + 1]

        return accent_phrases

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

        # TODO: rateの意味
        rate = 200

        # phoneme
        # Step1. まず、AccentPhraseをすべてMoraおよびOjtPhonemeの形に分解し、処理可能な形にする
        flatten_moras, phoneme_data_list = accent_phrases_shaping(query.accent_phrases)

        # Step2. OjtPhonemeのリストからOjtPhonemeのPhoneme ID(OpenJTalkにおける音素のID)のリストを作る
        phoneme_list_s = numpy.array(
            [p.phoneme_id for p in phoneme_data_list], dtype=numpy.int64
        )

        # length
        # Step3. 音素の長さをリストに展開・結合する。ここには前後の無音時間も含まれる
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
        # Step4. floatにキャストし、細かな値を四捨五入する
        phoneme_length = numpy.array(phoneme_length_list, dtype=numpy.float32)
        phoneme_length = numpy.round(phoneme_length * rate) / rate

        # Step5. lengthにSpeed Scale(話速)を適用する
        phoneme_length /= query.speedScale

        # TODO: 前の無音を少し長くすると最初のワードが途切れないワークアラウンド実装
        pre_padding_length = 0.4
        phoneme_length[0] += pre_padding_length

        # pitch
        # Step6. モーラの音高(ピッチ)を展開・結合し、floatにキャストする
        f0_list = [0] + [mora.pitch for mora in flatten_moras] + [0]
        f0 = numpy.array(f0_list, dtype=numpy.float32)
        # Step7. 音高(ピッチ)の調節を適用する(2のPitch Scale乗を掛ける)
        f0 *= 2 ** query.pitchScale

        # Step8. 有声音素(音高(ピッチ)が0より大きいもの)か否かを抽出する
        voiced = f0 > 0
        # Step9. 有声音素の音高(ピッチ)の平均値を求める
        mean_f0 = f0[voiced].mean()
        # Step10. 平均値がNaNではないとき、抑揚を適用する
        # 抑揚は音高と音高の平均値の差に抑揚を掛けたもの((f0 - mean_f0) * Intonation Scale)に抑揚の平均値(mean_f0)を足したもの
        if not numpy.isnan(mean_f0):
            f0[voiced] = (f0[voiced] - mean_f0) * query.intonationScale + mean_f0

        # Step11. OjtPhonemeの形に分解された音素リストから、vowel(母音)の位置を抜き出し、numpyのarrayにする
        _, _, vowel_indexes_data = split_mora(phoneme_data_list)
        vowel_indexes = numpy.array(vowel_indexes_data)

        # forward decode
        # Step12. 音素の長さにrateを掛け、intにキャストする
        phoneme_bin_num = numpy.round(phoneme_length * rate).astype(numpy.int32)

        # Step13. Phoneme IDを音素の長さ分繰り返す
        phoneme = numpy.repeat(phoneme_list_s, phoneme_bin_num)
        # Step14. f0を母音と子音の長さの合計分繰り返す
        f0 = numpy.repeat(
            f0,
            [a.sum() for a in numpy.split(phoneme_bin_num, vowel_indexes[:-1] + 1)],
        )

        # Step15. phonemeの長さとOjtPhonemeのnum_phoneme(45)分の0で初期化された2次元配列を用意する
        array = numpy.zeros((len(phoneme), OjtPhoneme.num_phoneme), dtype=numpy.float32)
        # Step16. Step15.で初期化された2次元配列の各行のPhoneme ID列目を1にする
        array[numpy.arange(len(phoneme)), phoneme] = 1
        phoneme = array

        # Step17. f0とphonemeをそれぞれデコード用にリサンプリングする
        f0 = SamplingData(array=f0, rate=rate).resample(24000 / 256)
        phoneme = SamplingData(array=phoneme, rate=rate).resample(24000 / 256)

        # Step18. 今まで生成された情報をdecode_forwarderにかけ、推論器によって音声波形を生成する
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
        # Step19. 音量が1ではないなら、その分を音声波形に適用する
        if query.volumeScale != 1:
            wave *= query.volumeScale

        # Step20. 出力サンプリングレートがデフォルト(decode forwarderによるもの、24kHz)でなければ、それを適用する
        if query.outputSamplingRate != self.default_sampling_rate:
            wave = resampy.resample(
                wave,
                self.default_sampling_rate,
                query.outputSamplingRate,
                filter="kaiser_fast",
            )

        # ステレオ変換
        # Step21. 出力設定がステレオなのであれば、ステレオ化する
        if query.outputStereo:
            wave = numpy.array([wave, wave]).T

        return wave
