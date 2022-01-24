import os
import sys
from ctypes import CDLL, POINTER, c_bool, c_char_p, c_float, c_int, c_long
from ctypes.util import find_library
from pathlib import Path
from typing import List, Optional

import numpy as np


def load_runtime_lib(runtime_dirs: List[Path]):
    if sys.platform == "win32":
        lib_file_names = ["torch_cpu.dll", "torch_cuda.dll", "onnxruntime.dll"]
        lib_names = ["torch_cpu", "torch_cuda", "onnxruntime"]
    elif sys.platform == "linux":
        lib_file_names = ["libtorch.so", "libonnxruntime.so"]
        lib_names = ["torch", "onnxruntime"]
    elif sys.platform == "darwin":
        lib_file_names = ["libonnxruntime.dylib"]
        lib_names = ["onnxruntime"]
    else:
        raise RuntimeError("不明なOSです")
    for lib_path in runtime_dirs:
        for file_name in lib_file_names:
            try:
                CDLL(str((lib_path / file_name).resolve(strict=True)))
            except OSError:
                pass
    for lib_name in lib_names:
        try:
            CDLL(find_library(lib_name))
        except (OSError, TypeError):
            pass


def check_core_type(core_dir: Path) -> Optional[str]:
    if sys.platform == "win32":
        if (core_dir / "core.dll").is_file() or (core_dir / "core_cpu.dll").is_file():
            return "libtorch"
        elif (core_dir / "core_gpu_x64_nvidia.dll").is_file() or (
            core_dir / "core_cpu_x64.dll"
        ).is_file():
            return "onnxruntime"
    elif sys.platform == "linux":
        if (core_dir / "libcore.so").is_file() or (
            core_dir / "libcore_cpu.so"
        ).is_file():
            return "libtorch"
        elif (core_dir / "libcore_gpu_x64_nvidia.so").is_file() or (
            core_dir / "libcore_cpu_x64.so"
        ).is_file():
            return "onnxruntime"
    elif sys.platform == "darwin":
        if (core_dir / "libcore_cpu_x64.dylib").is_file():
            return "onnxruntime"
    return None


def load_core(core_dir: Path, use_gpu: bool) -> CDLL:
    model_type = check_core_type(core_dir)
    if model_type is None:
        raise RuntimeError("コアが見つかりません")
    if sys.platform == "win32":
        if model_type == "libtorch":
            if use_gpu:
                try:
                    return CDLL(str((core_dir / "core.dll").resolve(strict=True)))
                except OSError:
                    pass
            try:
                return CDLL(str((core_dir / "core_cpu.dll").resolve(strict=True)))
            except OSError:
                return CDLL(str((core_dir / "core.dll").resolve(strict=True)))
        elif model_type == "onnxruntime":
            try:
                return CDLL(
                    str((core_dir / "core_gpu_x64_nvidia.dll").resolve(strict=True))
                )
            except OSError:
                return CDLL(str((core_dir / "core_cpu_x64.dll").resolve(strict=True)))
    elif sys.platform == "linux":
        if model_type == "libtorch":
            if use_gpu:
                try:
                    return CDLL(str((core_dir / "libcore.so").resolve(strict=True)))
                except OSError:
                    pass
            try:
                return CDLL(str((core_dir / "libcore_cpu.so").resolve(strict=True)))
            except OSError:
                return CDLL(str((core_dir / "libcore.so").resolve(strict=True)))
        elif model_type == "onnxruntime":
            try:
                return CDLL(
                    str((core_dir / "libcore_gpu_x64_nvidia.so").resolve(strict=True))
                )
            except OSError:
                return CDLL(str((core_dir / "libcore_cpu_x64.so").resolve(strict=True)))
    elif sys.platform == "darwin":
        if model_type == "onnxruntime":
            try:
                return CDLL(
                    str((core_dir / "libcore_cpu_x64.dylib").resolve(strict=True))
                )
            except OSError:
                pass
    raise RuntimeError("コアの読み込みに失敗しました")


class CoreWrapper:
    def __init__(self, use_gpu: bool, core_dir: Path, cpu_num_threads: int = 0) -> None:
        model_type = check_core_type(core_dir)
        self.core = load_core(core_dir, use_gpu)
        assert model_type is not None

        self.core.initialize.restype = c_bool
        self.core.metas.restype = c_char_p
        self.core.yukarin_s_forward.restype = c_bool
        self.core.yukarin_sa_forward.restype = c_bool
        self.core.decode_forward.restype = c_bool
        self.core.last_error_message.restype = c_char_p

        self.exist_suppoted_devices = False
        self.exist_finalize = False
        exist_cpu_num_threads = False
        if model_type == "onnxruntime":
            self.core.supported_devices.restype = c_char_p
            self.core.finalize.restype = None
            self.exist_suppoted_devices = True
            self.exist_finalize = True
            exist_cpu_num_threads = True

        self.core.yukarin_s_forward.argtypes = (
            c_int,
            POINTER(c_long),
            POINTER(c_long),
            POINTER(c_float),
        )
        self.core.yukarin_sa_forward.argtypes = (
            c_int,
            POINTER(c_long),
            POINTER(c_long),
            POINTER(c_long),
            POINTER(c_long),
            POINTER(c_long),
            POINTER(c_long),
            POINTER(c_long),
            POINTER(c_float),
        )
        self.core.decode_forward.argtypes = (
            c_int,
            c_int,
            POINTER(c_float),
            POINTER(c_float),
            POINTER(c_long),
            POINTER(c_float),
        )

        cwd = os.getcwd()
        os.chdir(core_dir)
        try:
            if exist_cpu_num_threads:
                if not self.core.initialize(".", use_gpu, cpu_num_threads):
                    raise Exception(self.core.last_error_message().decode("utf-8"))
            else:
                if not self.core.initialize(".", use_gpu):
                    raise Exception(self.core.last_error_message().decode("utf-8"))
        finally:
            os.chdir(cwd)

    def metas(self) -> str:
        return self.core.metas().decode("utf-8")

    def yukarin_s_forward(
        self,
        length: int,
        phoneme_list: np.ndarray,
        speaker_id: np.ndarray,
    ) -> np.ndarray:
        output = np.zeros((length,), dtype=np.float32)
        success = self.core.yukarin_s_forward(
            c_int(length),
            phoneme_list.ctypes.data_as(POINTER(c_long)),
            speaker_id.ctypes.data_as(POINTER(c_long)),
            output.ctypes.data_as(POINTER(c_float)),
        )
        if not success:
            raise Exception(self.core.last_error_message().decode("utf-8"))
        return output

    def yukarin_sa_forward(
        self,
        length: int,
        vowel_phoneme_list: np.ndarray,
        consonant_phoneme_list: np.ndarray,
        start_accent_list: np.ndarray,
        end_accent_list: np.ndarray,
        start_accent_phrase_list: np.ndarray,
        end_accent_phrase_list: np.ndarray,
        speaker_id: np.ndarray,
    ) -> np.ndarray:
        output = np.empty(
            (
                len(speaker_id),
                length,
            ),
            dtype=np.float32,
        )
        success = self.core.yukarin_sa_forward(
            c_int(length),
            vowel_phoneme_list.ctypes.data_as(POINTER(c_long)),
            consonant_phoneme_list.ctypes.data_as(POINTER(c_long)),
            start_accent_list.ctypes.data_as(POINTER(c_long)),
            end_accent_list.ctypes.data_as(POINTER(c_long)),
            start_accent_phrase_list.ctypes.data_as(POINTER(c_long)),
            end_accent_phrase_list.ctypes.data_as(POINTER(c_long)),
            speaker_id.ctypes.data_as(POINTER(c_long)),
            output.ctypes.data_as(POINTER(c_float)),
        )
        if not success:
            raise Exception(self.core.last_error_message().decode("utf-8"))
        return output

    def decode_forward(
        self,
        length: int,
        phoneme_size: int,
        f0: np.ndarray,
        phoneme: np.ndarray,
        speaker_id: np.ndarray,
    ) -> np.ndarray:
        output = np.empty((length * 256,), dtype=np.float32)
        success = self.core.decode_forward(
            c_int(length),
            c_int(phoneme_size),
            f0.ctypes.data_as(POINTER(c_float)),
            phoneme.ctypes.data_as(POINTER(c_float)),
            speaker_id.ctypes.data_as(POINTER(c_long)),
            output.ctypes.data_as(POINTER(c_float)),
        )
        if not success:
            raise Exception(self.core.last_error_message().decode("utf-8"))
        return output

    def supported_devices(self) -> str:
        if self.exist_suppoted_devices:
            return self.core.supported_devices().decode("utf-8")
        raise NameError

    def finalize(self) -> None:
        if self.exist_finalize:
            self.core.finalize()
            return
        raise NameError
