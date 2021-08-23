from unittest import TestCase

from voicevox_engine.full_context_label import Phoneme


class TestFullContextLabel(TestCase):
    def setUp(self) -> None:
        super().setUp()
        # pyopenjtalk.extract_fullcontext("A")の結果
        test_case_A = [
            "xx^xx-sil+e=i/A:xx+xx+xx/B:xx-xx_xx/C:xx_xx+xx/D:xx+xx_xx/E:xx_xx!xx_xx-xx"
            + "/F:xx_xx#xx_xx@xx_xx|xx_xx/G:2_1%0_xx_xx/H:xx_xx/I:xx-xx"
            + "@xx+xx&xx-xx|xx+xx/J:1_2/K:1+1-2",
            "xx^sil-e+i=sil/A:0+1+2/B:xx-xx_xx/C:xx_xx+xx/D:xx+xx_xx/E:xx_xx!xx_xx-xx"
            + "/F:2_1#0_xx@1_1|1_2/G:xx_xx%xx_xx_xx/H:xx_xx/I:1-2"
            + "@1+1&1-1|1+2/J:xx_xx/K:1+1-2",
            "sil^e-i+sil=xx/A:1+2+1/B:xx-xx_xx/C:xx_xx+xx/D:xx+xx_xx/E:xx_xx!xx_xx-xx"
            + "/F:2_1#0_xx@1_1|1_2/G:xx_xx%xx_xx_xx/H:xx_xx/I:1-2"
            + "@1+1&1-1|1+2/J:xx_xx/K:1+1-2",
            "e^i-sil+xx=xx/A:xx+xx+xx/B:xx-xx_xx/C:xx_xx+xx/D:xx+xx_xx/E:2_1!0_xx-xx"
            + "/F:xx_xx#xx_xx@xx_xx|xx_xx/G:xx_xx%xx_xx_xx/H:1_2/I:xx-xx"
            + "@xx+xx&xx-xx|xx+xx/J:xx_xx/K:1+1-2",
        ]
        self.phonemes = [Phoneme.from_label(label) for label in test_case_A]

    def test_phoneme(self):
        self.assertEqual(
            [phoneme.phoneme for phoneme in self.phonemes], ["sil", "e", "i", "sil"]
        )

    def test_is_pose(self):
        self.assertEqual(
            [phoneme.is_pose() for phoneme in self.phonemes], [True, False, False, True]
        )
