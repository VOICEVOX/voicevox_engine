"""テキスト分析の単体テスト。"""

import pytest

from voicevox_engine.tts_pipeline.model import AccentPhrase, Mora
from voicevox_engine.tts_pipeline.text_analyzer import (
    NonOjtPhonemeError,
    OjtUnknownPhonemeError,
    full_context_labels_to_accent_phrases,
    mora_to_text,
)


@pytest.fixture
def test_case_hello_hiho() -> list[str]:
    """「こんにちは、ヒホです。」のフルコンテキストラベル。"""
    # NOTE: `pyopenjtalk.extract_fullcontext("こんにちは、ヒホです。")` の出力をハードコードしたものである。
    return [
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


@pytest.fixture
def sil_sil() -> list[str]:
    """無音のみで構成されたフルコンテキストラベル。"""
    return [
        # sil (無音)
        "xx^xx-sil+sil=xx/A:xx+xx+xx/B:xx-xx_xx/C:xx_xx+xx/D:09+xx_xx/E:xx_xx!xx_xx-xx"
        + "/F:xx_xx#xx_xx@xx_xx|xx_xx/G:5_5%0_xx_xx/H:xx_xx/I:xx-xx"
        + "@xx+xx&xx-xx|xx+xx/J:1_5/K:2+2-9",
        # sil (無音)
        "xx^sil-sil+xx=xx/A:xx+xx+xx/B:10-7_2/C:xx_xx+xx/D:xx+xx_xx/E:4_1!0_xx-xx"
        + "/F:xx_xx#xx_xx@xx_xx|xx_xx/G:xx_xx%xx_xx_xx/H:1_4/I:xx-xx"
        + "@xx+xx&xx-xx|xx+xx/J:xx_xx/K:2+2-9",
    ]


def test_voice() -> None:
    assert mora_to_text("a") == "ア"
    assert mora_to_text("i") == "イ"
    assert mora_to_text("ka") == "カ"
    assert mora_to_text("N") == "ン"
    assert mora_to_text("cl") == "ッ"
    assert mora_to_text("gye") == "ギェ"
    assert mora_to_text("ye") == "イェ"
    assert mora_to_text("wo") == "ウォ"


def test_unvoice() -> None:
    assert mora_to_text("A") == "ア"
    assert mora_to_text("I") == "イ"
    assert mora_to_text("kA") == "カ"
    assert mora_to_text("gyE") == "ギェ"
    assert mora_to_text("yE") == "イェ"
    assert mora_to_text("wO") == "ウォ"


def test_invalid_mora() -> None:
    """変なモーラが来ても例外を投げない"""
    assert mora_to_text("x") == "x"
    assert mora_to_text("") == ""


def _gen_mora(text: str, consonant: str | None, vowel: str) -> Mora:
    return Mora(
        text=text,
        consonant=consonant,
        consonant_length=0 if consonant else None,
        vowel=vowel,
        vowel_length=0,
        pitch=0,
    )


def test_full_context_labels_to_accent_phrases_normal(
    test_case_hello_hiho: list[str],
) -> None:
    """`full_context_labels_to_accent_phrases()` は正常な日本語文のフルコンテキストラベルをパースする。"""
    # Expects
    true_accent_phrases = [
        AccentPhrase(
            moras=[
                _gen_mora("コ", "k", "o"),
                _gen_mora("ン", None, "N"),
                _gen_mora("ニ", "n", "i"),
                _gen_mora("チ", "ch", "i"),
                _gen_mora("ワ", "w", "a"),
            ],
            accent=5,
            pause_mora=_gen_mora("、", None, "pau"),
        ),
        AccentPhrase(
            moras=[
                _gen_mora("ヒ", "h", "i"),
                _gen_mora("ホ", "h", "o"),
                _gen_mora("デ", "d", "e"),
                _gen_mora("ス", "s", "U"),
            ],
            accent=1,
            pause_mora=None,
        ),
    ]
    # Outputs
    accent_phrases = full_context_labels_to_accent_phrases(test_case_hello_hiho)
    # Tests
    assert accent_phrases == true_accent_phrases


def test_full_context_labels_to_accent_phrases_normal_silence(
    sil_sil: list[str],
) -> None:
    """`full_context_labels_to_accent_phrases()` は正常な無音のフルコンテキストラベルをパースする。"""
    # Expects
    true_accent_phrases: list[AccentPhrase] = []
    # Outputs
    accent_phrases = full_context_labels_to_accent_phrases(sil_sil)
    # Tests
    assert accent_phrases == true_accent_phrases


def test_full_context_labels_to_accent_phrases_normal_no_label() -> None:
    """`full_context_labels_to_accent_phrases()` は空のフルコンテキストラベル系列をパースする。"""
    # Expects
    true_accent_phrases: list[AccentPhrase] = []
    # Outputs
    accent_phrases = full_context_labels_to_accent_phrases([])
    # Tests
    assert accent_phrases == true_accent_phrases


@pytest.fixture
def test_case_kog() -> list[str]:
    """OpenJTalk で想定されない音素を含むフルコンテキストラベル。"""
    p = "G"
    return [
        ".^.-sil+.=./A:.+xx+./B:.-._./C:._.+./D:.+._./E:._.!._.-./F:xx_xx#xx_.@xx_.|._./G:._.%._._./H:._./I:.-.@xx+.&.-.|.+./J:._./K:.+.-.",
        ".^.-k+.=./A:.+1+./B:.-._./C:._.+./D:.+._./E:._.!._.-./F:2_1#0_.@1_.|._./G:._.%._._./H:._./I:.-.@1+.&.-.|.+./J:._./K:.+.-.",
        ".^.-o+.=./A:.+1+./B:.-._./C:._.+./D:.+._./E:._.!._.-./F:2_1#0_.@1_.|._./G:._.%._._./H:._./I:.-.@1+.&.-.|.+./J:._./K:.+.-.",
        f".^.-{p}+.=./A:.+2+./B:.-._./C:._.+./D:.+._./E:._.!._.-./F:2_1#0_.@1_.|._./G:._.%._._./H:._./I:.-.@1+.&.-.|.+./J:._./K:.+.-.",
        ".^.-sil+.=./A:.+xx+./B:.-._./C:._.+./D:.+._./E:._.!._.-./F:xx_xx#xx_.@xx_.|._./G:._.%._._./H:._./I:.-.@xx+.&.-.|.+./J:._./K:.+.-.",
    ]


@pytest.fixture
def test_case_koxx() -> list[str]:
    """unknown 音素を含むフルコンテキストラベル。"""
    return [
        ".^.-sil+.=./A:.+xx+./B:.-._./C:._.+./D:.+._./E:._.!._.-./F:xx_xx#xx_.@xx_.|._./G:._.%._._./H:._./I:.-.@xx+.&.-.|.+./J:._./K:.+.-.",
        ".^.-k+.=./A:.+1+./B:.-._./C:._.+./D:.+._./E:._.!._.-./F:2_1#0_.@1_.|._./G:._.%._._./H:._./I:.-.@1+.&.-.|.+./J:._./K:.+.-.",
        ".^.-o+.=./A:.+1+./B:.-._./C:._.+./D:.+._./E:._.!._.-./F:2_1#0_.@1_.|._./G:._.%._._./H:._./I:.-.@1+.&.-.|.+./J:._./K:.+.-.",
        ".^.-xx+.=./A:.+2+./B:.-._./C:._.+./D:.+._./E:._.!._.-./F:2_1#0_.@1_.|._./G:._.%._._./H:._./I:.-.@1+.&.-.|.+./J:._./K:.+.-.",
        ".^.-sil+.=./A:.+xx+./B:.-._./C:._.+./D:.+._./E:._.!._.-./F:xx_xx#xx_.@xx_.|._./G:._.%._._./H:._./I:.-.@xx+.&.-.|.+./J:._./K:.+.-.",
    ]


def test_full_context_labels_to_accent_phrases_non_ojt_phoneme(
    test_case_kog: list[str],
) -> None:
    """`full_context_labels_to_accent_phrases()` は OpenJTalk で想定されない音素を受け入れない。"""
    with pytest.raises(NonOjtPhonemeError):
        full_context_labels_to_accent_phrases(test_case_kog)


def test_full_context_labels_to_accent_phrases_unknown_phoneme(
    test_case_koxx: list[str],
) -> None:
    """`full_context_labels_to_accent_phrases()` は unknown 音素を含むフルコンテキストラベルを受け入れない。"""
    with pytest.raises(OjtUnknownPhonemeError):
        full_context_labels_to_accent_phrases(test_case_koxx)
