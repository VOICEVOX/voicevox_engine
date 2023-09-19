import os
import platform
from ctypes import CDLL, POINTER, c_bool, c_char_p, c_float, c_int, c_long
from ctypes.util import find_library
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import List, Optional

import numpy as np


class OldCoreError(Exception):
    """古いコアが使用されている場合に発生するエラー"""


class CoreError(Exception):
    """コア呼び出しで発生したエラー"""


def load_runtime_lib(runtime_dirs: List[Path]):
    if platform.system() == "Windows":
        # DirectML.dllはonnxruntimeと互換性のないWindows標準搭載のものを優先して読み込むことがあるため、明示的に読み込む
        # 参考 1. https://github.com/microsoft/onnxruntime/issues/3360
        # 参考 2. https://tadaoyamaoka.hatenablog.com/entry/2020/06/07/113616
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


class GPUType(Enum):
    # NONEはCPUしか対応していないことを示す
    NONE = auto()
    CUDA = auto()
    DIRECT_ML = auto()


@dataclass(frozen=True)
class CoreInfo:
    name: str
    platform: str
    arch: str
    core_type: str
    gpu_type: GPUType


# version 0.12 より前のコアの情報
CORE_INFOS = [
    # Windows
    CoreInfo(
        name="core.dll",
        platform="Windows",
        arch="x64",
        core_type="libtorch",
        gpu_type=GPUType.CUDA,
    ),
    CoreInfo(
        name="core_cpu.dll",
        platform="Windows",
        arch="x64",
        core_type="libtorch",
        gpu_type=GPUType.NONE,
    ),
    CoreInfo(
        name="core_gpu_x64_nvidia.dll",
        platform="Windows",
        arch="x64",
        core_type="onnxruntime",
        gpu_type=GPUType.CUDA,
    ),
    CoreInfo(
        name="core_gpu_x64_directml.dll",
        platform="Windows",
        arch="x64",
        core_type="onnxruntime",
        gpu_type=GPUType.DIRECT_ML,
    ),
    CoreInfo(
        name="core_cpu_x64.dll",
        platform="Windows",
        arch="x64",
        core_type="onnxruntime",
        gpu_type=GPUType.NONE,
    ),
    CoreInfo(
        name="core_cpu_x86.dll",
        platform="Windows",
        arch="x86",
        core_type="onnxruntime",
        gpu_type=GPUType.NONE,
    ),
    CoreInfo(
        name="core_gpu_x86_directml.dll",
        platform="Windows",
        arch="x86",
        core_type="onnxruntime",
        gpu_type=GPUType.DIRECT_ML,
    ),
    CoreInfo(
        name="core_cpu_arm.dll",
        platform="Windows",
        arch="armv7l",
        core_type="onnxruntime",
        gpu_type=GPUType.NONE,
    ),
    CoreInfo(
        name="core_gpu_arm_directml.dll",
        platform="Windows",
        arch="armv7l",
        core_type="onnxruntime",
        gpu_type=GPUType.DIRECT_ML,
    ),
    CoreInfo(
        name="core_cpu_arm64.dll",
        platform="Windows",
        arch="aarch64",
        core_type="onnxruntime",
        gpu_type=GPUType.NONE,
    ),
    CoreInfo(
        name="core_gpu_arm64_directml.dll",
        platform="Windows",
        arch="aarch64",
        core_type="onnxruntime",
        gpu_type=GPUType.DIRECT_ML,
    ),
    # Linux
    CoreInfo(
        name="libcore.so",
        platform="Linux",
        arch="x64",
        core_type="libtorch",
        gpu_type=GPUType.CUDA,
    ),
    CoreInfo(
        name="libcore_cpu.so",
        platform="Linux",
        arch="x64",
        core_type="libtorch",
        gpu_type=GPUType.NONE,
    ),
    CoreInfo(
        name="libcore_gpu_x64_nvidia.so",
        platform="Linux",
        arch="x64",
        core_type="onnxruntime",
        gpu_type=GPUType.CUDA,
    ),
    CoreInfo(
        name="libcore_cpu_x64.so",
        platform="Linux",
        arch="x64",
        core_type="onnxruntime",
        gpu_type=GPUType.NONE,
    ),
    CoreInfo(
        name="libcore_cpu_armhf.so",
        platform="Linux",
        arch="armv7l",
        core_type="onnxruntime",
        gpu_type=GPUType.NONE,
    ),
    CoreInfo(
        name="libcore_cpu_arm64.so",
        platform="Linux",
        arch="aarch64",
        core_type="onnxruntime",
        gpu_type=GPUType.NONE,
    ),
    # macOS
    CoreInfo(
        name="libcore_cpu_universal2.dylib",
        platform="Darwin",
        arch="universal",
        core_type="onnxruntime",
        gpu_type=GPUType.NONE,
    ),
]


# version 0.12 以降のコアの名前の辞書
# - version 0.12, 0.13 のコアの名前: core
# - version 0.14 からのコアの名前: voicevox_core
CORENAME_DICT = {
    "Windows": ("voicevox_core.dll", "core.dll"),
    "Linux": ("libvoicevox_core.so", "libcore.so"),
    "Darwin": ("libvoicevox_core.dylib", "libcore.dylib"),
}


def find_version_0_12_core_or_later(core_dir: Path) -> Optional[str]:
    """
    core_dir で指定したディレクトリにあるコアライブラリが Version 0.12 以降である場合、
    見つかった共有ライブラリの名前を返す。

    Version 0.12 以降と判定する条件は、

    - core_dir に metas.json が存在しない
    - コアライブラリの名前が CORENAME_DICT の定義に従っている

    の両方が真のときである。
    cf. https://github.com/VOICEVOX/voicevox_engine/issues/385
    """
    if (core_dir / "metas.json").exists():
        return None

    for core_name in CORENAME_DICT[platform.system()]:
        if (core_dir / core_name).is_file():
            return core_name

    return None


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
    elif machine == "arm64":
        return "aarch64"
    elif machine in ["armv7l", "aarch64"]:
        return machine
    else:
        return None


def get_core_name(
    arch_name: str,
    platform_name: str,
    model_type: str,
    gpu_type: GPUType,
) -> Optional[str]:
    if platform_name == "Darwin":
        if gpu_type == GPUType.NONE and (arch_name == "x64" or arch_name == "aarch64"):
            arch_name = "universal"
        else:
            return None
    for core_info in CORE_INFOS:
        if (
            core_info.platform == platform_name
            and core_info.arch == arch_name
            and core_info.core_type == model_type
            and core_info.gpu_type == gpu_type
        ):
            return core_info.name
    return None


def get_suitable_core_name(
    model_type: str,
    gpu_type: GPUType,
) -> Optional[str]:
    arch_name = get_arch_name()
    if arch_name is None:
        return None
    platform_name = platform.system()
    return get_core_name(arch_name, platform_name, model_type, gpu_type)


def check_core_type(core_dir: Path) -> Optional[str]:
    # libtorch版はDirectML未対応なので、ここでは`gpu_type=GPUType.DIRECT_ML`は入れない
    libtorch_core_names = [
        get_suitable_core_name("libtorch", gpu_type=GPUType.CUDA),
        get_suitable_core_name("libtorch", gpu_type=GPUType.NONE),
    ]
    onnxruntime_core_names = [
        get_suitable_core_name("onnxruntime", gpu_type=GPUType.CUDA),
        get_suitable_core_name("onnxruntime", gpu_type=GPUType.DIRECT_ML),
        get_suitable_core_name("onnxruntime", gpu_type=GPUType.NONE),
    ]
    if any([(core_dir / name).is_file() for name in libtorch_core_names if name]):
        return "libtorch"
    elif any([(core_dir / name).is_file() for name in onnxruntime_core_names if name]):
        return "onnxruntime"
    else:
        return None


def load_core(core_dir: Path, use_gpu: bool) -> CDLL:
    core_name = find_version_0_12_core_or_later(core_dir)
    if core_name:
        try:
            # NOTE: CDLL クラスのコンストラクタの引数 name には文字列を渡す必要がある。
            #       Windows 環境では PathLike オブジェクトを引数として渡すと初期化に失敗する。
            return CDLL(str((core_dir / core_name).resolve(strict=True)))
        except OSError as err:
            raise RuntimeError(f"コアの読み込みに失敗しました：{err}")

    model_type = check_core_type(core_dir)
    if model_type is None:
        raise RuntimeError("コアが見つかりません")
    if use_gpu or model_type == "onnxruntime":
        core_name = get_suitable_core_name(model_type, gpu_type=GPUType.CUDA)
        if core_name:
            try:
                return CDLL(str((core_dir / core_name).resolve(strict=True)))
            except OSError:
                pass
        core_name = get_suitable_core_name(model_type, gpu_type=GPUType.DIRECT_ML)
        if core_name:
            try:
                return CDLL(str((core_dir / core_name).resolve(strict=True)))
            except OSError:
                pass
    core_name = get_suitable_core_name(model_type, gpu_type=GPUType.NONE)
    if core_name:
        try:
            return CDLL(str((core_dir / core_name).resolve(strict=True)))
        except OSError as err:
            if model_type == "libtorch":
                core_name = get_suitable_core_name(model_type, gpu_type=GPUType.CUDA)
                if core_name:
                    try:
                        return CDLL(str((core_dir / core_name).resolve(strict=True)))
                    except OSError as err_:
                        err = err_
            raise RuntimeError(f"コアの読み込みに失敗しました：{err}")
    else:
        raise RuntimeError(f"このコンピュータのアーキテクチャ {platform.machine()} で利用可能なコアがありません")


class CoreWrapper:
    def __init__(
        self,
        use_gpu: bool,
        core_dir: Path,
        cpu_num_threads: int = 0,
        load_all_models: bool = False,
    ) -> None:

        self.core = load_core(core_dir, use_gpu)

        self.core.initialize.restype = c_bool
        self.core.metas.restype = c_char_p
        self.core.yukarin_s_forward.restype = c_bool
        self.core.yukarin_sa_forward.restype = c_bool
        self.core.decode_forward.restype = c_bool
        self.core.last_error_message.restype = c_char_p

        self.exist_supported_devices = False
        self.exist_finalize = False
        exist_cpu_num_threads = False
        self.exist_load_model = False
        self.exist_is_model_loaded = False

        is_version_0_12_core_or_later = (
            find_version_0_12_core_or_later(core_dir) is not None
        )
        if is_version_0_12_core_or_later:
            model_type = "onnxruntime"
            self.exist_load_model = True
            self.exist_is_model_loaded = True
            self.core.load_model.argtypes = (c_long,)
            self.core.load_model.restype = c_bool
            self.core.is_model_loaded.argtypes = (c_long,)
            self.core.is_model_loaded.restype = c_bool
        else:
            model_type = check_core_type(core_dir)
        assert model_type is not None

        if model_type == "onnxruntime":
            self.core.supported_devices.restype = c_char_p
            self.core.finalize.restype = None
            self.exist_supported_devices = True
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
            if is_version_0_12_core_or_later:
                self.assert_core_success(
                    self.core.initialize(use_gpu, cpu_num_threads, load_all_models)
                )
            elif exist_cpu_num_threads:
                self.assert_core_success(
                    self.core.initialize(".", use_gpu, cpu_num_threads)
                )
            else:
                self.assert_core_success(self.core.initialize(".", use_gpu))
        finally:
            os.chdir(cwd)

    def metas(self) -> str:
        return self.core.metas().decode("utf-8")

    def yukarin_s_forward(
        self,
        length: int,
        phoneme_list: np.ndarray,
        style_id: np.ndarray,
    ) -> np.ndarray:
        output = np.zeros((length,), dtype=np.float32)
        self.assert_core_success(
            self.core.yukarin_s_forward(
                c_int(length),
                phoneme_list.ctypes.data_as(POINTER(c_long)),
                style_id.ctypes.data_as(POINTER(c_long)),
                output.ctypes.data_as(POINTER(c_float)),
            )
        )
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
        style_id: np.ndarray,
    ) -> np.ndarray:
        output = np.empty(
            (
                len(style_id),
                length,
            ),
            dtype=np.float32,
        )
        self.assert_core_success(
            self.core.yukarin_sa_forward(
                c_int(length),
                vowel_phoneme_list.ctypes.data_as(POINTER(c_long)),
                consonant_phoneme_list.ctypes.data_as(POINTER(c_long)),
                start_accent_list.ctypes.data_as(POINTER(c_long)),
                end_accent_list.ctypes.data_as(POINTER(c_long)),
                start_accent_phrase_list.ctypes.data_as(POINTER(c_long)),
                end_accent_phrase_list.ctypes.data_as(POINTER(c_long)),
                style_id.ctypes.data_as(POINTER(c_long)),
                output.ctypes.data_as(POINTER(c_float)),
            )
        )
        return output

    def decode_forward(
        self,
        length: int,
        phoneme_size: int,
        f0: np.ndarray,
        phoneme: np.ndarray,
        style_id: np.ndarray,
    ) -> np.ndarray:
        output = np.empty((length * 256,), dtype=np.float32)
        self.assert_core_success(
            self.core.decode_forward(
                c_int(length),
                c_int(phoneme_size),
                f0.ctypes.data_as(POINTER(c_float)),
                phoneme.ctypes.data_as(POINTER(c_float)),
                style_id.ctypes.data_as(POINTER(c_long)),
                output.ctypes.data_as(POINTER(c_float)),
            )
        )
        return output

    def supported_devices(self) -> str:
        if self.exist_supported_devices:
            return self.core.supported_devices().decode("utf-8")
        raise OldCoreError

    def finalize(self) -> None:
        if self.exist_finalize:
            self.core.finalize()
            return
        raise OldCoreError

    def load_model(self, style_id: int) -> None:
        if self.exist_load_model:
            self.assert_core_success(self.core.load_model(c_long(style_id)))
        raise OldCoreError

    def is_model_loaded(self, style_id: int) -> bool:
        if self.exist_is_model_loaded:
            return self.core.is_model_loaded(c_long(style_id))
        raise OldCoreError

    def assert_core_success(self, result: bool) -> None:
        if not result:
            raise CoreError(
                self.core.last_error_message().decode("utf-8", "backslashreplace")
            )
