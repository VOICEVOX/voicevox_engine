import math
from copy import deepcopy
from random import random
from typing import Union
from unittest import TestCase
from unittest.mock import Mock

import numpy

from voicevox_engine.acoustic_feature_extractor import OjtPhoneme
from voicevox_engine.model import AccentPhrase, AudioQuery, Mora
from voicevox_engine.synthesis_engine import SynthesisEngine

# TODO: import from voicevox_engine.synthesis_engine.mora
from voicevox_engine.synthesis_engine.synthesis_engine import (
    mora_phoneme_list,
    pre_process,
    split_mora,
    to_flatten_moras,
    to_phoneme_data_list,
    unvoiced_mora_phoneme_list,
)


def yukarin_s_mock(length: int, phoneme_list: numpy.ndarray, style_id: numpy.ndarray):
    result = []
    # mockとしての適当な処理、特に意味はない
    for i in range(length):
        result.append(float(phoneme_list[i] * 0.5 + style_id))
    return numpy.array(result)


def yukarin_sa_mock(
    length: int,
    vowel_phoneme_list: numpy.ndarray,
    consonant_phoneme_list: numpy.ndarray,
    start_accent_list: numpy.ndarray,
    end_accent_list: numpy.ndarray,
    start_accent_phrase_list: numpy.ndarray,
    end_accent_phrase_list: numpy.ndarray,
    style_id: numpy.ndarray,
):
    result = []
    # mockとしての適当な処理、特に意味はない
    for i in range(length):
        result.append(
            float(
                (
                    vowel_phoneme_list[0][i]
                    + consonant_phoneme_list[0][i]
                    + start_accent_list[0][i]
                    + end_accent_list[0][i]
                    + start_accent_phrase_list[0][i]
                    + end_accent_phrase_list[0][i]
                )
                * 0.5
                + style_id
            )
        )
    return numpy.array(result)[numpy.newaxis]


def decode_mock(
    length: int,
    phoneme_size: int,
    f0: numpy.ndarray,
    phoneme: numpy.ndarray,
    style_id: Union[numpy.ndarray, int],
):
    result = []
    # mockとしての適当な処理、特に意味はない
    for i in range(length):
        # decode forwardはデータサイズがlengthの256倍になるのでとりあえず256回データをresultに入れる
        for _ in range(256):
            result.append(
                float(
                    f0[i][0] * (numpy.where(phoneme[i] == 1)[0] / phoneme_size)
                    + style_id
                )
            )
    return numpy.array(result)


class MockCore:
    yukarin_s_forward = Mock(side_effect=yukarin_s_mock)
    yukarin_sa_forward = Mock(side_effect=yukarin_sa_mock)
    decode_forward = Mock(side_effect=decode_mock)

    def metas(self):
        return ""

    def supported_devices(self):
        return ""

    def is_model_loaded(self, style_id):
        return True


class TestSynthesisEngine(TestCase):
    def setUp(self):
        super().setUp()
        self.str_list_hello_hiho = (
            "sil k o N n i ch i w a pau h i h o d e s U sil".split()
        )
        self.phoneme_data_list_hello_hiho = [
            OjtPhoneme(phoneme=p, start=i, end=i + 1)
            for i, p in enumerate(
                "pau k o N n i ch i w a pau h i h o d e s U pau".split()
            )
        ]
        self.accent_phrases_hello_hiho = [
            AccentPhrase(
                moras=[
                    Mora(
                        text="コ",
                        consonant="k",
                        consonant_length=0.0,
                        vowel="o",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                    Mora(
                        text="ン",
                        consonant=None,
                        consonant_length=None,
                        vowel="N",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                    Mora(
                        text="ニ",
                        consonant="n",
                        consonant_length=0.0,
                        vowel="i",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                    Mora(
                        text="チ",
                        consonant="ch",
                        consonant_length=0.0,
                        vowel="i",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                    Mora(
                        text="ワ",
                        consonant="w",
                        consonant_length=0.0,
                        vowel="a",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                ],
                accent=5,
                pause_mora=Mora(
                    text="、",
                    consonant=None,
                    consonant_length=None,
                    vowel="pau",
                    vowel_length=0.0,
                    pitch=0.0,
                ),
            ),
            AccentPhrase(
                moras=[
                    Mora(
                        text="ヒ",
                        consonant="h",
                        consonant_length=0.0,
                        vowel="i",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                    Mora(
                        text="ホ",
                        consonant="h",
                        consonant_length=0.0,
                        vowel="o",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                    Mora(
                        text="デ",
                        consonant="d",
                        consonant_length=0.0,
                        vowel="e",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                    Mora(
                        text="ス",
                        consonant="s",
                        consonant_length=0.0,
                        vowel="U",
                        vowel_length=0.0,
                        pitch=0.0,
                    ),
                ],
                accent=1,
                pause_mora=None,
            ),
        ]
        core = MockCore()
        self.yukarin_s_mock = core.yukarin_s_forward
        self.yukarin_sa_mock = core.yukarin_sa_forward
        self.decode_mock = core.decode_forward
        self.synthesis_engine = SynthesisEngine(
            core=core,
        )

    def test_to_flatten_moras(self):
        flatten_moras = to_flatten_moras(self.accent_phrases_hello_hiho)
        self.assertEqual(
            flatten_moras,
            self.accent_phrases_hello_hiho[0].moras
            + [self.accent_phrases_hello_hiho[0].pause_mora]
            + self.accent_phrases_hello_hiho[1].moras,
        )

    def test_to_phoneme_data_list(self):
        phoneme_data_list = to_phoneme_data_list(self.str_list_hello_hiho)
        self.assertEqual(phoneme_data_list, self.phoneme_data_list_hello_hiho)

    def test_split_mora(self):
        consonant_phoneme_list, vowel_phoneme_list, vowel_indexes = split_mora(
            self.phoneme_data_list_hello_hiho
        )

        self.assertEqual(vowel_indexes, [0, 2, 3, 5, 7, 9, 10, 12, 14, 16, 18, 19])
        self.assertEqual(
            vowel_phoneme_list,
            [
                OjtPhoneme(phoneme="pau", start=0, end=1),
                OjtPhoneme(phoneme="o", start=2, end=3),
                OjtPhoneme(phoneme="N", start=3, end=4),
                OjtPhoneme(phoneme="i", start=5, end=6),
                OjtPhoneme(phoneme="i", start=7, end=8),
                OjtPhoneme(phoneme="a", start=9, end=10),
                OjtPhoneme(phoneme="pau", start=10, end=11),
                OjtPhoneme(phoneme="i", start=12, end=13),
                OjtPhoneme(phoneme="o", start=14, end=15),
                OjtPhoneme(phoneme="e", start=16, end=17),
                OjtPhoneme(phoneme="U", start=18, end=19),
                OjtPhoneme(phoneme="pau", start=19, end=20),
            ],
        )
        self.assertEqual(
            consonant_phoneme_list,
            [
                None,
                OjtPhoneme(phoneme="k", start=1, end=2),
                None,
                OjtPhoneme(phoneme="n", start=4, end=5),
                OjtPhoneme(phoneme="ch", start=6, end=7),
                OjtPhoneme(phoneme="w", start=8, end=9),
                None,
                OjtPhoneme(phoneme="h", start=11, end=12),
                OjtPhoneme(phoneme="h", start=13, end=14),
                OjtPhoneme(phoneme="d", start=15, end=16),
                OjtPhoneme(phoneme="s", start=17, end=18),
                None,
            ],
        )

    def test_pre_process(self):
        flatten_moras, phoneme_data_list = pre_process(
            deepcopy(self.accent_phrases_hello_hiho)
        )

        mora_index = 0
        phoneme_index = 1

        self.assertEqual(phoneme_data_list[0], OjtPhoneme("pau", 0, 1))
        for accent_phrase in self.accent_phrases_hello_hiho:
            moras = accent_phrase.moras
            for mora in moras:
                self.assertEqual(flatten_moras[mora_index], mora)
                mora_index += 1
                if mora.consonant is not None:
                    self.assertEqual(
                        phoneme_data_list[phoneme_index],
                        OjtPhoneme(mora.consonant, phoneme_index, phoneme_index + 1),
                    )
                    phoneme_index += 1
                self.assertEqual(
                    phoneme_data_list[phoneme_index],
                    OjtPhoneme(mora.vowel, phoneme_index, phoneme_index + 1),
                )
                phoneme_index += 1
            if accent_phrase.pause_mora:
                self.assertEqual(flatten_moras[mora_index], accent_phrase.pause_mora)
                mora_index += 1
                self.assertEqual(
                    phoneme_data_list[phoneme_index],
                    OjtPhoneme("pau", phoneme_index, phoneme_index + 1),
                )
                phoneme_index += 1
        self.assertEqual(
            phoneme_data_list[phoneme_index],
            OjtPhoneme("pau", phoneme_index, phoneme_index + 1),
        )

    def test_replace_phoneme_length(self):
        result = self.synthesis_engine.replace_phoneme_length(
            accent_phrases=deepcopy(self.accent_phrases_hello_hiho), style_id=1
        )

        # yukarin_sに渡される値の検証
        yukarin_s_args = self.yukarin_s_mock.call_args[1]
        list_length = yukarin_s_args["length"]
        phoneme_list = yukarin_s_args["phoneme_list"]
        self.assertEqual(list_length, 20)
        self.assertEqual(list_length, len(phoneme_list))
        numpy.testing.assert_array_equal(
            phoneme_list,
            numpy.array(
                [
                    0,
                    23,
                    30,
                    4,
                    28,
                    21,
                    10,
                    21,
                    42,
                    7,
                    0,
                    19,
                    21,
                    19,
                    30,
                    12,
                    14,
                    35,
                    6,
                    0,
                ],
                dtype=numpy.int64,
            ),
        )
        self.assertEqual(yukarin_s_args["style_id"], 1)

        # flatten_morasを使わずに愚直にaccent_phrasesにデータを反映させてみる
        true_result = deepcopy(self.accent_phrases_hello_hiho)
        index = 1

        def result_value(i: int):
            return float(phoneme_list[i] * 0.5 + 1)

        for accent_phrase in true_result:
            moras = accent_phrase.moras
            for mora in moras:
                if mora.consonant is not None:
                    mora.consonant_length = result_value(index)
                    index += 1
                mora.vowel_length = result_value(index)
                index += 1
            if accent_phrase.pause_mora is not None:
                accent_phrase.pause_mora.vowel_length = result_value(index)
                index += 1

        self.assertEqual(result, true_result)

    def test_replace_mora_pitch(self):
        # 空のリストでエラーを吐かないか
        empty_accent_phrases = []
        self.assertEqual(
            self.synthesis_engine.replace_mora_pitch(
                accent_phrases=empty_accent_phrases, style_id=1
            ),
            [],
        )

        result = self.synthesis_engine.replace_mora_pitch(
            accent_phrases=deepcopy(self.accent_phrases_hello_hiho), style_id=1
        )

        # yukarin_saに渡される値の検証
        yukarin_sa_args = self.yukarin_sa_mock.call_args[1]
        list_length = yukarin_sa_args["length"]
        vowel_phoneme_list = yukarin_sa_args["vowel_phoneme_list"][0]
        consonant_phoneme_list = yukarin_sa_args["consonant_phoneme_list"][0]
        start_accent_list = yukarin_sa_args["start_accent_list"][0]
        end_accent_list = yukarin_sa_args["end_accent_list"][0]
        start_accent_phrase_list = yukarin_sa_args["start_accent_phrase_list"][0]
        end_accent_phrase_list = yukarin_sa_args["end_accent_phrase_list"][0]
        self.assertEqual(list_length, 12)
        self.assertEqual(list_length, len(vowel_phoneme_list))
        self.assertEqual(list_length, len(consonant_phoneme_list))
        self.assertEqual(list_length, len(start_accent_list))
        self.assertEqual(list_length, len(end_accent_list))
        self.assertEqual(list_length, len(start_accent_phrase_list))
        self.assertEqual(list_length, len(end_accent_phrase_list))
        self.assertEqual(yukarin_sa_args["style_id"], 1)

        numpy.testing.assert_array_equal(
            vowel_phoneme_list,
            numpy.array(
                [
                    0,
                    30,
                    4,
                    21,
                    21,
                    7,
                    0,
                    21,
                    30,
                    14,
                    6,
                    0,
                ]
            ),
        )
        numpy.testing.assert_array_equal(
            consonant_phoneme_list,
            numpy.array(
                [
                    -1,
                    23,
                    -1,
                    28,
                    10,
                    42,
                    -1,
                    19,
                    19,
                    12,
                    35,
                    -1,
                ]
            ),
        )
        numpy.testing.assert_array_equal(
            start_accent_list, numpy.array([0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0])
        )
        numpy.testing.assert_array_equal(
            end_accent_list, numpy.array([0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0])
        )
        numpy.testing.assert_array_equal(
            start_accent_phrase_list, numpy.array([0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0])
        )
        numpy.testing.assert_array_equal(
            end_accent_phrase_list, numpy.array([0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0])
        )

        # flatten_morasを使わずに愚直にaccent_phrasesにデータを反映させてみる
        true_result = deepcopy(self.accent_phrases_hello_hiho)
        index = 1

        def result_value(i: int):
            # unvoiced_mora_phoneme_listのPhoneme ID版
            unvoiced_mora_phoneme_id_list = [
                OjtPhoneme(p, 0, 0).phoneme_id for p in unvoiced_mora_phoneme_list
            ]
            if vowel_phoneme_list[i] in unvoiced_mora_phoneme_id_list:
                return 0
            return (
                vowel_phoneme_list[i]
                + consonant_phoneme_list[i]
                + start_accent_list[i]
                + end_accent_list[i]
                + start_accent_phrase_list[i]
                + end_accent_phrase_list[i]
            ) * 0.5 + 1

        for accent_phrase in true_result:
            moras = accent_phrase.moras
            for mora in moras:
                mora.pitch = result_value(index)
                index += 1
            if accent_phrase.pause_mora is not None:
                accent_phrase.pause_mora.pitch = result_value(index)
                index += 1

        self.assertEqual(result, true_result)

    def synthesis_test_base(self, audio_query: AudioQuery):
        accent_phrases = audio_query.accent_phrases

        # decode forwardのために適当にpitchとlengthを設定し、リストで持っておく
        phoneme_length_list = [0.0]
        phoneme_id_list = [0]
        f0_list = [0.0]
        for accent_phrase in accent_phrases:
            moras = accent_phrase.moras
            for mora in moras:
                if mora.consonant is not None:
                    mora.consonant_length = 0.1
                    phoneme_length_list.append(0.1)
                    phoneme_id_list.append(OjtPhoneme(mora.consonant, 0, 0).phoneme_id)
                mora.vowel_length = 0.2
                phoneme_length_list.append(0.2)
                phoneme_id_list.append(OjtPhoneme(mora.vowel, 0, 0).phoneme_id)
                if mora.vowel not in unvoiced_mora_phoneme_list:
                    mora.pitch = 5.0 + random()
                f0_list.append(mora.pitch)
            if accent_phrase.pause_mora is not None:
                accent_phrase.pause_mora.vowel_length = 0.2
                phoneme_length_list.append(0.2)
                phoneme_id_list.append(OjtPhoneme("pau", 0, 0).phoneme_id)
                f0_list.append(0.0)
        phoneme_length_list.append(0.0)
        phoneme_id_list.append(0)
        f0_list.append(0.0)

        phoneme_length_list[0] = audio_query.prePhonemeLength
        phoneme_length_list[-1] = audio_query.postPhonemeLength

        for i in range(len(phoneme_length_list)):
            phoneme_length_list[i] /= audio_query.speedScale

        result = self.synthesis_engine.synthesis(query=audio_query, style_id=1)

        # decodeに渡される値の検証
        decode_args = self.decode_mock.call_args[1]
        list_length = decode_args["length"]
        self.assertEqual(
            list_length,
            int(sum([round(p * 24000 / 256) for p in phoneme_length_list])),
        )

        num_phoneme = OjtPhoneme.num_phoneme
        # mora_phoneme_listのPhoneme ID版
        mora_phoneme_id_list = [
            OjtPhoneme(p, 0, 0).phoneme_id for p in mora_phoneme_list
        ]

        # numpy.repeatをfor文でやる
        f0 = []
        phoneme = []
        f0_index = 0
        mean_f0 = []
        for i, phoneme_length in enumerate(phoneme_length_list):
            f0_single = numpy.array(f0_list[f0_index], dtype=numpy.float32) * (
                2**audio_query.pitchScale
            )
            for _ in range(int(round(phoneme_length * (24000 / 256)))):
                f0.append([f0_single])
                phoneme_s = []
                for _ in range(num_phoneme):
                    phoneme_s.append(0)
                # one hot
                phoneme_s[phoneme_id_list[i]] = 1
                phoneme.append(phoneme_s)
            # consonantとvowelを判別し、vowelであればf0_indexを一つ進める
            if phoneme_id_list[i] in mora_phoneme_id_list:
                if f0_single > 0:
                    mean_f0.append(f0_single)
                f0_index += 1

        mean_f0 = numpy.array(mean_f0, dtype=numpy.float32).mean()
        f0 = numpy.array(f0, dtype=numpy.float32)
        for i in range(len(f0)):
            if f0[i][0] != 0.0:
                f0[i][0] = (f0[i][0] - mean_f0) * audio_query.intonationScale + mean_f0

        phoneme = numpy.array(phoneme, dtype=numpy.float32)

        # 乱数の影響で数値の位置がずれが生じるので、大半(4/5)があっていればよしとする
        # また、上の部分のint(round(phoneme_length * (24000 / 256)))の影響で
        # 本来のf0/phonemeとテスト生成したf0/phonemeの長さが変わることがあり、
        # テスト生成したものが若干長くなることがあるので、本来のものの長さを基準にassertする
        assert_f0_count = 0
        decode_f0 = decode_args["f0"]
        for i in range(len(decode_f0)):
            # 乱数の影響等で数値にずれが生じるので、10の-5乗までの近似値であれば許容する
            assert_f0_count += math.isclose(f0[i][0], decode_f0[i][0], rel_tol=10e-5)
        self.assertTrue(assert_f0_count >= int(len(decode_f0) / 5) * 4)
        assert_phoneme_count = 0
        decode_phoneme = decode_args["phoneme"]
        for i in range(len(decode_phoneme)):
            assert_true_count = 0
            for j in range(len(decode_phoneme[i])):
                assert_true_count += bool(phoneme[i][j] == decode_phoneme[i][j])
            assert_phoneme_count += assert_true_count == num_phoneme
        self.assertTrue(assert_phoneme_count >= int(len(decode_phoneme) / 5) * 4)
        self.assertEqual(decode_args["style_id"], 1)

        # decode forwarderのmockを使う
        true_result = decode_mock(list_length, num_phoneme, f0, phoneme, 1)

        true_result *= audio_query.volumeScale

        # TODO: resampyの部分は値の検証しようがないので、パスする
        if audio_query.outputSamplingRate != 24000:
            return

        assert_result_count = 0
        for i in range(len(true_result)):
            if audio_query.outputStereo:
                assert_result_count += math.isclose(
                    true_result[i], result[i][0], rel_tol=10e-5
                ) and math.isclose(true_result[i], result[i][1], rel_tol=10e-5)
            else:
                assert_result_count += math.isclose(
                    true_result[i], result[i], rel_tol=10e-5
                )
        self.assertTrue(assert_result_count >= int(len(true_result) / 5) * 4)

    def test_synthesis(self):
        audio_query = AudioQuery(
            accent_phrases=deepcopy(self.accent_phrases_hello_hiho),
            speedScale=1.0,
            pitchScale=1.0,
            intonationScale=1.0,
            volumeScale=1.0,
            prePhonemeLength=0.1,
            postPhonemeLength=0.1,
            outputSamplingRate=24000,
            outputStereo=False,
            # このテスト内では使わないので生成不要
            kana="",
        )

        self.synthesis_test_base(audio_query)

        # speed scaleのテスト
        audio_query.speedScale = 1.2
        self.synthesis_test_base(audio_query)

        # pitch scaleのテスト
        audio_query.pitchScale = 1.5
        audio_query.speedScale = 1.0
        self.synthesis_test_base(audio_query)

        # intonation scaleのテスト
        audio_query.pitchScale = 1.0
        audio_query.intonationScale = 1.4
        self.synthesis_test_base(audio_query)

        # volume scaleのテスト
        audio_query.intonationScale = 1.0
        audio_query.volumeScale = 2.0
        self.synthesis_test_base(audio_query)

        # pre/post phoneme lengthのテスト
        audio_query.volumeScale = 1.0
        audio_query.prePhonemeLength = 0.5
        audio_query.postPhonemeLength = 0.5
        self.synthesis_test_base(audio_query)

        # output sampling rateのテスト
        audio_query.prePhonemeLength = 0.1
        audio_query.postPhonemeLength = 0.1
        audio_query.outputSamplingRate = 48000
        self.synthesis_test_base(audio_query)

        # output stereoのテスト
        audio_query.outputSamplingRate = 24000
        audio_query.outputStereo = True
        self.synthesis_test_base(audio_query)
