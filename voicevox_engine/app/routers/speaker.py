"""キャラクター情報機能を提供する API Router"""

import base64
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic.json_schema import SkipJsonSchema

from voicevox_engine.core.core_initializer import CoreManager
from voicevox_engine.metas.Metas import Speaker, SpeakerInfo
from voicevox_engine.metas.MetasStore import MetasStore, filter_characters_and_styles


def b64encode_str(s: bytes) -> str:
    return base64.b64encode(s).decode("utf-8")


def generate_speaker_router(
    core_manager: CoreManager,
    metas_store: MetasStore,
    speaker_info_dir: Path,
) -> APIRouter:
    """キャラクター情報 API Router を生成する"""
    router = APIRouter(tags=["その他"])

    @router.get("/speakers")
    def speakers(core_version: str | SkipJsonSchema[None] = None) -> list[Speaker]:
        """喋れるキャラクターの情報の一覧を取得します。"""
        version = core_version or core_manager.latest_version()
        core = core_manager.get_core(version)
        characters = metas_store.load_combined_metas(core.characters)
        return filter_characters_and_styles(characters, "speaker")

    @router.get("/speaker_info")
    def speaker_info(
        speaker_uuid: str, core_version: str | SkipJsonSchema[None] = None
    ) -> SpeakerInfo:
        """
        UUID で指定された喋れるキャラクターの情報を取得します。
        画像や音声はbase64エンコードされたものが返されます。
        """
        return _speaker_info(
            speaker_uuid=speaker_uuid,
            speaker_or_singer="speaker",
            core_version=core_version,
        )

    # FIXME: この関数をどこかに切り出す
    def _speaker_info(
        speaker_uuid: str,
        speaker_or_singer: Literal["speaker", "singer"],
        core_version: str | None,
    ) -> SpeakerInfo:
        # エンジンに含まれるキャラクターメタ情報は、次のディレクトリ構造に従わなければならない：
        # {root_dir}/
        #   character_info/
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

        version = core_version or core_manager.latest_version()

        # 該当キャラクターを検索する
        core_characters = core_manager.get_core(version).characters
        characters = metas_store.load_combined_metas(core_characters)
        speakers = filter_characters_and_styles(characters, speaker_or_singer)
        speaker = next(
            filter(lambda spk: spk.speaker_uuid == speaker_uuid, speakers), None
        )
        if speaker is None:
            msg = "該当するキャラクターが見つかりません"
            raise HTTPException(
                status_code=404, detail=msg
            )

        # キャラクター情報を取得する
        try:
            speaker_path = speaker_info_dir / speaker_uuid

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
            msg = "追加情報が見つかりませんでした"
            raise HTTPException(status_code=500, detail=msg)

        spk_info = SpeakerInfo(
            policy=policy, portrait=portrait, style_infos=style_infos
        )
        return spk_info

    @router.get("/singers")
    def singers(core_version: str | SkipJsonSchema[None] = None) -> list[Speaker]:
        """歌えるキャラクターの情報の一覧を取得します。"""
        version = core_version or core_manager.latest_version()
        core = core_manager.get_core(version)
        characters = metas_store.load_combined_metas(core.characters)
        return filter_characters_and_styles(characters, "singer")

    @router.get("/singer_info")
    def singer_info(
        speaker_uuid: str, core_version: str | SkipJsonSchema[None] = None
    ) -> SpeakerInfo:
        """
        UUID で指定された歌えるキャラクターの情報を取得します。
        画像や音声はbase64エンコードされたものが返されます。
        """
        return _speaker_info(
            speaker_uuid=speaker_uuid,
            speaker_or_singer="singer",
            core_version=core_version,
        )

    return router
