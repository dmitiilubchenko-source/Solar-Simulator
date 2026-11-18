"""Self-limited Windows fixtures, with no simulation imports."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

mode, target, *args = sys.argv[1:]
folder = Path(target)
(folder / f"{os.getpid()}.started").touch()
if mode == "argv":
    print(json.dumps({"args": args, "cwd": os.getcwd(), "stdin": sys.stdin.read(),
                      "env": {k: os.environ.get(k) for k in (
                         "PYTHONPATH", "PYTHONHOME", "OMP_NUM_THREADS",
                         "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS")}}, ensure_ascii=False))
    print("stderr Юникод", file=sys.stderr)
elif mode in ("parent", "grand", "short-parent", "joined"):
    next_mode = {"parent": "wait", "grand": "short-parent", "short-parent": "wait",
                 "joined": "burn"}[mode]
    child = subprocess.Popen([sys._base_executable, "-I", "-B", __file__, next_mode, target])
    (folder / f"{mode}.child").write_text(str(child.pid))
    if mode == "joined":
        child.wait(timeout=4)
    else:
        time.sleep(0.03 if mode == "short-parent" else 0.6)
elif mode == "wait":
    end = time.monotonic() + 2.5
    while time.monotonic() < end and not (folder / "release").exists():
        time.sleep(0.005)
elif mode == "burn":
    data = bytearray(16 * 1024**2)
    end = time.perf_counter() + 0.8
    while time.perf_counter() < end:
        sum(range(3000))
elif mode == "sleep":
    time.sleep(2.5)
elif mode == "disk":
    (folder / "payload.bin").write_bytes(bytes(2 * 1024**2))
    time.sleep(0.8)
elif mode == "crash":
    os._exit(9)
elif mode == "nonzero":
    raise SystemExit(7)
elif mode == "breakaway":
    try:
        child = subprocess.Popen([sys._base_executable, "-I", "-B", __file__, "wait", target],
                                 creationflags=0x01000000)
    except OSError as exc:
        print(json.dumps({"breakaway_winerror": exc.winerror}))
    else:
        (folder / "breakaway.child").write_text(str(child.pid))
        child.wait(timeout=4)
        print(json.dumps({"breakaway_created": True, "child_exit": child.returncode}))
