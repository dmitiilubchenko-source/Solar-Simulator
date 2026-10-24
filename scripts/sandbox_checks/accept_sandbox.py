"""Short reproducible acceptance of physics, provenance and checkpoint workflows."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from time import perf_counter

from scripts.assess_sandbox_limits import assess
from solar_simulator.branch_io import open_experiment
from solar_simulator.sandbox import branch_experiment, save_branch, load_branch
from solar_simulator.simulation import Body
from solar_simulator.state_export import export_state
from solar_simulator.storage import load, save, to_document
from solar_simulator.time_control import advance_towards
from solar_simulator.vector3 import Vector3

ROOT = Path(__file__).resolve().parents[2]


def check_receipts(root=ROOT):
    names = ("qualification-grid-validation.json", "strict-profile-validation.json", "sandbox-limits-validation.json")
    receipts = {}
    for name in names:
        receipt = json.loads((root/"docs"/name).read_bytes())
        for source, expected in receipt["source_sha256"].items():
            if hashlib.sha256((root/source).read_bytes()).hexdigest() != expected:
                raise ValueError("Scientific receipt source changed: "+source)
        receipts[name] = receipt
    strict = receipts["strict-profile-validation.json"]
    if not strict["checks_passed"] or not receipts["sandbox-limits-validation.json"]["checks_passed"]:
        raise ValueError("Current qualification failed")
    if hashlib.sha256((root/"docs/qualification-grid-validation.json").read_bytes()).hexdigest() != strict["before_report_sha256"]:
        raise ValueError("Original failure audit changed")
    if hashlib.sha256((root/"docs/solar-sandbox-strict-checkpoint.json").read_bytes()).hexdigest() != strict["checkpoint_sha256"]:
        raise ValueError("Strict initial checkpoint changed")
    for name in ("solar-system-reference.json", "solar-system-moon-reference.json"):
        expected = receipts["qualification-grid-validation.json"]["reference_sha256"]["docs/"+name]
        if hashlib.sha256((root/"docs"/name).read_bytes()).hexdigest() != expected:
            raise ValueError("Pinned JPL benchmark changed")
    return dict(current_qualification_passed=True, original_failure_retained=True,
        new_jpl_epochs_checked=strict["jpl_new_epochs_checked"], reports=list(names))


def workflows():
    state = load(ROOT/"docs/solar-sandbox-strict-checkpoint.json")
    start = to_document(state)
    while state.time < 10000.25:state = advance_towards(state, 10000.25)
    assert state.time == 10000.25 and state.settings.rtol == 3e-14
    with tempfile.TemporaryDirectory(prefix="solar-acceptance-") as folder:
        folder = Path(folder)
        save(state, folder/"checkpoint.json")
        restored = load(folder/"checkpoint.json")
        assert to_document(advance_towards(restored, 20000.5)) == to_document(advance_towards(state, 20000.5))
        addition = Body("Acceptance body", 5.9722e24, Vector3(0., 0., 3e11), Vector3(17000., 0., 0.))
        branch = branch_experiment(state, additions=(addition,))
        save_branch(branch, folder/"branch.json")
        restored_branch = load_branch(folder/"branch.json")
        assert to_document(restored_branch.parent) == to_document(state)
        opened, parent_snapshot = open_experiment(folder/"branch.json")
        assert to_document(opened) == to_document(branch.child)
        assert parent_snapshot == branch.parent_snapshot
        export_state(branch.child, folder/"state.csv")
        import csv
        with (folder/"state.csv").open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        assert len(rows) == 11 and rows[-1]["name"] == "Acceptance body"
        assert to_document(restored_branch.child) == to_document(branch.child)
    assert to_document(load(ROOT/"docs/solar-sandbox-strict-checkpoint.json")) == start
    return dict(exact_target_seconds=state.time, checkpoint_continue_exact=True,
        branch_parent_preserved=True, branch_addition_bodies=11, csv_rows=11, initial_unchanged=True)


def run():
    start = perf_counter()
    receipt = check_receipts()
    analytic = [assess("mass-double", backend) for backend in ("python", "rust")]
    assert all(row["checks_passed"] for row in analytic)
    journeys = workflows()
    return dict(checks_passed=True, scientific_receipts=receipt, analytic=analytic,
        workflows=journeys, wall_seconds=perf_counter()-start,
        limitations="Short acceptance, not a new year propagation or universal accuracy bound. No rendering benchmark; full tests and isolated portable checked separately.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output is not None and args.output.exists():raise FileExistsError("Preserve prior receipt")
    result = run()
    if args.output is not None:args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":main()
