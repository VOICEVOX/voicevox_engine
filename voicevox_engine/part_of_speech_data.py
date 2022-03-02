from typing import Dict

from .model import PartOfSpeechDetail

part_of_speech_data: Dict[str, PartOfSpeechDetail] = {
    "固有名詞": PartOfSpeechDetail(
        part_of_speech="名詞",
        part_of_speech_detail_1="固有名詞",
        part_of_speech_detail_2="一般",
        part_of_speech_detail_3="*",
        context_id=1348,
    ),
    "普通名詞": PartOfSpeechDetail(
        part_of_speech="名詞",
        part_of_speech_detail_1="一般",
        part_of_speech_detail_2="*",
        part_of_speech_detail_3="*",
        context_id=1345,
    ),
    "動詞": PartOfSpeechDetail(
        part_of_speech="動詞",
        part_of_speech_detail_1="自立",
        part_of_speech_detail_2="一般",
        part_of_speech_detail_3="*",
        context_id=642,
    ),
    "形容詞": PartOfSpeechDetail(
        part_of_speech="形容詞",
        part_of_speech_detail_1="自立",
        part_of_speech_detail_2="*",
        part_of_speech_detail_3="*",
        context_id=20,
    ),
    "語尾": PartOfSpeechDetail(
        part_of_speech="名詞",
        part_of_speech_detail_1="接尾",
        part_of_speech_detail_2="一般",
        part_of_speech_detail_3="*",
        context_id=1358,
    ),
}
