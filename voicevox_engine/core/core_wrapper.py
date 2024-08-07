"""VOICEVOX CORE の Python ラッパー"""

import os
import platform
from ctypes import _Pointer  # noqa: F401
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
    """
    コアの実行に必要な依存 DLL をロードする。検索対象ディレクトリは引数 `runtime_dirs` およびシステム検索対象ディレクトリ。

    Args:
        runtime_dirs - 直下に DLL が存在するディレクトリの一覧
    """
    # `lib_file_names`は「ENGINE が利用可能な DLL のファイル名一覧」である
    # `lib_names` は「ENGINE が利用可能な DLL のライブラリ名一覧」である（ライブラリ名は `libtorch.so.1.0` の `torch` 部分）
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

    # 引数指定ディレクトリ直下の DLL をロードする
    for runtime_dir in runtime_dirs:
        for lib_file_name in lib_file_names:
            try:
                CDLL(str((runtime_dir / lib_file_name).resolve(strict=True)))
            except OSError:
                pass

    # システム検索ディレクトリ直下の DLL をロードする
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
        raise RuntimeError(
            f"このコンピュータのアーキテクチャ {platform.machine()} で利用可能なコアがありません"
        )


_C_TYPE = (
    type[c_bool]
    | type[c_int]
    | type[c_long]
    | type[c_float]
    | type[c_char_p]
    | type["_Pointer[c_long]"]
    | type["_Pointer[c_float]"]
)


@dataclass(frozen=True)
class _CoreApiType:
    argtypes: tuple[_C_TYPE, ...]
    restype: _C_TYPE | None


# コアAPIの型情報
_CORE_API_TYPES = {
    # NOTE: initialize 関数には実際には引数があるが、コアのバージョンによって引数が異なるため、意図的に引数の型付けをしない
    "initialize": _CoreApiType(
        argtypes=(),
        restype=c_bool,
    ),
    "metas": _CoreApiType(
        argtypes=(),
        restype=c_char_p,
    ),
    "yukarin_s_forward": _CoreApiType(
        argtypes=(c_int, POINTER(c_long), POINTER(c_long), POINTER(c_float)),
        restype=c_bool,
    ),
    "yukarin_sa_forward": _CoreApiType(
        argtypes=(
            c_int,
            POINTER(c_long),
            POINTER(c_long),
            POINTER(c_long),
            POINTER(c_long),
            POINTER(c_long),
            POINTER(c_long),
            POINTER(c_long),
            POINTER(c_float),
        ),
        restype=c_bool,
    ),
    "decode_forward": _CoreApiType(
        argtypes=(
            c_int,
            c_int,
            POINTER(c_float),
            POINTER(c_float),
            POINTER(c_long),
            POINTER(c_float),
        ),
        restype=c_bool,
    ),
    "predict_sing_consonant_length_forward": _CoreApiType(
        argtypes=(
            c_int,
            POINTER(c_long),
            POINTER(c_long),
            POINTER(c_long),
            POINTER(c_long),
            POINTER(c_long),
        ),
        restype=c_bool,
    ),
    "predict_sing_f0_forward": _CoreApiType(
        argtypes=(
            c_int,
            POINTER(c_long),
            POINTER(c_long),
            POINTER(c_long),
            POINTER(c_float),
        ),
        restype=c_bool,
    ),
    "predict_sing_volume_forward": _CoreApiType(
        argtypes=(
            c_int,
            POINTER(c_long),
            POINTER(c_long),
            POINTER(c_float),
            POINTER(c_long),
            POINTER(c_float),
        ),
        restype=c_bool,
    ),
    "sf_decode_forward": _CoreApiType(
        argtypes=(
            c_int,
            POINTER(c_long),
            POINTER(c_float),
            POINTER(c_float),
            POINTER(c_long),
            POINTER(c_float),
        ),
        restype=c_bool,
    ),
    "last_error_message": _CoreApiType(
        argtypes=(),
        restype=c_char_p,
    ),
    "load_model": _CoreApiType(
        argtypes=(c_long,),
        restype=c_bool,
    ),
    "is_model_loaded": _CoreApiType(
        argtypes=(c_long,),
        restype=c_bool,
    ),
    "supported_devices": _CoreApiType(
        argtypes=(),
        restype=c_char_p,
    ),
    "finalize": _CoreApiType(
        argtypes=(),
        restype=None,
    ),
}


def _check_and_type_apis(core_cdll: CDLL) -> dict[str, bool]:
    """
    コアDLLの各関数を（その関数があれば）型付けする。APIの有無の情報を辞書として返す
    Parameters
    ----------
    core_cdll : CDLL
        コアDLL
    Returns
    -------
    api_exists : dict[str, bool]
        key: API名, value: APIの有無
    """
    api_exists = {}

    for api_name, api_type in _CORE_API_TYPES.items():
        if hasattr(core_cdll, api_name):
            api = getattr(core_cdll, api_name)

            if len(api_type.argtypes) > 0:
                api.argtypes = api_type.argtypes
            api.restype = api_type.restype

            api_exists[api_name] = True
        else:
            api_exists[api_name] = False

    return api_exists


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

        self.api_exists = _check_and_type_apis(self.core)

        exist_cpu_num_threads = False

        is_version_0_12_core_or_later = (
            _find_version_0_12_core_or_later(core_dir) is not None
        )
        model_type: Literal["libtorch", "onnxruntime"] | None
        if is_version_0_12_core_or_later:
            model_type = "onnxruntime"
        else:
            model_type = _check_core_type(core_dir)
        assert model_type is not None

        if model_type == "onnxruntime":
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
        metas_bytes: bytes = self.core.metas()
        return metas_bytes.decode("utf-8")

    def yukarin_s_forward(
        self,
        length: int,
        phoneme_list: NDArray[np.int64],
        style_id: NDArray[np.int64],
    ) -> NDArray[np.float32]:
        """
        音素列から、音素ごとの長さを求める関数
        Parameters
        ----------
        length : int
            音素列の長さ
        phoneme_list : NDArray[np.int64]
            音素列
        style_id : NDArray[np.int64]
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
        vowel_phoneme_list: NDArray[np.int64],
        consonant_phoneme_list: NDArray[np.int64],
        start_accent_list: NDArray[np.int64],
        end_accent_list: NDArray[np.int64],
        start_accent_phrase_list: NDArray[np.int64],
        end_accent_phrase_list: NDArray[np.int64],
        style_id: NDArray[np.int64],
    ) -> NDArray[np.float32]:
        """
        モーラごとの音素列とアクセント情報から、モーラごとの音高を求める関数
        Parameters
        ----------
        length : int
            モーラ列の長さ
        vowel_phoneme_list : NDArray[np.int64]
            母音の音素列
        consonant_phoneme_list : NDArray[np.int64]
            子音の音素列
        start_accent_list : NDArray[np.int64]
        アクセントの開始位置
        end_accent_list : NDArray[np.int64]
            アクセントの終了位置
        start_accent_phrase_list : NDArray[np.int64]
            アクセント句の開始位置
        end_accent_phrase_list : NDArray[np.int64]
            アクセント句の終了位置
        style_id : NDArray[np.int64]
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
        f0: NDArray[np.float32],
        phoneme: NDArray[np.float32],
        style_id: NDArray[np.int64],
    ) -> NDArray[np.float32]:
        """
        フレームごとの音素と音高から波形を求める関数
        Parameters
        ----------
        length : int
            フレームの長さ
        phoneme_size : int
            音素の種類数
        f0 : NDArray[np.float32]
            フレームごとの音高
        phoneme : NDArray[np.float32]
            フレームごとの音素
        style_id : NDArray[np.int64]
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

    def predict_sing_consonant_length_forward(
        self,
        length: int,
        consonant: NDArray[np.int64],
        vowel: NDArray[np.int64],
        note_duration: NDArray[np.int64],
        style_id: NDArray[np.int64],
    ) -> NDArray[np.int64]:
        """
        子音・母音列から、音素ごとの長さを求める関数
        Parameters
        ----------
        length : int
            音素列の長さ
        consonant : NDArray[np.int64]
            子音列
        vowel : NDArray[np.int64]
            母音列
        note_duration : NDArray[np.int64]
            ノート列
        style_id : NDArray[np.int64]
            スタイル番号
        Returns
        -------
        output : NDArray[np.int64]
            子音長
        """
        if self.api_exists["predict_sing_consonant_length_forward"]:
            output = np.zeros((length,), dtype=np.int64)
            self.assert_core_success(
                self.core.predict_sing_consonant_length_forward(
                    c_int(length),
                    consonant.ctypes.data_as(POINTER(c_long)),
                    vowel.ctypes.data_as(POINTER(c_long)),
                    note_duration.ctypes.data_as(POINTER(c_long)),
                    style_id.ctypes.data_as(POINTER(c_long)),
                    output.ctypes.data_as(POINTER(c_long)),
                )
            )
            return output
        raise OldCoreError

    def predict_sing_f0_forward(
        self,
        length: int,
        phoneme: NDArray[np.int64],
        note: NDArray[np.int64],
        style_id: NDArray[np.int64],
    ) -> NDArray[np.float32]:
        """
        フレームごとの音素列とノート列から、フレームごとのF0を求める関数
        Parameters
        ----------
        length : int
            フレームの長さ
        phoneme : NDArray[np.int64]
            フレームごとの音素
        note : NDArray[np.int64]
            フレームごとのノート
        style_id : NDArray[np.int64]
            スタイル番号
        Returns
        -------
        output : NDArray[np.float32]
            フレームごとの音高
        """
        if self.api_exists["predict_sing_f0_forward"]:
            output = np.zeros((length,), dtype=np.float32)
            self.assert_core_success(
                self.core.predict_sing_f0_forward(
                    c_int(length),
                    phoneme.ctypes.data_as(POINTER(c_long)),
                    note.ctypes.data_as(POINTER(c_long)),
                    style_id.ctypes.data_as(POINTER(c_long)),
                    output.ctypes.data_as(POINTER(c_float)),
                )
            )
            return output
        raise OldCoreError

    def predict_sing_volume_forward(
        self,
        length: int,
        phoneme: NDArray[np.int64],
        note: NDArray[np.int64],
        f0: NDArray[np.float32],
        style_id: NDArray[np.int64],
    ) -> NDArray[np.float32]:
        """
        フレームごとの音素列とノート列から、フレームごとのvolumeを求める関数
        Parameters
        ----------
        length : int
            フレームの長さ
        phoneme : NDArray[np.int64]
            フレームごとの音素
        note : NDArray[np.int64]
            フレームごとのノート
        f0 : NDArray[np.float32]
            フレームごとの音高
        style_id : NDArray[np.int64]
            スタイル番号
        Returns
        -------
        output : NDArray[np.float32]
            フレームごとの音量
        """
        if self.api_exists["predict_sing_volume_forward"]:
            output = np.zeros((length,), dtype=np.float32)
            self.assert_core_success(
                self.core.predict_sing_volume_forward(
                    c_int(length),
                    phoneme.ctypes.data_as(POINTER(c_long)),
                    note.ctypes.data_as(POINTER(c_long)),
                    f0.ctypes.data_as(POINTER(c_float)),
                    style_id.ctypes.data_as(POINTER(c_long)),
                    output.ctypes.data_as(POINTER(c_float)),
                )
            )
            return output
        raise OldCoreError

    def sf_decode_forward(
        self,
        length: int,
        phoneme: NDArray[np.int64],
        f0: NDArray[np.float32],
        volume: NDArray[np.float32],
        style_id: NDArray[np.int64],
    ) -> NDArray[np.float32]:
        """
        フレームごとの音素と音高から波形を求める関数
        Parameters
        ----------
        length : int
            フレームの長さ
        phoneme : NDArray[np.int64]
            フレームごとの音素
        f0 : NDArray[np.float32]
            フレームごとの音高
        volume : NDArray[np.float32]
            フレームごとの音量
        style_id : NDArray[np.int64]
            スタイル番号
        Returns
        -------
        output : NDArray[np.float32]
            音声波形
        """
        if self.api_exists["sf_decode_forward"]:
            output = np.zeros((length * 256,), dtype=np.float32)
            self.assert_core_success(
                self.core.sf_decode_forward(
                    c_int(length),
                    phoneme.ctypes.data_as(POINTER(c_long)),
                    f0.ctypes.data_as(POINTER(c_float)),
                    volume.ctypes.data_as(POINTER(c_float)),
                    style_id.ctypes.data_as(POINTER(c_long)),
                    output.ctypes.data_as(POINTER(c_float)),
                )
            )
            return output
        raise OldCoreError

    def supported_devices(self) -> str:
        """
        coreから取得した対応デバイスに関するjsonデータの文字列
        """
        if self.api_exists["supported_devices"]:
            supported_devices_byte: bytes = self.core.supported_devices()
            return supported_devices_byte.decode("utf-8")
        raise OldCoreError

    def finalize(self) -> None:
        if self.api_exists["finalize"]:
            self.core.finalize()
            return
        raise OldCoreError

    def load_model(self, style_id: int) -> None:
        if self.api_exists["load_model"]:
            self.assert_core_success(self.core.load_model(c_long(style_id)))
        raise OldCoreError

    def is_model_loaded(self, style_id: int) -> bool:
        if self.api_exists["is_model_loaded"]:
            loaded_bool: bool = self.core.is_model_loaded(c_long(style_id))
            return loaded_bool
        raise OldCoreError

    def assert_core_success(self, result: bool) -> None:
        if not result:
            raise CoreError(
                self.core.last_error_message().decode("utf-8", "backslashreplace")
            )
