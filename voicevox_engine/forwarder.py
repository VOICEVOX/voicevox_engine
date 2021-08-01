from typing import List, Optional

import numpy

from voicevox_engine.acoustic_feature_extractor import (
    BasePhoneme,
    JvsPhoneme,
    OjtPhoneme,
    SamplingData,
)
from voicevox_engine.full_context_label import extract_full_context_label

unvoiced_mora_phoneme_list = ["A", "I", "U", "E", "O", "cl", "pau"]
mora_phoneme_list = ["a", "i", "u", "e", "o", "N"] + unvoiced_mora_phoneme_list


def split_mora(phoneme_list: List[BasePhoneme]):
    vowel_indexes = [
        i for i, p in enumerate(phoneme_list) if p.phoneme in mora_phoneme_list
    ]
    vowel_phoneme_list = [phoneme_list[i] for i in vowel_indexes]
    consonant_phoneme_list: List[Optional[BasePhoneme]] = [None] + [
        None if post - prev == 1 else phoneme_list[post - 1]
        for prev, post in zip(vowel_indexes[:-1], vowel_indexes[1:])
    ]
    return consonant_phoneme_list, vowel_phoneme_list, vowel_indexes


class Forwarder:
    def __init__(
        self,
        yukarin_s_forwarder,
        yukarin_sa_forwarder,
        decode_forwarder,
    ):
        super().__init__()
        self.yukarin_s_forwarder = yukarin_s_forwarder
        self.yukarin_sa_forwarder = yukarin_sa_forwarder
        self.decode_forwarder = decode_forwarder
        self.yukarin_s_phoneme_class = OjtPhoneme
        self.yukarin_soso_phoneme_class = OjtPhoneme

    def forward(
        self, text: str, speaker_id: int, f0_speaker_id: int, f0_correct: float = 0
    ):
        rate = 200

        # phoneme
        utterance = extract_full_context_label(text)
        label_data_list = utterance.phonemes

        is_type1 = False
        phoneme_str_list = []
        start_accent_list = (
            numpy.ones(len(label_data_list), dtype=numpy.int64) * numpy.nan
        )
        end_accent_list = (
            numpy.ones(len(label_data_list), dtype=numpy.int64) * numpy.nan
        )
        start_accent_phrase_list = (
            numpy.ones(len(label_data_list), dtype=numpy.int64) * numpy.nan
        )
        end_accent_phrase_list = (
            numpy.ones(len(label_data_list), dtype=numpy.int64) * numpy.nan
        )
        for i, label in enumerate(label_data_list):
            is_end_accent = label.contexts["a1"] == "0"

            if label.contexts["a2"] == "1":
                is_type1 = is_end_accent

            if label.contexts["a2"] == "1" and is_type1:
                is_start_accent = True
            elif label.contexts["a2"] == "2" and not is_type1:
                is_start_accent = True
            else:
                is_start_accent = False

            phoneme_str_list.append(label.phoneme)
            start_accent_list[i] = is_start_accent
            end_accent_list[i] = is_end_accent
            start_accent_phrase_list[i] = label.contexts["a2"] == "1"
            end_accent_phrase_list[i] = label.contexts["a3"] == "1"

        start_accent_list = numpy.array(start_accent_list, dtype=numpy.int64)
        end_accent_list = numpy.array(end_accent_list, dtype=numpy.int64)
        start_accent_phrase_list = numpy.array(
            start_accent_phrase_list, dtype=numpy.int64
        )
        end_accent_phrase_list = numpy.array(end_accent_phrase_list, dtype=numpy.int64)

        # forward yukarin s
        assert self.yukarin_s_phoneme_class is not None

        phoneme_data_list = [
            self.yukarin_s_phoneme_class(phoneme=p, start=i, end=i + 1)
            for i, p in enumerate(phoneme_str_list)
        ]
        phoneme_data_list = self.yukarin_s_phoneme_class.convert(phoneme_data_list)
        phoneme_list_s = numpy.array(
            [p.phoneme_id for p in phoneme_data_list], dtype=numpy.int64
        )

        phoneme_length = self.yukarin_s_forwarder(
            length=len(phoneme_list_s),
            phoneme_list=numpy.ascontiguousarray(phoneme_list_s),
            speaker_id=numpy.array(f0_speaker_id, dtype=numpy.int64).reshape(-1),
        )
        phoneme_length[0] = phoneme_length[-1] = 0.1
        phoneme_length = numpy.round(phoneme_length * rate) / rate

        # forward yukarin sa
        (
            consonant_phoneme_data_list,
            vowel_phoneme_data_list,
            vowel_indexes_data,
        ) = split_mora(phoneme_data_list)

        vowel_indexes = numpy.array(vowel_indexes_data, dtype=numpy.int64)

        vowel_phoneme_list = numpy.array(
            [p.phoneme_id for p in vowel_phoneme_data_list], dtype=numpy.int64
        )
        consonant_phoneme_list = numpy.array(
            [
                p.phoneme_id if p is not None else -1
                for p in consonant_phoneme_data_list
            ],
            dtype=numpy.int64,
        )
        phoneme_length_sa = numpy.array(
            [a.sum() for a in numpy.split(phoneme_length, vowel_indexes[:-1] + 1)],
            dtype=numpy.float32,
        )

        f0_list = self.yukarin_sa_forwarder(
            length=vowel_phoneme_list.shape[0],
            vowel_phoneme_list=vowel_phoneme_list[numpy.newaxis],
            consonant_phoneme_list=consonant_phoneme_list[numpy.newaxis],
            start_accent_list=start_accent_list[vowel_indexes][numpy.newaxis],
            end_accent_list=end_accent_list[vowel_indexes][numpy.newaxis],
            start_accent_phrase_list=start_accent_phrase_list[vowel_indexes][
                numpy.newaxis
            ],
            end_accent_phrase_list=end_accent_phrase_list[vowel_indexes][numpy.newaxis],
            speaker_id=numpy.array(speaker_id, dtype=numpy.int64).reshape(-1),
        )[0]
        f0_list += f0_correct

        for i, p in enumerate(vowel_phoneme_data_list):
            if p.phoneme in unvoiced_mora_phoneme_list:
                f0_list[i] = 0

        phoneme = numpy.repeat(
            phoneme_list_s, numpy.round(phoneme_length * rate).astype(numpy.int64)
        )
        f0 = numpy.repeat(
            f0_list, numpy.round(phoneme_length_sa * rate).astype(numpy.int64)
        )

        # forward decode
        assert self.yukarin_soso_phoneme_class is not None

        if (
            self.yukarin_soso_phoneme_class is not JvsPhoneme
            and self.yukarin_soso_phoneme_class is not self.yukarin_s_phoneme_class
        ):
            phoneme = numpy.array(
                [
                    self.yukarin_soso_phoneme_class.phoneme_list.index(
                        JvsPhoneme.phoneme_list[p]
                    )
                    for p in phoneme
                ],
                dtype=numpy.int64,
            )

        array = numpy.zeros(
            (len(phoneme), self.yukarin_soso_phoneme_class.num_phoneme),
            dtype=numpy.float32,
        )
        array[numpy.arange(len(phoneme)), phoneme] = 1
        phoneme = array

        f0 = SamplingData(array=f0, rate=rate).resample(24000 / 256)
        phoneme = SamplingData(array=phoneme, rate=rate).resample(24000 / 256)

        wave = self.decode_forwarder(
            length=phoneme.shape[0],
            phoneme_size=phoneme.shape[1],
            f0=f0[:, numpy.newaxis],
            phoneme=phoneme,
            speaker_id=numpy.array(speaker_id, dtype=numpy.int64).reshape(-1),
        )
        return wave
