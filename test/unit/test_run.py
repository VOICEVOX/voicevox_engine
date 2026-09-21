"""`run.py` のテスト"""

import sys
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from run import Envs, read_cli_arguments


@pytest.mark.parametrize("source", ["cli", "env"])
@pytest.mark.parametrize("cpu_num_threads", [-1, 65536])
def test_read_cli_arguments_rejects_invalid_cpu_num_threads(
    source: str, cpu_num_threads: int
) -> None:
    envs = Envs(False, None, None, False, None, None, False)
    argv = ["run.py"]
    if source == "cli":
        argv.extend(["--cpu_num_threads", str(cpu_num_threads)])
    else:
        envs = Envs(False, str(cpu_num_threads), None, False, None, None, False)

    with patch.object(sys, "argv", argv):
        with pytest.raises(ValidationError):
            read_cli_arguments(envs)


@pytest.mark.parametrize("source", ["cli", "env"])
@pytest.mark.parametrize("cpu_num_threads", [0, 65535])
def test_read_cli_arguments_accepts_valid_cpu_num_threads(
    source: str, cpu_num_threads: int
) -> None:
    envs = Envs(False, None, None, False, None, None, False)
    argv = ["run.py"]
    if source == "cli":
        argv.extend(["--cpu_num_threads", str(cpu_num_threads)])
    else:
        envs = Envs(False, str(cpu_num_threads), None, False, None, None, False)

    with patch.object(sys, "argv", argv):
        assert read_cli_arguments(envs).cpu_num_threads == cpu_num_threads
