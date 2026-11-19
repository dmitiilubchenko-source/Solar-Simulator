"""Small deterministic fixtures. These tests never call a Solar integrator."""
import ast
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import zipfile
from unittest.mock import patch

import numpy as np
import pytest

from scripts.qualification410e import audit, source_guard, writer


OLD = Path("C:/Users/Admin/Desktop/Solar-packaging-040-4095/scripts/check_portable.py")
WRAPPER = Path(__file__).resolve().parents[1]/"check_portable.py"
NAMES = ["Sun", "Mercury", "Venus", "Earth", "Moon"]
STATS = dict(packets=2, rhs_calls=12, failed=False, finished=True)


def original_difference():
    tree = ast.parse(OLD.read_bytes())
    continuous = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "check_continuous")
    probe = next(n.value.value for n in continuous.body if isinstance(n, ast.Assign))
    function = next(n for n in ast.parse(probe).body if isinstance(n, ast.FunctionDef) and n.name == "difference")
    env = {"np": np}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(OLD), "exec"), env)
    return env["difference"]


@pytest.fixture
def case(tmp_path):
    root = tmp_path/"bundle with spaces"
    for name in (writer.REFERENCE, writer.YEAR_INPUT, writer.CATALOG_INPUT):
        path = root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name, encoding="utf8")
    output = tmp_path/"continuous-year-raw"
    reference = np.arange(60, dtype=np.float64).reshape(2, 5, 6) / 10
    actual = reference + np.arange(60, dtype=np.float64).reshape(2,5,6)*1e-9
    times = np.array([0., 60.])
    sample = dict(year_times=times, year_continuous=reference, year_independent=reference.copy(),
                  catalog_times=times, catalog_continuous=reference.copy())
    before = writer.input_hashes(root)
    provenance = dict(audit.PINS, wrapper_sha256=writer.sha(WRAPPER), writer_sha256=writer.sha(writer.__file__))
    binding = dict(provenance, reference=dict(path=writer.REFERENCE, sha256=before[writer.REFERENCE]),
                   scenario=dict(path=writer.YEAR_INPUT, sha256=before[writer.YEAR_INPUT]),
                   catalog_scenario=dict(path=writer.CATALOG_INPUT, sha256=before[writer.CATALOG_INPUT]))
    old = original_difference()
    stdout = dict(year_reproduction=old(actual, reference),
                  relative_independent=old(actual[:, 4]-actual[:, 3], reference[:, 4]-reference[:, 3]),
                  year_statistics=STATS, catalog_packets=2, catalog_rhs_calls=12,
                  catalog_reproduction=old(actual, reference))
    catalog = root/writer.CATALOG_OUT
    catalog.mkdir()
    epoch = 2461321.5
    rows = [(time, epoch+time/86400, name, *actual[i,j])
            for i,time in enumerate(times) for j,name in enumerate(NAMES)]
    catalog_meta = dict(status="complete", solver_executed=True, experimental=True,
                        automatically_scientifically_qualified=False, packet_steps=20,
                        input_sha256=before[writer.CATALOG_INPUT], native_binary_sha256=provenance["native_sha256"],
                        source_sha256={"continuous.py":"pin"}, sample_times_seconds=times.tolist(),
                        csv_rows=len(rows), packets=2, rhs_calls=12)
    def catalog_write(rows):
        with (catalog/"snapshots.csv").open("w", encoding="utf8", newline="") as f:
            w = csv.writer(f)
            w.writerow(("time_seconds", "epoch_jd_tdb", "name", *writer.COLUMNS))
            w.writerows(rows)
        meta = dict(catalog_meta, output_sha256={"snapshots.csv":writer.sha(catalog/"snapshots.csv")})
        (catalog/"receipt.json").write_text(json.dumps(meta),encoding="utf8")
        return dict(hashes={n:writer.sha(catalog/n) for n in ("receipt.json","snapshots.csv")},
                    input_sha256=before[writer.CATALOG_INPUT], native_sha256=provenance["native_sha256"],
                    source_sha256={"continuous.py":"pin"})
    catalog_pins = catalog_write(rows)
    return dict(root=root, output=output, sample=sample, before=before, actual=actual, times=times, stdout=stdout,
                binding=binding, provenance=provenance, catalog=catalog, catalog_pins=catalog_pins, rows=rows,
                catalog_write=catalog_write, catalog_scenario=dict(bodies=[dict(name=n) for n in NAMES],
                                                                origin=dict(epoch_jd_tdb=epoch)))


def publish(c, states=None):
    writer.write_year(c["output"], c["root"], c["provenance"], c["before"],
                      c["actual"] if states is None else states, c["times"], c["times"], NAMES,
                      c["actual"].shape, c["stdout"]["year_reproduction"],
                      c["stdout"]["relative_independent"], STATS)


def read(c):
    return audit.audit_year(c["output"], c["sample"], c["binding"], NAMES, c["stdout"])


def rewrite_manifest(c, **new):
    p = c["output"]/"manifest.json"
    m = json.loads(p.read_bytes())
    m.update(new)
    p.write_text(json.dumps(m), encoding="utf8")


def rewrite_npz(c, **new):
    p = c["output"]/"year-actual.npz"
    with np.load(p, allow_pickle=False) as old:
        data = {k:old[k] for k in old.files}
    data.update(new)
    np.savez(p, **data)
    rewrite_manifest(c, npz_sha256=writer.sha(p))  # Reach intended field check, beyond the digest.


def test_A_original_maxima_match(case):
    a, e = case["actual"], case["sample"]["year_continuous"]
    assert audit.maxima(a,e) == original_difference()(a,e)
    assert audit.maxima(a[:,4]-a[:,3],e[:,4]-e[:,3]) == original_difference()(a[:,4]-a[:,3],e[:,4]-e[:,3])


def test_B_roundtrip(case):
    publish(case)
    with np.load(case["output"]/"year-actual.npz", allow_pickle=False) as raw:
        assert np.array_equal(raw["states"],case["actual"])
        assert np.array_equal(raw["actual_epochs_seconds"],case["times"])
        assert np.array_equal(raw["requested_epochs_seconds"],case["times"])
        assert raw["body_names"].dtype.kind == "U" and np.array_equal(raw["body_names"], NAMES)
        assert np.array_equal(raw["state_columns"],writer.COLUMNS)


def test_C_recompute_from_published_arrays(case):
    publish(case)
    _, result = read(case)
    assert result["year"] == case["stdout"]["year_reproduction"]
    assert result["relative"] == case["stdout"]["relative_independent"]


def test_D_body_permutation(case):
    publish(case)
    rewrite_npz(case, body_names=np.asarray(NAMES[::-1]))
    with pytest.raises(ValueError, match="Body names or order"):
        read(case)


@pytest.mark.parametrize("epochs", [[60., 0.], [0.], [0., 0.]])
def test_E_epoch_permutation_missing_duplicate(case, epochs):
    publish(case)
    rewrite_npz(case, actual_epochs_seconds=np.array(epochs))
    with pytest.raises(ValueError, match="Actual epoch grid"):
        read(case)


@pytest.mark.parametrize("key", ["reference", "wrapper_sha256"])
def test_F_G_wrong_source_pins(case, key):
    publish(case)
    rewrite_manifest(case, **{key:"0"*64})
    with pytest.raises(ValueError, match=f"provenance mismatch: {key}"):
        read(case)


def test_H_truncated_with_matching_digest(case):
    publish(case)
    p = case["output"]/"year-actual.npz"
    p.write_bytes(p.read_bytes()[:37])
    rewrite_manifest(case, npz_sha256=writer.sha(p))
    with pytest.raises(zipfile.BadZipFile):
        read(case)


def test_I_object_array(case):
    publish(case)
    rewrite_npz(case, states=case["actual"].astype(object))
    with pytest.raises(ValueError, match="Object arrays cannot be loaded"):
        read(case)


def test_J_wrong_npz_digest(case):
    publish(case)
    rewrite_manifest(case, npz_sha256="0"*64)
    with pytest.raises(ValueError, match="NPZ SHA mismatch"):
        read(case)


def test_K_missing_manifest(case):
    case["output"].mkdir()
    with pytest.raises(FileNotFoundError, match="manifest.json"):
        read(case)


def test_L_manifest_incomplete(case):
    publish(case)
    rewrite_manifest(case, complete=False)
    with pytest.raises(ValueError, match="not a completion marker"):
        read(case)


@pytest.mark.parametrize("phase", ["write", "fsync", "replace"])
def test_M_npz_failure(case, phase):
    target = np if phase == "write" else writer.os
    attr = "savez" if phase=="write" else phase
    with patch.object(target, attr, side_effect=OSError(f"NPZ {phase} injected")) as hook:
        with pytest.raises(OSError, match=f"NPZ {phase} injected"):
            publish(case)
        hook.assert_called_once()
    assert (case["output"]/"year-actual.npz.partial").exists()
    assert not (case["output"]/"year-actual.npz").exists()
    assert not (case["output"]/"manifest.json").exists()


@pytest.mark.parametrize("phase", ["write", "replace"])
def test_N_manifest_failure_after_npz(case, phase):
    if phase == "write":
        original = Path.open
        def fail(path, *args, **kwargs):
            if path.name == "manifest.json.partial":
                raise OSError("manifest write injected")
            return original(path, *args, **kwargs)
        obj, attribute = Path, "open"
    else:
        original = writer.os.replace
        def fail(src, dst):
            if dst.name == "manifest.json":
                raise OSError("manifest replace injected")
            return original(src,dst)
        obj, attribute = writer.os, "replace"
    with patch.object(obj, attribute, fail):
        with pytest.raises(OSError, match=f"manifest {phase} injected"):
            publish(case)
    assert (case["output"]/"year-actual.npz").is_file()
    assert not (case["output"]/"manifest.json").exists()


def test_O_collision_refused_without_overwrite(case):
    publish(case)
    old = {p.name:p.read_bytes() for p in case["output"].iterdir()}
    with pytest.raises(FileExistsError):
        publish(case)
    assert {p.name:p.read_bytes() for p in case["output"].iterdir()} == old


@pytest.mark.parametrize("bad", [np.nan, np.inf])
def test_P_nonfinite_rejected_on_write_and_read(case, bad):
    states = case["actual"].copy()
    states[0,0,0] = bad
    with pytest.raises(ValueError, match="Invalid evidence state"):
        publish(case, states=states)
    publish(case)
    rewrite_npz(case, states=states)
    with pytest.raises(ValueError, match="finiteness"):
        read(case)


def test_Q_reference_relabelled_as_actual_with_wrong_origin(case):
    publish(case)
    rewrite_npz(case, states=case["sample"]["year_continuous"])
    rewrite_manifest(case, capture="copied_reference")
    with pytest.raises(ValueError, match="capture metadata"):
        read(case)


def test_R_corrupt_stdout_aggregate(case):
    publish(case)
    case["stdout"]["year_reproduction"]["position_metres"] += 1e-3
    with pytest.raises(ValueError, match="Year aggregate mismatch"):
        read(case)


@pytest.mark.parametrize("mutation,reason", [("missing","row count"),("duplicate","body order"),
                                            ("reordered","body order"),("epoch","epoch mismatch")])
def test_S_catalog_rows_checked_before_reshape(case, mutation, reason):
    rows = case["rows"].copy()
    if mutation=="missing":
        rows.pop()
    elif mutation=="duplicate":
        rows[1]=rows[0]
    elif mutation=="reordered":
        rows[1],rows[2]=rows[2],rows[1]
    else:
        rows[0]=(99., *rows[0][1:])
    pins = case["catalog_write"](rows)
    with pytest.raises(ValueError, match=reason):
        audit.audit_catalog(case["catalog"],case["sample"],case["catalog_scenario"],pins,case["stdout"])


def test_T_catalog_minimal_agrees_with_old(case):
    result = audit.audit_catalog(case["catalog"],case["sample"],case["catalog_scenario"],
                                 case["catalog_pins"],case["stdout"])
    assert result["metrics"] == case["stdout"]["catalog_reproduction"]
    assert (result["rows"],result["epochs"],result["bodies"]) == (10,2,5)


def test_actual_isolated_writer_argv_and_nonzero_on_collision(case):
    # Invoke the same runpy loading convention in an isolated CPython child, with
    # synthetic arrays only. The child cannot import or execute a Solar solver.
    descriptor = case["root"]/"fixture.json"
    descriptor.write_text(json.dumps(dict(provenance=case["provenance"],before=case["before"],
        states=case["actual"].tolist(),times=case["times"].tolist(),names=NAMES,stdout=case["stdout"])),
        encoding="utf8")
    code = """import json,numpy as np,pathlib,runpy,sys
w=runpy.run_path(sys.argv[1]); root=pathlib.Path.cwd()
d=json.loads((root/'fixture.json').read_bytes()); a=np.array(d['states']); t=np.array(d['times'])
s=d['stdout']; w['write_year'](sys.argv[2],root,d['provenance'],d['before'],a,t,t,d['names'],a.shape,s['year_reproduction'],s['relative_independent'],s['year_statistics'])"""
    command = [sys.executable, "-I", "-B", "-c", code, writer.__file__, str(case["output"])]
    subprocess.run(command, cwd=case["root"], check=True, capture_output=True, timeout=10)
    read(case)
    repeated = subprocess.run(command, cwd=case["root"], capture_output=True, timeout=10)
    assert repeated.returncode != 0 and b"FileExistsError" in repeated.stderr


def test_exact_capture_loop_keeps_existing_samples(case):
    tree = ast.parse(WRAPPER.read_bytes())
    probe = ast.parse(source_guard.func(tree, "check_continuous").body[1].value.value)
    begin = next(i for i,n in enumerate(probe.body) if ast.unparse(n).startswith("session = ContinuousRun"))
    end = next(i for i,n in enumerate(probe.body) if isinstance(n,ast.If)
               and ast.unparse(n.body[0]).startswith("evidence_api['write_year']"))
    calls = []
    snapshots = []
    for epoch, rows in zip(case["times"], case["actual"]):
        bodies = [SimpleNamespace(name=name, position=SimpleNamespace(x=row[0],y=row[1],z=row[2]),
                                  velocity=SimpleNamespace(x=row[3],y=row[4],z=row[5]))
                  for name,row in zip(NAMES, rows)]
        snapshots.append(SimpleNamespace(time=epoch,bodies=bodies))

    class SyntheticSession:
        def __init__(self, seed, target):
            assert seed is snapshots[0] and target == case["times"][-1]
            self.current = seed
            self.statistics = STATS

        def next(self, packet_steps, *, until):
            calls.append((packet_steps, until))
            self.current = snapshots[1]

    extra = [source_guard.func(probe,"matrix"),source_guard.func(probe,"difference")]
    tree = ast.Module(body=extra+probe.body[begin:end+1], type_ignores=[])
    env = dict(np=np, ContinuousRun=SyntheticSession, seed=snapshots[0], sample=case["sample"],
               evidence_api={"write_year":writer.write_year}, sys=SimpleNamespace(argv=["-c","writer",case["output"]]),
               root=case["root"], provenance=case["provenance"], inputs_before=case["before"],
               actual_epochs_seconds=[])
    exec(compile(tree, str(WRAPPER), "exec"), env)
    assert calls == [(20,60.)]
    read(case)


def test_catalog_hashes_checked_before_rows(case):
    (case["catalog"]/"snapshots.csv").write_text("different bytes")
    with pytest.raises(ValueError, match="Catalog snapshots.csv SHA mismatch"):
        audit.audit_catalog(case["catalog"],case["sample"],case["catalog_scenario"],
                            case["catalog_pins"],case["stdout"])


def test_frozen_wrapper_numerical_ast_and_unrelated_bytes():
    assert source_guard.verify()[0]["continuous_numerical_AST_equal"]
