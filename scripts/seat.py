"""Which seat is calling: found from the process tree, not from anything the caller sets.

Every seat runs under its own launcher, band-work/seats/<seat>/launch.(js|cmd). A tool
started anywhere beneath that process, including by a helper the seat spawns, belongs to
that seat. UMBRA_SEAT is only consulted when no launcher is found among the ancestors.
"""
import json
import os
import re
import subprocess
import sys

LAUNCHER = re.compile(r"seats[\\/](\w+)[\\/]launch\.(?:js|cmd)", re.IGNORECASE)


def _processes():
    if sys.platform != "win32":
        return {}
    query = ("Get-CimInstance Win32_Process -Property ProcessId,ParentProcessId,CommandLine | "
             "Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Compress")
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", query],
                             capture_output=True, text=True, timeout=60).stdout
        rows = json.loads(out)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return {}
    return {r["ProcessId"]: (r["ParentProcessId"], r.get("CommandLine") or "") for r in rows}


def caller_seat():
    table = _processes()
    pid, seen = os.getpid(), set()
    while pid in table and pid not in seen:
        seen.add(pid)
        parent, command = table[pid]
        match = LAUNCHER.search(command)
        if match:
            return match.group(1).lower()
        pid = parent
    return os.environ.get("UMBRA_SEAT") or None


def refuse_unless(claimed, action):
    actual = caller_seat()
    if actual and actual != claimed:
        sys.exit(f"refused: this session is seat {actual} and cannot {action} as {claimed}. "
                 f"Work owned by another seat is handed to that seat in the room.")
