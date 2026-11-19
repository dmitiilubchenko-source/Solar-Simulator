"""Run only small synthetic evidence tests under the pinned Windows supervisor."""
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
RAW = Path("C:/Users/Admin/Documents/Codex/Solar 410E 20261119")
SUPERVISOR = Path("C:/Users/Admin/Desktop/Solar-tooling-4103")
PYTHON = Path("C:/Users/Admin/Documents/Codex/Solar407V-20261111/env/Scripts/python.exe")
MONITOR = "8a0571d04a35898b1e3e1f5f0d2ac8734920b32c286fc0a35e773d6853dfec17"
CONSUMER = "0ae10ef3f2ec04d8dbdafdb3ef7988a81070bbd3267ebc3d995f96269fb0cb5d"


def verify(path, pin):
    if hashlib.sha256(path.read_bytes()).hexdigest() != pin:
        raise ValueError(f"Tooling pin mismatch: {path.name}")


def run(label):
    stamp, cpu = time.perf_counter(), time.process_time()
    for name, pin in (("monitor.py", MONITOR),("consumer.py", CONSUMER)):
        verify(SUPERVISOR/"scripts/qualification4103"/name, pin)
    sys.path.insert(0, str(SUPERVISOR))
    from scripts.qualification4103 import monitor as guard
    from scripts.qualification4103.consumer import require_completion

    output = RAW/label
    output.mkdir(exist_ok=False)
    command = [str(PYTHON), "-X", "utf8", "-B", "-m", "pytest", "scripts/qualification410e/test_evidence.py",
               "-q", "-p", "no:cacheprovider", "--junitxml", str(output/"tests.xml"),
               "--basetemp", str(output/"fixtures")]
    guard.monitor(command, output/"guard", RAW, dict(cpu_seconds=24,wall_seconds=50,
                  private_bytes=512*1024**2,disk_bytes=64*1024**2), cwd=ROOT, expected_sha=MONITOR)
    receipt = require_completion(output/"guard", MONITOR)
    guard.save(output/"resource-receipt.json",dict(worker_cpu=receipt["worker_CPU_seconds"],
               parent_cpu=time.process_time()-cpu,wall=time.perf_counter()-stamp,
               peak_private=receipt["peak_private_tree_sampled"],measured_test_scope=True))
    print((output/"guard/stdout.log").read_text(encoding="utf8"))


if __name__=="__main__":
    run(sys.argv[1])
