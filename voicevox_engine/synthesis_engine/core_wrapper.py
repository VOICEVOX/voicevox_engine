import os
import sys
import numpy as np
from pathlib import Path
from ctypes import cdll, c_bool, c_char_p, c_int, c_long, c_float, POINTER

class CoreWrapper:
    def __init__(self, use_gpu: bool, old_voicelib_dir: Path, libtorch_dir: Path) -> None:
        if sys.platform == "win32":
            os.add_dll_directory(libtorch_dir.resolve())
            os.environ["PATH"] += ";"+str(libtorch_dir.resolve())
            if not use_gpu:
                self.core = cdll.LoadLibrary(str((old_voicelib_dir / "core_cpu.dll").resolve()))
            else:
                self.core = cdll.LoadLibrary(str((old_voicelib_dir / "core.dll").resolve()))
        elif sys.platform == "linux":
            if not use_gpu:
                cdll.LoadLibrary(str((libtorch_dir / "libc10.so").resolve()))
                cdll.LoadLibrary(str((libtorch_dir / "libtorch_cpu.so").resolve()))
                cdll.LoadLibrary(str((libtorch_dir / "libtorch.so").resolve()))
                self.core = cdll.LoadLibrary(str((old_voicelib_dir / "libcore_cpu.so").resolve()))
            else: # not tested
                cdll.LoadLibrary(str((libtorch_dir / "libc10.so").resolve()))
                cdll.LoadLibrary(str((libtorch_dir / "libtorch_cuda.so").resolve()))
                cdll.LoadLibrary(str((libtorch_dir / "libtorch.so").resolve()))
                self.core = cdll.LoadLibrary(str((old_voicelib_dir / "libcore.so").resolve()))
        elif sys.platform == "darwin": # not tested
            cdll.LoadLibrary(str((libtorch_dir / "libc10.dylib").resolve()))
            cdll.LoadLibrary(str((libtorch_dir / "libtorch_cpu.dylib").resolve()))
            cdll.LoadLibrary(str((libtorch_dir / "libtorch.dylib").resolve()))
            self.core = cdll.LoadLibrary(str((old_voicelib_dir / "libcore_cpu.dylib").resolve()))


        self.core.initialize.restype = c_bool
        self.core.metas.restype = c_char_p
        self.core.yukarin_s_forward.restype = c_bool
        self.core.yukarin_sa_forward.restype = c_bool
        self.core.decode_forward.restype = c_bool
        self.core.last_error_message.restype = c_char_p

        self.core.yukarin_s_forward.argtypes = (c_int, POINTER(c_long), POINTER(c_long), POINTER(c_float))
        self.core.yukarin_sa_forward.argtypes = (c_int, POINTER(c_long), POINTER(c_long), POINTER(c_long), POINTER(c_long), POINTER(c_long), POINTER(c_long), POINTER(c_long), POINTER(c_float))
        self.core.decode_forward.argtypes = (c_int, c_int, POINTER(c_float), POINTER(c_float), POINTER(c_long), POINTER(c_float))

        cwd = os.getcwd()
        os.chdir(old_voicelib_dir)
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
        output = np.empty((len(speaker_id), length,), dtype=np.float32)
        success = self.core.yukarin_sa_forward(
            c_int(length),
            vowel_phoneme_list.ctypes.data_as(POINTER(c_long)),
            consonant_phoneme_list.ctypes.data_as(POINTER(c_long)),
            start_accent_list.ctypes.data_as(POINTER(c_long)),
            end_accent_list.ctypes.data_as(POINTER(c_long)),
            start_accent_phrase_list.ctypes.data_as(POINTER(c_long)),
            end_accent_phrase_list.ctypes.data_as(POINTER(c_long)),
            speaker_id.ctypes.data_as(POINTER(c_long)),
            output.ctypes.data_as(POINTER(c_float))
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
        output = np.empty((length*256,), dtype=np.float32)
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
