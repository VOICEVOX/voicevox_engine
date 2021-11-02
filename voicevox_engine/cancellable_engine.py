import argparse
import asyncio
import multiprocessing
from typing import List, Optional, Tuple

import numpy as np
from fastapi import HTTPException, Request

from voicevox_engine.model import AudioQuery, Speaker
from voicevox_engine.synthesis_engine import make_synthesis_engine


class CancellableEngine:
    """
    音声合成のキャンセル機能に関するクラス
    初期化後は、synthesis関数で音声合成できる
    （オリジナルと比べ引数が増えているので注意）

    Attributes
    ----------
    client_connections: List[Tuple[Request, multiprocessing.Process]]
        Requestは接続の監視に使用され、multiprocessing.Processは通信切断時のプロセスキルに使用される
        クライアントから接続があるとListにTupleが追加される
        接続が切断、もしくは音声合成が終了すると削除される
    procs_and_cons: List[Tuple[multiprocessing.Process, multiprocessing.connection.Connection]]
        音声合成の準備が終わっているプロセスのList
        （音声合成中のプロセスは入っていない）

    Warnings
    --------
    音声合成の結果のオブジェクトが32MiBを超えるとValueErrorが発生する可能性がある
    https://docs.python.org/ja/3/library/multiprocessing.html
    """

    def __init__(self, args) -> None:
        """
        変数の初期化を行う
        また、args.init_processesの数だけプロセスを起動し、procs_and_consに格納する
        """
        self.args = args
        if not self.args.enable_cancellable_synthesis:
            raise HTTPException(
                status_code=404,
                detail="実験的機能はデフォルトで無効になっています。使用するには引数を指定してください。",
            )

        self.client_connections: List[Tuple[Request, multiprocessing.Process]] = []
        self.procs_and_cons: List[
            Tuple[multiprocessing.Process, multiprocessing.connection.Connection]
        ] = []
        for _ in range(self.args.init_processes):
            new_proc, sub_proc_con1 = self.start_new_proc()
            self.procs_and_cons.append((new_proc, sub_proc_con1))

    def start_new_proc(
        self,
    ) -> Tuple[multiprocessing.Process, multiprocessing.connection.Connection]:
        """
        新しく開始したプロセスを返す関数

        Returns
        -------
        ret_proc: multiprocessing.Process
            新規のプロセス
        sub_proc_con1: multiprocessing.connection.Connection
            ret_procのプロセスと通信するためのPipe
        """
        sub_proc_con1, sub_proc_con2 = multiprocessing.Pipe(True)
        ret_proc = multiprocessing.Process(
            target=synthesis_subprocess,
            kwargs={"args": self.args, "sub_proc_con": sub_proc_con2},
            daemon=True,
        )
        ret_proc.start()
        return ret_proc, sub_proc_con1

    def get_proc(
        self, req: Request
    ) -> Tuple[multiprocessing.Process, multiprocessing.connection.Connection]:
        """
        音声合成可能なプロセスを返す関数
        準備済みのプロセスがあればそれを、無ければstart_new_procの結果を返す

        Parameters
        ----------
        req: fastapi.Request
            接続確立時に受け取ったものをそのまま渡せばよい
            https://fastapi.tiangolo.com/advanced/using-request-directly/

        Returns
        -------
        ret_proc: multiprocessing.Process
            音声合成可能なプロセス
        sub_proc_con1: multiprocessing.connection.Connection
            ret_procのプロセスと通信するためのPipe
        """
        try:
            ret_proc, sub_proc_con1 = self.procs_and_cons.pop(0)
        except IndexError:
            ret_proc, sub_proc_con1 = self.start_new_proc()
        self.client_connections.append((req, ret_proc))
        return ret_proc, sub_proc_con1

    def remove_con(
        self,
        req: Request,
        proc: multiprocessing.Process,
        sub_proc_con: Optional[multiprocessing.connection.Connection],
    ) -> None:
        """
        接続が切断された時の処理を行う関数
        client_connectionsからの削除、プロセスの後処理を行う
        args.max_wait_processesより、procs_and_consの長さが短い場合はプロセスをそこに加える
        同じか長い場合は停止される

        Parameters
        ----------
        req: fastapi.Request
            接続確立時に受け取ったものをそのまま渡せばよい
            https://fastapi.tiangolo.com/advanced/using-request-directly/
        proc: multiprocessing.Process
            音声合成を行っていたプロセス
        sub_proc_con: multiprocessing.connection.Connection, optional
            音声合成を行っていたプロセスとのPipe
            指定されていない場合、プロセスは再利用されず終了される
        """
        try:
            self.client_connections.remove((req, proc))
        except ValueError:
            pass
        try:
            if not proc.is_alive() or sub_proc_con is None:
                proc.close()
                raise ValueError
        except ValueError:
            if len(self.procs_and_cons) < self.args.max_wait_processes:
                new_proc, new_sub_proc_con1 = self.start_new_proc()
                self.procs_and_cons.append((new_proc, new_sub_proc_con1))
            return
        if len(self.procs_and_cons) < self.args.max_wait_processes:
            self.procs_and_cons.append((proc, sub_proc_con))
        else:
            proc.terminate()
            proc.join()
            proc.close()
        return

    def synthesis(
        self, query: AudioQuery, speaker_id: Speaker, request: Request
    ) -> np.ndarray:
        """
        音声合成を行う関数
        通常エンジンの引数に比べ、requestが必要になっている

        Parameters
        ----------
        query: AudioQuery
        speaker_id: Speaker
        request: fastapi.Request
            接続確立時に受け取ったものをそのまま渡せばよい
            https://fastapi.tiangolo.com/advanced/using-request-directly/

        Returns
        -------
        wave: np.ndarray
            生成された音声データ
        """
        proc, sub_proc_con1 = self.get_proc(request)
        try:
            sub_proc_con1.send((query, speaker_id))
            wave = sub_proc_con1.recv()
        except EOFError:
            raise HTTPException(status_code=422, detail="既にサブプロセスは終了されています")

        self.remove_con(request, proc, sub_proc_con1)
        return wave

    async def catch_disconnection(self):
        """
        接続監視を行うコルーチン
        """
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


def synthesis_subprocess(
    args: argparse.Namespace, sub_proc_con: multiprocessing.connection.Connection
):
    """
    音声合成を行うサブプロセスで行うための関数
    pickle化の関係でグローバルに書いている

    Parameters
    ----------
    args: argparse.Namespace
        起動時に作られたものをそのまま渡す
    sub_proc_con: multiprocessing.connection.Connection
        メインプロセスと通信するためのPipe
    """

    engine = make_synthesis_engine(
        use_gpu=args.use_gpu,
        voicevox_dir=args.voicevox_dir,
        voicelib_dir=args.voicelib_dir,
    )
    while True:
        try:
            query, speaker_id = sub_proc_con.recv()
            wave = engine.synthesis(query=query, speaker_id=speaker_id)
            sub_proc_con.send(wave)
        except Exception:
            sub_proc_con.close()
            raise
