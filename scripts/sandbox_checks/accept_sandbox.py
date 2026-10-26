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


CURRENT_RECEIPT = "docs/current-runtime-375-validation.json"
CURRENT_RECEIPT_SHA = "e7d8d97f0a17a142cb4cc1203792fd8cc174fe0bc61a403538de9a524a42f9d6"


def check_receipts(root=ROOT):
    """Require new measured evidence and exact current sources/environment.

    Historical grid/Strict reports are immutable inputs, not today's source
    authorization. No historical source resolver is used here.
    """
    root = Path(root).resolve()
    path = root/CURRENT_RECEIPT
    if hashlib.sha256(path.read_bytes()).hexdigest() != CURRENT_RECEIPT_SHA:
        raise ValueError("Current scientific receipt changed: "+CURRENT_RECEIPT)
    receipt = json.loads(path.read_bytes())
    bindings = {**receipt["source_sha256"], **receipt["input_sha256"],
        receipt["protocol"]:receipt["protocol_sha256"],
        receipt["array_archive"]:receipt["array_sha256"]}
    for name, expected in bindings.items():
        source = (root/name).resolve()
        if (not source.is_relative_to(root) or not source.is_file()
                or hashlib.sha256(source.read_bytes()).hexdigest() != expected):
            raise ValueError("Scientific receipt source/input changed: "+name)
    if (receipt["current_runtime_qualified"] is not True
            or receipt["solver_executed"] is not True or receipt["failed_criteria"]
            or not receipt["gates"] or any(type(v) is not bool or not v for v in receipt["gates"].values())):
        raise ValueError("Current qualification failed")
    from solar_simulator.recipe import runtime_fingerprint
    environment = runtime_fingerprint("rust")
    environment.pop("package_files")  # Executed modules/data are checked above against root.
    if environment != receipt["environment"]:
        raise ValueError("Qualified numerical environment/native changed")
    failed = json.loads((root/"docs/qualification-grid-validation.json").read_bytes())
    strict = json.loads((root/"docs/strict-profile-validation.json").read_bytes())
    if (failed["checks_passed"] is not False or strict["checks_passed"] is not True
            or receipt["original_failure_retained"] is not True):
        raise ValueError("Original failure or historical Strict qualification changed")
    return dict(current_qualification_passed=True, original_failure_retained=True,
        new_jpl_epochs_checked=receipt["jpl_new_epochs_checked"],
        reports=[CURRENT_RECEIPT,"docs/qualification-grid-validation.json",
                 "docs/strict-profile-validation.json","docs/sandbox-limits-validation.json"],
        runtime_commit=receipt["runtime_commit"], scope="qualification375 measured desktop environment")


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
