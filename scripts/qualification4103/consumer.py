"""Read a completed supervisor receipt from a fresh, source-bound run directory."""
import json
import math
from pathlib import Path


def require_completion(directory, expected_sha):
    receipt = json.loads((Path(directory) / 'supervisor.json').read_bytes())
    job = receipt.get('final_job')
    cpu = receipt.get('worker_CPU_seconds')
    if (
        receipt.get('monitor_SHA256') != expected_sha
        or receipt.get('complete') is not True
        or type(receipt.get('exit_code')) is not int
        or receipt['exit_code'] != 0
        or receipt.get('error') != []
        or receipt.get('limit_reason') is not None
        or not isinstance(job, dict)
        or type(job.get('active')) is not int
        or job['active'] != 0
        or type(cpu) not in (int, float)
        or not math.isfinite(cpu)
        or cpu < 0
        or any(type(job.get(key)) is not int or job[key] < 0 for key in ('user_100ns', 'kernel_100ns'))
        or cpu != (job['user_100ns'] + job['kernel_100ns']) / 10_000_000
        or any(process.get('alive') is not False for process in receipt['processes'])
    ):
        raise ValueError('Supervisor completion is unavailable or invalid')
    return receipt
