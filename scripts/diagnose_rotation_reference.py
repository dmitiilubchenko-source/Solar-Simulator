"""Locate the dominant difference in the originally failed change-50 reference."""
import hashlib
import json
from pathlib import Path

import numpy as np
from assess_rotation import cases, reference

ROOT = Path(__file__).resolve().parents[1]


def diagnose():
    name, figure, point, initial, times, step = list(cases())[-1]
    first = reference(figure, initial, times, point, 3e-11, step)
    second = reference(figure, initial, times, point, 3e-12, step)
    a, b = first[:, 6:15].reshape(-1, 3, 3), second[:, 6:15].reshape(-1, 3, 3)
    sa = np.einsum("nij,nj->ni", a, first[:, 15:])
    sb = np.einsum("nij,nj->ni", b, second[:, 15:])
    metrics = dict(relative_position=float(np.max(np.linalg.norm(first[:, :3]-second[:, :3], axis=1))/np.linalg.norm(initial[:3])),
        relative_velocity=float(np.max(np.linalg.norm(first[:, 3:6]-second[:, 3:6], axis=1))/np.linalg.norm(initial[3:6])),
        rotation_frobenius=float(np.max(np.linalg.norm(a-b, axis=(1, 2)))),
        spin_relative=float(np.max(np.linalg.norm(sa-sb, axis=1))/np.linalg.norm(initial[10:])),
        matrix_orthogonality_low=float(np.max(np.linalg.norm(np.einsum("nji,njk->nik", a, a)-np.eye(3), axis=(1, 2)))),
        matrix_orthogonality_high=float(np.max(np.linalg.norm(np.einsum("nji,njk->nik", b, b)-np.eye(3), axis=(1, 2)))))
    return dict(original_rtols=[3e-11, 3e-12], duration_seconds=float(times[-1]), samples=len(times), metrics=metrics,
        source_sha256=hashlib.sha256((ROOT/"scripts/assess_rotation.py").read_bytes()).hexdigest(),
        interpretation="Local RK45 tolerance does not bound accumulated phase/orientation error over 20 periods. Identify dominant group; no exact global error bound claimed.")


if __name__ == "__main__":
    # Non-destructive reproduction: verify an existing diagnostic or create it.
    path = ROOT/"docs/rotation-reference-diagnosis.json"
    data = diagnose()
    if path.exists():
        old = json.loads(path.read_text())
        if old != data:
            raise ValueError("Existing diagnostic differs; preserve it and investigate")
        print("Original reference diagnostic reproduced exactly")
    else:
        path.write_text(json.dumps(data, indent=2)+"\n", encoding="utf-8")
        print(json.dumps(data, indent=2))
