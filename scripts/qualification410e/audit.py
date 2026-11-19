"""Independently audit continuous artifacts produced by the exact portable wrapper."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile

import numpy as np


SCHEMA = "solar-continuous-year-evidence-v1"
COLUMNS = ("x_m", "y_m", "z_m", "vx_m_s", "vy_m_s", "vz_m_s")
UNITS = ("m", "m", "m", "m/s", "m/s", "m/s")
REFERENCE = "docs/continuous-integration-reference.npz"
YEAR_SCENARIO = "scenarios/solar-sandbox-strict.json"
CATALOG_SCENARIO = "scenarios/solar-system-asteroids-catalog-rust-1pn-solar-q2-relative.json"
CURRENT_MANIFEST = "verification-current040/manifest-v1.json"
PINS = {
    "portable_sha256": "33114f5ac2234e01e1e248fae757187a50a81020e2b225ee6b746e28e1073e33",
    "runtime_commit": "237f73612c3c159acf92b32a15cf0289958fd921",
    "runtime_tree": "5cf43fd9c5bb7d0d80a427d8a6d11ec8b81cb8e9",
    "native_sha256": "a2b7e07573720a269efc712ee4fb74dcc747d24a4967d72d4c3d812158b3399b",
    "current_manifest_sha256": "9251bc2e05381f16c197168c3b80035d2f07e03f35b27698e6feeb532465120b",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return digest(path.read_bytes())


def require(condition, error):
    if not condition:
        raise ValueError(error)


def maxima(actual, expected):
    delta = actual - expected
    squared = np.square(delta)
    return {name: float(np.sqrt(np.add.reduce(squared[..., cols], axis=-1)).max())
            for name, cols in (("position_metres", slice(0, 3)), ("velocity_m_per_s", slice(3, 6)))}


def compare(data, claimed, position, velocity, label):
    require(data["position_metres"] < position and data["velocity_m_per_s"] < velocity,
            f"{label} thresholds")
    require(data == claimed, f"{label} aggregate mismatch")


def audit_year(output, sample, expected, names, stdout):
    manifest = json.loads((output/"manifest.json").read_bytes())
    require(manifest.get("evidence_schema") == SCHEMA and manifest.get("complete") is True,
            "Evidence manifest is not a completion marker")
    for key, value in expected.items():
        require(manifest.get(key) == value, f"Evidence provenance mismatch: {key}")
    require(manifest.get("packet_steps") == 20 and manifest.get("units") == list(UNITS)
            and manifest.get("output_directory") == str(output.resolve())
            and manifest.get("capture") == "actual_states_from_same_continuous_integration",
            "Evidence capture metadata mismatch")
    raw = output/"year-actual.npz"
    require(sha(raw) == manifest.get("npz_sha256"), "NPZ SHA mismatch")
    with np.load(raw, allow_pickle=False) as archive:
        required = {"states", "actual_epochs_seconds", "requested_epochs_seconds", "body_names", "state_columns"}
        require(len(archive.files) == len(required) and set(archive.files) == required, "Unexpected NPZ fields")
        arrays = {key: archive[key] for key in required}
    states = arrays["states"]
    requested = arrays["requested_epochs_seconds"]
    actual_epochs = arrays["actual_epochs_seconds"]
    for key in ("states", "actual_epochs_seconds", "requested_epochs_seconds"):
        values = arrays[key]
        require(values.dtype == np.dtype("float64") and np.isfinite(values).all(), f"Invalid dtype or finiteness: {key}")
    expected_shape = (len(sample["year_times"]), len(names), len(COLUMNS))
    require(states.shape == sample["year_continuous"].shape == sample["year_independent"].shape == expected_shape,
            "State shape mismatch")
    require(requested.ndim == 1 and np.array_equal(requested, sample["year_times"])
            and (np.diff(requested) > 0).all(), "Requested epoch grid mismatch")
    require(np.array_equal(actual_epochs, requested), "Actual epoch grid mismatch")
    require(len(set(names)) == len(names) and names[3:5] == ["Earth", "Moon"],
            "Pinned scenario must identify indices 3 and 4 as Earth and Moon")
    require(arrays["body_names"].dtype.kind == "U" and arrays["body_names"].tolist() == names
            and manifest["body_names"] == names, "Body names or order mismatch")
    require(arrays["state_columns"].dtype.kind == "U" and arrays["state_columns"].tolist() == list(COLUMNS)
            and manifest["state_columns"] == list(COLUMNS), "State columns mismatch")
    require(manifest["arrays"] == {key: dict(shape=list(value.shape), dtype=str(value.dtype))
                                  for key, value in arrays.items()}, "Array metadata mismatch")

    year = maxima(states, sample["year_continuous"])
    independent = sample["year_independent"]
    relative = maxima(states[:, 4]-states[:, 3], independent[:, 4]-independent[:, 3])
    compare(year, stdout["year_reproduction"], .1, 1e-6, "Year")
    compare(relative, stdout["relative_independent"], .1, 1e-5, "Moon–Earth")
    require(manifest["year_reproduction"] == year and manifest["relative_independent"] == relative,
            "Manifest aggregate mismatch")
    stats = manifest["year_statistics"]
    require(stats == stdout["year_statistics"] and stats["finished"] is True and stats["failed"] is False
            and stats["packets"] > 0 and stats["rhs_calls"] > 0, "Year solver statistics mismatch")
    return manifest, dict(year=year, relative=relative, epochs=len(requested), bodies=len(names))


def audit_catalog(output, sample, catalog_scenario, pins, stdout):
    for file in ("receipt.json", "snapshots.csv"):
        require(sha(output/file) == pins["hashes"][file], f"Catalog {file} SHA mismatch")
    receipt = json.loads((output/"receipt.json").read_bytes())
    times = sample["catalog_times"]
    reference = sample["catalog_continuous"]
    names = [body["name"] for body in catalog_scenario["bodies"]]
    require(len(names) == len(set(names)) and reference.shape == (len(times), len(names), len(COLUMNS)),
            "Pinned catalog reference/body shape mismatch")
    require(receipt["status"] == "complete" and receipt["solver_executed"] is True
            and receipt["experimental"] is True and receipt["automatically_scientifically_qualified"] is False
            and receipt["packet_steps"] == 20 and receipt["input_sha256"] == pins["input_sha256"]
            and receipt["native_binary_sha256"] == pins["native_sha256"]
            and receipt["source_sha256"] == pins["source_sha256"]
            and receipt["output_sha256"]["snapshots.csv"] == pins["hashes"]["snapshots.csv"]
            and receipt["sample_times_seconds"] == times.tolist()
            and receipt["csv_rows"] == len(times)*len(names), "Catalog receipt binding mismatch")
    require(receipt["packets"] == stdout["catalog_packets"] and receipt["rhs_calls"] == stdout["catalog_rhs_calls"]
            and receipt["packets"] > 0 and receipt["rhs_calls"] > 0, "Catalog solver statistics mismatch")

    rows = []
    base_epoch = catalog_scenario["origin"]["epoch_jd_tdb"]
    with (output/"snapshots.csv").open(encoding="utf8", newline="") as stream:
        reader = csv.DictReader(stream)
        header = reader.fieldnames or []
        require(len(set(header)) == len(header)
                and {"time_seconds", "epoch_jd_tdb", "name", *COLUMNS}.issubset(header),
                "Catalog CSV columns mismatch")
        for index, row in enumerate(reader):
            group, body = divmod(index, len(names))
            require(group < len(times), "Catalog row count mismatch")
            t = float(times[group])
            require(row["name"] == names[body], f"Catalog body order mismatch at row {index+1}")
            require(float(row["time_seconds"]) == t and float(row["epoch_jd_tdb"]) == base_epoch+t/86400,
                    f"Catalog epoch mismatch at row {index+1}")
            rows.append([float(row[key]) for key in COLUMNS])
    require(len(rows) == len(times)*len(names), "Catalog row count mismatch")
    actual = np.array(rows, dtype=np.float64)
    require(np.isfinite(actual).all(), "Catalog state is nonfinite")
    computed = maxima(actual.reshape(reference.shape), reference)
    compare(computed, stdout["catalog_reproduction"], .1, 1e-6, "Catalog")
    return dict(metrics=computed, rows=len(rows), epochs=len(times), bodies=len(names))


def load_bindings(archive, bundle=None):
    require(archive.stat().st_size == 114633711 and sha(archive) == PINS["portable_sha256"], "Portable ZIP pin mismatch")
    with zipfile.ZipFile(archive) as package:
        require(len(package.infolist()) == 6005, "Portable member count mismatch")
        prefix = package.namelist()[0].split("/")[0] + "/"
        inputs = {name:package.read(prefix+name) for name in
                  (REFERENCE, YEAR_SCENARIO, CATALOG_SCENARIO, CURRENT_MANIFEST)}
        require(digest(inputs[CURRENT_MANIFEST]) == PINS["current_manifest_sha256"], "Current manifest pin mismatch")
        current = json.loads(inputs[CURRENT_MANIFEST])
        require(current["source_commit"] == PINS["runtime_commit"] and current["source_tree"] == PINS["runtime_tree"]
                and current["native_SHA256"] == PINS["native_sha256"], "Runtime/native pin mismatch")
        native = [entry for entry in current["runtime_files"] if "/solar_native/" in entry and entry.endswith(".pyd")]
        require(len(native) == 1, "Native package member is ambiguous")
        member = "runtime/" + native[0]
        require(digest(package.read(prefix+member)) == PINS["native_sha256"], "Native package bytes mismatch")
        if bundle is not None:
            for name, blob in inputs.items():
                require((bundle/name).read_bytes() == blob, f"Relocated input mismatch: {name}")
            require(sha(bundle/member) == PINS["native_sha256"], "Relocated native bytes mismatch")
        source = {Path(name).name: value for name,value in current["runtime_files"].items()
                  if "/solar_simulator/" in name}
    with np.load(io.BytesIO(inputs[REFERENCE]), allow_pickle=False) as reference:
        sample = {key:reference[key] for key in reference.files}
    require(sample["year_continuous"].shape == (125,10,6) and sample["catalog_continuous"].shape == (11,354,6),
            "Pinned reference dimensions mismatch")
    for field in ("year_times", "catalog_times", "year_continuous", "year_independent", "catalog_continuous"):
        require(sample[field].dtype == np.dtype("float64") and np.isfinite(sample[field]).all(),
                "Pinned reference array invalid")
    bindings = dict(PINS, reference=dict(path=REFERENCE, sha256=digest(inputs[REFERENCE])),
                    scenario=dict(path=YEAR_SCENARIO, sha256=digest(inputs[YEAR_SCENARIO])),
                    catalog_scenario=dict(path=CATALOG_SCENARIO, sha256=digest(inputs[CATALOG_SCENARIO])))
    sources = {name:source[name] for name in ("continuous.py", "continuous_cli.py", "accuracy.py", "native_forces.py",
                                            "coordinates.py", "error_control.py", "oblateness.py", "orientation.py")}
    return bindings, sample, json.loads(inputs[YEAR_SCENARIO]), json.loads(inputs[CATALOG_SCENARIO]), sources


def audit_portable(archive, bundle, wrapper, wrapper_pin, writer, writer_pin, log):
    require(sha(wrapper) == wrapper_pin, "Wrapper SHA mismatch")
    require(sha(writer) == writer_pin, "Writer SHA mismatch")
    bindings, sample, year, catalog, sources = load_bindings(archive, bundle)
    bindings.update(wrapper_sha256=wrapper_pin, writer_sha256=writer_pin)
    stdout, offset = json.JSONDecoder().raw_decode(log.read_text(encoding="utf8").lstrip())
    footer = log.read_text(encoding="utf8").lstrip()[offset:].strip()
    require(footer == f"RELOCATED_DIR={bundle}", "Wrapper stdout bundle binding mismatch")
    stdout = stdout["continuous"]
    require(stdout["isolated"] == 1 and stdout["experimental"] is True and stdout["general_release_passed"] is False,
            "Wrapper scope mismatch")
    output = bundle.parent/"continuous-year-raw"
    manifest, year_result = audit_year(output, sample, bindings, [b["name"] for b in year["bodies"]], stdout)
    catalog_pins = dict(hashes=manifest["catalog_outputs"], input_sha256=bindings["catalog_scenario"]["sha256"],
                        source_sha256=sources, native_sha256=PINS["native_sha256"])
    return dict(**year_result, catalog=audit_catalog(bundle/"continuous-catalog-check", sample, catalog, catalog_pins, stdout))


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("archive", "bundle", "wrapper", "writer", "log"):
        cli.add_argument("--"+name, type=Path, required=True)
    cli.add_argument("--wrapper-sha", required=True)
    cli.add_argument("--writer-sha", required=True)
    args = cli.parse_args()
    result = audit_portable(args.archive, args.bundle.resolve(), args.wrapper, args.wrapper_sha,
                            args.writer, args.writer_sha, args.log)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
