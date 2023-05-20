import pytest
import subprocess
from voicevox_engine.utility import get_process_by_port


def test_port_occupation():
    port = 8080
    proc = subprocess.Popen(["python", "-m", "http.server", str(port)])

    result = get_process_by_port(port).processes

    proc.kill()

    assert len(result) > 0
