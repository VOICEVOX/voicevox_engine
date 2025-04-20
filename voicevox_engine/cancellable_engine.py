"""キャンセル可能な音声合成"""

import asyncio
import sys
from multiprocessing import Pipe, Process
from queue import Queue

if sys.platform == "win32":
    from multiprocessing.connection import PipeConnection as ConnectionType
else:
    from multiprocessing.connection import Connection as ConnectionType

from pathlib import Path
from tempfile import NamedTemporaryFile

import soundfile
from fastapi import Request

from .core.core_initializer import initialize_cores
from .metas.Metas import StyleId
from .model import AudioQuery
from .tts_pipeline.tts_engine import LatestVersion, make_tts_engines_from_cores


class CancellableEngineInternalError(Exception):
    """キャンセル可能エンジンの内部エラー"""

    pass


class CancellableEngine:
    """キャンセル可能な合成をサポートする音声合成エンジン"""

    def __init__(
        self,
        init_processes: int,
        use_gpu: bool,
        voicelib_dirs: list[Path] | None = None,
        voicevox_dir: Path | None = None,
        runtime_dirs: list[Path] | None = None,
        cpu_num_threads: int | None = None,
        enable_mock: bool = True,
    ) -> None:
        """init_processesの数だけ同時処理できるエンジンを立ち上げる。その他の引数はcore_initializerを参照。"""
        self.use_gpu = use_gpu
        self.voicelib_dirs = voicelib_dirs
        self.voicevox_dir = voicevox_dir
        self.runtime_dirs = runtime_dirs
        self.cpu_num_threads = cpu_num_threads
        self.enable_mock = enable_mock

        # 実行中プール
        # 「実行されているリクエスト」と「そのリクエストを処理しているプロセス」のペアのリスト
        self._actives_pool: list[tuple[Request, Process]] = []

        # 待機中プール
        # 「待機しているプロセス」と「そのプロセスへのコネクション」のペアのキュー
        self._idles_pool: Queue[tuple[Process, ConnectionType]] = Queue()

        # 指定された数のプロセスを起動し待機中プールへ移動する
        for _ in range(init_processes):
            self._idles_pool.put(self._start_new_process())

    def _start_new_process(self) -> tuple[Process, ConnectionType]:
        """音声合成可能な新しいプロセスを開始し、そのプロセスと、プロセスへのコネクションを返す。"""
        connection_outer, connection_inner = Pipe(True)
        new_process = Process(
            target=start_synthesis_subprocess,
            kwargs={
                "use_gpu": self.use_gpu,
                "voicelib_dirs": self.voicelib_dirs,
                "voicevox_dir": self.voicevox_dir,
                "runtime_dirs": self.runtime_dirs,
                "cpu_num_threads": self.cpu_num_threads,
                "enable_mock": self.enable_mock,
                "connection": connection_inner,
            },
            daemon=True,
        )
        new_process.start()
        return new_process, connection_outer

    def _finalize_con(
        self, req: Request, proc: Process, sub_proc_con: ConnectionType | None
    ) -> None:
        """
        プロセスを後処理する

        Parameters
        ----------
        req:
            HTTP 接続状態に関するオブジェクト
        proc:
            音声合成を行っていたプロセス
        sub_proc_con:
            音声合成を行っていたプロセスとのコネクション
            指定されていない場合、プロセスは再利用されず終了される
        """
        # ペアを実行中プールから除外する
        try:
            self._actives_pool.remove((req, proc))
        except ValueError:
            pass

        # ペアを待機中プールへ移動する
        try:
            if not proc.is_alive() or sub_proc_con is None:
                proc.close()
                raise ValueError
            # プロセスが死んでいないので再利用する
            self._idles_pool.put((proc, sub_proc_con))
        except ValueError:
            # プロセスが死んでいるので新しく作り直す
            self._idles_pool.put(self._start_new_process())

    def synthesize_wave(
        self,
        query: AudioQuery,
        style_id: StyleId,
        request: Request,
        version: str | LatestVersion,
    ) -> str:
        """
        サブプロセスで音声合成用のクエリ・スタイルIDから音声を生成し、音声ファイル名を返す。

        Parameters
        ----------
        request:
            HTTP 接続状態に関するオブジェクト
        version:
            合成に用いる TTSEngine のバージョン
        """
        # 待機中プールのペアを実行中プールへ移動する
        synth_process, synth_connection = self._idles_pool.get()
        self._actives_pool.append((request, synth_process))

        # プロセスへ入力を渡して音声を合成する
        try:
            synth_connection.send((query, style_id, version))
            audio_file_name = synth_connection.recv()

            if not isinstance(audio_file_name, str):
                # ここには来ないはず
                raise CancellableEngineInternalError("不正な値が生成されました")
        except EOFError as e:
            raise CancellableEngineInternalError(
                "既にサブプロセスは終了されています"
            ) from e
        except Exception:
            self._finalize_con(request, synth_process, synth_connection)
            raise
        self._finalize_con(request, synth_process, synth_connection)

        return audio_file_name

    async def catch_disconnection(self) -> None:
        """接続監視を行うコルーチン。"""
        while True:
            await asyncio.sleep(1)
            for con in self._actives_pool:
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
                        self._finalize_con(req, proc, None)


# NOTE: pickle化の関係でグローバルに書いている
def start_synthesis_subprocess(
    use_gpu: bool,
    voicelib_dirs: list[Path] | None,
    voicevox_dir: Path | None,
    runtime_dirs: list[Path] | None,
    cpu_num_threads: int | None,
    enable_mock: bool,
    connection: ConnectionType,
) -> None:
    """
    コネクションへの入力に応答して音声合成するループを実行する

    引数 use_gpu, voicelib_dirs, voicevox_dir,
    runtime_dirs, cpu_num_threads, enable_mock は、 core_initializer を参照

    Parameters
    ----------
    connection:
        メインプロセスと通信するためのコネクション
    """
    # 音声合成エンジンを用意する
    core_manager = initialize_cores(
        use_gpu=use_gpu,
        voicelib_dirs=voicelib_dirs,
        voicevox_dir=voicevox_dir,
        runtime_dirs=runtime_dirs,
        cpu_num_threads=cpu_num_threads,
        enable_mock=enable_mock,
    )
    tts_engines = make_tts_engines_from_cores(core_manager)
    assert len(tts_engines.versions()) != 0, "音声合成エンジンがありません。"

    while True:
        try:
            # キューの入力を受け取る
            query, style_id, version = connection.recv()

            # 音声を合成しファイルへ保存する
            try:
                _engine = tts_engines.get_tts_engine(version)
            except Exception:
                # コネクションを介して「バージョンが見つからないエラー」を送信する
                connection.send("")  # `""` をエラーして扱う
                continue
            # FIXME: enable_interrogative_upspeakフラグをWebAPIから受け渡してくる
            wave = _engine.synthesize_wave(
                query, style_id, enable_interrogative_upspeak=False
            )
            with NamedTemporaryFile(delete=False) as f:
                soundfile.write(
                    file=f, data=wave, samplerate=query.outputSamplingRate, format="WAV"
                )

            # コネクションを介してファイル名を送信する
            connection.send(f.name)

        except Exception:
            connection.close()
            raise
