from unittest import TestCase

from voicevox_engine.full_context_label import AccentPhrase, Mora, Phoneme


class TestBasePhonemes(TestCase):
    def setUp(self):
        super().setUp()
        # pyopenjtalk.extract_fullcontext("A")の結果
        # 出来る限りテスト内で他のライブラリに依存しないために、テストケースを生成している
        self.test_case_A = [
            # 無音
            "xx^xx-sil+e=i/A:xx+xx+xx/B:xx-xx_xx/C:xx_xx+xx/D:xx+xx_xx/E:xx_xx!xx_xx-xx"
            + "/F:xx_xx#xx_xx@xx_xx|xx_xx/G:2_1%0_xx_xx/H:xx_xx/I:xx-xx"
            + "@xx+xx&xx-xx|xx+xx/J:1_2/K:1+1-2",
            # e
            "xx^sil-e+i=sil/A:0+1+2/B:xx-xx_xx/C:xx_xx+xx/D:xx+xx_xx/E:xx_xx!xx_xx-xx"
            + "/F:2_1#0_xx@1_1|1_2/G:xx_xx%xx_xx_xx/H:xx_xx/I:1-2"
            + "@1+1&1-1|1+2/J:xx_xx/K:1+1-2",
            # i
            "sil^e-i+sil=xx/A:1+2+1/B:xx-xx_xx/C:xx_xx+xx/D:xx+xx_xx/E:xx_xx!xx_xx-xx"
            + "/F:2_1#0_xx@1_1|1_2/G:xx_xx%xx_xx_xx/H:xx_xx/I:1-2"
            + "@1+1&1-1|1+2/J:xx_xx/K:1+1-2",
            # 無音
            "e^i-sil+xx=xx/A:xx+xx+xx/B:xx-xx_xx/C:xx_xx+xx/D:xx+xx_xx/E:2_1!0_xx-xx"
            + "/F:xx_xx#xx_xx@xx_xx|xx_xx/G:xx_xx%xx_xx_xx/H:1_2/I:xx-xx"
            + "@xx+xx&xx-xx|xx+xx/J:xx_xx/K:1+1-2",
        ]
        # pyopenjtalk.extract_fullcontext("あか")の結果
        self.test_case_aka = [
            # 無音
            "xx^xx-sil+a=k/A:xx+xx+xx/B:xx-xx_xx/C:xx_xx+xx/D:09+xx_xx/E:xx_xx!xx_xx-xx"
            + "/F:xx_xx#xx_xx@xx_xx|xx_xx/G:2_1%0_xx_xx/H:xx_xx/I:xx-xx"
            + "@xx+xx&xx-xx|xx+xx/J:1_2/K:1+1-2",
            # a
            "xx^sil-a+k=a/A:0+1+2/B:xx-xx_xx/C:09_xx+xx/D:23+xx_xx/E:xx_xx!xx_xx-xx"
            + "/F:2_1#0_xx@1_1|1_2/G:xx_xx%xx_xx_xx/H:xx_xx/I:1-2"
            + "@1+1&1-1|1+2/J:xx_xx/K:1+1-2",
            # k
            "sil^a-k+a=sil/A:1+2+1/B:09-xx_xx/C:23_xx+xx/D:xx+xx_xx/E:xx_xx!xx_xx-xx"
            + "/F:2_1#0_xx@1_1|1_2/G:xx_xx%xx_xx_xx/H:xx_xx/I:1-2"
            + "@1+1&1-1|1+2/J:xx_xx/K:1+1-2",
            # a
            "a^k-a+sil=xx/A:1+2+1/B:09-xx_xx/C:23_xx+xx/D:xx+xx_xx/E:xx_xx!xx_xx-xx"
            + "/F:2_1#0_xx@1_1|1_2/G:xx_xx%xx_xx_xx/H:xx_xx/I:1-2"
            + "@1+1&1-1|1+2/J:xx_xx/K:1+1-2",
            # 無音
            "k^a-sil+xx=xx/A:xx+xx+xx/B:23-xx_xx/C:xx_xx+xx/D:xx+xx_xx/E:2_1!0_xx-xx/"
            + "F:xx_xx#xx_xx@xx_xx|xx_xx/G:xx_xx%xx_xx_xx/H:1_2/I:xx-xx"
            + "@xx+xx&xx-xx|xx+xx/J:xx_xx/K:1+1-2",
        ]
        self.phonemes_A = [Phoneme.from_label(label) for label in self.test_case_A]
        self.phonemes_aka = [Phoneme.from_label(label) for label in self.test_case_aka]


class TestPhoneme(TestBasePhonemes):
    def test_phoneme(self):
        self.assertEqual(
            [phoneme.phoneme for phoneme in self.phonemes_A], ["sil", "e", "i", "sil"]
        )
        self.assertEqual(
            [phoneme.phoneme for phoneme in self.phonemes_aka],
            ["sil", "a", "k", "a", "sil"],
        )

    def test_is_pose(self):
        self.assertEqual(
            [phoneme.is_pose() for phoneme in self.phonemes_A],
            [True, False, False, True],
        )
        self.assertEqual(
            [phoneme.is_pose() for phoneme in self.phonemes_aka],
            [True, False, False, False, True],
        )

    def test_label(self) -> None:
        self.assertEqual(
            [phoneme.label for phoneme in self.phonemes_A], self.test_case_A
        )
        self.assertEqual(
            [phoneme.label for phoneme in self.phonemes_aka], self.test_case_aka
        )


class TestMora(TestBasePhonemes):
    def setUp(self) -> None:
        super().setUp()
        # contexts["a2"] == "1"
        self.mora_A_1 = Mora(consonant=None, vowel=self.phonemes_A[1])
        # contexts["a2"] == "2"
        self.mora_A_2 = Mora(consonant=None, vowel=self.phonemes_A[2])
        # contexts["a2"] == "1"
        self.mora_aka_1 = Mora(consonant=None, vowel=self.phonemes_aka[1])
        # contexts["a2"] == "2"
        self.mora_aka_2 = Mora(
            consonant=self.phonemes_aka[2], vowel=self.phonemes_aka[3]
        )

    def test_phonemes(self) -> None:
        self.assertEqual(self.mora_A_1.phonemes[0].phoneme, "e")
        self.assertEqual(self.mora_A_2.phonemes[0].phoneme, "i")
        self.assertEqual(self.mora_aka_1.phonemes[0].phoneme, "a")
        self.assertEqual(self.mora_aka_2.phonemes[0].phoneme, "k")
        self.assertEqual(self.mora_aka_2.phonemes[1].phoneme, "a")

    def test_labels(self) -> None:
        self.assertEqual(self.mora_A_1.labels, self.test_case_A[1:2])
        self.assertEqual(self.mora_A_2.labels, self.test_case_A[2:3])
        self.assertEqual(self.mora_aka_1.labels, self.test_case_aka[1:2])
        self.assertEqual(self.mora_aka_2.labels, self.test_case_aka[2:4])

    def test_set_context(self):
        # phonemeにあたる"p3"を書き換える
        self.mora_A_1.set_context("p3", "a")
        self.assertEqual(self.mora_A_1.vowel.phoneme, "a")
        # 元に戻す
        self.mora_A_1.set_context("p3", "e")


class TestAccentPhrase(TestBasePhonemes):
    def setUp(self) -> None:
        super().setUp()
        self.accent_phrase_A = AccentPhrase.from_phonemes(self.phonemes_A[1:3])
        self.accent_phrase_aka = AccentPhrase.from_phonemes(self.phonemes_aka[1:4])

    def test_accent(self):
        self.assertEqual(self.accent_phrase_A.accent, 1)
        self.assertEqual(self.accent_phrase_aka.accent, 1)

    def test_phonemes(self):
        self.assertEqual(
            [phoneme.phoneme for phoneme in self.accent_phrase_A.phonemes], ["e", "i"]
        )
        self.assertEqual(
            [phoneme.phoneme for phoneme in self.accent_phrase_aka.phonemes],
            ["a", "k", "a"],
        )

    def test_labels(self):
        self.assertEqual(self.accent_phrase_A.labels, self.test_case_A[1:3])
        self.assertEqual(
            self.accent_phrase_aka.labels,
            self.test_case_aka[1:4],
        )

    def test_merge(self):
        # aka + ei = アカエイ
        merged_accent_phrase = self.accent_phrase_aka.merge(self.accent_phrase_A)
        self.assertEqual(merged_accent_phrase.accent, 1)
        self.assertEqual(
            [phoneme.phoneme for phoneme in merged_accent_phrase.phonemes],
            ["a", "k", "a", "e", "i"],
        )
        self.assertEqual(
            merged_accent_phrase.labels,
            self.test_case_aka[1:4] + self.test_case_A[1:3],
        )
