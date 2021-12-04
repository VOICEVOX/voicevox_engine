from voicevox_engine.acoustic_feature_extractor import OjtPhoneme
from voicevox_engine.model import AccentPhrase, Mora

str_list = "sil k o N n i ch i w a pau h i h o d e s U sil".split()

phoneme_data_list = [
    OjtPhoneme(phoneme=p, start=i, end=i + 1)
    for i, p in enumerate("pau k o N n i ch i w a pau h i h o d e s U pau".split())
]

accent_phrases = [
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
