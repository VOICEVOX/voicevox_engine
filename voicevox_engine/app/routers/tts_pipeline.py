"""音声合成機能を提供する API Router"""

import zipfile
from tempfile import NamedTemporaryFile, TemporaryFile
from typing import Annotated, Self

import soundfile
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema
from starlette.background import BackgroundTask
from starlette.responses import FileResponse

from voicevox_engine.cancellable_engine import (
    CancellableEngine,
    CancellableEngineInternalError,
)
from voicevox_engine.core.core_adapter import DeviceSupport
from voicevox_engine.metas.Metas import StyleId
from voicevox_engine.model import AudioQuery
from voicevox_engine.preset.preset_manager import (
    PresetInputError,
    PresetInternalError,
    PresetManager,
)
from voicevox_engine.tts_pipeline.connect_base64_waves import (
    ConnectBase64WavesException,
    connect_base64_waves,
)
from voicevox_engine.tts_pipeline.kana_converter import (
    ParseKanaError,
    create_kana,
    parse_kana,
)
from voicevox_engine.tts_pipeline.model import (
    AccentPhrase,
    FrameAudioQuery,
    ParseKanaErrorCode,
    Score,
)
from voicevox_engine.tts_pipeline.tts_engine import (
    LATEST_VERSION,
    TalkSingInvalidInputError,
    TTSEngineManager,
)
from voicevox_engine.utility.file_utility import try_delete_file


class ParseKanaBadRequest(BaseModel):
    text: str = Field(description="エラーメッセージ")
    error_name: str = Field(
        description="エラー名\n\n"
        "|name|description|\n|---|---|\n"
        + "\n".join(
            [
                "| {} | {} |".format(err.name, err.value)
                for err in list(ParseKanaErrorCode)
            ]
        ),
    )
    error_args: dict[str, str] = Field(description="エラーを起こした箇所")

    def __init__(self, err: ParseKanaError):
        super().__init__(text=err.text, error_name=err.errname, error_args=err.kwargs)


class SupportedDevicesInfo(BaseModel):
    """
    対応しているデバイスの情報
    """

    cpu: bool = Field(description="CPUに対応しているか")
    cuda: bool = Field(description="CUDA(Nvidia GPU)に対応しているか")
    dml: bool = Field(description="DirectML(Nvidia GPU/Radeon GPU等)に対応しているか")

    @classmethod
    def generate_from(cls, device_support: DeviceSupport) -> Self:
        """`DeviceSupport` インスタンスからこのインスタンスを生成する。"""
        return cls(
            cpu=device_support.cpu,
            cuda=device_support.cuda,
            dml=device_support.dml,
        )


def generate_tts_pipeline_router(
    tts_engines: TTSEngineManager,
    preset_manager: PresetManager,
    cancellable_engine: CancellableEngine | None,
) -> APIRouter:
    """音声合成 API Router を生成する"""
    router = APIRouter()

    @router.post(
        "/audio_query",
        tags=["クエリ作成"],
        summary="音声合成用のクエリを作成する",
    )
    def audio_query(
        text: str,
        style_id: Annotated[StyleId, Query(alias="speaker")],
        core_version: str | SkipJsonSchema[None] = None,
    ) -> AudioQuery:
        """
        音声合成用のクエリの初期値を得ます。ここで得られたクエリはそのまま音声合成に利用できます。各値の意味は`Schemas`を参照してください。
        """
        version = core_version or LATEST_VERSION
        engine = tts_engines.get_engine(version)
        accent_phrases = engine.create_accent_phrases(text, style_id)
        return AudioQuery(
            accent_phrases=accent_phrases,
            speedScale=1,
            pitchScale=0,
            intonationScale=1,
            volumeScale=1,
            prePhonemeLength=0.1,
            postPhonemeLength=0.1,
            pauseLength=None,
            pauseLengthScale=1,
            outputSamplingRate=engine.default_sampling_rate,
            outputStereo=False,
            kana=create_kana(accent_phrases),
        )

    @router.post(
        "/audio_query_from_preset",
        tags=["クエリ作成"],
        summary="音声合成用のクエリをプリセットを用いて作成する",
    )
    def audio_query_from_preset(
        text: str,
        preset_id: int,
        core_version: str | SkipJsonSchema[None] = None,
    ) -> AudioQuery:
        """
        音声合成用のクエリの初期値を得ます。ここで得られたクエリはそのまま音声合成に利用できます。各値の意味は`Schemas`を参照してください。
        """
        version = core_version or LATEST_VERSION
        engine = tts_engines.get_engine(version)
        try:
            presets = preset_manager.load_presets()
        except PresetInputError as err:
            raise HTTPException(status_code=422, detail=str(err))
        except PresetInternalError as err:
            raise HTTPException(status_code=500, detail=str(err))
        for preset in presets:
            if preset.id == preset_id:
                selected_preset = preset
                break
        else:
            raise HTTPException(
                status_code=422, detail="該当するプリセットIDが見つかりません"
            )

        accent_phrases = engine.create_accent_phrases(text, selected_preset.style_id)
        return AudioQuery(
            accent_phrases=accent_phrases,
            speedScale=selected_preset.speedScale,
            pitchScale=selected_preset.pitchScale,
            intonationScale=selected_preset.intonationScale,
            volumeScale=selected_preset.volumeScale,
            prePhonemeLength=selected_preset.prePhonemeLength,
            postPhonemeLength=selected_preset.postPhonemeLength,
            pauseLength=selected_preset.pauseLength,
            pauseLengthScale=selected_preset.pauseLengthScale,
            outputSamplingRate=engine.default_sampling_rate,
            outputStereo=False,
            kana=create_kana(accent_phrases),
        )

    @router.post(
        "/accent_phrases",
        tags=["クエリ編集"],
        summary="テキストからアクセント句を得る",
        responses={
            400: {
                "description": "読み仮名のパースに失敗",
                "model": ParseKanaBadRequest,
            }
        },
    )
    def accent_phrases(
        text: str,
        style_id: Annotated[StyleId, Query(alias="speaker")],
        is_kana: bool = False,
        core_version: str | SkipJsonSchema[None] = None,
    ) -> list[AccentPhrase]:
        """
        テキストからアクセント句を得ます。
        is_kanaが`true`のとき、テキストは次のAquesTalk 風記法で解釈されます。デフォルトは`false`です。
        * 全てのカナはカタカナで記述される
        * アクセント句は`/`または`、`で区切る。`、`で区切った場合に限り無音区間が挿入される。
        * カナの手前に`_`を入れるとそのカナは無声化される
        * アクセント位置を`'`で指定する。全てのアクセント句にはアクセント位置を1つ指定する必要がある。
        * アクセント句末に`？`(全角)を入れることにより疑問文の発音ができる。
        """
        version = core_version or LATEST_VERSION
        engine = tts_engines.get_engine(version)
        if is_kana:
            try:
                return engine.create_accent_phrases_from_kana(text, style_id)
            except ParseKanaError as err:
                raise HTTPException(
                    status_code=400, detail=ParseKanaBadRequest(err).model_dump()
                )
        else:
            return engine.create_accent_phrases(text, style_id)

    @router.post(
        "/mora_data",
        tags=["クエリ編集"],
        summary="アクセント句から音高・音素長を得る",
    )
    def mora_data(
        accent_phrases: list[AccentPhrase],
        style_id: Annotated[StyleId, Query(alias="speaker")],
        core_version: str | SkipJsonSchema[None] = None,
    ) -> list[AccentPhrase]:
        version = core_version or LATEST_VERSION
        engine = tts_engines.get_engine(version)
        return engine.update_length_and_pitch(accent_phrases, style_id)

    @router.post(
        "/mora_length",
        tags=["クエリ編集"],
        summary="アクセント句から音素長を得る",
    )
    def mora_length(
        accent_phrases: list[AccentPhrase],
        style_id: Annotated[StyleId, Query(alias="speaker")],
        core_version: str | SkipJsonSchema[None] = None,
    ) -> list[AccentPhrase]:
        version = core_version or LATEST_VERSION
        engine = tts_engines.get_engine(version)
        return engine.update_length(accent_phrases, style_id)

    @router.post(
        "/mora_pitch",
        tags=["クエリ編集"],
        summary="アクセント句から音高を得る",
    )
    def mora_pitch(
        accent_phrases: list[AccentPhrase],
        style_id: Annotated[StyleId, Query(alias="speaker")],
        core_version: str | SkipJsonSchema[None] = None,
    ) -> list[AccentPhrase]:
        version = core_version or LATEST_VERSION
        engine = tts_engines.get_engine(version)
        return engine.update_pitch(accent_phrases, style_id)

    @router.post(
        "/synthesis",
        response_class=FileResponse,
        responses={
            200: {
                "content": {
                    "audio/wav": {"schema": {"type": "string", "format": "binary"}}
                },
            }
        },
        tags=["音声合成"],
        summary="音声合成する",
    )
    def synthesis(
        query: AudioQuery,
        style_id: Annotated[StyleId, Query(alias="speaker")],
        enable_interrogative_upspeak: Annotated[
            bool,
            Query(
                description="疑問系のテキストが与えられたら語尾を自動調整する",
            ),
        ] = True,
        core_version: str | SkipJsonSchema[None] = None,
    ) -> FileResponse:
        version = core_version or LATEST_VERSION
        engine = tts_engines.get_engine(version)
        wave = engine.synthesize_wave(
            query, style_id, enable_interrogative_upspeak=enable_interrogative_upspeak
        )

        with NamedTemporaryFile(delete=False) as f:
            soundfile.write(
                file=f, data=wave, samplerate=query.outputSamplingRate, format="WAV"
            )

        return FileResponse(
            f.name,
            media_type="audio/wav",
            background=BackgroundTask(try_delete_file, f.name),
        )

    @router.post(
        "/cancellable_synthesis",
        response_class=FileResponse,
        responses={
            200: {
                "content": {
                    "audio/wav": {"schema": {"type": "string", "format": "binary"}}
                },
            }
        },
        tags=["音声合成"],
        summary="音声合成する（キャンセル可能）",
    )
    def cancellable_synthesis(
        query: AudioQuery,
        request: Request,
        style_id: Annotated[StyleId, Query(alias="speaker")],
        core_version: str | SkipJsonSchema[None] = None,
    ) -> FileResponse:
        if cancellable_engine is None:
            raise HTTPException(
                status_code=404,
                detail="実験的機能はデフォルトで無効になっています。使用するには引数を指定してください。",
            )
        try:
            version = core_version or LATEST_VERSION
            f_name = cancellable_engine._synthesis_impl(
                query, style_id, request, version=version
            )
        except CancellableEngineInternalError as e:
            raise HTTPException(status_code=500, detail=str(e))

        if f_name == "":
            raise HTTPException(status_code=422, detail="不明なバージョンです")

        return FileResponse(
            f_name,
            media_type="audio/wav",
            background=BackgroundTask(try_delete_file, f_name),
        )

    @router.post(
        "/multi_synthesis",
        response_class=FileResponse,
        responses={
            200: {
                "content": {
                    "application/zip": {
                        "schema": {"type": "string", "format": "binary"}
                    }
                },
            }
        },
        tags=["音声合成"],
        summary="複数まとめて音声合成する",
    )
    def multi_synthesis(
        queries: list[AudioQuery],
        style_id: Annotated[StyleId, Query(alias="speaker")],
        core_version: str | SkipJsonSchema[None] = None,
    ) -> FileResponse:
        version = core_version or LATEST_VERSION
        engine = tts_engines.get_engine(version)
        sampling_rate = queries[0].outputSamplingRate

        with NamedTemporaryFile(delete=False) as f:
            with zipfile.ZipFile(f, mode="a") as zip_file:
                for i in range(len(queries)):
                    if queries[i].outputSamplingRate != sampling_rate:
                        raise HTTPException(
                            status_code=422,
                            detail="サンプリングレートが異なるクエリがあります",
                        )

                    with TemporaryFile() as wav_file:
                        wave = engine.synthesize_wave(queries[i], style_id)
                        soundfile.write(
                            file=wav_file,
                            data=wave,
                            samplerate=sampling_rate,
                            format="WAV",
                        )
                        wav_file.seek(0)
                        zip_file.writestr(f"{str(i + 1).zfill(3)}.wav", wav_file.read())

        return FileResponse(
            f.name,
            media_type="application/zip",
            background=BackgroundTask(try_delete_file, f.name),
        )

    @router.post(
        "/sing_frame_audio_query",
        tags=["クエリ作成"],
        summary="歌唱音声合成用のクエリを作成する",
    )
    def sing_frame_audio_query(
        score: Score,
        style_id: Annotated[StyleId, Query(alias="speaker")],
        core_version: str | SkipJsonSchema[None] = None,
    ) -> FrameAudioQuery:
        """
        歌唱音声合成用のクエリの初期値を得ます。ここで得られたクエリはそのまま歌唱音声合成に利用できます。各値の意味は`Schemas`を参照してください。
        """
        version = core_version or LATEST_VERSION
        engine = tts_engines.get_engine(version)
        try:
            phonemes, f0, volume = engine.create_sing_phoneme_and_f0_and_volume(
                score, style_id
            )
        except TalkSingInvalidInputError as e:
            raise HTTPException(status_code=400, detail=str(e))

        return FrameAudioQuery(
            f0=f0,
            volume=volume,
            phonemes=phonemes,
            volumeScale=1,
            outputSamplingRate=engine.default_sampling_rate,
            outputStereo=False,
        )

    @router.post(
        "/sing_frame_volume",
        tags=["クエリ編集"],
        summary="スコア・歌唱音声合成用のクエリからフレームごとの音量を得る",
    )
    def sing_frame_volume(
        score: Score,
        frame_audio_query: FrameAudioQuery,
        style_id: Annotated[StyleId, Query(alias="speaker")],
        core_version: str | SkipJsonSchema[None] = None,
    ) -> list[float]:
        version = core_version or LATEST_VERSION
        engine = tts_engines.get_engine(version)
        try:
            return engine.create_sing_volume_from_phoneme_and_f0(
                score, frame_audio_query.phonemes, frame_audio_query.f0, style_id
            )
        except TalkSingInvalidInputError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post(
        "/frame_synthesis",
        response_class=FileResponse,
        responses={
            200: {
                "content": {
                    "audio/wav": {"schema": {"type": "string", "format": "binary"}}
                },
            }
        },
        tags=["音声合成"],
    )
    def frame_synthesis(
        query: FrameAudioQuery,
        style_id: Annotated[StyleId, Query(alias="speaker")],
        core_version: str | SkipJsonSchema[None] = None,
    ) -> FileResponse:
        """
        歌唱音声合成を行います。
        """
        version = core_version or LATEST_VERSION
        engine = tts_engines.get_engine(version)
        try:
            wave = engine.frame_synthsize_wave(query, style_id)
        except TalkSingInvalidInputError as e:
            raise HTTPException(status_code=400, detail=str(e))

        with NamedTemporaryFile(delete=False) as f:
            soundfile.write(
                file=f, data=wave, samplerate=query.outputSamplingRate, format="WAV"
            )

        return FileResponse(
            f.name,
            media_type="audio/wav",
            background=BackgroundTask(try_delete_file, f.name),
        )

    @router.post(
        "/connect_waves",
        response_class=FileResponse,
        responses={
            200: {
                "content": {
                    "audio/wav": {"schema": {"type": "string", "format": "binary"}}
                },
            }
        },
        tags=["その他"],
        summary="base64エンコードされた複数のwavデータを一つに結合する",
    )
    def connect_waves(waves: list[str]) -> FileResponse:
        """
        base64エンコードされたwavデータを一纏めにし、wavファイルで返します。
        """
        try:
            waves_nparray, sampling_rate = connect_base64_waves(waves)
        except ConnectBase64WavesException as err:
            raise HTTPException(status_code=422, detail=str(err))

        with NamedTemporaryFile(delete=False) as f:
            soundfile.write(
                file=f,
                data=waves_nparray,
                samplerate=sampling_rate,
                format="WAV",
            )

        return FileResponse(
            f.name,
            media_type="audio/wav",
            background=BackgroundTask(try_delete_file, f.name),
        )

    @router.post(
        "/validate_kana",
        tags=["その他"],
        summary="テキストがAquesTalk 風記法に従っているか判定する",
        responses={
            400: {
                "description": "テキストが不正です",
                "model": ParseKanaBadRequest,
            }
        },
    )
    async def validate_kana(
        text: Annotated[str, Query(description="判定する対象の文字列")]
    ) -> bool:
        """
        テキストがAquesTalk 風記法に従っているかどうかを判定します。
        従っていない場合はエラーが返ります。
        """
        try:
            parse_kana(text)
            return True
        except ParseKanaError as err:
            raise HTTPException(
                status_code=400,
                detail=ParseKanaBadRequest(err).model_dump(),
            )

    @router.post("/initialize_speaker", status_code=204, tags=["その他"])
    def initialize_speaker(
        style_id: Annotated[StyleId, Query(alias="speaker")],
        skip_reinit: Annotated[
            bool,
            Query(
                description="既に初期化済みのスタイルの再初期化をスキップするかどうか"
            ),
        ] = False,
        core_version: str | SkipJsonSchema[None] = None,
    ) -> None:
        """
        指定されたスタイルを初期化します。
        実行しなくても他のAPIは使用できますが、初回実行時に時間がかかることがあります。
        """
        version = core_version or LATEST_VERSION
        engine = tts_engines.get_engine(version)
        engine.initialize_synthesis(style_id, skip_reinit=skip_reinit)

    @router.get("/is_initialized_speaker", tags=["その他"])
    def is_initialized_speaker(
        style_id: Annotated[StyleId, Query(alias="speaker")],
        core_version: str | SkipJsonSchema[None] = None,
    ) -> bool:
        """
        指定されたスタイルが初期化されているかどうかを返します。
        """
        version = core_version or LATEST_VERSION
        engine = tts_engines.get_engine(version)
        return engine.is_synthesis_initialized(style_id)

    @router.get("/supported_devices", tags=["その他"])
    def supported_devices(
        core_version: str | SkipJsonSchema[None] = None,
    ) -> SupportedDevicesInfo:
        """対応デバイスの一覧を取得します。"""
        version = core_version or LATEST_VERSION
        supported_devices = tts_engines.get_engine(version).supported_devices
        if supported_devices is None:
            raise HTTPException(status_code=422, detail="非対応の機能です。")
        return SupportedDevicesInfo.generate_from(supported_devices)

    return router
