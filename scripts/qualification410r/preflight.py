"""Read only the qualified input bytes. Never extract a package or run a solver."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import time
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RAW = Path("C:/Users/Admin/Documents/Codex/Solar 410R 20261119")
PACKAGING = Path("C:/Users/Admin/Desktop/Solar-packaging-040-4095")
RUNTIME = Path("C:/Users/Admin/Desktop/Solar-candidate-040-version-407v")
SUPERVISOR = Path("C:/Users/Admin/Desktop/Solar-tooling-4103")
ORIGINAL = Path("C:/Users/Admin/Desktop/Solar-simulator")
WHEEL = Path("C:/Users/Admin/Documents/Codex/Solar407V-20261111/wheels/solar_native-0.4.0-cp314-cp314t-win_amd64.whl")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(path):
    return sha(Path(path).read_bytes())


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True, timeout=10).strip()


def run():
    cpu, wall = time.process_time(), time.perf_counter()
    plan_file = HERE / "execution-plan.json"
    plan = json.loads(plan_file.read_bytes())
    pins = plan["bindings"]
    assert (RAW / plan_file.name).read_bytes() == plan_file.read_bytes()
    assert digest(ROOT / "scripts/qualification410/execution-plan.json") == plan["sealed_parent_sha"]
    assert digest(ROOT / "scripts/qualification4103/admission-amendment410-v3.json") == plan["amendment_sha"]
    for folder, commit in ((PACKAGING, pins["packaging_commit"]), (RUNTIME, pins["source_commit"]),
                           (SUPERVISOR, pins["supervisor_tip"]), (ORIGINAL, "ebde749d11405c0fdeca640d9d515be6db61a59b")):
        assert git(folder, "rev-parse", "HEAD") == commit
        assert not git(folder, "status", "--porcelain")
    assert git(RUNTIME, "rev-parse", "HEAD^{tree}") == pins["source_tree"]
    git(SUPERVISOR, "merge-base", "--is-ancestor", pins["supervisor_commit"], pins["supervisor_tip"])
    checked = {}
    for name, key in (("monitor.py", "qualified_supervisor_sha"), ("consumer.py", "receipt_consumer_sha"),
                      ("audit.py", "auditor_4103_sha")):
        path = SUPERVISOR / "scripts/qualification4103" / name
        digest_actual = digest(path)
        assert digest_actual == pins[key] == digest(HERE.parent / "qualification4103" / name)
        checked[name] = digest_actual
    wrapper = Path(pins["acceptance_tool"]["path"])
    assert wrapper == PACKAGING/"scripts/check_portable.py"
    assert digest(wrapper) == pins["acceptance_tool"]["SHA256"]
    assert plan["command"][4] == str(wrapper) and plan["command"][6:] == [
        "--current040-manifest-sha256", pins["current_manifest_SHA256"]]
    a = pins["archive"]
    archive = Path(a["archive"])
    assert archive.stat().st_size == a["archive_size"] == 114633711 and digest(archive) == a["archive_SHA256"]
    contract = archive.with_name("asset-contract.json")
    assert digest(contract) == a["asset_contract_SHA256"]
    assets = json.loads(contract.read_bytes())
    hashes = {}
    with zipfile.ZipFile(archive) as zf:
        assert len(zf.infolist()) == 6005 == len(assets["files"])
        for member in zf.infolist():
            parts = PurePosixPath(member.filename).parts
            assert parts[0] == assets["root"] and len(parts) > 1 and ".." not in parts
            assert "\\" not in member.filename and ":" not in member.filename
            assert not stat.S_ISLNK(member.external_attr >> 16)
            relative = "/".join(parts[1:])
            assert relative not in hashes
            expected = assets["files"][relative]
            blob = zf.read(member)  # ZipExtFile verifies CRC when read to EOF.
            hashes[relative] = sha(blob)
            assert len(blob) == expected["size"] and hashes[relative] == expected["sha256"]
    assert set(hashes) == set(assets["files"])
    for name, key in (("verification-current040/manifest-v1.json", "current_manifest_SHA256"),
                      ("verification-current040/recompute_current040_v1.py", "current_verifier_SHA256"),
                      ("verification/recompute_jpl.py", "historical_verifier_SHA256")):
        assert hashes[name] == pins[key]
    native = [value for name, value in hashes.items() if "/solar_native/" in name and name.endswith(".pyd")]
    assert native == [pins["native_SHA256"]]
    assert digest(WHEEL) == pins["wheel_SHA256"] and "cp314-cp314t-win_amd64" in WHEEL.name
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[name] = "1"
    for name in ("PYTHONPATH", "PYTHONHOME", "PYTHONHASHSEED"):
        os.environ.pop(name, None)
    from solar_simulator.recipe import runtime_fingerprint
    fp = sha((json.dumps(runtime_fingerprint("rust"), indent=2) + "\n").encode())
    assert fp == pins["source_environment_fingerprint"]
    assert not (PACKAGING / ".tools").exists()
    assert not any(Path(plan["output"][name]).exists() for name in ("guard", "temp"))
    free = shutil.disk_usage(archive.parent).free
    assert free > 4*1024**3
    result = dict(identity="PASS", members_crc_size_sha_verified=len(hashes), source_fingerprint=fp,
                  archive_sha=a["archive_SHA256"], asset_contract_sha=digest(contract), wheel_sha=digest(WHEEL),
                  native_sha=native[0], wrapper_sha=digest(wrapper), tooling_sha=checked,
                  plan_sha=digest(plan_file), host_python=sys.version.splitlines()[0],
                  free_disk_bytes=free, attempt_started=False, packaging_output_exists=False,
                  cpu_seconds=time.process_time()-cpu, wall_seconds=time.perf_counter()-wall)
    with (RAW / "input-preflight.json").open("x", encoding="utf8") as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result))


if __name__ == "__main__":
    run()
