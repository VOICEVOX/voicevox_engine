from unittest import TestCase

from voicevox_engine.acoustic_feature_extractor import OjtPhoneme

TRUE_NUM_PHONEME = 45


class TestOjtPhoneme(TestCase):
    def setUp(self):
        super().setUp()
        # list_idx      0 1 2 3 4 5  6 7 8 9  10 1 2 3 4 5 6 7 8   9
        hello_hiho = "sil k o N n i ch i w a pau h i h o d e s U sil".split()
        self.ojt_hello_hiho = [OjtPhoneme(s) for s in hello_hiho]

    def test_const(self):
        self.assertEqual(OjtPhoneme._NUM_PHONEME, TRUE_NUM_PHONEME)
        self.assertEqual(OjtPhoneme._PHONEME_LIST[1], "A")
        self.assertEqual(OjtPhoneme._PHONEME_LIST[14], "e")
        self.assertEqual(OjtPhoneme._PHONEME_LIST[26], "m")
        self.assertEqual(OjtPhoneme._PHONEME_LIST[38], "ts")
        self.assertEqual(OjtPhoneme._PHONEME_LIST[41], "v")

    def test_convert(self):
        sil_phoneme = OjtPhoneme("sil")
        self.assertEqual(sil_phoneme.phoneme, "pau")

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
            for j in range(TRUE_NUM_PHONEME):
                if phoneme_id_list[i] == j:
                    self.assertEqual(phoneme.onehot[j], 1.0)
                else:
                    self.assertEqual(phoneme.onehot[j], 0.0)
