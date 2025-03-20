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
    """マルチプロセスでの合成・キャンセル可能な合成をサポートする音声合成エンジン"""

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
        """
        init_processesの数だけプロセスを起動し、procs_and_consに格納する。その他の引数はcore_initializerを参照。
        """

        self.use_gpu = use_gpu
        self.voicelib_dirs = voicelib_dirs
        self.voicevox_dir = voicevox_dir
        self.runtime_dirs = runtime_dirs
        self.cpu_num_threads = cpu_num_threads
        self.enable_mock = enable_mock

        # Requestは切断の監視に使用され、Processは切断時のプロセスキルに使用される
        # クライアントから接続があるとlistにtupleが追加される
        # 切断、もしくは音声合成が終了すると削除される
        self._watching_reqs_and_procs: list[tuple[Request, Process]] = []

        # 待機しているサブプロセスと、それと通信できるコネクション
        procs_and_cons: Queue[tuple[Process, ConnectionType]] = Queue()
        for _ in range(init_processes):
            procs_and_cons.put(self._start_new_process())
        self._waiting_procs_and_cons = procs_and_cons

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
                "sub_proc_con": connection_inner,
            },
            daemon=True,
        )
        new_process.start()
        return new_process, connection_outer

    def _finalize_con(
        self, req: Request, proc: Process, sub_proc_con: ConnectionType | None
    ) -> None:
        """
        プロセスの後処理をおこなう。

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
        # 監視対象リストから除外する
        try:
            self._watching_reqs_and_procs.remove((req, proc))
        except ValueError:
            pass

        # 待機中リストへ再登録する
        try:
            if not proc.is_alive() or sub_proc_con is None:
                proc.close()
                raise ValueError
            # プロセスが死んでいない場合は再利用する
            self._waiting_procs_and_cons.put((proc, sub_proc_con))
        except ValueError:
            # プロセスが死んでいるので新しく作り直す
            self._waiting_procs_and_cons.put(self._start_new_process())

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
        # 待機中のプロセスとそのコネクションを取得し、監視対象リストへ登録する
        synth_process, synth_connection = self._waiting_procs_and_cons.get()
        self._watching_reqs_and_procs.append((request, synth_process))

        # サブプロセスへ入力を渡して音声を合成する
        try:
            synth_connection.send((query, style_id, version))
            audio_file_name = synth_connection.recv()

            if not isinstance(audio_file_name, str):
                # ここには来ないはず
                raise CancellableEngineInternalError("不正な値が生成されました")
        except EOFError:
            raise CancellableEngineInternalError("既にサブプロセスは終了されています")
        except Exception:
            self._finalize_con(request, synth_process, synth_connection)
            raise
        self._finalize_con(request, synth_process, synth_connection)

        return audio_file_name

    async def catch_disconnection(self) -> None:
        """
        接続監視を行うコルーチン
        """
        while True:
            await asyncio.sleep(1)
            for con in self._watching_reqs_and_procs:
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
    コネクションへの入力に応答して音声合成をおこなうループを実行する

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

    # 「キュー入力待機 → キュー入力受付 → 音声合成 → ファイル名送信」をループする
    while True:
        try:
            # キューへ入力が来たらそれを受け取る
            query, style_id, version = connection.recv()

            # 音声を合成しファイルへ保存する
            try:
                _engine = tts_engines.get_engine(version)
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
