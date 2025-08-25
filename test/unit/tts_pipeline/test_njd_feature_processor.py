"""NJD Feature処理の単体テスト。"""

import pytest

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


@pytest.mark.parametrize(
    ("input_features", "true_features"),
    [
        # アルファベットに挟まれた空白を削除する
        pytest.param(
            [
                _gen_noun_feature("Ｖｏｉｃｅ"),
                _gen_pau_space_feature(),
                _gen_noun_feature("ｖｏｘ"),
            ],
            [
                _gen_noun_feature("Ｖｏｉｃｅ"),
                _gen_noun_feature("ｖｏｘ"),
            ],
            id="normal",
        ),
        # アルファベットに挟まれた複数の空白を全て削除する
        pytest.param(
            [
                _gen_noun_feature("Ｖｏｉｃｅ"),
                _gen_pau_space_feature(),
                _gen_noun_feature("ｖｏｘ"),
                _gen_pau_space_feature(),
                _gen_noun_feature("Ｅｎｇｉｎｅ"),
            ],
            [
                _gen_noun_feature("Ｖｏｉｃｅ"),
                _gen_noun_feature("ｖｏｘ"),
                _gen_noun_feature("Ｅｎｇｉｎｅ"),
            ],
            id="multiple",
        ),
        # 日本語に挟まれた空白を削除しない
        pytest.param(
            [
                _gen_noun_feature("ボイス"),
                _gen_pau_space_feature(),
                _gen_noun_feature("ボックス"),
            ],
            [
                _gen_noun_feature("ボイス"),
                _gen_pau_space_feature(),
                _gen_noun_feature("ボックス"),
            ],
            id="japanese",
        ),
        # 日本語とアルファベットに挟まれた空白を削除しない
        pytest.param(
            [
                _gen_noun_feature("ボイス"),
                _gen_pau_space_feature(),
                _gen_noun_feature("ｖｏｘ"),
            ],
            [
                _gen_noun_feature("ボイス"),
                _gen_pau_space_feature(),
                _gen_noun_feature("ｖｏｘ"),
            ],
            id="japanese_alphabet",
        ),
        # アルファベットと日本語に挟まれた空白を削除しない
        pytest.param(
            [
                _gen_noun_feature("Ｖｏｉｃｅ"),
                _gen_pau_space_feature(),
                _gen_noun_feature("ボックス"),
            ],
            [
                _gen_noun_feature("Ｖｏｉｃｅ"),
                _gen_pau_space_feature(),
                _gen_noun_feature("ボックス"),
            ],
            id="alphabet_japanese",
        ),
        # 文頭の空白を削除しない
        pytest.param(
            [
                _gen_pau_space_feature(),
                _gen_noun_feature("Ｖｏｉｃｅ"),
                _gen_noun_feature("ｖｏｘ"),
            ],
            [
                _gen_pau_space_feature(),
                _gen_noun_feature("Ｖｏｉｃｅ"),
                _gen_noun_feature("ｖｏｘ"),
            ],
            id="first_space",
        ),
        # 文末の空白を削除しない
        pytest.param(
            [
                _gen_noun_feature("Ｖｏｉｃｅ"),
                _gen_noun_feature("ｖｏｘ"),
                _gen_pau_space_feature(),
            ],
            [
                _gen_noun_feature("Ｖｏｉｃｅ"),
                _gen_noun_feature("ｖｏｘ"),
                _gen_pau_space_feature(),
            ],
            id="last_space",
        ),
        # 空の入力に対し空のリストを返す
        pytest.param(
            [],
            [],
            id="empty_input",
        ),
    ],
)
def test_remove_pau_space_between_alphabet(
    input_features: list[NjdFeature], true_features: list[NjdFeature]
) -> None:
    """_remove_pau_space_between_alphabetのテスト"""
    # Outputs
    result = _remove_pau_space_between_alphabet(input_features)
    # Tests
    assert true_features == result
