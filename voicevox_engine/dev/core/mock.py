import json
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from ...core.core_wrapper import CoreWrapper


class MockCoreWrapper(CoreWrapper):
    """`CoreWrapper` Mock"""

    def __init__(
        self,
        use_gpu: bool = False,
        core_dir: Path | None = None,
        cpu_num_threads: int = 0,
        load_all_models: bool = False,
    ) -> None:
        self.default_sampling_rate = 24000

    def metas(self) -> str:
        return json.dumps(
            [
                {
                    "name": "dummy1",
                    "styles": [
                        {"name": "style0", "id": 0},
                        {"name": "style1", "id": 2},
                        {"name": "style2", "id": 4},
                        {"name": "style3", "id": 6},
                    ],
                    "speaker_uuid": "7ffcb7ce-00ec-4bdc-82cd-45a8889e43ff",
                    "version": "mock",
                },
                {
                    "name": "dummy2",
                    "styles": [
                        {"name": "style0", "id": 1},
                        {"name": "style1", "id": 3},
                        {"name": "style2", "id": 5},
                        {"name": "style3", "id": 7},
                    ],
                    "speaker_uuid": "388f246b-8c41-4ac1-8e2d-5d79f3ff56d9",
                    "version": "mock",
                },
                {
                    "name": "dummy3",
                    "styles": [
                        {"name": "style0", "id": 8},
                    ],
                    "speaker_uuid": "35b2c544-660e-401e-b503-0e14c635303a",
                    "version": "mock",
                },
                {
                    "name": "dummy4",
                    "styles": [
                        {"name": "style0", "id": 9},
                    ],
                    "speaker_uuid": "b1a81618-b27b-40d2-b0ea-27a9ad408c4b",
                    "version": "mock",
                },
            ]
        )

    def yukarin_s_forward(
        self, length: int, phoneme_list: NDArray[np.int64], style_id: NDArray[np.int64]
    ) -> NDArray[np.float32]:
        """音素系列サイズ・音素ID系列・スタイルIDから音素長系列を生成する"""
        result = []
        # mockとしての適当な処理、特に意味はない
        for i in range(length):
            result.append(round((phoneme_list[i] * 0.0625 + style_id).item(), 2))
        return np.array(result, dtype=np.float32)

    def yukarin_sa_forward(
        self,
        length: int,
        vowel_phoneme_list: NDArray[np.int64],
        consonant_phoneme_list: NDArray[np.int64],
        start_accent_list: NDArray[np.int64],
        end_accent_list: NDArray[np.int64],
        start_accent_phrase_list: NDArray[np.int64],
        end_accent_phrase_list: NDArray[np.int64],
        style_id: NDArray[np.int64],
    ) -> NDArray[np.float32]:
        """モーラ系列サイズ・母音系列・子音系列・アクセント位置・アクセント句区切り・スタイルIDからモーラ音高系列を生成する"""
        assert length > 1, "前後無音を必ず付与しなければならない"

        result = []
        # mockとしての適当な処理、特に意味はない
        for i in range(length):
            result.append(
                round(
                    (
                        (
                            vowel_phoneme_list[0][i]
                            + consonant_phoneme_list[0][i]
                            + start_accent_list[0][i]
                            + end_accent_list[0][i]
                            + start_accent_phrase_list[0][i]
                            + end_accent_phrase_list[0][i]
                        )
                        * 0.0625
                        + style_id
                    ).item(),
                    2,
                )
            )
        return np.array(result, dtype=np.float32)[np.newaxis]

    def decode_forward(
        self,
        length: int,
        phoneme_size: int,
        f0: NDArray[np.float32],
        phoneme: NDArray[np.float32],
        style_id: NDArray[np.int64],
    ) -> NDArray[np.float32]:
        """フレーム長・音素種類数・フレーム音高・フレーム音素onehot・スタイルIDからダミー音声波形を生成する"""
        # 入力値を反映し、長さが 256 倍であるダミー配列を出力する
        result: list[NDArray[np.float32]] = []
        for i in range(length):
            result += [
                (f0[i, 0] * (np.where(phoneme[i] == 1)[0] / phoneme_size) + style_id)
            ] * 256
        return np.array(result, dtype=np.float32)

    def predict_sing_consonant_length_forward(
        self,
        length: int,
        consonant: NDArray[np.int64],
        vowel: NDArray[np.int64],
        note_duration: NDArray[np.int64],
        style_id: NDArray[np.int64],
    ) -> NDArray[np.int64]:
        """母音系列・子音系列・ノート列・スタイルIDから子音長系列を生成する"""
        result = []
        # mockとしての適当な処理、特に意味はない
        for i in range(length):
            # 子音が無い場合は長さ0
            if consonant[i] == -1:
                result.append(0)
                continue

            result.append(
                consonant[i] % 2 + vowel[i] % 3 + note_duration[i] % 5 + style_id % 7
            )
        return np.array(result, dtype=np.int64)

    def predict_sing_f0_forward(
        self,
        length: int,
        phoneme: NDArray[np.int64],
        note: NDArray[np.int64],
        style_id: NDArray[np.int64],
    ) -> NDArray[np.float32]:
        """音素系列・ノート系列・スタイルIDから音高系列を生成する"""
        result = []
        # mockとしての適当な処理。大体MIDIノートに従う周波数になるように調整
        for i in range(length):
            if note[i] == -1:
                result.append(0)
                continue
            result.append(2 ** ((note[i] - 69) / 12) * (440 + phoneme / 10 + style_id))
        return np.array(result, dtype=np.float32)

    def predict_sing_volume_forward(
        self,
        length: int,
        phoneme: NDArray[np.int64],
        note: NDArray[np.int64],
        f0: NDArray[np.float32],
        style_id: NDArray[np.int64],
    ) -> NDArray[np.float32]:
        """音素系列・ノート系列・音高系列・スタイルIDから音量系列を生成する"""
        result = []
        # mockとしての適当な処理。大体0~1の範囲になるように調整
        for i in range(length):
            if note[i] == -1:
                result.append(0)
                continue
            result.append(
                (phoneme[i] / 100)
                * (note[i] / 88)
                * (f0[i] / 880)
                * ((style_id % 10 + 1) / 10)
            )
        return np.array(result, dtype=np.float32)

    def sf_decode_forward(
        self,
        length: int,
        phoneme: NDArray[np.int64],
        f0: NDArray[np.float32],
        volume: NDArray[np.float32],
        style_id: NDArray[np.int64],
    ) -> NDArray[np.float32]:
        """入力からダミー音声波形を生成する"""
        # 入力値を反映し、長さが 256 倍であるダミー配列を出力する
        result: list[NDArray[np.float32]] = []
        for i in range(length):
            result += [
                ((f0[i] / 880) * volume[i] * (phoneme[i] / 100) + style_id)
            ] * 256
        return np.array(result, dtype=np.float32)

    def supported_devices(self):
        return json.dumps(
            {
                "cpu": True,
                "cuda": False,
            }
        )

    def finalize(self) -> None:
        pass

    def load_model(self, style_id: int) -> None:
        pass

    def is_model_loaded(self, style_id: int) -> bool:
        return True

    def assert_core_success(self, result: bool) -> None:
        pass
