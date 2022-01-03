import argparse
import asyncio
import queue
from multiprocessing import Pipe, Process
from multiprocessing.connection import Connection
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List, Optional, Tuple

import soundfile

# FIXME: remove FastAPI dependency
from fastapi import HTTPException, Request

from .model import AudioQuery, Speaker
from .synthesis_engine import make_synthesis_engine


class CancellableEngine:
    """
    音声合成のキャンセル機能に関するクラス
    初期化後は、synthesis関数で音声合成できる
    （オリジナルと比べ引数が増えているので注意）

    Attributes
    ----------
    watch_con_list: List[Tuple[Request, Process]]
        Requestは接続の監視に使用され、Processは通信切断時のプロセスキルに使用される
        クライアントから接続があるとListにTupleが追加される
        接続が切断、もしくは音声合成が終了すると削除される
    procs_and_cons: queue.Queue[Tuple[Process, Connection]]
        音声合成の準備が終わっているプロセスのList
        （音声合成中のプロセスは入っていない）
    """

    def __init__(self, args, voicelib_dir) -> None:
        """
        変数の初期化を行う
        また、args.init_processesの数だけプロセスを起動し、procs_and_consに格納する
        """
        self.args = args
        self.voicelib_dir = voicelib_dir
        if not self.args.enable_cancellable_synthesis:
            raise HTTPException(
                status_code=404,
                detail="実験的機能はデフォルトで無効になっています。使用するには引数を指定してください。",
            )

        self.watch_con_list: List[Tuple[Request, Process]] = []
        self.procs_and_cons: queue.Queue[Tuple[Process, Connection]] = queue.Queue()
        for _ in range(self.args.init_processes):
            self.procs_and_cons.put(self.start_new_proc())

    def start_new_proc(
        self,
    ) -> Tuple[Process, Connection]:
        """
        新しく開始したプロセスを返す関数

        Returns
        -------
        ret_proc: Process
            新規のプロセス
        sub_proc_con1: Connection
            ret_procのプロセスと通信するためのPipe
        """
        sub_proc_con1, sub_proc_con2 = Pipe(True)
        ret_proc = Process(
            target=start_synthesis_subprocess,
            kwargs={
                "args": self.args,
                "voicelib_dir": self.voicelib_dir,
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
        sub_proc_con: Optional[Connection],
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
        sub_proc_con: Connection, optional
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

    def synthesis(
        self, query: AudioQuery, speaker_id: Speaker, request: Request
    ) -> str:
        """
        音声合成を行う関数
        通常エンジンの引数に比べ、requestが必要になっている
        また、返り値がファイル名になっている

        Parameters
        ----------
        query: AudioQuery
        speaker_id: Speaker
        request: fastapi.Request
            接続確立時に受け取ったものをそのまま渡せばよい
            https://fastapi.tiangolo.com/advanced/using-request-directly/

        Returns
        -------
        f_name: str
            生成された音声ファイルの名前
        """
        proc, sub_proc_con1 = self.procs_and_cons.get()
        self.watch_con_list.append((request, proc))
        try:
            sub_proc_con1.send((query, speaker_id))
            f_name = sub_proc_con1.recv()
        except EOFError:
            raise HTTPException(status_code=422, detail="既にサブプロセスは終了されています")
        except Exception:
            self.finalize_con(request, proc, sub_proc_con1)
            raise

        self.finalize_con(request, proc, sub_proc_con1)
        return f_name

    async def catch_disconnection(self):
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
    args: argparse.Namespace, voicelib_dir: Path, sub_proc_con: Connection
):
    """
    音声合成を行うサブプロセスで行うための関数
    pickle化の関係でグローバルに書いている

    Parameters
    ----------
    args: argparse.Namespace
        起動時に作られたものをそのまま渡す
    sub_proc_con: Connection
        メインプロセスと通信するためのPipe
    """

    engine = make_synthesis_engine(
        use_gpu=args.use_gpu,
        voicevox_dir=args.voicevox_dir,
        voicelib_dir=voicelib_dir,
        model_lib_dir=args.model_lib_dir,
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
