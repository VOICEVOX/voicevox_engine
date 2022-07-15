from copy import deepcopy
from itertools import chain
from unittest import TestCase

from voicevox_engine.full_context_label import (
    AccentPhrase,
    BreathGroup,
    Mora,
    Phoneme,
    Utterance,
)


class TestBasePhonemes(TestCase):
    def setUp(self):
        super().setUp()
        # pyopenjtalk.extract_fullcontext("こんにちは、ヒホです。")の結果
        # 出来る限りテスト内で他のライブラリに依存しないため、
        # またテスト内容を透明化するために、テストケースを生成している
        self.test_case_hello_hiho = [
            # sil (無音)
            "xx^xx-sil+k=o/A:xx+xx+xx/B:xx-xx_xx/C:xx_xx+xx/D:09+xx_xx/E:xx_xx!xx_xx-xx"
            + "/F:xx_xx#xx_xx@xx_xx|xx_xx/G:5_5%0_xx_xx/H:xx_xx/I:xx-xx"
            + "@xx+xx&xx-xx|xx+xx/J:1_5/K:2+2-9",
            # k
            "xx^sil-k+o=N/A:-4+1+5/B:xx-xx_xx/C:09_xx+xx/D:09+xx_xx/E:xx_xx!xx_xx-xx"
            + "/F:5_5#0_xx@1_1|1_5/G:4_1%0_xx_0/H:xx_xx/I:1-5"
            + "@1+2&1-2|1+9/J:1_4/K:2+2-9",
            # o
            "sil^k-o+N=n/A:-4+1+5/B:xx-xx_xx/C:09_xx+xx/D:09+xx_xx/E:xx_xx!xx_xx-xx"
            + "/F:5_5#0_xx@1_1|1_5/G:4_1%0_xx_0/H:xx_xx/I:1-5"
            + "@1+2&1-2|1+9/J:1_4/K:2+2-9",
            # N (ん)
            "k^o-N+n=i/A:-3+2+4/B:xx-xx_xx/C:09_xx+xx/D:09+xx_xx/E:xx_xx!xx_xx-xx"
            + "/F:5_5#0_xx@1_1|1_5/G:4_1%0_xx_0/H:xx_xx/I:1-5"
            + "@1+2&1-2|1+9/J:1_4/K:2+2-9",
            # n
            "o^N-n+i=ch/A:-2+3+3/B:xx-xx_xx/C:09_xx+xx/D:09+xx_xx/E:xx_xx!xx_xx-xx"
            + "/F:5_5#0_xx@1_1|1_5/G:4_1%0_xx_0/H:xx_xx/I:1-5"
            + "@1+2&1-2|1+9/J:1_4/K:2+2-9",
            # i
            "N^n-i+ch=i/A:-2+3+3/B:xx-xx_xx/C:09_xx+xx/D:09+xx_xx/E:xx_xx!xx_xx-xx"
            + "/F:5_5#0_xx@1_1|1_5/G:4_1%0_xx_0/H:xx_xx/I:1-5"
            + "@1+2&1-2|1+9/J:1_4/K:2+2-9",
            # ch
            "n^i-ch+i=w/A:-1+4+2/B:xx-xx_xx/C:09_xx+xx/D:09+xx_xx/E:xx_xx!xx_xx-xx"
            + "/F:5_5#0_xx@1_1|1_5/G:4_1%0_xx_0/H:xx_xx/I:1-5"
            + "@1+2&1-2|1+9/J:1_4/K:2+2-9",
            # i
            "i^ch-i+w=a/A:-1+4+2/B:xx-xx_xx/C:09_xx+xx/D:09+xx_xx/E:xx_xx!xx_xx-xx"
            + "/F:5_5#0_xx@1_1|1_5/G:4_1%0_xx_0/H:xx_xx/I:1-5"
            + "@1+2&1-2|1+9/J:1_4/K:2+2-9",
            # w
            "ch^i-w+a=pau/A:0+5+1/B:xx-xx_xx/C:09_xx+xx/D:09+xx_xx/E:xx_xx!xx_xx-xx"
            + "/F:5_5#0_xx@1_1|1_5/G:4_1%0_xx_0/H:xx_xx/I:1-5"
            + "@1+2&1-2|1+9/J:1_4/K:2+2-9",
            # a
            "i^w-a+pau=h/A:0+5+1/B:xx-xx_xx/C:09_xx+xx/D:09+xx_xx/E:xx_xx!xx_xx-xx"
            + "/F:5_5#0_xx@1_1|1_5/G:4_1%0_xx_0/H:xx_xx/I:1-5"
            + "@1+2&1-2|1+9/J:1_4/K:2+2-9",
            # pau (読点)
            "w^a-pau+h=i/A:xx+xx+xx/B:09-xx_xx/C:xx_xx+xx/D:09+xx_xx/E:5_5!0_xx-xx"
            + "/F:xx_xx#xx_xx@xx_xx|xx_xx/G:4_1%0_xx_xx/H:1_5/I:xx-xx"
            + "@xx+xx&xx-xx|xx+xx/J:1_4/K:2+2-9",
            # h
            "a^pau-h+i=h/A:0+1+4/B:09-xx_xx/C:09_xx+xx/D:22+xx_xx/E:5_5!0_xx-0"
            + "/F:4_1#0_xx@1_1|1_4/G:xx_xx%xx_xx_xx/H:1_5/I:1-4"
            + "@2+1&2-1|6+4/J:xx_xx/K:2+2-9",
            # i
            "pau^h-i+h=o/A:0+1+4/B:09-xx_xx/C:09_xx+xx/D:22+xx_xx/E:5_5!0_xx-0"
            + "/F:4_1#0_xx@1_1|1_4/G:xx_xx%xx_xx_xx/H:1_5/I:1-4"
            + "@2+1&2-1|6+4/J:xx_xx/K:2+2-9",
            # h
            "h^i-h+o=d/A:1+2+3/B:09-xx_xx/C:22_xx+xx/D:10+7_2/E:5_5!0_xx-0"
            + "/F:4_1#0_xx@1_1|1_4/G:xx_xx%xx_xx_xx/H:1_5/I:1-4"
            + "@2+1&2-1|6+4/J:xx_xx/K:2+2-9",
            # o
            "i^h-o+d=e/A:1+2+3/B:09-xx_xx/C:22_xx+xx/D:10+7_2/E:5_5!0_xx-0"
            + "/F:4_1#0_xx@1_1|1_4/G:xx_xx%xx_xx_xx/H:1_5/I:1-4"
            + "@2+1&2-1|6+4/J:xx_xx/K:2+2-9",
            # d
            "h^o-d+e=s/A:2+3+2/B:22-xx_xx/C:10_7+2/D:xx+xx_xx/E:5_5!0_xx-0"
            + "/F:4_1#0_xx@1_1|1_4/G:xx_xx%xx_xx_xx/H:1_5/I:1-4"
            + "@2+1&2-1|6+4/J:xx_xx/K:2+2-9",
            # e
            "o^d-e+s=U/A:2+3+2/B:22-xx_xx/C:10_7+2/D:xx+xx_xx/E:5_5!0_xx-0"
            + "/F:4_1#0_xx@1_1|1_4/G:xx_xx%xx_xx_xx/H:1_5/I:1-4"
            + "@2+1&2-1|6+4/J:xx_xx/K:2+2-9",
            # s
            "d^e-s+U=sil/A:3+4+1/B:22-xx_xx/C:10_7+2/D:xx+xx_xx/E:5_5!0_xx-0"
            + "/F:4_1#0_xx@1_1|1_4/G:xx_xx%xx_xx_xx/H:1_5/I:1-4"
            + "@2+1&2-1|6+4/J:xx_xx/K:2+2-9",
            # U (無声母音)
            "e^s-U+sil=xx/A:3+4+1/B:22-xx_xx/C:10_7+2/D:xx+xx_xx/E:5_5!0_xx-0"
            + "/F:4_1#0_xx@1_1|1_4/G:xx_xx%xx_xx_xx/H:1_5/I:1-4"
            + "@2+1&2-1|6+4/J:xx_xx/K:2+2-9",
            # sil (無音)
            "s^U-sil+xx=xx/A:xx+xx+xx/B:10-7_2/C:xx_xx+xx/D:xx+xx_xx/E:4_1!0_xx-xx"
            + "/F:xx_xx#xx_xx@xx_xx|xx_xx/G:xx_xx%xx_xx_xx/H:1_4/I:xx-xx"
            + "@xx+xx&xx-xx|xx+xx/J:xx_xx/K:2+2-9",
        ]
        self.phonemes_hello_hiho = [
            Phoneme.from_label(label) for label in self.test_case_hello_hiho
        ]


class TestPhoneme(TestBasePhonemes):
    def test_phoneme(self):
        self.assertEqual(
            " ".join([phoneme.phoneme for phoneme in self.phonemes_hello_hiho]),
            "sil k o N n i ch i w a pau h i h o d e s U sil",
        )

    def test_is_pause(self):
        self.assertEqual(
            [phoneme.is_pause() for phoneme in self.phonemes_hello_hiho],
            [
                True,  # sil
                False,  # k
                False,  # o
                False,  # N
                False,  # n
                False,  # i
                False,  # ch
                False,  # i
                False,  # w
                False,  # a
                True,  # pau
                False,  # h
                False,  # i
                False,  # h
                False,  # o
                False,  # d
                False,  # e
                False,  # s
                False,  # u
                True,  # sil
            ],
        )

    def test_label(self) -> None:
        self.assertEqual(
            [phoneme.label for phoneme in self.phonemes_hello_hiho],
            self.test_case_hello_hiho,
        )


class TestMora(TestBasePhonemes):
    def setUp(self) -> None:
        super().setUp()
        # contexts["a2"] == "1" ko
        self.mora_hello_1 = Mora(
            consonant=self.phonemes_hello_hiho[1], vowel=self.phonemes_hello_hiho[2]
        )
        # contexts["a2"] == "2" N
        self.mora_hello_2 = Mora(consonant=None, vowel=self.phonemes_hello_hiho[3])
        # contexts["a2"] == "3" ni
        self.mora_hello_3 = Mora(
            consonant=self.phonemes_hello_hiho[4], vowel=self.phonemes_hello_hiho[5]
        )
        # contexts["a2"] == "4" chi
        self.mora_hello_4 = Mora(
            consonant=self.phonemes_hello_hiho[6], vowel=self.phonemes_hello_hiho[7]
        )
        # contexts["a2"] == "5" wa
        self.mora_hello_5 = Mora(
            consonant=self.phonemes_hello_hiho[8], vowel=self.phonemes_hello_hiho[9]
        )
        # contexts["a2"] == "1" hi
        self.mora_hiho_1 = Mora(
            consonant=self.phonemes_hello_hiho[11], vowel=self.phonemes_hello_hiho[12]
        )
        # contexts["a2"] == "2" ho
        self.mora_hiho_2 = Mora(
            consonant=self.phonemes_hello_hiho[13], vowel=self.phonemes_hello_hiho[14]
        )
        # contexts["a2"] == "3" de
        self.mora_hiho_3 = Mora(
            consonant=self.phonemes_hello_hiho[15], vowel=self.phonemes_hello_hiho[16]
        )
        # contexts["a2"] == "1" sU
        self.mora_hiho_4 = Mora(
            consonant=self.phonemes_hello_hiho[17], vowel=self.phonemes_hello_hiho[18]
        )

    def assert_phonemes(self, mora: Mora, mora_str: str) -> None:
        self.assertEqual(
            "".join([phoneme.phoneme for phoneme in mora.phonemes]), mora_str
        )

    def assert_labels(self, mora: Mora, label_start: int, label_end: int) -> None:
        self.assertEqual(mora.labels, self.test_case_hello_hiho[label_start:label_end])

    def test_phonemes(self) -> None:
        self.assert_phonemes(self.mora_hello_1, "ko")
        self.assert_phonemes(self.mora_hello_2, "N")
        self.assert_phonemes(self.mora_hello_3, "ni")
        self.assert_phonemes(self.mora_hello_4, "chi")
        self.assert_phonemes(self.mora_hello_5, "wa")
        self.assert_phonemes(self.mora_hiho_1, "hi")
        self.assert_phonemes(self.mora_hiho_2, "ho")
        self.assert_phonemes(self.mora_hiho_3, "de")
        self.assert_phonemes(self.mora_hiho_4, "sU")

    def test_labels(self) -> None:
        self.assert_labels(self.mora_hello_1, 1, 3)
        self.assert_labels(self.mora_hello_2, 3, 4)
        self.assert_labels(self.mora_hello_3, 4, 6)
        self.assert_labels(self.mora_hello_4, 6, 8)
        self.assert_labels(self.mora_hello_5, 8, 10)
        self.assert_labels(self.mora_hiho_1, 11, 13)
        self.assert_labels(self.mora_hiho_2, 13, 15)
        self.assert_labels(self.mora_hiho_3, 15, 17)
        self.assert_labels(self.mora_hiho_4, 17, 19)

    def test_set_context(self):
        # 値を書き換えるので、他のテストに影響を出さないためにdeepcopyする
        mora_hello_1 = deepcopy(self.mora_hello_1)
        # phonemeにあたる"p3"を書き換える
        mora_hello_1.set_context("p3", "a")
        self.assert_phonemes(mora_hello_1, "aa")


class TestAccentPhrase(TestBasePhonemes):
    def setUp(self) -> None:
        super().setUp()
        # TODO: ValueErrorを吐く作為的ではない自然な例の模索
        # 存在しないなら放置でよい
        self.accent_phrase_hello = AccentPhrase.from_phonemes(
            self.phonemes_hello_hiho[1:10]
        )
        self.accent_phrase_hiho = AccentPhrase.from_phonemes(
            self.phonemes_hello_hiho[11:19]
        )

    def test_accent(self):
        self.assertEqual(self.accent_phrase_hello.accent, 5)
        self.assertEqual(self.accent_phrase_hiho.accent, 1)

    def test_set_context(self):
        accent_phrase_hello = deepcopy(self.accent_phrase_hello)
        # phonemeにあたる"p3"を書き換える
        accent_phrase_hello.set_context("p3", "a")
        self.assertEqual(
            "".join([phoneme.phoneme for phoneme in accent_phrase_hello.phonemes]),
            "aaaaaaaaa",
        )

    def test_phonemes(self):
        self.assertEqual(
            " ".join(
                [phoneme.phoneme for phoneme in self.accent_phrase_hello.phonemes]
            ),
            "k o N n i ch i w a",
        )
        self.assertEqual(
            " ".join([phoneme.phoneme for phoneme in self.accent_phrase_hiho.phonemes]),
            "h i h o d e s U",
        )

    def test_labels(self):
        self.assertEqual(
            self.accent_phrase_hello.labels, self.test_case_hello_hiho[1:10]
        )
        self.assertEqual(
            self.accent_phrase_hiho.labels, self.test_case_hello_hiho[11:19]
        )

    def test_merge(self):
        # 「こんにちはヒホです」
        # 読点を無くしたものと同等
        merged_accent_phrase = self.accent_phrase_hello.merge(self.accent_phrase_hiho)
        self.assertEqual(merged_accent_phrase.accent, 5)
        self.assertEqual(
            " ".join([phoneme.phoneme for phoneme in merged_accent_phrase.phonemes]),
            "k o N n i ch i w a h i h o d e s U",
        )
        self.assertEqual(
            merged_accent_phrase.labels,
            self.test_case_hello_hiho[1:10] + self.test_case_hello_hiho[11:19],
        )


class TestBreathGroup(TestBasePhonemes):
    def setUp(self) -> None:
        super().setUp()
        self.breath_group_hello = BreathGroup.from_phonemes(
            self.phonemes_hello_hiho[1:10]
        )
        self.breath_group_hiho = BreathGroup.from_phonemes(
            self.phonemes_hello_hiho[11:19]
        )

    def test_set_context(self):
        # 値を書き換えるので、他のテストに影響を出さないためにdeepcopyする
        breath_group_hello = deepcopy(self.breath_group_hello)
        # phonemeにあたる"p3"を書き換える
        breath_group_hello.set_context("p3", "a")
        self.assertEqual(
            "".join([phoneme.phoneme for phoneme in breath_group_hello.phonemes]),
            "aaaaaaaaa",
        )

    def test_phonemes(self):
        self.assertEqual(
            " ".join([phoneme.phoneme for phoneme in self.breath_group_hello.phonemes]),
            "k o N n i ch i w a",
        )
        self.assertEqual(
            " ".join([phoneme.phoneme for phoneme in self.breath_group_hiho.phonemes]),
            "h i h o d e s U",
        )

    def test_labels(self):
        self.assertEqual(
            self.breath_group_hello.labels, self.test_case_hello_hiho[1:10]
        )
        self.assertEqual(
            self.breath_group_hiho.labels, self.test_case_hello_hiho[11:19]
        )


class TestUtterance(TestBasePhonemes):
    def setUp(self) -> None:
        super().setUp()
        self.utterance_hello_hiho = Utterance.from_phonemes(self.phonemes_hello_hiho)

    def test_phonemes(self):
        self.assertEqual(
            " ".join(
                [phoneme.phoneme for phoneme in self.utterance_hello_hiho.phonemes]
            ),
            "sil k o N n i ch i w a pau h i h o d e s U sil",
        )
        changed_utterance = Utterance.from_phonemes(self.utterance_hello_hiho.phonemes)
        self.assertEqual(len(changed_utterance.breath_groups), 2)
        accent_phrases = list(
            chain.from_iterable(
                breath_group.accent_phrases
                for breath_group in changed_utterance.breath_groups
            )
        )
        for prev, cent, post in zip(
            [None] + accent_phrases[:-1],
            accent_phrases,
            accent_phrases[1:] + [None],
        ):
            mora_num = len(cent.moras)
            accent = cent.accent

            if prev is not None:
                for phoneme in prev.phonemes:
                    self.assertEqual(phoneme.contexts["g1"], str(mora_num))
                    self.assertEqual(phoneme.contexts["g2"], str(accent))

            if post is not None:
                for phoneme in post.phonemes:
                    self.assertEqual(phoneme.contexts["e1"], str(mora_num))
                    self.assertEqual(phoneme.contexts["e2"], str(accent))

            for phoneme in cent.phonemes:
                self.assertEqual(
                    phoneme.contexts["k2"],
                    str(
                        sum(
                            [
                                len(breath_group.accent_phrases)
                                for breath_group in changed_utterance.breath_groups
                            ]
                        )
                    ),
                )

        for prev, cent, post in zip(
            [None] + changed_utterance.breath_groups[:-1],
            changed_utterance.breath_groups,
            changed_utterance.breath_groups[1:] + [None],
        ):
            accent_phrase_num = len(cent.accent_phrases)

            if prev is not None:
                for phoneme in prev.phonemes:
                    self.assertEqual(phoneme.contexts["j1"], str(accent_phrase_num))

            if post is not None:
                for phoneme in post.phonemes:
                    self.assertEqual(phoneme.contexts["h1"], str(accent_phrase_num))

            for phoneme in cent.phonemes:
                self.assertEqual(phoneme.contexts["i1"], str(accent_phrase_num))
                self.assertEqual(
                    phoneme.contexts["i5"],
                    str(accent_phrases.index(cent.accent_phrases[0]) + 1),
                )
                self.assertEqual(
                    phoneme.contexts["i6"],
                    str(
                        len(accent_phrases)
                        - accent_phrases.index(cent.accent_phrases[0])
                    ),
                )

    def test_labels(self):
        self.assertEqual(self.utterance_hello_hiho.labels, self.test_case_hello_hiho)
