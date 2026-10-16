"""Export a bounded, SHA-verified public comparison bundle; no runtime edits."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np

from scripts.assess_dense_jpl import verified_sources
from scripts.replay_jpl import replay

ROOT = Path(__file__).resolve().parents[1]


def export(output):
    output = Path(output).resolve()
    if output.exists():raise FileExistsError("Preserve existing bundle")
    report = json.loads((ROOT/"docs/dense-jpl-validation.json").read_bytes())
    strict = json.loads((ROOT/"docs/strict-profile-validation.json").read_bytes())
    reference = json.loads((ROOT/"docs/qualification-grid-reference.json").read_bytes())
    for receipt in (report,strict,reference):verified_sources(receipt)
    for name,digest in report["input_sha256"].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != digest:
            raise ValueError("Changed qualified input: "+name)
    cache = ROOT/".tools/qualification138/production139.npz"
    if hashlib.sha256(cache.read_bytes()).hexdigest() != strict["cache_sha256"]:
        raise ValueError("Changed production cache")
    profiles = {}
    with np.load(cache,allow_pickle=False) as data:
        epochs = reference["epochs_jd_tdb"]
        times = (np.array(epochs)-reference["origin"]["epoch_jd_tdb"])*86400
        if not np.array_equal(times,data["times"]):raise ValueError("Different cached epochs")
        for name in ("python","rust","rust_tighter"):
            profiles[name] = data[name].tolist()
            if not np.array_equal(np.asarray(profiles[name]),data[name]):
                raise ValueError("Trajectory JSON round trip failed")
    settings = {}
    for name in profiles:
        settings[name] = deepcopy(report["strict_settings"] if name == "rust_tighter" else report["standard_settings"])
        settings[name]["backend"] = "python" if name == "python" else "rust"
    output.mkdir(parents=True,exist_ok=False)
    payloads = {"reference.json":"docs/qualification-grid-reference.json",
        "dense-report.json":"docs/dense-jpl-validation.json", "strict-report.json":"docs/strict-profile-validation.json",
        "numerical-before.json":"docs/qualification-grid-validation.json",
        "initial.json":"docs/solar-sandbox-strict-checkpoint.json",
        "initial-dataset.json":"src/solar_simulator/data/solar-system-moon-20261008.json",
        "replay_jpl.py":"scripts/replay_jpl.py", "recompute_jpl.py":"scripts/recompute_jpl.py"}
    for destination,source in payloads.items():shutil.copy2(ROOT/source,output/destination)
    trajectory = dict(units="SI",origin=reference["origin"],epochs_jd_tdb=epochs,profiles=profiles,settings=settings)
    (output/"trajectories.json").write_text(json.dumps(trajectory,allow_nan=False,separators=(",",":"))+"\n",encoding="utf-8")
    for body in reference["bodies"]:
        offset = 0
        for request in body["requests"]:
            name = f"horizons-{body['id']}-{offset:03d}.json"
            raw = (ROOT/".tools/qualification144/jpl-batches"/name).read_bytes()
            if hashlib.sha256(raw).hexdigest() != request["response_sha256"]:
                raise ValueError("Changed primary response: "+name)
            (output/"raw").mkdir(exist_ok=True)
            (output/"raw"/name).write_bytes(raw)
            offset += len(request["epochs_jd_tdb"])
    (output/"README.md").write_text("""# Solar: автономное сравнение с JPL

Этот комплект воспроизводит опубликованные остатки сохранённых траекторий.
125 эпох/10 тел/один год, SI/SSB/EclipticJ2000/TDB, DE441. Нового расчёта
движения здесь нет. Численные проверки RK45/Kepler были отдельными;
исходный численный неуспех стандартного Rust-профиля сохранён в numerical-before.json.

Из каталога комплекта с Python и NumPy:

```text
python -I replay_jpl.py .
```

В portable запускайте JPL Verification.cmd из её корневого каталога.
Проверяются SHA, первичные ответы, эпоха/координаты/единицы, GM/начало,
настройки и вычисленные заново остатки. Пороги:10 км/тело и1 км/Moon−Earth.
Данные не подгонялись. Между эпохами или в отредактированных системах
этот результат не является гарантией. EIH1PN+фиксированныеSun/EarthJ2;
приливы, все астероиды и смешанныеPN-figureчлены отсутствуют.

Сеть, исходный checkout и приватный кеш не нужны. NumPy требуется;
portable уже содержит его. manifest.json фиксирует состав и SHA.
Для доверия к передаваемому manifest сверяйте опубликованный SHA всегоZIP.
""",encoding="utf-8",newline="\n")
    manifest = dict(schema=1,kind="saved-trajectory-jpl-replay",production_cache_sha256=strict["cache_sha256"],
        provenance=dict(dense_report_sha256=hashlib.sha256((ROOT/"docs/dense-jpl-validation.json").read_bytes()).hexdigest(),
            strict_report_sha256=hashlib.sha256((ROOT/"docs/strict-profile-validation.json").read_bytes()).hexdigest(),
            exporter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),
        files={p.relative_to(output).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in output.rglob("*") if p.is_file()})
    (output/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    result = replay(output)
    if not result["checks_passed"]:raise ValueError("Exported replay failed")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    result = export(args.output)
    print(json.dumps(result,indent=2))


if __name__ == "__main__":main()
