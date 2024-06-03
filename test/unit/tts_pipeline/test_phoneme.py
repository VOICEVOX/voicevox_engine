import pytest

from voicevox_engine.tts_pipeline.phoneme import Phoneme

TRUE_NUM_PHONEME = 45


def test_unknown_phoneme() -> None:
    """Unknown音素 `xx` のID取得を拒否する"""
    # Inputs
    unknown_phoneme = Phoneme("xx")

    # Tests
    with pytest.raises(ValueError):
        unknown_phoneme.id


# list_idx      0 1 2 3 4 5  6 7 8 9  10 1 2 3 4 5 6 7 8   9
hello_hiho = "sil k o N n i ch i w a pau h i h o d e s U sil".split()
ojt_hello_hiho = [Phoneme(s) for s in hello_hiho]


def test_const() -> None:
    assert Phoneme._NUM_PHONEME == TRUE_NUM_PHONEME
    assert Phoneme._PHONEME_LIST[1] == "A"
    assert Phoneme._PHONEME_LIST[14] == "e"
    assert Phoneme._PHONEME_LIST[26] == "m"
    assert Phoneme._PHONEME_LIST[38] == "ts"
    assert Phoneme._PHONEME_LIST[41] == "v"


def test_convert() -> None:
    sil_phoneme = Phoneme("sil")
    assert sil_phoneme._phoneme == "pau"


def test_phoneme_id() -> None:
    ojt_str_hello_hiho = " ".join([str(p.id) for p in ojt_hello_hiho])
    assert ojt_str_hello_hiho == "0 23 30 4 28 21 10 21 42 7 0 19 21 19 30 12 14 35 6 0"


def test_onehot() -> None:
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
    for i, phoneme in enumerate(ojt_hello_hiho):
        for j in range(TRUE_NUM_PHONEME):
            if phoneme_id_list[i] == j:
                assert phoneme.onehot[j] == 1.0
            else:
                assert phoneme.onehot[j] == 0.0
