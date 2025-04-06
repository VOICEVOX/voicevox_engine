from voicevox_engine.tts_pipeline.njd_feature_processor import (
    NjdFeature,
    _remove_full_width_space,
)


def test_remove_full_width_space_normal() -> None:
    # Inputs
    input_features = [
        NjdFeature(
            string="　",
            pos="フィラー",
            pos_group1="*",
            pos_group2="*",
            pos_group3="*",
            ctype="*",
            cform="*",
            orig="",
            read="",
            pron="、",
            acc=0,
            mora_size=0,
            chain_rule="*",
            chain_flag=0,
        ),
        NjdFeature(
            string="ボイボ",
            pos="名詞",
            pos_group1="一般",
            pos_group2="*",
            pos_group3="*",
            ctype="*",
            cform="*",
            orig="ボイボ",
            read="ボイボ",
            pron="ボイボ",
            acc=1,
            mora_size=3,
            chain_rule="*",
            chain_flag=0,
        ),
    ]
    # Expects
    true_features = [
        NjdFeature(
            string="ボイボ",
            pos="名詞",
            pos_group1="一般",
            pos_group2="*",
            pos_group3="*",
            ctype="*",
            cform="*",
            orig="ボイボ",
            read="ボイボ",
            pron="ボイボ",
            acc=1,
            mora_size=3,
            chain_rule="*",
            chain_flag=0,
        )
    ]
    # Outputs
    result = _remove_full_width_space(input_features)
    # Tests
    assert true_features == result


def test_remove_full_width_space_non_matching() -> None:
    # Inputs
    input_features = [
        NjdFeature(
            string="ボイボ",
            pos="名詞",
            pos_group1="一般",
            pos_group2="*",
            pos_group3="*",
            ctype="*",
            cform="*",
            orig="ボイボ",
            read="ボイボ",
            pron="ボイボ",
            acc=1,
            mora_size=3,
            chain_rule="*",
            chain_flag=0,
        )
    ]
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
