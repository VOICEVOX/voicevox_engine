import os
import sys
from ctypes import (
    CDLL,
    POINTER,
    LibraryLoader,
    c_bool,
    c_char_p,
    c_float,
    c_int,
    c_long,
)
from pathlib import Path

import numpy as np


def load_model_lib(use_gpu: bool, model_type: str, model_lib_dir: Path):
    if model_type == "libtorch":
        if sys.platform == "win32":
            if use_gpu:
                model_libs = ["c10.dll", "torch.dll", "torch_cuda.dll"]
            else:
                model_libs = ["c10.dll", "torch.dll", "torch_cpu.dll"]
        elif sys.platform == "linux":
            if use_gpu:
                model_libs = ["libc10.so", "libtorch.so", "libtorch_cuda.so"]
            else:
                model_libs = ["libc10.so", "libtorch.so", "libtorch_cuda.so"]
        elif sys.platform == "darwin":
            model_libs = ["libc10.dylib", "libtorch.dylib", "libtorch_cpu.dylib"]
        else:
            raise RuntimeError("不明なOSです")
    elif model_type == "onnxruntime":
        if sys.platform == "win32":
            model_libs = ["onnxruntime.dll"]
        elif sys.platform == "linux":
            model_libs = ["libonnxruntime.so"]
        elif sys.platform == "darwin":
            model_libs = ["libonnxruntime.dylib"]
    else:
        raise RuntimeError("不明なmodel_typeです")

    for lib_name in model_libs:
        LibraryLoader(CDLL(str((model_lib_dir / lib_name).resolve(strict=True))))


class CoreWrapper:
    def __init__(
        self,
        use_gpu: bool,
        voicelib_dir: Path,
        model_lib_dir: Path,
        model_type: str,
    ) -> None:
        load_model_lib(use_gpu, model_type, model_lib_dir)
        if model_type == "libtorch":
            if sys.platform == "win32":
                if use_gpu:
                    self.core = CDLL(
                        str((voicelib_dir / "core.dll").resolve(strict=True))
                    )
                else:
                    try:
                        self.core = CDLL(
                            str((voicelib_dir / "core_cpu.dll").resolve(strict=True))
                        )
                    except FileNotFoundError:
                        self.core = CDLL(
                            str((voicelib_dir / "core.dll").resolve(strict=True))
                        )
            elif sys.platform == "linux":
                if use_gpu:
                    self.core = CDLL(
                        str((voicelib_dir / "libcore.so").resolve(strict=True))
                    )
                else:
                    try:
                        self.core = CDLL(
                            str((voicelib_dir / "libcore_cpu.so").resolve(strict=True))
                        )
                    except FileNotFoundError:
                        self.core = CDLL(
                            str((voicelib_dir / "libcore.so").resolve(strict=True))
                        )
            elif sys.platform == "darwin":
                try:
                    self.core = CDLL(
                        str((voicelib_dir / "libcore_cpu.dylib").resolve(strict=True))
                    )
                except FileNotFoundError:
                    self.core = CDLL(
                        str((voicelib_dir / "libcore.dylib").resolve(strict=True))
                    )
            else:
                raise RuntimeError("不明なOSです")
        elif model_type == "onnxruntime":
            if sys.platform == "win32":
                try:
                    self.core = CDLL(
                        str(
                            (voicelib_dir / "core_gpu_x64_nvidia.dll").resolve(
                                strict=True
                            )
                        )
                    )
                except FileNotFoundError:
                    self.core = CDLL(
                        str((voicelib_dir / "core_cpu_x64.dll").resolve(strict=True))
                    )
            elif sys.platform == "linux":
                try:
                    self.core = CDLL(
                        str(
                            (voicelib_dir / "libcore_gpu_x64_nvidia.so").resolve(
                                strict=True
                            )
                        )
                    )
                except FileNotFoundError:
                    self.core = CDLL(
                        str((voicelib_dir / "libcore_cpu_x64.so").resolve(strict=True))
                    )
            elif sys.platform == "darwin":
                self.core = CDLL(
                    str((voicelib_dir / "libcore_cpu_x64.dylib").resolve(strict=True))
                )

        self.core.initialize.restype = c_bool
        self.core.metas.restype = c_char_p
        self.core.yukarin_s_forward.restype = c_bool
        self.core.yukarin_sa_forward.restype = c_bool
        self.core.decode_forward.restype = c_bool
        self.core.last_error_message.restype = c_char_p

        self.exist_suppoted_devices = False
        self.exist_finalize = False
        if model_type == "onnxruntime":
            self.core.supported_devices.restype = c_char_p
            self.core.finalize.restype = None
            self.exist_suppoted_devices = True
            self.exist_finalize = True

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
        os.chdir(voicelib_dir)
        try:
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
    ):
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
