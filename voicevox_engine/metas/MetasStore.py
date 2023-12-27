import json
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Tuple

from voicevox_engine.metas.Metas import (
    CoreSpeaker,
    EngineSpeaker,
    Speaker,
    SpeakerStyle,
)

if TYPE_CHECKING:
    from voicevox_engine.core_adapter import CoreAdapter


class MetasStore:
    """
    話者やスタイルのメタ情報を管理する
    """

    def __init__(self, engine_speakers_path: Path) -> None:
        """
        Parameters
        ----------
        engine_speakers_path : Path
            エンジンに含まれる話者メタ情報ディレクトリのパス。
        """
        # エンジンに含まれる各話者のメタ情報
        self._loaded_metas: Dict[str, EngineSpeaker] = {
            folder.name: EngineSpeaker(
                **json.loads((folder / "metas.json").read_text(encoding="utf-8"))
            )
            for folder in engine_speakers_path.iterdir()
        }

    # FIXME: engineではなくList[CoreSpeaker]を渡す形にすることで
    # TTSEngineBaseによる循環importを修正する
    def load_combined_metas(self, core: "CoreAdapter") -> List[Speaker]:
        """
        コアに含まれる話者メタ情報とエンジンに含まれる話者メタ情報を統合
        Parameters
        ----------
        core : CoreAdapter
            話者メタ情報をもったコア
        Returns
        -------
        ret : List[Speaker]
            エンジンとコアに含まれる話者メタ情報
        """
        # コアに含まれる話者メタ情報の収集
        core_metas = [CoreSpeaker(**speaker) for speaker in json.loads(core.speakers)]
        # エンジンに含まれる話者メタ情報との統合
        return [
            Speaker(
                **self._loaded_metas[speaker_meta.speaker_uuid].dict(),
                **speaker_meta.dict(),
            )
            for speaker_meta in core_metas
        ]


def construct_lookup(
    speakers: List[Speaker],
) -> Dict[int, Tuple[Speaker, SpeakerStyle]]:
    """
    スタイルID に話者メタ情報・スタイルメタ情報を紐付ける対応表を生成
    Parameters
    ----------
    speakers : List[Speaker]
        話者メタ情報
    Returns
    -------
    ret : Dict[int, Tuple[Speaker, SpeakerStyle]]
        スタイルID に話者メタ情報・スタイルメタ情報が紐付いた対応表
    """
    lookup_table: dict[int, tuple[Speaker, SpeakerStyle]] = dict()
    for speaker in speakers:
        for style in speaker.styles:
            lookup_table[style.id] = (speaker, style)
    return lookup_table
