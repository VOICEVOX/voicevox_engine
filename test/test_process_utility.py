import subprocess
import time

import pytest

from voicevox_engine.utility import get_process_by_port


def test_port_occupation():
    port = 8080
    proc = subprocess.Popen(["python", "-m", "http.server", str(port)])

    # for http server listening
    time.sleep(1)

    result = get_process_by_port(port).processes

    assert len(result) > 0
    proc.kill()
