import json
from pathlib import Path

import numpy
from numpy import ndarray

from ...core_wrapper import CoreWrapper


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
        self, length: int, phoneme_list: ndarray, style_id: ndarray
    ) -> ndarray:
        """音素系列サイズ・音素ID系列・スタイルIDから音素長系列を生成する"""
        # Mock: 定数の音素長系列を生成。[0.1, 0.1, ...]
        return 0.1 * numpy.ones((length,), dtype=numpy.float32)

    def yukarin_sa_forward(
        self,
        length: int,
        vowel_phoneme_list: ndarray,
        consonant_phoneme_list: ndarray,
        start_accent_list: ndarray,
        end_accent_list: ndarray,
        start_accent_phrase_list: ndarray,
        end_accent_phrase_list: ndarray,
        style_id: ndarray,
    ) -> ndarray:
        """モーラ系列サイズ・母音系列・子音系列・アクセント位置・アクセント句区切り・スタイルIDからモーラ音高系列を生成する"""
        assert length > 1, "前後無音を必ず付与しなければならない"
        # Mock: 定数のモーラ音高系列を生成。[0, 200, 100, 100, ..., 100, 0]
        pitch = 100 * numpy.ones((1, length), dtype=numpy.float32)
        pitch[0, 0] = 0.0  # 開始無音 (pau)
        pitch[0, 1] = 200.0  # 分散 0 を避けるため
        pitch[0, length] = 0.0  # 終了無音 (pau)
        return pitch

    def decode_forward(
        self,
        length: int,
        phoneme_size: int,
        f0: ndarray,
        phoneme: ndarray,
        style_id: ndarray,
    ) -> ndarray:
        """フレーム長・音素種類数・フレーム音高・フレーム音素onehot・スタイルIDから音声波形を生成する"""
        # Mock: 定数の音声波形を生成。[0.1, 0.1, ..., 0.1, 0.1]
        return 0.1 * numpy.one((length * 256,), dtype=numpy.float32)

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
