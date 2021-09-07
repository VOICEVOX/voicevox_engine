from itertools import chain
from typing import List, Optional

import numpy

from voicevox_engine.acoustic_feature_extractor import (
    BasePhoneme,
    OjtPhoneme,
    SamplingData,
)
from voicevox_engine.model import AccentPhrase, AudioQuery

unvoiced_mora_phoneme_list = ["A", "I", "U", "E", "O", "cl", "pau"]
mora_phoneme_list = ["a", "i", "u", "e", "o", "N"] + unvoiced_mora_phoneme_list


def to_flatten_moras(accent_phrases: List[AccentPhrase]):
    return list(
        chain.from_iterable(
            accent_phrase.moras
            + (
                [accent_phrase.pause_mora]
                if accent_phrase.pause_mora is not None
                else []
            )
            for accent_phrase in accent_phrases
        )
    )


def to_phoneme_data_list(phoneme_str_list: List[str]):
    phoneme_data_list = [
        OjtPhoneme(phoneme=p, start=i, end=i + 1)
        for i, p in enumerate(phoneme_str_list)
    ]
    phoneme_data_list = OjtPhoneme.convert(phoneme_data_list)
    return phoneme_data_list


def f0_mean(f0: numpy.ndarray, rate: float, split_second_list: List[float]):
    indexes = numpy.floor(numpy.array(split_second_list) * rate).astype(int)
    for a in numpy.split(f0, indexes):
        a[:] = numpy.mean(a[a > 0])
    f0[numpy.isnan(f0)] = 0
    return f0


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


class SynthesisEngine:
    def __init__(
        self,
        yukarin_s_forwarder,
        yukarin_sa_forwarder,
        decode_forwarder,
    ):
        """
        yukarin_s_forwarder: 音素列から、音素ごとの長さを求める関数
            length: 音素列の長さ
            phoneme_list: 音素列
            speaker_id: 話者番号
            return: 音素ごとの長さ

        yukarin_sa_forwarder: モーラごとの音素列とアクセント情報から、モーラごとの音高を求める関数
            length: モーラ列の長さ
            vowel_phoneme_list: 母音の音素列
            consonant_phoneme_list: 子音の音素列
            start_accent_list: アクセントの開始位置
            end_accent_list: アクセントの終了位置
            start_accent_phrase_list: アクセント句の開始位置
            end_accent_phrase_list: アクセント句の終了位置
            speaker_id: 話者番号
            return: モーラごとの音高

        decode_forwarder: フレームごとの音素と音高から波形を求める関数
            length: フレームの長さ
            phoneme_size: 音素の種類数
            f0: フレームごとの音高
            phoneme: フレームごとの音素
            speaker_id: 話者番号
            return: 音声波形
        """
        super().__init__()
        self.yukarin_s_forwarder = yukarin_s_forwarder
        self.yukarin_sa_forwarder = yukarin_sa_forwarder
        self.decode_forwarder = decode_forwarder
        self.yukarin_s_phoneme_class = OjtPhoneme
        self.yukarin_soso_phoneme_class = OjtPhoneme

    def replace_phoneme_length(
        self, accent_phrases: List[AccentPhrase], speaker_id: int
    ) -> List[AccentPhrase]:
        # phoneme
        flatten_moras = to_flatten_moras(accent_phrases)

        phoneme_each_mora = [
            ([mora.consonant] if mora.consonant is not None else []) + [mora.vowel]
            for mora in flatten_moras
        ]
        phoneme_str_list = list(chain.from_iterable(phoneme_each_mora))
        phoneme_str_list = ["pau"] + phoneme_str_list + ["pau"]

        phoneme_data_list = to_phoneme_data_list(phoneme_str_list)
        _, _, vowel_indexes_data = split_mora(phoneme_data_list)

        # yukarin_s
        phoneme_list_s = numpy.array(
            [p.phoneme_id for p in phoneme_data_list], dtype=numpy.int64
        )
        phoneme_length = self.yukarin_s_forwarder(
            length=len(phoneme_list_s),
            phoneme_list=phoneme_list_s,
            speaker_id=numpy.array(speaker_id, dtype=numpy.int64).reshape(-1),
        )

        for i, mora in enumerate(flatten_moras):
            mora.consonant_length = (
                phoneme_length[vowel_indexes_data[i + 1] - 1]
                if mora.consonant is not None
                else None
            )
            mora.vowel_length = phoneme_length[vowel_indexes_data[i + 1]]

        return accent_phrases

    def replace_mora_pitch(
        self, accent_phrases: List[AccentPhrase], speaker_id: int
    ) -> List[AccentPhrase]:
        # phoneme
        flatten_moras = to_flatten_moras(accent_phrases)

        phoneme_each_mora = [
            ([mora.consonant] if mora.consonant is not None else []) + [mora.vowel]
            for mora in flatten_moras
        ]
        phoneme_str_list = list(chain.from_iterable(phoneme_each_mora))
        phoneme_str_list = ["pau"] + phoneme_str_list + ["pau"]

        # accent
        def _repeat_with_mora(array, accent_phrase):
            return numpy.repeat(
                array,
                [
                    1 if mora.consonant is None else 2
                    for mora in accent_phrase.moras
                    + (
                        [accent_phrase.pause_mora]
                        if accent_phrase.pause_mora is not None
                        else []
                    )
                ],
            )

        start_accent_list = numpy.concatenate(
            [
                _repeat_with_mora(
                    numpy.r_[
                        numpy.eye(len(accent_phrase.moras))[
                            0 if accent_phrase.accent == 1 else 1
                        ],
                        (0 if accent_phrase.pause_mora is not None else []),
                    ],
                    accent_phrase=accent_phrase,
                )
                for accent_phrase in accent_phrases
            ]
        )
        end_accent_list = numpy.concatenate(
            [
                _repeat_with_mora(
                    numpy.r_[
                        numpy.eye(len(accent_phrase.moras))[accent_phrase.accent - 1],
                        (0 if accent_phrase.pause_mora is not None else []),
                    ],
                    accent_phrase=accent_phrase,
                )
                for accent_phrase in accent_phrases
            ]
        )
        start_accent_phrase_list = numpy.concatenate(
            [
                _repeat_with_mora(
                    numpy.r_[
                        numpy.eye(len(accent_phrase.moras))[0],
                        (0 if accent_phrase.pause_mora is not None else []),
                    ],
                    accent_phrase=accent_phrase,
                )
                for accent_phrase in accent_phrases
            ]
        )
        end_accent_phrase_list = numpy.concatenate(
            [
                _repeat_with_mora(
                    numpy.r_[
                        numpy.eye(len(accent_phrase.moras))[-1],
                        (0 if accent_phrase.pause_mora is not None else []),
                    ],
                    accent_phrase=accent_phrase,
                )
                for accent_phrase in accent_phrases
            ]
        )

        start_accent_list = numpy.r_[0, start_accent_list, 0]
        end_accent_list = numpy.r_[0, end_accent_list, 0]
        start_accent_phrase_list = numpy.r_[0, start_accent_phrase_list, 0]
        end_accent_phrase_list = numpy.r_[0, end_accent_phrase_list, 0]

        start_accent_list = numpy.array(start_accent_list, dtype=numpy.int64)
        end_accent_list = numpy.array(end_accent_list, dtype=numpy.int64)
        start_accent_phrase_list = numpy.array(
            start_accent_phrase_list, dtype=numpy.int64
        )
        end_accent_phrase_list = numpy.array(end_accent_phrase_list, dtype=numpy.int64)

        phoneme_data_list = to_phoneme_data_list(phoneme_str_list)
        (
            consonant_phoneme_data_list,
            vowel_phoneme_data_list,
            vowel_indexes_data,
        ) = split_mora(phoneme_data_list)

        # yukarin_sa
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

        for i, p in enumerate(vowel_phoneme_data_list):
            if p.phoneme in unvoiced_mora_phoneme_list:
                f0_list[i] = 0

        for i, mora in enumerate(flatten_moras):
            mora.pitch = f0_list[i + 1]

        return accent_phrases

    def synthesis(self, query: AudioQuery, speaker_id: int):
        rate = 200

        # phoneme
        flatten_moras = to_flatten_moras(query.accent_phrases)
        phoneme_each_mora = [
            ([mora.consonant] if mora.consonant is not None else []) + [mora.vowel]
            for mora in flatten_moras
        ]
        phoneme_str_list = list(chain.from_iterable(phoneme_each_mora))
        phoneme_str_list = ["pau"] + phoneme_str_list + ["pau"]

        phoneme_data_list = to_phoneme_data_list(phoneme_str_list)
        phoneme_list_s = numpy.array(
            [p.phoneme_id for p in phoneme_data_list], dtype=numpy.int64
        )

        # length
        phoneme_length_list = (
            [query.prePhonemeLength]
            + [
                length
                for mora in flatten_moras
                for length in (
                    [mora.consonant_length] if mora.consonant is not None else []
                )
                + [mora.vowel_length]
            ]
            + [query.postPhonemeLength]
        )
        phoneme_length = numpy.array(phoneme_length_list, dtype=numpy.float32)
        phoneme_length = numpy.round(phoneme_length * rate) / rate

        phoneme_length /= query.speedScale

        # pitch
        f0_list = [0] + [mora.pitch for mora in flatten_moras] + [0]
        f0 = numpy.array(f0_list, dtype=numpy.float32)
        f0 *= 2 ** query.pitchScale

        voiced = f0 > 0
        mean_f0 = f0[voiced].mean()
        if not numpy.isnan(mean_f0):
            f0[voiced] = (f0[voiced] - mean_f0) * query.intonationScale + mean_f0

        _, _, vowel_indexes_data = split_mora(phoneme_data_list)
        vowel_indexes = numpy.array(vowel_indexes_data)

        # forward decode
        phoneme_bin_num = numpy.round(phoneme_length * rate).astype(numpy.int32)

        phoneme = numpy.repeat(phoneme_list_s, phoneme_bin_num)
        f0 = numpy.repeat(
            f0,
            [a.sum() for a in numpy.split(phoneme_bin_num, vowel_indexes[:-1] + 1)],
        )

        array = numpy.zeros((len(phoneme), OjtPhoneme.num_phoneme), dtype=numpy.float32)
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

        # volume
        if query.volumeScale != 1:
            wave *= query.volumeScale

        return wave
