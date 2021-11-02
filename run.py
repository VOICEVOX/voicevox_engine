import argparse
import asyncio
import base64
import io
import multiprocessing
import os
import sys
import zipfile
from functools import lru_cache
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryFile
from typing import List, Optional, Tuple

import numpy as np
import pyworld as pw
import soundfile
import uvicorn
import yaml
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from starlette.responses import FileResponse

from voicevox_engine.full_context_label import extract_full_context_label
from voicevox_engine.kana_parser import create_kana, parse_kana
from voicevox_engine.model import (
    AccentPhrase,
    AudioQuery,
    Mora,
    ParseKanaBadRequest,
    ParseKanaError,
    Preset,
    Speaker,
)
from voicevox_engine.mora_list import openjtalk_mora2text
from voicevox_engine.synthesis_engine import SynthesisEngine


class PresetLoader:
    def __init__(self):
        self.presets = []
        self.last_modified_time = 0
        self.PRESET_FILE_NAME = "presets.yaml"

    def load_presets(self):
        """
        プリセットのYAMLファイルを読み込む

        Returns
        -------
        ret: tuple[Preset, str]
            プリセットとエラー文のタプル
        """
        _presets = []

        # 設定ファイルのタイムスタンプを確認
        try:
            _last_modified_time = os.path.getmtime(self.PRESET_FILE_NAME)
            if _last_modified_time == self.last_modified_time:
                return self.presets, ""
        except OSError:
            return None, "プリセットの設定ファイルが見つかりません"

        try:
            with open(self.PRESET_FILE_NAME, encoding="utf-8") as f:
                obj = yaml.safe_load(f)
                if obj is None:
                    raise FileNotFoundError
        except FileNotFoundError:
            return None, "プリセットの設定ファイルが空の内容です"

        for preset in obj:
            try:
                _presets.append(Preset(**preset))
            except ValidationError:
                return None, "プリセットの設定ファイルにミスがあります"

        # idが一意か確認
        if len([preset.id for preset in _presets]) != len(
            {preset.id for preset in _presets}
        ):
            return None, "プリセットのidに重複があります"

        self.presets = _presets
        self.last_modified_time = _last_modified_time
        return self.presets, ""


class ProcessManager:
    def __init__(self) -> None:
        self.client_connections: List[Tuple[Request, multiprocessing.Process]] = []
        self.procs_and_cons: List[
            Tuple[multiprocessing.Process, multiprocessing.connection.Connection]
        ] = []
        for _ in range(2):
            new_proc, sub_proc_con1 = self.start_new_proc()
            self.procs_and_cons.append((new_proc, sub_proc_con1))

    def start_new_proc(self) -> multiprocessing.Process:
        sub_proc_con1, sub_proc_con2 = multiprocessing.Pipe(True)
        ret_proc = multiprocessing.Process(
            target=wrap_synthesis, kwargs={"args": args, "sub_proc_con": sub_proc_con2}, daemon=True
        )
        ret_proc.start()
        return ret_proc, sub_proc_con1

    def get_proc(
        self, req: Request
    ) -> Tuple[multiprocessing.Process, multiprocessing.connection.Connection]:
        try:
            new_proc, sub_proc_con1 = self.procs_and_cons.pop(0)
        except IndexError:
            new_proc, sub_proc_con1 = self.start_new_proc()
        self.client_connections.append((req, new_proc))
        return new_proc, sub_proc_con1

    def remove_con(
        self,
        req: Request,
        proc: multiprocessing.Process,
        sub_proc_con: Optional[multiprocessing.connection.Connection],
    ) -> None:
        try:
            self.client_connections.remove((req, proc))
        except ValueError:
            pass
        try:
            if not proc.is_alive() or sub_proc_con is None:
                proc.close()
                raise ValueError
        except ValueError:
            if len(self.procs_and_cons) <= 5:
                new_proc, new_sub_proc_con1 = self.start_new_proc()
                self.procs_and_cons.append((new_proc, new_sub_proc_con1))
            return
        if len(self.procs_and_cons) <= 4:
            self.procs_and_cons.append((proc, sub_proc_con))
        else:
            proc.terminate()
            proc.join()
            proc.close()
        return

    async def catch_disconnection(self):
        lock = asyncio.Lock()
        while True:
            await asyncio.sleep(1)
            async with lock:
                for con in self.client_connections:
                    req, proc = con
                    if await req.is_disconnected():
                        try:
                            if proc.is_alive():
                                proc.terminate()
                                proc.join()
                            proc.close()
                        except ValueError:
                            pass
                        finally:
                            self.remove_con(req, proc, None)


def make_synthesis_engine(
    use_gpu: bool,
    voicevox_dir: Optional[Path] = None,
    voicelib_dir: Optional[Path] = None,
) -> SynthesisEngine:
    """
    音声ライブラリをロードして、音声合成エンジンを生成

    Parameters
    ----------
    use_gpu: bool
        音声ライブラリに GPU を使わせるか否か
    voicevox_dir: Path, optional, default=None
        音声ライブラリの Python モジュールがあるディレクトリ
        None のとき、Python 標準のモジュール検索パスのどれかにあるとする
    voicelib_dir: Path, optional, default=None
        音声ライブラリ自体があるディレクトリ
        None のとき、音声ライブラリの Python モジュールと同じディレクトリにあるとする
    """

    # Python モジュール検索パスへ追加
    if voicevox_dir is not None:
        print("Notice: --voicevox_dir is " + voicevox_dir.as_posix(), file=sys.stderr)
        if voicevox_dir.exists():
            sys.path.insert(0, str(voicevox_dir))

    has_voicevox_core = True
    try:
        import core
    except ImportError:
        import traceback

        from voicevox_engine.dev import core

        has_voicevox_core = False

        # 音声ライブラリの Python モジュールをロードできなかった
        traceback.print_exc()
        print(
            "Notice: mock-library will be used. Try re-run with valid --voicevox_dir",  # noqa
            file=sys.stderr,
        )

    if voicelib_dir is None:
        if voicevox_dir is not None:
            voicelib_dir = voicevox_dir
        else:
            voicelib_dir = Path(__file__).parent  # core.__file__だとnuitkaビルド後にエラー

    core.initialize(voicelib_dir.as_posix() + "/", use_gpu)

    if has_voicevox_core:
        return SynthesisEngine(
            yukarin_s_forwarder=core.yukarin_s_forward,
            yukarin_sa_forwarder=core.yukarin_sa_forward,
            decode_forwarder=core.decode_forward,
            speakers=core.metas(),
        )

    from voicevox_engine.dev.synthesis_engine import (
        SynthesisEngine as mock_synthesis_engine,
    )

    # モックで置き換える
    return mock_synthesis_engine(speakers=core.metas())


def mora_to_text(mora: str):
    if mora[-1:] in ["A", "I", "U", "E", "O"]:
        # 無声化母音を小文字に
        mora = mora[:-1] + mora[-1].lower()
    if mora in openjtalk_mora2text:
        return openjtalk_mora2text[mora]
    else:
        return mora


def wrap_synthesis(
    args: argparse.Namespace, sub_proc_con: multiprocessing.connection.Connection
):
    engine = make_synthesis_engine(
        use_gpu=args.use_gpu,
        voicevox_dir=args.voicevox_dir,
        voicelib_dir=args.voicelib_dir,
    )
    while True:
        try:
            query, speaker_id = sub_proc_con.recv()
            wave = engine.synthesis(query=query, speaker_id=speaker_id)
            with NamedTemporaryFile(delete=False) as f:
                soundfile.write(
                    file=f, data=wave, samplerate=query.outputSamplingRate, format="WAV"
                )
            sub_proc_con.send(f.name)
        except Exception:
            sub_proc_con.close()
            raise


def generate_app(engine: SynthesisEngine) -> FastAPI:
    root_dir = Path(__file__).parent

    default_sampling_rate = engine.default_sampling_rate

    app = FastAPI(
        title="VOICEVOX ENGINE",
        description="VOICEVOXの音声合成エンジンです。",
        version=(root_dir / "VERSION.txt").read_text().strip(),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    preset_loader = PresetLoader()

    def replace_mora_data(
        accent_phrases: List[AccentPhrase], speaker_id: int
    ) -> List[AccentPhrase]:
        return engine.replace_mora_pitch(
            accent_phrases=engine.replace_phoneme_length(
                accent_phrases=accent_phrases,
                speaker_id=speaker_id,
            ),
            speaker_id=speaker_id,
        )

    def create_accent_phrases(text: str, speaker_id: int) -> List[AccentPhrase]:
        if len(text.strip()) == 0:
            return []

        utterance = extract_full_context_label(text)
        if len(utterance.breath_groups) == 0:
            return []

        return replace_mora_data(
            accent_phrases=[
                AccentPhrase(
                    moras=[
                        Mora(
                            text=mora_to_text(
                                "".join([p.phoneme for p in mora.phonemes])
                            ),
                            consonant=(
                                mora.consonant.phoneme
                                if mora.consonant is not None
                                else None
                            ),
                            consonant_length=0 if mora.consonant is not None else None,
                            vowel=mora.vowel.phoneme,
                            vowel_length=0,
                            pitch=0,
                        )
                        for mora in accent_phrase.moras
                    ],
                    accent=accent_phrase.accent,
                    pause_mora=(
                        Mora(
                            text="、",
                            consonant=None,
                            consonant_length=None,
                            vowel="pau",
                            vowel_length=0,
                            pitch=0,
                        )
                        if (
                            i_accent_phrase == len(breath_group.accent_phrases) - 1
                            and i_breath_group != len(utterance.breath_groups) - 1
                        )
                        else None
                    ),
                )
                for i_breath_group, breath_group in enumerate(utterance.breath_groups)
                for i_accent_phrase, accent_phrase in enumerate(
                    breath_group.accent_phrases
                )
            ],
            speaker_id=speaker_id,
        )

    def decode_base64_waves(waves: List[str]):
        if len(waves) == 0:
            raise HTTPException(status_code=422, detail="wavファイルが含まれていません")

        waves_nparray = []
        for i in range(len(waves)):
            try:
                wav_bin = base64.standard_b64decode(waves[i])
            except ValueError:
                raise HTTPException(status_code=422, detail="base64デコードに失敗しました")
            try:
                _data, _sampling_rate = soundfile.read(io.BytesIO(wav_bin))
            except Exception:
                raise HTTPException(status_code=422, detail="wavファイルを読み込めませんでした")
            if i == 0:
                sampling_rate = _sampling_rate
                channels = _data.ndim
            else:
                if sampling_rate != _sampling_rate:
                    raise HTTPException(status_code=422, detail="ファイル間でサンプリングレートが異なります")
                if channels != _data.ndim:
                    if channels == 1:
                        _data = _data.T[0]
                    else:
                        _data = np.array([_data, _data]).T
            waves_nparray.append(_data)

        return waves_nparray, sampling_rate

    @lru_cache(maxsize=4)
    def synthesis_world_params(
        query: AudioQuery, base_speaker: int, target_speaker: int
    ):
        base_wave = engine.synthesis(query=query, speaker_id=base_speaker).astype(
            "float"
        )
        target_wave = engine.synthesis(query=query, speaker_id=target_speaker).astype(
            "float"
        )

        frame_period = 1.0
        fs = query.outputSamplingRate
        base_f0, base_time_axis = pw.harvest(base_wave, fs, frame_period=frame_period)
        base_spectrogram = pw.cheaptrick(base_wave, base_f0, base_time_axis, fs)
        base_aperiodicity = pw.d4c(base_wave, base_f0, base_time_axis, fs)

        target_f0, morph_time_axis = pw.harvest(
            target_wave, fs, frame_period=frame_period
        )
        target_spectrogram = pw.cheaptrick(target_wave, target_f0, morph_time_axis, fs)
        target_spectrogram.resize(base_spectrogram.shape)

        return (
            fs,
            frame_period,
            base_f0,
            base_aperiodicity,
            base_spectrogram,
            target_spectrogram,
        )

    @app.on_event("startup")
    async def start_catch_disconnection():
        loop = asyncio.get_event_loop()
        _ = loop.create_task(proc_manager.catch_disconnection())

    @app.post(
        "/audio_query",
        response_model=AudioQuery,
        tags=["クエリ作成"],
        summary="音声合成用のクエリを作成する",
    )
    def audio_query(text: str, speaker: int):
        """
        クエリの初期値を得ます。ここで得られたクエリはそのまま音声合成に利用できます。各値の意味は`Schemas`を参照してください。
        """
        accent_phrases = create_accent_phrases(text, speaker_id=speaker)
        return AudioQuery(
            accent_phrases=accent_phrases,
            speedScale=1,
            pitchScale=0,
            intonationScale=1,
            volumeScale=1,
            prePhonemeLength=0.1,
            postPhonemeLength=0.1,
            outputSamplingRate=default_sampling_rate,
            outputStereo=False,
            kana=create_kana(accent_phrases),
        )

    @app.post(
        "/audio_query_from_preset",
        response_model=AudioQuery,
        tags=["クエリ作成"],
        summary="音声合成用のクエリをプリセットを用いて作成する",
    )
    def audio_query_from_preset(text: str, preset_id: int):
        """
        クエリの初期値を得ます。ここで得られたクエリはそのまま音声合成に利用できます。各値の意味は`Schemas`を参照してください。
        """
        presets, err_detail = preset_loader.load_presets()
        if err_detail:
            raise HTTPException(status_code=422, detail=err_detail)
        for preset in presets:
            if preset.id == preset_id:
                selected_preset = preset
                break
        else:
            raise HTTPException(status_code=422, detail="該当するプリセットIDが見つかりません")

        accent_phrases = create_accent_phrases(
            text, speaker_id=selected_preset.style_id
        )
        return AudioQuery(
            accent_phrases=accent_phrases,
            speedScale=selected_preset.speedScale,
            pitchScale=selected_preset.pitchScale,
            intonationScale=selected_preset.intonationScale,
            volumeScale=selected_preset.volumeScale,
            prePhonemeLength=selected_preset.prePhonemeLength,
            postPhonemeLength=selected_preset.postPhonemeLength,
            outputSamplingRate=default_sampling_rate,
            outputStereo=False,
            kana=create_kana(accent_phrases),
        )

    @app.post(
        "/accent_phrases",
        response_model=List[AccentPhrase],
        tags=["クエリ編集"],
        summary="テキストからアクセント句を得る",
        responses={
            400: {
                "description": "読み仮名のパースに失敗",
                "model": ParseKanaBadRequest,
            }
        },
    )
    def accent_phrases(text: str, speaker: int, is_kana: bool = False):
        """
        テキストからアクセント句を得ます。
        is_kanaが`true`のとき、テキストは次のようなAquesTalkライクな記法に従う読み仮名として処理されます。デフォルトは`false`です。
        * 全てのカナはカタカナで記述される
        * アクセント句は`/`または`、`で区切る。`、`で区切った場合に限り無音区間が挿入される。
        * カナの手前に`_`を入れるとそのカナは無声化される
        * アクセント位置を`'`で指定する。全てのアクセント句にはアクセント位置を1つ指定する必要がある。
        """
        if is_kana:
            try:
                accent_phrases = parse_kana(text)
            except ParseKanaError as err:
                raise HTTPException(
                    status_code=400,
                    detail=ParseKanaBadRequest(err).dict(),
                )
            return replace_mora_data(accent_phrases=accent_phrases, speaker_id=speaker)
        else:
            return create_accent_phrases(text, speaker_id=speaker)

    @app.post(
        "/mora_data",
        response_model=List[AccentPhrase],
        tags=["クエリ編集"],
        summary="アクセント句から音高・音素長を得る",
    )
    def mora_data(accent_phrases: List[AccentPhrase], speaker: int):
        return replace_mora_data(accent_phrases, speaker_id=speaker)

    @app.post(
        "/mora_length",
        response_model=List[AccentPhrase],
        tags=["クエリ編集"],
        summary="アクセント句から音素長を得る",
    )
    def mora_length(accent_phrases: List[AccentPhrase], speaker: int):
        return engine.replace_phoneme_length(
            accent_phrases=accent_phrases, speaker_id=speaker
        )

    @app.post(
        "/mora_pitch",
        response_model=List[AccentPhrase],
        tags=["クエリ編集"],
        summary="アクセント句から音高を得る",
    )
    def mora_pitch(accent_phrases: List[AccentPhrase], speaker: int):
        return engine.replace_mora_pitch(
            accent_phrases=accent_phrases, speaker_id=speaker
        )

    @app.post(
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
    def synthesis(query: AudioQuery, speaker: int):
        wave = engine.synthesis(query=query, speaker_id=speaker)

        with NamedTemporaryFile(delete=False) as f:
            soundfile.write(
                file=f, data=wave, samplerate=query.outputSamplingRate, format="WAV"
            )

        return FileResponse(f.name, media_type="audio/wav")

    @app.post(
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
    def cancellable_synthesis(query: AudioQuery, speaker: int, request: Request):
        proc, sub_proc_con1 = proc_manager.get_proc(request)
        try:
            sub_proc_con1.send((query, speaker))
            f_name = sub_proc_con1.recv()
        except EOFError:
            raise HTTPException(status_code=422, detail="既にサブプロセスは終了されています")

        proc_manager.remove_con(request, proc, sub_proc_con1)
        return FileResponse(f_name, media_type="audio/wav")

    @app.post(
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
    def multi_synthesis(queries: List[AudioQuery], speaker: int):
        sampling_rate = queries[0].outputSamplingRate

        with NamedTemporaryFile(delete=False) as f:

            with zipfile.ZipFile(f, mode="a") as zip_file:

                for i in range(len(queries)):

                    if queries[i].outputSamplingRate != sampling_rate:
                        raise HTTPException(
                            status_code=422, detail="サンプリングレートが異なるクエリがあります"
                        )

                    with TemporaryFile() as wav_file:

                        wave = engine.synthesis(query=queries[i], speaker_id=speaker)
                        soundfile.write(
                            file=wav_file,
                            data=wave,
                            samplerate=sampling_rate,
                            format="WAV",
                        )
                        wav_file.seek(0)
                        zip_file.writestr(f"{str(i+1).zfill(3)}.wav", wav_file.read())

        return FileResponse(f.name, media_type="application/zip")

    @app.post(
        "/synthesis_morphing",
        response_class=FileResponse,
        responses={
            200: {
                "content": {
                    "audio/wav": {"schema": {"type": "string", "format": "binary"}}
                },
            }
        },
        tags=["音声合成"],
        summary="2人の話者でモーフィングした音声を合成する",
    )
    def synthesis_morphing(
        query: AudioQuery,
        base_speaker: int,
        target_speaker: int,
        morph_rate: float,
    ):
        """
        指定された2人の話者で音声を合成、指定した割合でモーフィングした音声を得ます。
        モーフィングの割合は`morph_rate`で指定でき、0.0でベースの話者、1.0でターゲットの話者に近づきます。
        """

        if morph_rate < 0.0 or morph_rate > 1.0:
            raise HTTPException(
                status_code=422, detail="morph_rateは0.0から1.0の範囲で指定してください"
            )

        # WORLDに掛けるため合成はモノラルで行う
        output_stereo = query.outputStereo
        query.outputStereo = False

        (
            fs,
            frame_period,
            base_f0,
            base_aperiodicity,
            base_spectrogram,
            target_spectrogram,
        ) = synthesis_world_params(query, base_speaker, target_speaker)

        morph_spectrogram = (
            base_spectrogram * (1.0 - morph_rate) + target_spectrogram * morph_rate
        )

        y_h = pw.synthesize(
            base_f0, morph_spectrogram, base_aperiodicity, fs, frame_period
        )

        if output_stereo:
            y_h = np.array([y_h, y_h]).T

        with NamedTemporaryFile(delete=False) as f:
            soundfile.write(file=f, data=y_h, samplerate=fs, format="WAV")

        return FileResponse(f.name, media_type="audio/wav")

    @app.post(
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
    def connect_waves(waves: List[str]):
        """
        base64エンコードされたwavデータを一纏めにし、wavファイルで返します。
        """
        waves_nparray, sampling_rate = decode_base64_waves(waves)

        with NamedTemporaryFile(delete=False) as f:
            soundfile.write(
                file=f,
                data=np.concatenate(waves_nparray),
                samplerate=sampling_rate,
                format="WAV",
            )

            return FileResponse(f.name, media_type="audio/wav")

    @app.get("/presets", response_model=List[Preset], tags=["その他"])
    def get_presets():
        """
        エンジンが保持しているプリセットの設定を返します

        Returns
        -------
        presets: List[Preset]
            プリセットのリスト
        """
        presets, err_detail = preset_loader.load_presets()
        if err_detail:
            raise HTTPException(status_code=422, detail=err_detail)
        return presets

    @app.get("/version", tags=["その他"])
    def version() -> str:
        return (root_dir / "VERSION.txt").read_text()

    @app.get("/speakers", response_model=List[Speaker], tags=["その他"])
    def speakers():
        return Response(
            content=engine.speakers,
            media_type="application/json",
        )

    return app


if __name__ == "__main__":
    multiprocessing.freeze_support()
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=50021)
    parser.add_argument("--use_gpu", action="store_true")
    parser.add_argument("--voicevox_dir", type=Path, default=None)
    parser.add_argument("--voicelib_dir", type=Path, default=None)
    args = parser.parse_args()
    proc_manager = ProcessManager()
    uvicorn.run(
        generate_app(
            make_synthesis_engine(
                use_gpu=args.use_gpu,
                voicevox_dir=args.voicevox_dir,
                voicelib_dir=args.voicelib_dir,
            )
        ),
        host=args.host,
        port=args.port,
    )
