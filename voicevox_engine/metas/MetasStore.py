import base64
import json
import traceback
from copy import deepcopy
from pathlib import Path
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, Field, parse_obj_as

from voicevox_engine.core.core_adapter import CoreAdapter, CoreSpeakerStyle
from voicevox_engine.metas.Metas import (
    Speaker,
    SpeakerInfo,
    SpeakerStyle,
    SpeakerSupportedFeatures,
    StyleId,
    StyleType,
)


def cast_styles(cores: list[CoreSpeakerStyle]) -> list[SpeakerStyle]:
    """コアから取得したスタイル情報をエンジン形式へキャストする。"""
    return [
        SpeakerStyle(name=core.name, id=StyleId(core.id), type=core.type)
        for core in cores
    ]


class _EngineSpeaker(BaseModel):
    """
    エンジンに含まれる話者情報
    """

    supported_features: SpeakerSupportedFeatures = Field(
        default_factory=SpeakerSupportedFeatures
    )


def b64encode_str(s: bytes) -> str:
    return base64.b64encode(s).decode("utf-8")


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
        self._speakers_path = engine_speakers_path
        # エンジンに含まれる各話者のメタ情報
        self._loaded_metas: dict[str, _EngineSpeaker] = {
            folder.name: _EngineSpeaker(
                **json.loads((folder / "metas.json").read_text(encoding="utf-8"))
            )
            for folder in engine_speakers_path.iterdir()
        }

    # FIXME: engineではなくlist[CoreSpeaker]を渡す形にすることで
    # TTSEngineによる循環importを修正する
    def load_combined_metas(self, core: CoreAdapter) -> list[Speaker]:
        """
        コアに含まれる話者メタ情報とエンジンに含まれる話者メタ情報を統合
        Parameters
        ----------
        core : CoreAdapter
            話者メタ情報をもったコア
        Returns
        -------
        ret : list[Speaker]
            エンジンとコアに含まれる話者メタ情報
        """
        # コアに含まれる話者メタ情報の収集
        core_metas = core.speakers
        # エンジンに含まれる話者メタ情報との統合
        return [
            Speaker(
                supported_features=self._loaded_metas[
                    speaker_meta.speaker_uuid
                ].supported_features,
                name=speaker_meta.name,
                speaker_uuid=speaker_meta.speaker_uuid,
                styles=cast_styles(speaker_meta.styles),
                version=speaker_meta.version,
            )
            for speaker_meta in core_metas
        ]

    def speaker_info(
        self,
        speaker_uuid: str,
        speaker_or_singer: Literal["speaker", "singer"],
        core: CoreAdapter,
    ) -> SpeakerInfo:
        # エンジンに含まれる話者メタ情報は、次のディレクトリ構造に従わなければならない：
        # {root_dir}/
        #   speaker_info/
        #       {speaker_uuid_0}/
        #           policy.md
        #           portrait.png
        #           icons/
        #               {id_0}.png
        #               {id_1}.png
        #               ...
        #           portraits/
        #               {id_0}.png
        #               {id_1}.png
        #               ...
        #           voice_samples/
        #               {id_0}_001.wav
        #               {id_0}_002.wav
        #               {id_0}_003.wav
        #               {id_1}_001.wav
        #               ...
        #       {speaker_uuid_1}/
        #           ...

        # 該当話者を検索する
        speakers = parse_obj_as(list[Speaker], core.speakers)
        speakers = filter_speakers_and_styles(speakers, speaker_or_singer)
        speaker = next(
            filter(lambda spk: spk.speaker_uuid == speaker_uuid, speakers), None
        )
        if speaker is None:
            # FIXME: ドメインを合わせる
            raise HTTPException(status_code=404, detail="該当する話者が見つかりません")

        # 話者情報を取得する
        try:
            speaker_path = self._speakers_path / speaker_uuid

            # speaker policy
            policy_path = speaker_path / "policy.md"
            policy = policy_path.read_text("utf-8")

            # speaker portrait
            portrait_path = speaker_path / "portrait.png"
            portrait = b64encode_str(portrait_path.read_bytes())

            # スタイル情報を取得する
            style_infos = []
            for style in speaker.styles:
                id = style.id

                # style icon
                style_icon_path = speaker_path / "icons" / f"{id}.png"
                icon = b64encode_str(style_icon_path.read_bytes())

                # style portrait
                style_portrait_path = speaker_path / "portraits" / f"{id}.png"
                style_portrait = None
                if style_portrait_path.exists():
                    style_portrait = b64encode_str(style_portrait_path.read_bytes())

                # voice samples
                voice_samples: list[str] = []
                for j in range(3):
                    num = str(j + 1).zfill(3)
                    voice_path = speaker_path / "voice_samples" / f"{id}_{num}.wav"
                    voice_samples.append(b64encode_str(voice_path.read_bytes()))

                style_infos.append(
                    {
                        "id": id,
                        "icon": icon,
                        "portrait": style_portrait,
                        "voice_samples": voice_samples,
                    }
                )
        except FileNotFoundError:
            traceback.print_exc()
            # FIXME: ドメインを合わせる
            msg = "追加情報が見つかりませんでした"
            raise HTTPException(status_code=500, detail=msg)

        spk_info = SpeakerInfo(
            policy=policy, portrait=portrait, style_infos=style_infos
        )
        return spk_info


def construct_lookup(
    speakers: list[Speaker],
) -> dict[StyleId, tuple[Speaker, SpeakerStyle]]:
    """
    スタイルID に話者メタ情報・スタイルメタ情報を紐付ける対応表を生成
    Parameters
    ----------
    speakers : list[Speaker]
        話者メタ情報
    Returns
    -------
    ret : dict[StyleId, tuple[Speaker, SpeakerStyle]]
        スタイルID に話者メタ情報・スタイルメタ情報が紐付いた対応表
    """
    lookup_table: dict[StyleId, tuple[Speaker, SpeakerStyle]] = dict()
    for speaker in speakers:
        for style in speaker.styles:
            lookup_table[style.id] = (speaker, style)
    return lookup_table


def filter_speakers_and_styles(
    speakers: list[Speaker],
    speaker_or_singer: Literal["speaker", "singer"],
) -> list[Speaker]:
    """
    話者・スタイルをフィルタリングする。
    speakerの場合はトーク系スタイルのみ、singerの場合はソング系スタイルのみを残す。
    スタイル数が0になった話者は除外する。
    """
    style_types: list[StyleType]
    if speaker_or_singer == "speaker":
        style_types = ["talk"]
    elif speaker_or_singer == "singer":
        style_types = ["singing_teacher", "frame_decode", "sing"]

    speakers = deepcopy(speakers)
    for speaker in speakers:
        speaker.styles = [
            style for style in speaker.styles if style.type in style_types
        ]
    return [speaker for speaker in speakers if len(speaker.styles) > 0]
