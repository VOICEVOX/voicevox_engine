import os
from pathlib import Path
from typing import List, Type
from unittest import TestCase

from voicevox_engine.acoustic_feature_extractor import (
    BasePhoneme,
    JvsPhoneme,
    OjtPhoneme,
)


class TestBasePhoneme(TestCase):
    def setUp(self):
        super().setUp()
        self.str_hello_hiho = "sil k o N n i ch i w a pau h i h o d e s U sil"
        self.base_hello_hiho = [
            BasePhoneme(s, i, i + 1) for i, s in enumerate(self.str_hello_hiho.split())
        ]
        self.lab_str = """
            0.00	1.00	pau
            1.00	2.00	k
            2.00	3.00	o
            3.00	4.00	N
            4.00	5.00	n
            5.00	6.00	i
            6.00	7.00	ch
            7.00	8.00	i
            8.00	9.00	w
            9.00	10.00	a
            10.00	11.00	pau
            11.00	12.00	h
            12.00	13.00	i
            13.00	14.00	h
            14.00	15.00	o
            15.00	16.00	d
            16.00	17.00	e
            17.00	18.00	s
            18.00	19.00	U
            19.00	20.00	pau
        """.replace(
            " ", ""
        )[
            1:-1
        ]  # ダブルクオーテーションx3で囲われている部分で、空白をすべて置き換え、先頭と最後の"\n"を除外する

    def test_repr_(self):
        self.assertEqual(
            self.base_hello_hiho[1].__repr__(), "Phoneme(phoneme='k', start=1, end=2)"
        )
        self.assertEqual(
            self.base_hello_hiho[10].__repr__(),
            "Phoneme(phoneme='pau', start=10, end=11)",
        )

    def test_convert(self):
        with self.assertRaises(NotImplementedError):
            BasePhoneme.convert(self.base_hello_hiho)

    def test_duration(self):
        self.assertEqual(self.base_hello_hiho[1].duration, 1)

    def test_parse(self):
        parse_str_1 = "0 1 pau"
        parse_str_2 = "32.67543 33.48933 e"
        parsed_base_1 = BasePhoneme.parse(parse_str_1)
        parsed_base_2 = BasePhoneme.parse(parse_str_2)
        self.assertEqual(parsed_base_1.phoneme, "pau")
        self.assertEqual(parsed_base_1.start, 0.0)
        self.assertEqual(parsed_base_1.end, 1.0)
        self.assertEqual(parsed_base_2.phoneme, "e")
        self.assertEqual(parsed_base_2.start, 32.68)
        self.assertEqual(parsed_base_2.end, 33.49)

    def lab_test_base(
        self,
        file_path: str,
        phonemes: List["BasePhoneme"],
        phoneme_class: Type["BasePhoneme"],
    ):
        phoneme_class.save_lab_list(phonemes, Path(file_path))
        with open(file_path, mode="r") as f:
            self.assertEqual(f.read(), self.lab_str)
        result_phoneme = phoneme_class.load_lab_list(Path(file_path))
        self.assertEqual(result_phoneme, phonemes)
        os.remove(file_path)


class TestJvsPhoneme(TestBasePhoneme):
    def setUp(self):
        super().setUp()
        base_hello_hiho = [
            JvsPhoneme(s, i, i + 1) for i, s in enumerate(self.str_hello_hiho.split())
        ]
        self.jvs_hello_hiho = JvsPhoneme.convert(base_hello_hiho)

    def test_phoneme_list(self):
        self.assertEqual(JvsPhoneme.phoneme_list[1], "I")
        self.assertEqual(JvsPhoneme.phoneme_list[14], "gy")
        self.assertEqual(JvsPhoneme.phoneme_list[26], "p")
        self.assertEqual(JvsPhoneme.phoneme_list[38], "z")

    def test_const(self):
        self.assertEqual(JvsPhoneme.num_phoneme, 39)
        self.assertEqual(JvsPhoneme.space_phoneme, "pau")

    def test_convert(self):
        converted_str_hello_hiho = " ".join([p.phoneme for p in self.jvs_hello_hiho])
        self.assertEqual(
            converted_str_hello_hiho, "pau k o N n i ch i w a pau h i h o d e s U pau"
        )

    def test_equal(self):
        # jvs_hello_hihoの2番目の"k"と比較
        true_jvs_phoneme = JvsPhoneme("k", 1, 2)
        # OjtPhonemeと比べる、比較はBasePhoneme内で実装されているので、比較結果はTrue
        true_ojt_phoneme = OjtPhoneme("k", 1, 2)

        false_jvs_phoneme_1 = JvsPhoneme("a", 1, 2)
        false_jvs_phoneme_2 = JvsPhoneme("k", 2, 3)
        self.assertTrue(self.jvs_hello_hiho[1] == true_jvs_phoneme)
        self.assertTrue(self.jvs_hello_hiho[1] == true_ojt_phoneme)
        self.assertFalse(self.jvs_hello_hiho[1] == false_jvs_phoneme_1)
        self.assertFalse(self.jvs_hello_hiho[1] == false_jvs_phoneme_2)

    def test_verify(self):
        for phoneme in self.jvs_hello_hiho:
            phoneme.verify()

    def test_phoneme_id(self):
        jvs_str_hello_hiho = " ".join([str(p.phoneme_id) for p in self.jvs_hello_hiho])
        self.assertEqual(
            jvs_str_hello_hiho, "0 19 25 2 23 17 7 17 36 4 0 15 17 15 25 9 11 30 3 0"
        )

    def test_onehot(self):
        phoneme_id_list = [
            0,
            19,
            25,
            2,
            23,
            17,
            7,
            17,
            36,
            4,
            0,
            15,
            17,
            15,
            25,
            9,
            11,
            30,
            3,
            0,
        ]
        for i, phoneme in enumerate(self.jvs_hello_hiho):
            for j in range(JvsPhoneme.num_phoneme):
                if phoneme_id_list[i] == j:
                    self.assertEqual(phoneme.onehot[j], True)
                else:
                    self.assertEqual(phoneme.onehot[j], False)

    def test_parse(self):
        parse_str_1 = "0 1 pau"
        parse_str_2 = "15.32654 16.39454 a"
        parsed_jvs_1 = JvsPhoneme.parse(parse_str_1)
        parsed_jvs_2 = JvsPhoneme.parse(parse_str_2)
        self.assertEqual(parsed_jvs_1.phoneme_id, 0)
        self.assertEqual(parsed_jvs_2.phoneme_id, 4)

    def test_lab_list(self):
        self.lab_test_base("./jvs_lab_test", self.jvs_hello_hiho, JvsPhoneme)


class TestOjtPhoneme(TestBasePhoneme):
    def setUp(self):
        super().setUp()
        self.str_hello_hiho = "sil k o N n i ch i w a pau h i h o d e s U sil"
        base_hello_hiho = [
            OjtPhoneme(s, i, i + 1) for i, s in enumerate(self.str_hello_hiho.split())
        ]
        self.ojt_hello_hiho = OjtPhoneme.convert(base_hello_hiho)

    def test_phoneme_list(self):
        self.assertEqual(OjtPhoneme.phoneme_list[1], "A")
        self.assertEqual(OjtPhoneme.phoneme_list[14], "e")
        self.assertEqual(OjtPhoneme.phoneme_list[26], "m")
        self.assertEqual(OjtPhoneme.phoneme_list[38], "ts")
        self.assertEqual(OjtPhoneme.phoneme_list[41], "v")

    def test_const(self):
        self.assertEqual(OjtPhoneme.num_phoneme, 45)
        self.assertEqual(OjtPhoneme.space_phoneme, "pau")

    def test_convert(self):
        ojt_str_hello_hiho = " ".join([p.phoneme for p in self.ojt_hello_hiho])
        self.assertEqual(
            ojt_str_hello_hiho, "pau k o N n i ch i w a pau h i h o d e s U pau"
        )

    def test_equal(self):
        # ojt_hello_hihoの10番目の"a"と比較
        true_ojt_phoneme = OjtPhoneme("a", 9, 10)
        # JvsPhonemeと比べる、比較はBasePhoneme内で実装されているので、比較結果はTrue
        true_jvs_phoneme = JvsPhoneme("a", 9, 10)

        false_ojt_phoneme_1 = OjtPhoneme("k", 9, 10)
        false_ojt_phoneme_2 = OjtPhoneme("a", 10, 11)
        self.assertTrue(self.ojt_hello_hiho[9] == true_ojt_phoneme)
        self.assertTrue(self.ojt_hello_hiho[9] == true_jvs_phoneme)
        self.assertFalse(self.ojt_hello_hiho[9] == false_ojt_phoneme_1)
        self.assertFalse(self.ojt_hello_hiho[9] == false_ojt_phoneme_2)

    def test_verify(self):
        for phoneme in self.ojt_hello_hiho:
            phoneme.verify()

    def test_phoneme_id(self):
        ojt_str_hello_hiho = " ".join([str(p.phoneme_id) for p in self.ojt_hello_hiho])
        self.assertEqual(
            ojt_str_hello_hiho, "0 23 30 4 28 21 10 21 42 7 0 19 21 19 30 12 14 35 6 0"
        )

    def test_onehot(self):
        phoneme_id_list = [
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
        ]
        for i, phoneme in enumerate(self.ojt_hello_hiho):
            for j in range(OjtPhoneme.num_phoneme):
                if phoneme_id_list[i] == j:
                    self.assertEqual(phoneme.onehot[j], True)
                else:
                    self.assertEqual(phoneme.onehot[j], False)

    def test_parse(self):
        parse_str_1 = "0 1 pau"
        parse_str_2 = "32.67543 33.48933 e"
        parsed_ojt_1 = OjtPhoneme.parse(parse_str_1)
        parsed_ojt_2 = OjtPhoneme.parse(parse_str_2)
        self.assertEqual(parsed_ojt_1.phoneme_id, 0)
        self.assertEqual(parsed_ojt_2.phoneme_id, 14)

    def tes_lab_list(self):
        self.lab_test_base("./ojt_lab_test", self.ojt_hello_hiho, OjtPhoneme)
