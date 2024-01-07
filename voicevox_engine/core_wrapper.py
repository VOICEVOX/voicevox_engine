import os
import platform
from ctypes import CDLL, POINTER, c_bool, c_char_p, c_float, c_int, c_long
from ctypes.util import find_library
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Literal

import numpy as np
from numpy.typing import NDArray


class OldCoreError(Exception):
    """古いコアが使用されている場合に発生するエラー"""


class CoreError(Exception):
    """コア呼び出しで発生したエラー"""


def load_runtime_lib(runtime_dirs: list[Path]) -> None:
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
class _CoreInfo:
    name: str  # Coreファイル名
    platform: Literal["Windows", "Linux", "Darwin"]  # 対応システム/OS
    arch: Literal["x64", "x86", "armv7l", "aarch64", "universal"]  # 対応アーキテクチャ
    core_type: Literal["libtorch", "onnxruntime"]  # `model_type`
    gpu_type: GPUType  # NONE | CUDA | DIRECT_ML


# version 0.12 より前のコアの情報
_CORE_INFOS = [
    # Windows
    _CoreInfo(
        name="core.dll",
        platform="Windows",
        arch="x64",
        core_type="libtorch",
        gpu_type=GPUType.CUDA,
    ),
    _CoreInfo(
        name="core_cpu.dll",
        platform="Windows",
        arch="x64",
        core_type="libtorch",
        gpu_type=GPUType.NONE,
    ),
    _CoreInfo(
        name="core_gpu_x64_nvidia.dll",
        platform="Windows",
        arch="x64",
        core_type="onnxruntime",
        gpu_type=GPUType.CUDA,
    ),
    _CoreInfo(
        name="core_gpu_x64_directml.dll",
        platform="Windows",
        arch="x64",
        core_type="onnxruntime",
        gpu_type=GPUType.DIRECT_ML,
    ),
    _CoreInfo(
        name="core_cpu_x64.dll",
        platform="Windows",
        arch="x64",
        core_type="onnxruntime",
        gpu_type=GPUType.NONE,
    ),
    _CoreInfo(
        name="core_cpu_x86.dll",
        platform="Windows",
        arch="x86",
        core_type="onnxruntime",
        gpu_type=GPUType.NONE,
    ),
    _CoreInfo(
        name="core_gpu_x86_directml.dll",
        platform="Windows",
        arch="x86",
        core_type="onnxruntime",
        gpu_type=GPUType.DIRECT_ML,
    ),
    _CoreInfo(
        name="core_cpu_arm.dll",
        platform="Windows",
        arch="armv7l",
        core_type="onnxruntime",
        gpu_type=GPUType.NONE,
    ),
    _CoreInfo(
        name="core_gpu_arm_directml.dll",
        platform="Windows",
        arch="armv7l",
        core_type="onnxruntime",
        gpu_type=GPUType.DIRECT_ML,
    ),
    _CoreInfo(
        name="core_cpu_arm64.dll",
        platform="Windows",
        arch="aarch64",
        core_type="onnxruntime",
        gpu_type=GPUType.NONE,
    ),
    _CoreInfo(
        name="core_gpu_arm64_directml.dll",
        platform="Windows",
        arch="aarch64",
        core_type="onnxruntime",
        gpu_type=GPUType.DIRECT_ML,
    ),
    # Linux
    _CoreInfo(
        name="libcore.so",
        platform="Linux",
        arch="x64",
        core_type="libtorch",
        gpu_type=GPUType.CUDA,
    ),
    _CoreInfo(
        name="libcore_cpu.so",
        platform="Linux",
        arch="x64",
        core_type="libtorch",
        gpu_type=GPUType.NONE,
    ),
    _CoreInfo(
        name="libcore_gpu_x64_nvidia.so",
        platform="Linux",
        arch="x64",
        core_type="onnxruntime",
        gpu_type=GPUType.CUDA,
    ),
    _CoreInfo(
        name="libcore_cpu_x64.so",
        platform="Linux",
        arch="x64",
        core_type="onnxruntime",
        gpu_type=GPUType.NONE,
    ),
    _CoreInfo(
        name="libcore_cpu_armhf.so",
        platform="Linux",
        arch="armv7l",
        core_type="onnxruntime",
        gpu_type=GPUType.NONE,
    ),
    _CoreInfo(
        name="libcore_cpu_arm64.so",
        platform="Linux",
        arch="aarch64",
        core_type="onnxruntime",
        gpu_type=GPUType.NONE,
    ),
    # macOS
    _CoreInfo(
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
_CORENAME_DICT = {
    "Windows": ("voicevox_core.dll", "core.dll"),
    "Linux": ("libvoicevox_core.so", "libcore.so"),
    "Darwin": ("libvoicevox_core.dylib", "libcore.dylib"),
}


def _find_version_0_12_core_or_later(core_dir: Path) -> str | None:
    """
    `core_dir`直下に存在する コア Version 0.12 以降の共有ライブラリ名（None: 不在）

    Version 0.12 以降と判定する条件は、

    - core_dir に metas.json が存在しない
    - コアライブラリの名前が CORENAME_DICT の定義に従っている

    の両方が真のときである。
    cf. https://github.com/VOICEVOX/voicevox_engine/issues/385
    """
    if (core_dir / "metas.json").exists():
        return None

    for core_name in _CORENAME_DICT[platform.system()]:
        if (core_dir / core_name).is_file():
            return core_name

    return None


def _get_arch_name() -> Literal["x64", "x86", "aarch64", "armv7l"] | None:
    """
    実行中マシンのアーキテクチャ（None: サポート外アーキテクチャ）
    """
    machine = platform.machine()
    # 特定のアーキテクチャ上で複数パターンの文字列を返し得るので一意に変換
    if machine == "x86_64" or machine == "x64" or machine == "AMD64":
        return "x64"
    elif machine == "i386" or machine == "x86":
        return "x86"
    elif machine == "arm64":
        return "aarch64"
    elif machine == "aarch64":
        return "aarch64"
    elif machine == "armv7l":
        return "armv7l"
    else:
        return None


def _get_core_name(
    arch_name: Literal["x64", "x86", "aarch64", "armv7l", "universal"],
    platform_name: str,
    model_type: Literal["libtorch", "onnxruntime"],
    gpu_type: GPUType,
) -> str | None:
    """
    設定値を満たすCoreの名前（None: サポート外）。
    macOSの場合はarch_nameをuniversalにする。
    Parameters
    ----------
    arch_name : Literal["x64", "x86", "aarch64", "armv7l", "universal"]
        実行中マシンのアーキテクチャ
    platform_name : str
        実行中マシンのシステム名
    model_type: Literal["libtorch", "onnxruntime"]
    gpu_type: GPUType
    Returns
    -------
    name : str | None
        Core名（None: サポート外）
    """
    if platform_name == "Darwin":
        if gpu_type == GPUType.NONE and (arch_name == "x64" or arch_name == "aarch64"):
            arch_name = "universal"
        else:
            return None
    for core_info in _CORE_INFOS:
        if (
            core_info.platform == platform_name
            and core_info.arch == arch_name
            and core_info.core_type == model_type
            and core_info.gpu_type == gpu_type
        ):
            return core_info.name
    return None


def _get_suitable_core_name(
    model_type: Literal["libtorch", "onnxruntime"],
    gpu_type: GPUType,
) -> str | None:
    """実行中マシン・引数設定値でサポートされるコアのファイル名（None: サポート外）"""
    # 実行中マシンのアーキテクチャ・システム名
    arch_name = _get_arch_name()
    platform_name = platform.system()
    if arch_name is None:
        return None
    return _get_core_name(arch_name, platform_name, model_type, gpu_type)


def _check_core_type(core_dir: Path) -> Literal["libtorch", "onnxruntime"] | None:
    """`core_dir`直下に存在し実行中マシンで利用可能な Core の model_type（None: 利用可能 Core 無し）"""
    libtorch_core_names = [
        _get_suitable_core_name("libtorch", gpu_type=GPUType.CUDA),
        _get_suitable_core_name("libtorch", gpu_type=GPUType.NONE),
        # ("libtorch", GPUType.DIRECT_ML): libtorch版はDirectML未対応
    ]
    onnxruntime_core_names = [
        _get_suitable_core_name("onnxruntime", gpu_type=GPUType.CUDA),
        _get_suitable_core_name("onnxruntime", gpu_type=GPUType.DIRECT_ML),
        _get_suitable_core_name("onnxruntime", gpu_type=GPUType.NONE),
    ]
    if any([(core_dir / name).is_file() for name in libtorch_core_names if name]):
        return "libtorch"
    elif any([(core_dir / name).is_file() for name in onnxruntime_core_names if name]):
        return "onnxruntime"
    else:
        return None


def load_core(core_dir: Path, use_gpu: bool) -> CDLL:
    """
    `core_dir` 直下に存在し実行中マシンでサポートされるコアDLLのロード
    Parameters
    ----------
    core_dir : Path
        直下にコア（共有ライブラリ）が存在するディレクトリ
    use_gpu
    Returns
    -------
    core : CDLL
        コアDLL
    """
    # Core>=0.12
    core_name = _find_version_0_12_core_or_later(core_dir)
    if core_name:
        try:
            # NOTE: CDLL クラスのコンストラクタの引数 name には文字列を渡す必要がある。
            #       Windows 環境では PathLike オブジェクトを引数として渡すと初期化に失敗する。
            return CDLL(str((core_dir / core_name).resolve(strict=True)))
        except OSError as err:
            raise RuntimeError(f"コアの読み込みに失敗しました：{err}")

    # Core<0.12
    model_type = _check_core_type(core_dir)
    if model_type is None:
        raise RuntimeError("コアが見つかりません")
    if use_gpu or model_type == "onnxruntime":
        core_name = _get_suitable_core_name(model_type, gpu_type=GPUType.CUDA)
        if core_name:
            try:
                return CDLL(str((core_dir / core_name).resolve(strict=True)))
            except OSError:
                pass
        core_name = _get_suitable_core_name(model_type, gpu_type=GPUType.DIRECT_ML)
        if core_name:
            try:
                return CDLL(str((core_dir / core_name).resolve(strict=True)))
            except OSError:
                pass
    core_name = _get_suitable_core_name(model_type, gpu_type=GPUType.NONE)
    if core_name:
        try:
            return CDLL(str((core_dir / core_name).resolve(strict=True)))
        except OSError as err:
            if model_type == "libtorch":
                core_name = _get_suitable_core_name(model_type, gpu_type=GPUType.CUDA)
                if core_name:
                    try:
                        return CDLL(str((core_dir / core_name).resolve(strict=True)))
                    except OSError as err_:
                        err = err_
            raise RuntimeError(f"コアの読み込みに失敗しました：{err}")
    else:
        raise RuntimeError(f"このコンピュータのアーキテクチャ {platform.machine()} で利用可能なコアがありません")


def _type_initialize(core_cdll: CDLL) -> None:
    """コアDLL `initialize` 関数を型付けする"""
    core_cdll.initialize.restype = c_bool


def _type_metas(core_cdll: CDLL) -> None:
    """コアDLL `metas` 関数を型付けする"""
    core_cdll.metas.restype = c_char_p


def _type_yukarin_s_forward(core_cdll: CDLL) -> None:
    """コアDLL `yukarin_s_forward` 関数を型付けする"""
    core_cdll.yukarin_s_forward.argtypes = (
        c_int,
        POINTER(c_long),
        POINTER(c_long),
        POINTER(c_float),
    )
    core_cdll.yukarin_s_forward.restype = c_bool


def _type_yukarin_sa_forward(core_cdll: CDLL) -> None:
    """コアDLL `yukarin_sa_forward` 関数を型付けする"""
    core_cdll.yukarin_sa_forward.argtypes = (
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
    core_cdll.yukarin_sa_forward.restype = c_bool


def _type_decode_forward(core_cdll: CDLL) -> None:
    """コアDLL `decode_forward` 関数を型付けする"""
    core_cdll.decode_forward.argtypes = (
        c_int,
        c_int,
        POINTER(c_float),
        POINTER(c_float),
        POINTER(c_long),
        POINTER(c_float),
    )
    core_cdll.decode_forward.restype = c_bool


def _type_last_error_message(core_cdll: CDLL) -> None:
    """コアDLL `last_error_message` 関数を型付けする"""
    core_cdll.last_error_message.restype = c_char_p


def _type_load_model(core_cdll: CDLL) -> None:
    """コアDLL `load_model` 関数を型付けする"""
    core_cdll.load_model.argtypes = (c_long,)
    core_cdll.load_model.restype = c_bool


def _type_is_model_loaded(core_cdll: CDLL) -> None:
    """コアDLL `is_model_loaded` 関数を型付けする"""
    core_cdll.is_model_loaded.argtypes = (c_long,)
    core_cdll.is_model_loaded.restype = c_bool


def _type_supported_devices(core_cdll: CDLL) -> None:
    """コアDLL `supported_devices` 関数を型付けする"""
    core_cdll.supported_devices.restype = c_char_p


def _type_finalize(core_cdll: CDLL) -> None:
    """コアDLL `finalize` 関数を型付けする"""
    core_cdll.finalize.restype = None


class CoreWrapper:
    def __init__(
        self,
        use_gpu: bool,
        core_dir: Path,
        cpu_num_threads: int = 0,
        load_all_models: bool = False,
    ) -> None:
        self.default_sampling_rate = 24000

        self.core = load_core(core_dir, use_gpu)

        _type_initialize(self.core)

        _type_metas(self.core)
        _type_yukarin_s_forward(self.core)
        _type_yukarin_sa_forward(self.core)
        _type_decode_forward(self.core)
        _type_last_error_message(self.core)

        self.exist_supported_devices = False
        self.exist_finalize = False
        exist_cpu_num_threads = False
        self.exist_load_model = False
        self.exist_is_model_loaded = False

        is_version_0_12_core_or_later = (
            _find_version_0_12_core_or_later(core_dir) is not None
        )
        model_type: Literal["libtorch", "onnxruntime"] | None
        if is_version_0_12_core_or_later:
            model_type = "onnxruntime"
            self.exist_load_model = True
            self.exist_is_model_loaded = True
            _type_load_model(self.core)
            _type_is_model_loaded(self.core)
        else:
            model_type = _check_core_type(core_dir)
        assert model_type is not None

        if model_type == "onnxruntime":
            _type_supported_devices(self.core)
            _type_finalize(self.core)
            self.exist_supported_devices = True
            self.exist_finalize = True
            exist_cpu_num_threads = True

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
        phoneme_list: NDArray[np.integer],
        style_id: NDArray[np.integer],
    ) -> NDArray[np.float32]:
        """
        音素列から、音素ごとの長さを求める関数
        Parameters
        ----------
        length : int
            音素列の長さ
        phoneme_list : NDArray[np.integer]
            音素列
        style_id : NDArray[np.integer]
            スタイル番号
        Returns
        -------
        output : NDArray[np.float32]
            音素ごとの長さ
        """
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
        vowel_phoneme_list: NDArray[np.integer],
        consonant_phoneme_list: NDArray[np.integer],
        start_accent_list: NDArray[np.integer],
        end_accent_list: NDArray[np.integer],
        start_accent_phrase_list: NDArray[np.integer],
        end_accent_phrase_list: NDArray[np.integer],
        style_id: NDArray[np.integer],
    ) -> NDArray[np.float32]:
        """
        モーラごとの音素列とアクセント情報から、モーラごとの音高を求める関数
        Parameters
        ----------
        length : int
            モーラ列の長さ
        vowel_phoneme_list : NDArray[np.integer]
            母音の音素列
        consonant_phoneme_list : NDArray[np.integer]
            子音の音素列
        start_accent_list : NDArray[np.integer]
        アクセントの開始位置
        end_accent_list : NDArray[np.integer]
            アクセントの終了位置
        start_accent_phrase_list : NDArray[np.integer]
            アクセント句の開始位置
        end_accent_phrase_list : NDArray[np.integer]
            アクセント句の終了位置
        style_id : NDArray[np.integer]
            スタイル番号
        Returns
        -------
        output : NDArray[np.float32]
            モーラごとの音高
        """
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
        f0: NDArray[np.floating],
        phoneme: NDArray[np.floating],
        style_id: NDArray[np.integer],
    ) -> NDArray[np.float32]:
        """
        フレームごとの音素と音高から波形を求める関数
        Parameters
        ----------
        length : int
            フレームの長さ
        phoneme_size : int
            音素の種類数
        f0 : NDArray[np.floating]
            フレームごとの音高
        phoneme : NDArray[np.floating]
            フレームごとの音素
        style_id : NDArray[np.integer]
            スタイル番号
        Returns
        -------
        output : NDArray[np.float32]
            音声波形
        """

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
        """
        coreから取得した対応デバイスに関するjsonデータの文字列
        """
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
