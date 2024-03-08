import os


def get_half_logical_cores() -> int:
    logical_cores = os.cpu_count()
    if logical_cores is None:
        return 0
    return logical_cores // 2
