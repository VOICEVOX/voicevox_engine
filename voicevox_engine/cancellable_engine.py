"""キャンセル可能な音声合成"""

import asyncio
import queue
import sys
from multiprocessing import Pipe, Process

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
    """
    音声合成のキャンセル機能に関するクラス
    初期化後は、synthesis関数で音声合成できる
    （オリジナルと比べ引数が増えているので注意）

    パラメータ use_gpu, voicelib_dirs, voicevox_dir,
    runtime_dirs, cpu_num_threads, enable_mock は、 core_initializer を参照

    Attributes
    ----------
    watch_con_list: list[tuple[Request, Process]]
        Requestは接続の監視に使用され、Processは通信切断時のプロセスキルに使用される
        クライアントから接続があるとlistにtupleが追加される
        接続が切断、もしくは音声合成が終了すると削除される
    procs_and_cons: queue.Queue[tuple[Process, ConnectionType]]
        音声合成の準備が終わっているプロセスのList
        （音声合成中のプロセスは入っていない）
    """

    def __init__(
        self,
        init_processes: int,
        use_gpu: bool,
        voicelib_dirs: list[Path] | None,
        voicevox_dir: Path | None,
        runtime_dirs: list[Path] | None,
        cpu_num_threads: int | None,
        enable_mock: bool,
    ) -> None:
        """
        変数の初期化を行う
        また、init_processesの数だけプロセスを起動し、procs_and_consに格納する
        """

        self.use_gpu = use_gpu
        self.voicelib_dirs = voicelib_dirs
        self.voicevox_dir = voicevox_dir
        self.runtime_dirs = runtime_dirs
        self.cpu_num_threads = cpu_num_threads
        self.enable_mock = enable_mock

        self.watch_con_list: list[tuple[Request, Process]] = []

        procs_and_cons: queue.Queue[tuple[Process, ConnectionType]] = queue.Queue()
        for _ in range(init_processes):
            procs_and_cons.put(self.start_new_proc())
        self.procs_and_cons = procs_and_cons

    def start_new_proc(
        self,
    ) -> tuple[Process, ConnectionType]:
        """
        新しく開始したプロセスを返す関数

        Returns
        -------
        ret_proc: Process
            新規のプロセス
        sub_proc_con1: ConnectionType
            ret_procのプロセスと通信するためのPipe
        """
        sub_proc_con1, sub_proc_con2 = Pipe(True)
        ret_proc = Process(
            target=start_synthesis_subprocess,
            kwargs={
                "use_gpu": self.use_gpu,
                "voicelib_dirs": self.voicelib_dirs,
                "voicevox_dir": self.voicevox_dir,
                "runtime_dirs": self.runtime_dirs,
                "cpu_num_threads": self.cpu_num_threads,
                "enable_mock": self.enable_mock,
                "sub_proc_con": sub_proc_con2,
            },
            daemon=True,
        )
        ret_proc.start()
        return ret_proc, sub_proc_con1

    def finalize_con(
        self,
        req: Request,
        proc: Process,
        sub_proc_con: ConnectionType | None,
    ) -> None:
        """
        接続が切断された時の処理を行う関数
        watch_con_listからの削除、プロセスの後処理を行う
        プロセスが生きている場合はそのままprocs_and_consに加える
        死んでいる場合は新しく生成したものをprocs_and_consに加える

        Parameters
        ----------
        req: fastapi.Request
            接続確立時に受け取ったものをそのまま渡せばよい
            https://fastapi.tiangolo.com/advanced/using-request-directly/
        proc: Process
            音声合成を行っていたプロセス
        sub_proc_con: ConnectionType, optional
            音声合成を行っていたプロセスとのPipe
            指定されていない場合、プロセスは再利用されず終了される
        """
        try:
            self.watch_con_list.remove((req, proc))
        except ValueError:
            pass
        try:
            if not proc.is_alive() or sub_proc_con is None:
                proc.close()
                raise ValueError
            # プロセスが死んでいない場合は再利用する
            self.procs_and_cons.put((proc, sub_proc_con))
        except ValueError:
            # プロセスが死んでいるので新しく作り直す
            self.procs_and_cons.put(self.start_new_proc())

    def _synthesis_impl(
        self,
        query: AudioQuery,
        style_id: StyleId,
        request: Request,
        version: str | LatestVersion,
    ) -> str:
        """
        音声合成を行う関数
        通常エンジンの引数に比べ、requestが必要になっている
        また、返り値がファイル名になっている

        Parameters
        ----------
        query: AudioQuery
        style_id: StyleId
        request: fastapi.Request
            接続確立時に受け取ったものをそのまま渡せばよい
            https://fastapi.tiangolo.com/advanced/using-request-directly/
        version

        Returns
        -------
        f_name: str
            生成された音声ファイルの名前
        """
        proc, sub_proc_con1 = self.procs_and_cons.get()
        self.watch_con_list.append((request, proc))
        try:
            sub_proc_con1.send((query, style_id, version))
            f_name = sub_proc_con1.recv()
            if isinstance(f_name, str):
                audio_file_name = f_name
            else:
                # ここには来ないはず
                raise CancellableEngineInternalError("不正な値が生成されました")
        except EOFError:
            raise CancellableEngineInternalError("既にサブプロセスは終了されています")
        except Exception:
            self.finalize_con(request, proc, sub_proc_con1)
            raise

        self.finalize_con(request, proc, sub_proc_con1)
        return audio_file_name

    async def catch_disconnection(self) -> None:
        """
        接続監視を行うコルーチン
        """
        while True:
            await asyncio.sleep(1)
            for con in self.watch_con_list:
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
                        self.finalize_con(req, proc, None)


def start_synthesis_subprocess(
    use_gpu: bool,
    voicelib_dirs: list[Path] | None,
    voicevox_dir: Path | None,
    runtime_dirs: list[Path] | None,
    cpu_num_threads: int | None,
    enable_mock: bool,
    sub_proc_con: ConnectionType,
) -> None:
    """
    音声合成を行うサブプロセスで行うための関数
    pickle化の関係でグローバルに書いている

    引数 use_gpu, voicelib_dirs, voicevox_dir,
    runtime_dirs, cpu_num_threads, enable_mock は、 core_initializer を参照

    Parameters
    ----------
    sub_proc_con: ConnectionType
        メインプロセスと通信するためのPipe
    """

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
            query, style_id, version = sub_proc_con.recv()
            try:
                _engine = tts_engines.get_engine(version)
            except Exception:
                # バージョンが見つからないエラー
                sub_proc_con.send("")
                continue
            # FIXME: enable_interrogative_upspeakフラグをWebAPIから受け渡してくる
            wave = _engine.synthesize_wave(
                query, style_id, enable_interrogative_upspeak=False
            )
            with NamedTemporaryFile(delete=False) as f:
                soundfile.write(
                    file=f, data=wave, samplerate=query.outputSamplingRate, format="WAV"
                )
            sub_proc_con.send(f.name)
        except Exception:
            sub_proc_con.close()
            raise
