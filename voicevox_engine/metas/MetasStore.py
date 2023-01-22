import json
from pathlib import Path
from typing import Dict

from voicevox_engine.metas.Metas import SpeakerSupportPermittedSynthesisMorphing


class MetasStore:
    def __init__(self, engine_speakers_path: Path) -> None:
        self._engine_speakers_path = engine_speakers_path
        self._loaded_metas = {
            folder.name: self.fill_missing_speaker_properties(
                json.loads((folder / "metas.json").read_text(encoding="utf-8"))
            )
            for folder in engine_speakers_path.iterdir()
        }

    @staticmethod
    def fill_missing_speaker_properties(speaker: Dict):
        speaker.setdefault(
            "supported_features",
            dict(),
        )
        speaker["supported_features"].setdefault(
            "permitted_synthesis_morphing",
            SpeakerSupportPermittedSynthesisMorphing(None),
        )
        return speaker

    def speaker_engine_metas(self, speaker_uuid: str):
        return self.loaded_metas[speaker_uuid]

    def combine_metas(self, core_metas):
        """
        与えられたmetaにエンジンのコア情報を付加して返す
        core_metas: コアのmetas()が返すJSONのpythonオブジェクト形式
        """

        return [
            {**speaker_meta, **self.speaker_engine_metas(speaker_meta["speaker_uuid"])}
            for speaker_meta in core_metas
        ]

    @property
    def engine_speakers_path(self) -> Path:
        return self._engine_speakers_path

    @property
    def loaded_metas(self):
        return self._loaded_metas
