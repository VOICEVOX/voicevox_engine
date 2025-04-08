from voicevox_engine.tts_pipeline.njd_feature_processor import (
    NjdFeature,
    _remove_full_width_space,
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


def test_remove_full_width_space_normal() -> None:
    # Inputs
    input_features = [
        _gen_pau_space_feature(),
        _gen_noun_feature("ボイボ"),
    ]
    # Expects
    true_features = [_gen_noun_feature("ボイボ")]
    # Outputs
    result = _remove_full_width_space(input_features)
    # Tests
    assert true_features == result


def test_remove_full_width_space_non_matching() -> None:
    # Inputs
    input_features = [_gen_noun_feature("ボイボ")]
    # Outputs
    result = _remove_full_width_space(input_features)
    # Tests
    assert input_features == result


def test_remove_full_width_space_empty_input() -> None:
    # Inputs
    input_features: list[NjdFeature] = []
    # Outputs
    result = _remove_full_width_space(input_features)
    # Tests
    assert len(result) == 0
