from typing import Optional
from psutil import AccessDenied, Process, net_connections, process_iter




def check_port_is_live(port: int) -> bool:
    return port in list(map(lambda c: c.laddr.port, net_connections()))



class GetProcessResult:
    def __init__(self, processes: list[Process], has_checked_all: bool):
        self.processes = processes
        self.has_checked_all = has_checked_all


def get_process_by_port(port: int) -> GetProcessResult:
    processes = []
    has_checked_all = True

    def has_process_port(proc):
        return len([conn for conn in proc.connections() if conn.laddr.port == port]) > 0

    for proc in process_iter():
        try:
            if has_process_port(proc):
                processes.append(Process(proc.pid))
        except AccessDenied:
            has_checked_all = False
    return GetProcessResult(processes, has_checked_all)
  
