"""`cpu_execution.py` のテスト"""

import pickle
from typing import cast
from unittest.mock import patch

import pytest

from voicevox_engine.core import cpu_execution
from voicevox_engine.core.cpu_execution import (
    HybridCpuTopology,
    LegacyCpuExecutionPlan,
    LinuxCpuExecutionPlan,
    WindowsCpuExecutionPlan,
    create_legacy_cpu_execution_plan,
    create_linux_cpu_execution_plan,
    create_windows_cpu_execution_plan,
)


def _create_topology(
    p_logical_cpu_ids: tuple[int, ...],
    e_logical_cpu_ids: tuple[int, ...],
) -> HybridCpuTopology:
    return HybridCpuTopology(p_logical_cpu_ids, e_logical_cpu_ids)


@pytest.mark.parametrize(
    ("cpu_num_threads", "logical_cpu_count", "expected"),
    [
        (None, 8, 4),
        (0, 8, 4),
        (None, 9, 4),
        (None, None, 0),
        (4, 8, 4),
        (65535, None, 65535),
    ],
)
def test_create_legacy_cpu_execution_plan(
    cpu_num_threads: int | None,
    logical_cpu_count: int | None,
    expected: int,
) -> None:
    """レガシーCPU実行計画を生成できる。"""
    plan = create_legacy_cpu_execution_plan(
        cpu_num_threads,
        logical_cpu_count,
    )

    assert plan == LegacyCpuExecutionPlan(expected)


@pytest.mark.parametrize("cpu_num_threads", [True, False, -1, 65536])
def test_create_legacy_cpu_execution_plan_rejects_invalid_value(
    cpu_num_threads: int,
) -> None:
    """レガシーCPU実行計画が不正なCPUスレッド数を拒否する。"""
    with pytest.raises(ValueError, match="cpu_num_threads"):
        create_legacy_cpu_execution_plan(cpu_num_threads, 8)


@pytest.mark.parametrize("logical_cpu_count", [0, -1, True, "8"])
def test_create_legacy_cpu_execution_plan_rejects_invalid_cpu_counts(
    logical_cpu_count: int | None,
) -> None:
    """レガシーCPU実行計画が不正なCPU数を拒否する。"""
    with pytest.raises(ValueError, match="CPU|cpu_count"):
        create_legacy_cpu_execution_plan(
            None,
            logical_cpu_count,
        )


@pytest.mark.parametrize("cpu_num_threads", [1, 65535])
def test_create_legacy_cpu_execution_plan_explicit_value_ignores_cpu_counts(
    cpu_num_threads: int,
) -> None:
    """レガシーCPU実行計画が明示値ならCPU数を参照しない。"""
    plan = create_legacy_cpu_execution_plan(cpu_num_threads, 0)

    assert plan == LegacyCpuExecutionPlan(cpu_num_threads)


def test_create_windows_cpu_execution_plan_uses_all_p_logical_cpus() -> None:
    """Windowsの計画がNと全P論理CPUを分けて扱う。"""
    topology = _create_topology(tuple(range(16)), (1000,))

    plan = create_windows_cpu_execution_plan(8, topology)

    assert plan == WindowsCpuExecutionPlan(
        8,
        tuple(range(16)),
    )


@pytest.mark.parametrize(
    ("p_logical_cpu_ids", "e_logical_cpu_ids", "expected_cpu_num_threads"),
    [
        ((0, 1, 2, 3), (4,), 2),
        ((10, 11, 20, 21, 30), (40,), 3),
    ],
)
def test_create_linux_cpu_execution_plan_uses_resolved_thread_count(
    p_logical_cpu_ids: tuple[int, ...],
    e_logical_cpu_ids: tuple[int, ...],
    expected_cpu_num_threads: int,
) -> None:
    """Linuxの計画が解決済みのNを使う。"""
    topology = _create_topology(p_logical_cpu_ids, e_logical_cpu_ids)

    plan = create_linux_cpu_execution_plan(expected_cpu_num_threads, topology)

    assert plan == LinuxCpuExecutionPlan(expected_cpu_num_threads, p_logical_cpu_ids)


def test_create_linux_cpu_execution_plan_uses_all_p_logical_cpu_ids() -> None:
    """Linuxの計画がP論理CPU IDをすべて対象にする。"""
    topology = _create_topology((10, 20), (30,))

    assert create_linux_cpu_execution_plan(1, topology) == LinuxCpuExecutionPlan(
        1,
        (10, 20),
    )


@pytest.mark.parametrize("cpu_num_threads", [None, 0])
def test_create_linux_cpu_execution_plan_rejects_unresolved_thread_count(
    cpu_num_threads: int | None,
) -> None:
    """Linuxの計画が未解決のNを拒否する。"""
    topology = _create_topology((0, 1), (2,))

    with pytest.raises(ValueError, match="cpu_num_threads"):
        create_linux_cpu_execution_plan(cast(int, cpu_num_threads), topology)


@pytest.mark.parametrize(
    ("cpu_num_threads", "expected"),
    [
        (1, LinuxCpuExecutionPlan(1, (0, 1))),
        (2, LegacyCpuExecutionPlan(2)),
        (4, LegacyCpuExecutionPlan(4)),
        (8, LegacyCpuExecutionPlan(8)),
    ],
)
def test_create_linux_cpu_execution_plan_uses_p_count_boundary(
    cpu_num_threads: int,
    expected: LegacyCpuExecutionPlan | LinuxCpuExecutionPlan,
) -> None:
    """Linuxの計画がP>Nだけaffinityを設定する。"""
    topology = _create_topology((0, 1), (2, 3))

    assert create_linux_cpu_execution_plan(cpu_num_threads, topology) == expected


def test_create_windows_cpu_execution_plan_uses_legacy_when_p_equals_n() -> None:
    """Windowsの計画がP=Nならaffinityなしになる。"""
    topology = _create_topology((0, 1), (2, 3))

    assert create_windows_cpu_execution_plan(2, topology) == LegacyCpuExecutionPlan(2)


@pytest.mark.parametrize("cpu_num_threads", [None, 0])
def test_create_windows_cpu_execution_plan_rejects_unresolved_thread_count(
    cpu_num_threads: int | None,
) -> None:
    """Windowsの計画が未解決のNを拒否する。"""
    topology = _create_topology((0, 1), (2,))

    with pytest.raises(ValueError, match="cpu_num_threads"):
        create_windows_cpu_execution_plan(cast(int, cpu_num_threads), topology)


@pytest.mark.parametrize("e_logical_cpu_ids", [()])
def test_create_linux_cpu_execution_plan_rejects_missing_e_cores(
    e_logical_cpu_ids: tuple[int, ...],
) -> None:
    """Linuxの計画がEコアのない構成を拒否する。"""
    topology = _create_topology((10, 20), e_logical_cpu_ids)

    with pytest.raises(ValueError, match="Eコア"):
        create_linux_cpu_execution_plan(1, topology)


def test_create_windows_cpu_execution_plan_uses_all_p_when_p_exceeds_n() -> None:
    """Windowsの明示計画がNより多い全P論理CPUを対象にする。"""
    topology = _create_topology(
        (21, 5, 13, 40, 8),
        (100, 64, 88, 120, 112, 200, 184),
    )

    plan = create_windows_cpu_execution_plan(3, topology)

    assert plan == WindowsCpuExecutionPlan(
        3,
        (5, 8, 13, 21, 40),
    )


def test_create_windows_cpu_execution_plan_sorts_logical_cpu_ids() -> None:
    """Windowsの計画が論理CPU IDの入力順によらず同じP集合になる。"""
    topology = _create_topology(
        (40, 8, 21, 5, 13),
        (120, 112, 100, 64, 88, 200, 184),
    )

    plan = create_windows_cpu_execution_plan(3, topology)

    assert plan == WindowsCpuExecutionPlan(
        3,
        (5, 8, 13, 21, 40),
    )


@pytest.mark.parametrize("cpu_num_threads", [4, 8, 10])
def test_create_windows_cpu_execution_plan_uses_legacy_when_p_does_not_exceed_n(
    cpu_num_threads: int,
) -> None:
    """Windowsの計画がP<=Nならaffinityなしになる。"""
    topology = _create_topology((0, 1), (2, 3))

    assert create_windows_cpu_execution_plan(
        cpu_num_threads, topology
    ) == LegacyCpuExecutionPlan(cpu_num_threads)


def test_create_linux_cpu_execution_plan_uses_legacy_when_p_does_not_exceed_n() -> None:
    """Linuxの明示計画がP論理CPU数以下のNでaffinityなしになる。"""
    topology = _create_topology((10, 20), (30,))

    plan = create_linux_cpu_execution_plan(2, topology)

    assert plan == LegacyCpuExecutionPlan(2)


def test_create_linux_cpu_execution_plan_keeps_explicit_value_over_capacity() -> None:
    """Linuxの明示値が利用可能CPU数を超えても保持される。"""
    topology = _create_topology((0, 1), (2,))

    assert create_linux_cpu_execution_plan(10, topology) == LegacyCpuExecutionPlan(10)


@pytest.mark.parametrize("p_logical_cpu_ids", [(0, 0), ()])
def test_create_windows_cpu_execution_plan_rejects_invalid_p_logical_cpu_ids(
    p_logical_cpu_ids: tuple[int, ...],
) -> None:
    """Windowsの計画が重複または空のP論理CPU集合を拒否する。"""
    topology = _create_topology(p_logical_cpu_ids, (100,))

    with pytest.raises(ValueError, match="Pコア|論理CPU ID"):
        create_windows_cpu_execution_plan(1, topology)


@pytest.mark.parametrize(
    "topology",
    [
        _create_topology((0,), (0,)),
        _create_topology((0, True), (1,)),
        _create_topology((0,), (1, -1)),
        _create_topology((0,), (1, 1)),
    ],
)
def test_create_cpu_execution_plan_rejects_invalid_flat_topology(
    topology: HybridCpuTopology,
) -> None:
    """CPU計画がP/E集合の重複、bool、負数を拒否する。"""
    with pytest.raises(ValueError, match="論理CPU"):
        create_linux_cpu_execution_plan(1, topology)


def test_create_linux_cpu_execution_plan_supports_non_contiguous_ids() -> None:
    """Linuxの計画が非連続な論理CPU IDを正規化する。"""
    topology = _create_topology((17, 3, 42), (99,))

    plan = create_linux_cpu_execution_plan(2, topology)

    assert plan == LinuxCpuExecutionPlan(2, (3, 17, 42))


@pytest.mark.parametrize("cpu_num_threads", [65535, 65536])
def test_create_linux_cpu_execution_plan_validates_thread_value(
    cpu_num_threads: int,
) -> None:
    """Linuxの計画がCPUスレッド数の指定値を検証する。"""
    topology = _create_topology((0, 1), (100,))

    if cpu_num_threads == 65535:
        assert create_linux_cpu_execution_plan(
            cpu_num_threads, topology
        ) == LegacyCpuExecutionPlan(cpu_num_threads)
    else:
        with pytest.raises(ValueError, match="cpu_num_threads"):
            create_linux_cpu_execution_plan(cpu_num_threads, topology)


@pytest.mark.parametrize(
    "plan",
    [
        LegacyCpuExecutionPlan(4),
        WindowsCpuExecutionPlan(2, (0, 1)),
        LinuxCpuExecutionPlan(2, (10, 20)),
    ],
)
def test_cpu_execution_plan_is_pickleable(
    plan: LegacyCpuExecutionPlan | WindowsCpuExecutionPlan | LinuxCpuExecutionPlan,
) -> None:
    """CPU実行計画がpickle化できる。"""
    assert pickle.loads(pickle.dumps(plan)) == plan


def test_create_cpu_execution_plan_dispatches_windows_hybrid() -> None:
    """共通の計画生成がWindowsのhybrid検出と計画生成へ振り分ける。"""
    topology = _create_topology((0, 1), (2,))
    expected = WindowsCpuExecutionPlan(1, (0,))
    with patch(
        "voicevox_engine.core.cpu_execution.platform.system",
        return_value="Windows",
    ):
        with patch(
            "voicevox_engine.core.cpu_execution_windows.detect_windows_hybrid_cpu_topology",
            return_value=topology,
        ):
            with patch.object(
                cpu_execution,
                "create_windows_cpu_execution_plan",
                return_value=expected,
            ) as create_plan:
                plan = cpu_execution.create_cpu_execution_plan(1)

    assert plan == expected
    create_plan.assert_called_once_with(1, topology)


def test_create_cpu_execution_plan_dispatches_linux_hybrid() -> None:
    """共通の計画生成がLinuxのhybrid検出と計画生成へ振り分ける。"""
    topology = _create_topology((0, 1), (2,))
    expected = LinuxCpuExecutionPlan(1, (0,))
    with patch(
        "voicevox_engine.core.cpu_execution.platform.system",
        return_value="Linux",
    ):
        with patch(
            "voicevox_engine.core.cpu_execution_linux.detect_linux_hybrid_cpu_topology",
            return_value=topology,
        ):
            with patch.object(
                cpu_execution,
                "create_linux_cpu_execution_plan",
                return_value=expected,
            ) as create_plan:
                plan = cpu_execution.create_cpu_execution_plan(1)

    assert plan == expected
    create_plan.assert_called_once_with(1, topology)


@pytest.mark.parametrize(
    ("system", "detector_path"),
    [
        (
            "Windows",
            "voicevox_engine.core.cpu_execution_windows.detect_windows_hybrid_cpu_topology",
        ),
        (
            "Linux",
            "voicevox_engine.core.cpu_execution_linux.detect_linux_hybrid_cpu_topology",
        ),
    ],
)
@pytest.mark.parametrize("requested_cpu_num_threads", [None, 0])
def test_create_cpu_execution_plan_uses_system_count_for_p_equals_n(
    system: str,
    detector_path: str,
    requested_cpu_num_threads: int | None,
) -> None:
    """自動指定のNがシステム全体のCPU数から解決される。"""
    topology = _create_topology((0, 1), (2,))
    with patch(
        "voicevox_engine.core.cpu_execution.platform.system", return_value=system
    ):
        with patch(detector_path, return_value=topology) as detector:
            with patch(
                "voicevox_engine.core.cpu_execution.psutil.cpu_count",
                return_value=4,
            ) as cpu_count:
                plan = cpu_execution.create_cpu_execution_plan(
                    requested_cpu_num_threads
                )

    assert plan == LegacyCpuExecutionPlan(2)
    cpu_count.assert_called_once_with(logical=True)
    detector.assert_called_once_with()


@pytest.mark.parametrize(
    ("system", "detector_path"),
    [
        (
            "Windows",
            "voicevox_engine.core.cpu_execution_windows.detect_windows_hybrid_cpu_topology",
        ),
        (
            "Linux",
            "voicevox_engine.core.cpu_execution_linux.detect_linux_hybrid_cpu_topology",
        ),
    ],
)
def test_create_cpu_execution_plan_uses_system_count_when_p_does_not_exceed_n(
    system: str,
    detector_path: str,
) -> None:
    """許可範囲のP数がN以下でもシステム全体のNを使う。"""
    topology = _create_topology(tuple(range(6)), (100, 101))
    with patch(
        "voicevox_engine.core.cpu_execution.platform.system", return_value=system
    ):
        with patch(detector_path, return_value=topology):
            with patch(
                "voicevox_engine.core.cpu_execution.psutil.cpu_count",
                return_value=20,
            ):
                plan = cpu_execution.create_cpu_execution_plan(None)

    assert plan == LegacyCpuExecutionPlan(10)


@pytest.mark.parametrize(
    ("system", "detector_path"),
    [
        (
            "Windows",
            "voicevox_engine.core.cpu_execution_windows.detect_windows_hybrid_cpu_topology",
        ),
        (
            "Linux",
            "voicevox_engine.core.cpu_execution_linux.detect_linux_hybrid_cpu_topology",
        ),
    ],
)
def test_create_cpu_execution_plan_targets_all_allowed_p_cpus(
    system: str,
    detector_path: str,
) -> None:
    """P>Nなら許可された全P論理CPUを対象にする。"""
    p_logical_cpu_ids = (1, 3, 5, 7, 9)
    topology = _create_topology(p_logical_cpu_ids, (100,))
    with patch(
        "voicevox_engine.core.cpu_execution.platform.system", return_value=system
    ):
        with patch(detector_path, return_value=topology):
            with patch(
                "voicevox_engine.core.cpu_execution.psutil.cpu_count",
                return_value=8,
            ):
                plan = cpu_execution.create_cpu_execution_plan(None)

    if system == "Windows":
        assert plan == WindowsCpuExecutionPlan(4, p_logical_cpu_ids)
    else:
        assert plan == LinuxCpuExecutionPlan(4, p_logical_cpu_ids)


@pytest.mark.parametrize(
    ("system", "detector_path"),
    [
        (
            "Windows",
            "voicevox_engine.core.cpu_execution_windows.detect_windows_hybrid_cpu_topology",
        ),
        (
            "Linux",
            "voicevox_engine.core.cpu_execution_linux.detect_linux_hybrid_cpu_topology",
        ),
    ],
)
def test_create_cpu_execution_plan_keeps_system_n_when_detection_is_unavailable(
    system: str,
    detector_path: str,
) -> None:
    """P/E検出不能でもシステム全体から解決したNを使う。"""
    with patch(
        "voicevox_engine.core.cpu_execution.platform.system", return_value=system
    ):
        with patch(detector_path, return_value=None) as detector:
            with patch(
                "voicevox_engine.core.cpu_execution.psutil.cpu_count",
                return_value=9,
            ) as cpu_count:
                plan = cpu_execution.create_cpu_execution_plan(None)

    assert plan == LegacyCpuExecutionPlan(4)
    cpu_count.assert_called_once_with(logical=True)
    detector.assert_called_once_with()


def test_create_cpu_execution_plan_resolves_n_before_detection() -> None:
    """自動指定ではCPU数取得がP/E検出より先に一度だけ行われる。"""
    events: list[str] = []

    def get_cpu_count(*, logical: bool) -> int:
        assert logical
        events.append("cpu_count")
        return 8

    def detect_topology() -> None:
        events.append("detect")

    with patch(
        "voicevox_engine.core.cpu_execution.platform.system", return_value="Linux"
    ):
        with patch(
            "voicevox_engine.core.cpu_execution.psutil.cpu_count",
            side_effect=get_cpu_count,
        ) as cpu_count:
            with patch(
                "voicevox_engine.core.cpu_execution_linux.detect_linux_hybrid_cpu_topology",
                side_effect=detect_topology,
            ) as detector:
                plan = cpu_execution.create_cpu_execution_plan(0)

    assert plan == LegacyCpuExecutionPlan(4)
    assert events == ["cpu_count", "detect"]
    cpu_count.assert_called_once_with(logical=True)
    detector.assert_called_once_with()


def test_create_cpu_execution_plan_skips_detection_without_system_count() -> None:
    """システム全体のCPU数が取得できなければ検出せず0を返す。"""
    with patch(
        "voicevox_engine.core.cpu_execution.platform.system", return_value="Linux"
    ):
        with patch(
            "voicevox_engine.core.cpu_execution.psutil.cpu_count", return_value=None
        ):
            with patch(
                "voicevox_engine.core.cpu_execution_linux.detect_linux_hybrid_cpu_topology",
                side_effect=AssertionError("P/E検出は呼び出されません"),
            ):
                plan = cpu_execution.create_cpu_execution_plan(None)

    assert plan == LegacyCpuExecutionPlan(0)


def test_create_cpu_execution_plan_skips_os_detection_with_one_system_cpu() -> None:
    """論理CPUが1つならN=0のlegacy計画をOS検出なしで返す。"""
    with patch(
        "voicevox_engine.core.cpu_execution.platform.system",
        side_effect=AssertionError("OS検出は呼び出されません"),
    ):
        with patch(
            "voicevox_engine.core.cpu_execution.psutil.cpu_count", return_value=1
        ) as cpu_count:
            plan = cpu_execution.create_cpu_execution_plan(None)

    assert plan == LegacyCpuExecutionPlan(0)
    cpu_count.assert_called_once_with(logical=True)


@pytest.mark.parametrize(
    ("system", "detector_path"),
    [
        (
            "Windows",
            "voicevox_engine.core.cpu_execution_windows.detect_windows_hybrid_cpu_topology",
        ),
        (
            "Linux",
            "voicevox_engine.core.cpu_execution_linux.detect_linux_hybrid_cpu_topology",
        ),
    ],
)
def test_create_cpu_execution_plan_uses_legacy_for_non_hybrid_without_psutil(
    system: str,
    detector_path: str,
) -> None:
    """明示値のnon-hybrid計画はpsutilを読まずlegacy計画を返す。"""
    with patch(
        "voicevox_engine.core.cpu_execution.platform.system",
        return_value=system,
    ):
        with patch(detector_path, return_value=None):
            with patch(
                "voicevox_engine.core.cpu_execution.psutil.cpu_count",
                side_effect=AssertionError("psutilは呼び出されません"),
            ):
                plan = cpu_execution.create_cpu_execution_plan(3)

    assert plan == LegacyCpuExecutionPlan(3)


def test_create_cpu_execution_plan_uses_legacy_for_darwin() -> None:
    """Darwinの計画生成はlegacyへ振り分ける。"""
    with patch(
        "voicevox_engine.core.cpu_execution.platform.system",
        return_value="Darwin",
    ):
        with patch(
            "voicevox_engine.core.cpu_execution.psutil.cpu_count",
            return_value=8,
        ) as cpu_count:
            plan = cpu_execution.create_cpu_execution_plan(None)

    assert plan == LegacyCpuExecutionPlan(4)
    cpu_count.assert_called_once_with(logical=True)


def test_create_cpu_execution_plan_validates_before_os_detection() -> None:
    """不正なCPUスレッド数はOS検出前に拒否する。"""
    with patch(
        "voicevox_engine.core.cpu_execution.platform.system",
        side_effect=AssertionError("OS検出は開始されません"),
    ):
        with pytest.raises(ValueError, match="cpu_num_threads"):
            cpu_execution.create_cpu_execution_plan(True)


def test_create_cpu_execution_plan_uses_legacy_for_unknown_os() -> None:
    """未知のOSの共通計画生成がaffinityなしへ振り分ける。"""
    with patch(
        "voicevox_engine.core.cpu_execution.platform.system",
        return_value="Plan9",
    ):
        with patch(
            "voicevox_engine.core.cpu_execution.psutil.cpu_count",
            return_value=9,
        ) as cpu_count:
            assert cpu_execution.create_cpu_execution_plan(
                None
            ) == LegacyCpuExecutionPlan(4)
    cpu_count.assert_called_once_with(logical=True)


def test_apply_and_validate_cpu_execution_plan_dispatch() -> None:
    """共通の適用と検証がWindows、Linux、legacyへ振り分ける。"""
    windows_plan = WindowsCpuExecutionPlan(1, (0,))
    linux_plan = LinuxCpuExecutionPlan(1, (0,))
    with patch(
        "voicevox_engine.core.cpu_execution_windows.apply_windows_cpu_execution_plan"
    ) as apply_windows:
        with patch(
            "voicevox_engine.core.cpu_execution_windows.validate_windows_cpu_execution_plan"
        ) as validate_windows:
            cpu_execution.apply_cpu_execution_plan(windows_plan)
            cpu_execution.validate_cpu_execution_plan(windows_plan)
    with patch(
        "voicevox_engine.core.cpu_execution_linux.apply_linux_cpu_execution_plan"
    ) as apply_linux:
        with patch(
            "voicevox_engine.core.cpu_execution_linux.validate_linux_cpu_execution_plan"
        ) as validate_linux:
            cpu_execution.apply_cpu_execution_plan(linux_plan)
            cpu_execution.validate_cpu_execution_plan(linux_plan)

    cpu_execution.apply_cpu_execution_plan(LegacyCpuExecutionPlan(0))
    cpu_execution.validate_cpu_execution_plan(LegacyCpuExecutionPlan(0))
    apply_windows.assert_called_once_with(windows_plan)
    validate_windows.assert_called_once_with(windows_plan)
    apply_linux.assert_called_once_with(linux_plan)
    validate_linux.assert_called_once_with(linux_plan)
