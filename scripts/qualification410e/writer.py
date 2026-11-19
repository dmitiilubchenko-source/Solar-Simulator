"""Publish external evidence from an already evaluated portable acceptance loop."""
import hashlib
from importlib.util import find_spec
import json
import os
from pathlib import Path


SCHEMA = "solar-continuous-year-evidence-v1"
COLUMNS = ("x_m", "y_m", "z_m", "vx_m_s", "vy_m_s", "vz_m_s")
UNITS = ("m", "m", "m", "m/s", "m/s", "m/s")
YEAR_INPUT = "scenarios/solar-sandbox-strict.json"
REFERENCE = "docs/continuous-integration-reference.npz"
CATALOG_INPUT = "scenarios/solar-system-asteroids-catalog-rust-1pn-solar-q2-relative.json"
CATALOG_OUT = "continuous-catalog-check"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def input_hashes(root):
    return {name: sha(root/name) for name in (REFERENCE, YEAR_INPUT, CATALOG_INPUT)}


def observe_inputs(root, provenance):
    """Bind the exact files the child is about to use and its loaded native module."""
    import solar_native

    native = Path(find_spec(solar_native.point_acceleration.__module__).origin).resolve()
    if not native.is_relative_to(root/"runtime") or sha(native) != provenance["native_sha256"]:
        raise ValueError("Loaded native does not match sealed package")
    return input_hashes(root)


def _atomic_write(path, write, validate=None):
    partial = path.with_suffix(path.suffix + ".partial")
    with partial.open("xb") as stream:
        write(stream)
        stream.flush()
        os.fsync(stream.fileno())
    if validate is not None:
        validate(partial)
    os.replace(partial, path)


def write_year(output, root, provenance, before, states, epochs, requested, names,
               expected_shape, year, relative, statistics):
    """Preserve partial artifacts on failure. Only the final manifest marks completion."""
    import numpy as np

    output = Path(output).resolve()
    root = Path(root).resolve()
    if output.is_relative_to(root):
        raise ValueError("Evidence output must be outside the extracted package")
    if input_hashes(root) != before:
        raise ValueError("Evidence inputs changed during the calculation")
    if sha(Path(__file__)) != provenance["writer_sha256"]:
        raise ValueError("Evidence writer changed during the calculation")
    names = tuple(names)
    if len(set(names)) != len(names) or names[3:5] != ("Earth", "Moon"):
        raise ValueError("Evidence body order must identify Earth and Moon")
    arrays = dict(states=np.asarray(states), actual_epochs_seconds=np.asarray(epochs),
                  requested_epochs_seconds=np.asarray(requested),
                  body_names=np.asarray(names, dtype="U"),
                  state_columns=np.asarray(COLUMNS, dtype="U"))
    if (states.shape != tuple(expected_shape) or states.shape != (len(requested), len(names), 6)
            or any(arrays[k].dtype != np.dtype("float64") or not np.isfinite(arrays[k]).all()
                   for k in ("states", "actual_epochs_seconds", "requested_epochs_seconds"))):
        raise ValueError("Invalid evidence state or epoch array")
    if (arrays["requested_epochs_seconds"].ndim != 1
            or not (np.diff(arrays["requested_epochs_seconds"]) > 0).all()
            or not np.array_equal(arrays["actual_epochs_seconds"], arrays["requested_epochs_seconds"])):
        raise ValueError("Actual epochs differ from the requested grid")

    catalog = root / CATALOG_OUT
    catalog_hashes = {name: sha(catalog/name) for name in ("snapshots.csv", "receipt.json")}
    catalog_receipt = json.loads((catalog/"receipt.json").read_bytes())
    if catalog_receipt["output_sha256"]["snapshots.csv"] != catalog_hashes["snapshots.csv"]:
        raise ValueError("Catalog CSV differs from the completed solver receipt")

    def validate(path):
        with np.load(path, allow_pickle=False) as saved:
            if set(saved.files) != set(arrays) or any(
                saved[key].dtype != item.dtype or not np.array_equal(saved[key], item)
                for key, item in arrays.items()
            ):
                raise ValueError("Evidence NPZ readback failed")

    output.mkdir(exist_ok=False)
    raw = output/"year-actual.npz"
    _atomic_write(raw, lambda stream: np.savez(stream, **arrays), validate)
    manifest = dict(
        evidence_schema=SCHEMA, complete=True, **provenance,
        reference=dict(path=REFERENCE, sha256=before[REFERENCE]),
        scenario=dict(path=YEAR_INPUT, sha256=before[YEAR_INPUT]),
        catalog_scenario=dict(path=CATALOG_INPUT, sha256=before[CATALOG_INPUT]),
        catalog_outputs=catalog_hashes, packet_steps=20, units=list(UNITS),
        arrays={name:dict(shape=list(item.shape), dtype=str(item.dtype)) for name, item in arrays.items()},
        body_names=list(names), state_columns=list(COLUMNS),
        npz_sha256=sha(raw), year_reproduction=year, relative_independent=relative,
        year_statistics=statistics, output_directory=str(output),
        capture="actual_states_from_same_continuous_integration",
    )
    data = (json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf8")
    _atomic_write(output/"manifest.json", lambda stream: stream.write(data))
