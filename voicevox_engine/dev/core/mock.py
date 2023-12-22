import json
from pathlib import Path
from unittest.mock import Mock

from ...core_wrapper import CoreWrapper


class MockCore(CoreWrapper):
    """`CoreWrapper` Mock"""

    def __init__(
        self,
        use_gpu: bool = False,
        core_dir: Path | None = None,
        cpu_num_threads: int = 0,
        load_all_models: bool = False,
    ) -> None:
        self.default_sampling_rate = 24000

        self.yukarin_s_forward = Mock()
        self.yukarin_sa_forward = Mock()
        self.decode_forward = Mock()

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
