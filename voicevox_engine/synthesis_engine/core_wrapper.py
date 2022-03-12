import os
import platform
from ctypes import CDLL, POINTER, c_bool, c_char_p, c_float, c_int, c_long
from ctypes.util import find_library
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import numpy as np


def load_runtime_lib(runtime_dirs: List[Path]):
    if platform.system() == "Windows":
        # DirectML.dllはonnxruntimeと互換性のないWindows標準搭載のものを優先して読み込むことがあるため、明示的に読み込む
        # (参考: https://github.com/microsoft/onnxruntime/issues/3360, https://tadaoyamaoka.hatenablog.com/entry/2020/06/07/113616)
        lib_file_names = [
            "torch_cpu.dll",
            "torch_cuda.dll",
            "DirectML.dll",
            "onnxruntime.dll",
        ]
        lib_names = ["torch_cpu", "torch_cuda", "onnxruntime"]
    elif platform.system() == "Linux":
        lib_file_names = ["libtorch.so", "libonnxruntime.so"]
        lib_names = ["torch", "onnxruntime"]
    elif platform.system() == "Darwin":
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


@dataclass(frozen=True)
class CoreInfo:
    name: str
    platform: str
    arch: str
    core_type: str
    is_cuda_core: bool
    is_directml_core: bool


CORE_INFOS = [
    # Windows
    CoreInfo(
        name="core.dll",
        platform="Windows",
        arch="x64",
        core_type="libtorch",
        is_cuda_core=True,
        is_directml_core=False,
    ),
    CoreInfo(
        name="core_cpu.dll",
        platform="Windows",
        arch="x64",
        core_type="libtorch",
        is_cuda_core=False,
        is_directml_core=False,
    ),
    CoreInfo(
        name="core_gpu_x64_nvidia.dll",
        platform="Windows",
        arch="x64",
        core_type="onnxruntime",
        is_cuda_core=True,
        is_directml_core=False,
    ),
    CoreInfo(
        name="core_gpu_x64_directml.dll",
        platform="Windows",
        arch="x64",
        core_type="onnxruntime",
        is_cuda_core=False,
        is_directml_core=True,
    ),
    CoreInfo(
        name="core_cpu_x64.dll",
        platform="Windows",
        arch="x64",
        core_type="onnxruntime",
        is_cuda_core=False,
        is_directml_core=False,
    ),
    CoreInfo(
        name="core_cpu_x86.dll",
        platform="Windows",
        arch="x86",
        core_type="onnxruntime",
        is_cuda_core=False,
        is_directml_core=False,
    ),
    CoreInfo(
        name="core_gpu_x86_directml.dll",
        platform="Windows",
        arch="x86",
        core_type="onnxruntime",
        is_cuda_core=False,
        is_directml_core=True,
    ),
    CoreInfo(
        name="core_cpu_arm.dll",
        platform="Windows",
        arch="armv7l",
        core_type="onnxruntime",
        is_cuda_core=False,
        is_directml_core=False,
    ),
    CoreInfo(
        name="core_gpu_arm_directml.dll",
        platform="Windows",
        arch="armv7l",
        core_type="onnxruntime",
        is_cuda_core=False,
        is_directml_core=True,
    ),
    CoreInfo(
        name="core_cpu_arm64.dll",
        platform="Windows",
        arch="aarch64",
        core_type="onnxruntime",
        is_cuda_core=False,
        is_directml_core=False,
    ),
    CoreInfo(
        name="core_gpu_arm64_directml.dll",
        platform="Windows",
        arch="aarch64",
        core_type="onnxruntime",
        is_cuda_core=False,
        is_directml_core=True,
    ),
    # Linux
    CoreInfo(
        name="libcore.so",
        platform="Linux",
        arch="x64",
        core_type="libtorch",
        is_cuda_core=True,
        is_directml_core=False,
    ),
    CoreInfo(
        name="libcore_cpu.so",
        platform="Linux",
        arch="x64",
        core_type="libtorch",
        is_cuda_core=False,
        is_directml_core=False,
    ),
    CoreInfo(
        name="libcore_gpu_x64_nvidia.so",
        platform="Linux",
        arch="x64",
        core_type="onnxruntime",
        is_cuda_core=True,
        is_directml_core=False,
    ),
    CoreInfo(
        name="libcore_cpu_x64.so",
        platform="Linux",
        arch="x64",
        core_type="onnxruntime",
        is_cuda_core=False,
        is_directml_core=False,
    ),
    CoreInfo(
        name="libcore_cpu_armhf.so",
        platform="Linux",
        arch="armv7l",
        core_type="onnxruntime",
        is_cuda_core=False,
        is_directml_core=False,
    ),
    CoreInfo(
        name="libcore_cpu_arm64.so",
        platform="Linux",
        arch="aarch64",
        core_type="onnxruntime",
        is_cuda_core=False,
        is_directml_core=False,
    ),
    # macOS
    CoreInfo(
        name="libcore_cpu_universal2.dylib",
        platform="Darwin",
        arch="universal",
        core_type="onnxruntime",
        is_cuda_core=False,
        is_directml_core=False,
    ),
]


def get_arch_name() -> Optional[str]:
    """
    platform.machine() が特定のアーキテクチャ上で複数パターンの文字列を返し得るので、
    一意な文字列に変換する
    サポート外のアーキテクチャである場合、None を返す
    """
    machine = platform.machine()
    if machine == "x86_64" or machine == "x64" or machine == "AMD64":
        return "x64"
    elif machine == "i386" or machine == "x86":
        return "x86"
    elif machine in ["armv7l", "aarch64"]:
        return machine
    else:
        return None


def get_core_name(
    arch_name: str,
    platform_name: str,
    model_type: str,
    is_cuda_core: bool,
    is_directml_core: bool,
) -> Optional[str]:
    if platform_name == "Darwin":
        if (not is_cuda_core and not is_directml_core) and (
            arch_name == "x64" or arch_name == "aarch64"
        ):
            arch_name = "universal"
        else:
            return None
    for core_info in CORE_INFOS:
        if (
            core_info.platform == platform_name
            and core_info.arch == arch_name
            and core_info.core_type == model_type
            and core_info.is_cuda_core == is_cuda_core
            and core_info.is_directml_core == is_directml_core
        ):
            return core_info.name
    return None


def get_suitable_core_name(
    model_type: str, is_cuda_core: bool, is_directml_core: bool
) -> Optional[str]:
    arch_name = get_arch_name()
    if arch_name is None:
        return None
    platform_name = platform.system()
    return get_core_name(
        arch_name, platform_name, model_type, is_cuda_core, is_directml_core
    )


def check_core_type(core_dir: Path) -> Optional[str]:
    # libtorch版はDirectML未対応なので、ここでは`is_directml_core=True`は入れない
    libtorch_core_names = [
        get_suitable_core_name("libtorch", is_cuda_core=True, is_directml_core=False),
        get_suitable_core_name("libtorch", is_cuda_core=False, is_directml_core=False),
    ]
    onnxruntime_core_names = [
        get_suitable_core_name(
            "onnxruntime", is_cuda_core=True, is_directml_core=False
        ),
        get_suitable_core_name(
            "onnxruntime", is_cuda_core=False, is_directml_core=True
        ),
        get_suitable_core_name(
            "onnxruntime", is_cuda_core=False, is_directml_core=False
        ),
    ]
    if any([(core_dir / name).is_file() for name in libtorch_core_names if name]):
        return "libtorch"
    elif any([(core_dir / name).is_file() for name in onnxruntime_core_names if name]):
        return "onnxruntime"
    else:
        return None


def load_core(core_dir: Path, use_gpu: bool) -> CDLL:
    model_type = check_core_type(core_dir)
    if model_type is None:
        raise RuntimeError("コアが見つかりません")
    if use_gpu or model_type == "onnxruntime":
        core_name = get_suitable_core_name(
            model_type, is_cuda_core=True, is_directml_core=False
        )
        if core_name:
            try:
                return CDLL(str((core_dir / core_name).resolve(strict=True)))
            except OSError:
                pass
        core_name = get_suitable_core_name(
            model_type, is_cuda_core=False, is_directml_core=True
        )
        if core_name:
            try:
                return CDLL(str((core_dir / core_name).resolve(strict=True)))
            except OSError:
                pass
    core_name = get_suitable_core_name(
        model_type, is_cuda_core=False, is_directml_core=False
    )
    if core_name:
        try:
            return CDLL(str((core_dir / core_name).resolve(strict=True)))
        except OSError as err:
            if model_type == "libtorch":
                core_name = get_suitable_core_name(
                    model_type, is_cuda_core=True, is_directml_core=False
                )
                if core_name:
                    try:
                        return CDLL(str((core_dir / core_name).resolve(strict=True)))
                    except OSError as err_:
                        err = err_
            raise RuntimeError(f"コアの読み込みに失敗しました：{err}")
    else:
        raise RuntimeError(f"このコンピュータのアーキテクチャ {platform.machine()} で利用可能なコアがありません")


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
