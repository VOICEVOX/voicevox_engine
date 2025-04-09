from voicevox_engine.tts_pipeline.njd_feature_processor import (
    NjdFeature,
    _remove_pau_space_between_alphabet,
)


def _gen_noun_feature(string: str) -> NjdFeature:
    return NjdFeature(
        string=string,
        pos="名詞",
        pos_group1="一般",
        pos_group2="*",
        pos_group3="*",
        ctype="*",
        cform="*",
        orig=string,
        read="ダミー",
        pron="ダミー",
        acc=0,
        mora_size=3,
        chain_rule="*",
        chain_flag=0,
    )


def _gen_pau_space_feature() -> NjdFeature:
    return NjdFeature(
        string="　",
        pos="記号",
        pos_group1="空白",
        pos_group2="*",
        pos_group3="*",
        ctype="*",
        cform="*",
        orig="　",
        read="、",
        pron="、",
        acc=0,
        mora_size=0,
        chain_rule="*",
        chain_flag=0,
    )


def test_remove_pau_space_between_alphabet_normal() -> None:
    """`_remove_pau_space_between_alphabet`はアルファベットに挟まれた空白を削除する"""
    # Inputs
    input_features = [
        _gen_noun_feature("Ｖｏｉｃｅ"),
        _gen_pau_space_feature(),
        _gen_noun_feature("ｖｏｘ"),
    ]
    # Expects
    true_features = [
        _gen_noun_feature("Ｖｏｉｃｅ"),
        _gen_noun_feature("ｖｏｘ"),
    ]
    # Outputs
    result = _remove_pau_space_between_alphabet(input_features)
    # Tests
    assert true_features == result


def test_remove_pau_space_between_alphabet_multiple() -> None:
    """`_remove_pau_space_between_alphabet`はアルファベットに挟まれた複数の空白を全て削除する"""
    # Inputs
    input_features = [
        _gen_noun_feature("Ｖｏｉｃｅ"),
        _gen_pau_space_feature(),
        _gen_noun_feature("ｖｏｘ"),
        _gen_pau_space_feature(),
        _gen_noun_feature("Ｅｎｇｉｎｅ"),
    ]
    # Expects
    true_features = [
        _gen_noun_feature("Ｖｏｉｃｅ"),
        _gen_noun_feature("ｖｏｘ"),
        _gen_noun_feature("Ｅｎｇｉｎｅ"),
    ]
    # Outputs
    result = _remove_pau_space_between_alphabet(input_features)
    # Tests
    assert true_features == result


def test_remove_pau_space_between_alphabet_japanese() -> None:
    """`_remove_pau_space_between_alphabet`は日本語に挟まれた空白を削除しない"""
    # Inputs
    input_features = [
        _gen_noun_feature("ボイス"),
        _gen_pau_space_feature(),
        _gen_noun_feature("ボックス"),
    ]
    # Outputs
    result = _remove_pau_space_between_alphabet(input_features)
    # Tests
    assert input_features == result


def test_remove_pau_space_between_alphabet_japanese_alphabet() -> None:
    """`_remove_pau_space_between_alphabet`は日本語とアルファベットに挟まれた空白を削除しない"""
    # Inputs
    input_features = [
        _gen_noun_feature("ボイス"),
        _gen_pau_space_feature(),
        _gen_noun_feature("ｖｏｘ"),
    ]
    # Outputs
    result = _remove_pau_space_between_alphabet(input_features)
    # Tests
    assert input_features == result


def test_remove_pau_space_between_alphabet_alphabet_japanese() -> None:
    """`_remove_pau_space_between_alphabet`はアルファベットと日本語に挟まれた空白を削除しない"""
    # Inputs
    input_features = [
        _gen_noun_feature("Ｖｏｉｃｅ"),
        _gen_pau_space_feature(),
        _gen_noun_feature("ボックス"),
    ]
    # Outputs
    result = _remove_pau_space_between_alphabet(input_features)
    # Tests
    assert input_features == result


def test_remove_pau_space_between_alphabet_first_space() -> None:
    """`_remove_pau_space_between_alphabet`は文頭の空白を削除しない"""
    # Inputs
    input_features = [
        _gen_pau_space_feature(),
        _gen_noun_feature("Ｖｏｉｃｅ"),
        _gen_noun_feature("ｖｏｘ"),
    ]
    # Outputs
    result = _remove_pau_space_between_alphabet(input_features)
    # Tests
    assert input_features == result


def test_remove_pau_space_between_alphabet_last_space() -> None:
    """`_remove_pau_space_between_alphabet`は文末の空白を削除しない"""
    # Inputs
    input_features = [
        _gen_noun_feature("Ｖｏｉｃｅ"),
        _gen_noun_feature("ｖｏｘ"),
        _gen_pau_space_feature(),
    ]
    # Outputs
    result = _remove_pau_space_between_alphabet(input_features)
    # Tests
    assert input_features == result


def test_remove_pau_space_between_alphabet_empty_input() -> None:
    """`_remove_pau_space_between_alphabet`は空の入力に対し空のリストを返す"""
    # Inputs
    input_features: list[NjdFeature] = []
    # Outputs
    result = _remove_pau_space_between_alphabet(input_features)
    # Tests
    assert len(result) == 0
