from unittest import TestCase

from voicevox_engine.acoustic_feature_extractor import OjtPhoneme


def is_same_phoneme(p1: OjtPhoneme, p2: OjtPhoneme) -> bool:
    """2つのOjtPhonemeが同じ`.phoneme`/`.start`/`.end`を持つ"""
    return p1.phoneme == p2.phoneme and p1.start == p2.start and p1.end == p2.end


class TestOjtPhoneme(TestCase):
    def setUp(self):
        super().setUp()
        # list_idx      0 1 2 3 4 5  6 7 8 9  10 1 2 3 4 5 6 7 8   9
        hello_hiho = "sil k o N n i ch i w a pau h i h o d e s U sil".split()
        self.ojt_hello_hiho = [
            OjtPhoneme(s, i, i + 1) for i, s in enumerate(hello_hiho)
        ]

    def test_repr_(self):
        self.assertEqual(
            self.ojt_hello_hiho[1].__repr__(), "Phoneme(phoneme='k', start=1, end=2)"
        )
        self.assertEqual(
            self.ojt_hello_hiho[10].__repr__(),
            "Phoneme(phoneme='pau', start=10, end=11)",
        )

    def test_phoneme_list(self):
        self.assertEqual(OjtPhoneme.phoneme_list[1], "A")
        self.assertEqual(OjtPhoneme.phoneme_list[14], "e")
        self.assertEqual(OjtPhoneme.phoneme_list[26], "m")
        self.assertEqual(OjtPhoneme.phoneme_list[38], "ts")
        self.assertEqual(OjtPhoneme.phoneme_list[41], "v")

    def test_const(self):
        TRUE_NUM_PHONEME = 45
        self.assertEqual(OjtPhoneme.num_phoneme, TRUE_NUM_PHONEME)
        self.assertEqual(OjtPhoneme.space_phoneme, "pau")

    def test_convert(self):
        sil_phoneme = OjtPhoneme("sil", 0, 0)
        self.assertEqual(sil_phoneme.phoneme, "pau")

    def test_equal(self):
        # ojt_hello_hihoの10番目の"a"と比較
        true_ojt_phoneme = OjtPhoneme("a", 9, 10)

        false_ojt_phoneme_1 = OjtPhoneme("k", 9, 10)
        false_ojt_phoneme_2 = OjtPhoneme("a", 10, 11)
        self.assertTrue(is_same_phoneme(self.ojt_hello_hiho[9], true_ojt_phoneme))
        self.assertFalse(is_same_phoneme(self.ojt_hello_hiho[9], false_ojt_phoneme_1))
        self.assertFalse(is_same_phoneme(self.ojt_hello_hiho[9], false_ojt_phoneme_2))

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
                    self.assertEqual(phoneme.onehot[j], 1.0)
                else:
                    self.assertEqual(phoneme.onehot[j], 0.0)
