"""Measure many-body integration, adapters, diagnostics and a real Tk canvas."""
import argparse
import cProfile
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import platform
import statistics
from time import perf_counter
from unittest.mock import patch

import numpy as np

from solar_simulator.cli import report
from solar_simulator.experiment import advance, preset
from solar_simulator.oblateness import sun_earth_moon_quadrupoles
from solar_simulator.storage import to_document

ROOT = Path(__file__).resolve().parents[1]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def measure(function, repetitions=3, calls=1, key=None):
    expected = function()  # Warmup, excluded from timing.
    if key is not None:
        expected = key(expected)
    samples = []
    for _ in range(repetitions):
        start = perf_counter()
        for _ in range(calls):
            actual = function()
        samples.append((perf_counter()-start)/calls)
        if key is not None:
            actual = key(actual)  # Validation/serialization outside timed region.
        if isinstance(expected, tuple):
            for a, b in zip(actual, expected):
                np.testing.assert_array_equal(a, b)
        elif isinstance(expected, np.ndarray):
            np.testing.assert_array_equal(actual, expected)
        else:
            assert actual == expected, "Repeated result changed"
    return dict(raw_seconds=samples, median_seconds=statistics.median(samples))


def scientific(name):
    state = preset(name, backend="rust")
    return replace(state, settings=replace(state.settings, integrator="dop853",
        physics="eih-1pn", figures=sun_earth_moon_quadrupoles(state.bodies, state.origin),
        relative_pair=("Earth", "Moon"), rtol=3e-14,
        position_atol=1e-7, velocity_atol=1e-13))


def packet(state):
    return advance(state, 20)


def physics(output):
    from solar_simulator import accuracy
    from solar_simulator.native_forces import prepare
    from solar_simulator.relativity import C
    import solar_native
    rows = {}
    cases = {str(n)+"-scientific-rust": scientific(name) for n, name in (
        (10, "solar-system-moon"), (27, "solar-system-asteroids-full"),
        (354, "solar-system-asteroids-catalog"))}
    for backend in ("python", "rust"):
        state = preset("solar-system-asteroids-catalog", backend=backend)
        cases["354-newtonian-"+backend] = replace(state,
            settings=replace(state.settings, integrator="dop853"))
    for label, state in cases.items():
        print("Measuring "+label, flush=True)
        row = dict(settings=asdict(state.settings), origin=asdict(state.origin),
            initial_sha256=digest(to_document(state)), bodies=len(state.bodies))
        row["packet"] = measure(lambda: packet(state), key=lambda s: digest(to_document(s)))
        final = advance(state, 20)
        row["final_sha256"] = digest(to_document(final))
        row["report"] = measure(lambda: report(final), calls=3)
        def with_report():
            final = advance(state, 20)
            return final, report(final)
        row["packet_with_report"] = measure(with_report,
            key=lambda pair: (digest(to_document(pair[0])), pair[1]))
        if state.settings.backend == "rust":
            masses = np.array([b.mass for b in state.bodies])
            p = np.array([tuple((b.position.x, b.position.y, b.position.z)) for b in state.bodies])
            v = np.array([tuple((b.velocity.x, b.velocity.y, b.velocity.z)) for b in state.bodies])
            c = C if state.settings.physics == "eih-1pn" else None
            force = prepare(masses)
            owned = (masses.tolist(), p.tolist(), v.tolist())
            expected = force(p, v, c)
            np.testing.assert_array_equal(np.array(solar_native.point_acceleration(*owned, c)), expected)
            row["adapter"] = measure(lambda: force(p, v, c), calls=10)
            row["native_with_owned_lists"] = measure(
                lambda: np.array(solar_native.point_acceleration(*owned, c)), calls=10)
            row["python_conversions_only"] = measure(
                lambda: (p.tolist(), v.tolist(), np.array(expected.tolist())), calls=10)
        callbacks = []
        original = accuracy.solve_ivp
        def observed(fun, *args, **kwargs):
            times = []
            def timed(*a):
                start = perf_counter()
                result = fun(*a)
                times.append(perf_counter()-start)
                return result
            result = original(timed, *args, **kwargs)
            callbacks.append(dict(rhs_calls=int(result.nfev), rhs_seconds=sum(times)))
            return result
        # Instrumentation and profiler are separate from uninstrumented timings.
        with patch("solar_simulator.accuracy.solve_ivp", observed):
            profiled = packet(state)
        assert digest(to_document(profiled)) == row["final_sha256"]
        row["instrumented_solver"] = callbacks
        profiler = cProfile.Profile()
        profiler.runcall(lambda: report(advance(state, 20)))
        profiler.dump_stats(str(output.parent/(output.stem+"-"+label+".prof")))
        rows[label] = row
        if label == "354-scientific-rust":
            data = dict(initial=to_document(state), final=to_document(final))
            rendered = json.dumps(data, ensure_ascii=False, allow_nan=False)+"\n"
            inputs = output.parent/"render-input.json"
            if inputs.exists():
                assert inputs.read_text(encoding="utf-8") == rendered
            else:
                inputs.write_text(rendered, encoding="utf-8", newline="\n")
    return rows


def render(inputs, output):
    import tkinter as tk
    from solar_simulator.app import Laboratory
    from solar_simulator.storage import from_document
    data = json.loads(inputs.read_bytes())
    state = from_document(data["final"])
    initial = from_document(data["initial"])
    frames = [{b.name: (b.position.x, b.position.y, b.position.z) for b in s.bodies}
              for s in (initial, state)]
    values = report(state)
    root = tk.Tk()
    app = Laboratory(root, state)
    root.update()
    root.withdraw()
    app.canvas.draw_idle = lambda: None
    rows = []
    try:
        for history in (60, 1500):
            app.frames.clear()
            app.frames.extend(frames[i % 2] for i in range(history))
            app.energies.clear()
            app.energies.extend((i*3600., values["energy_budget_residual_joules"]) for i in range(history))
            for view in ("Все тела", "Земля и Луна"):
                app.view.set(view)
                app.reference.set("Тело: Earth" if view == "Земля и Луна" else "Инерциальная")
                app._draw(values)
                app.canvas.draw()
                build, paint = [], []
                for _ in range(3):
                    start = perf_counter()
                    app._draw(values)
                    middle = perf_counter()
                    app.canvas.draw()
                    end = perf_counter()
                    build.append(middle-start)
                    paint.append(end-middle)
                suffix = "all" if view == "Все тела" else "relative"
                pixels = np.asarray(app.canvas.buffer_rgba()).copy()
                from PIL import Image
                Image.fromarray(pixels).save(output.with_name(f"{output.stem}-{history}-{suffix}.png"))
                rows.append(dict(history=history, view=view, build_raw_seconds=build,
                    paint_raw_seconds=paint, full_raw_seconds=[a+b for a,b in zip(build,paint)],
                    full_median_seconds=statistics.median(a+b for a,b in zip(build,paint)),
                    pixel_sha256=hashlib.sha256(pixels.tobytes()).hexdigest(),
                    path_sha256=digest([path.tolist() for path in app._plot_artists.paths.get_segments()]),
                    markers_sha256=digest(app._plot_artists.markers.get_offsets().tolist()),
                    limits=[list(app.orbit.get_xlim()), list(app.orbit.get_ylim())],
                    figure_pixels=list(app.canvas.get_width_height())))
        assert to_document(app.experiment) == data["final"]
    finally:
        app.close()
    return dict(input_sha256=hashlib.sha256(inputs.read_bytes()).hexdigest(), results=rows)


def partition():
    """Diagnose restarts; this changes output cadence, never runtime defaults."""
    from solar_simulator import accuracy
    state = scientific("solar-system-asteroids-catalog")
    initial = digest(to_document(state))
    def small():
        current = state
        for _ in range(10):
            current = advance(current, 20)
        return current
    def large():
        return advance(state, 200)
    rows = {}
    finals = {}
    for label, function in (("ten_packets_20", small), ("one_packet_200", large)):
        print("Measuring "+label, flush=True)
        rows[label] = measure(function, key=lambda s: digest(to_document(s)))
        finals[label] = function()
        calls = []
        original = accuracy.solve_ivp
        def observed(*args, **kwargs):
            result = original(*args, **kwargs)
            calls.append(int(result.nfev))
            return result
        with patch("solar_simulator.accuracy.solve_ivp", observed):
            timed = function()
        assert to_document(timed) == to_document(finals[label])
        rows[label].update(rhs_calls=sum(calls), solves=len(calls), nfev_per_solve=calls,
            final_sha256=digest(to_document(finals[label])), report=report(finals[label]))
    a, b = (finals[label] for label in rows)
    assert a.time == b.time == 720000. and digest(to_document(state)) == initial
    differences = {x.name: dict(position_metres=x.position.distance_to(y.position),
        velocity_metres_per_second=x.velocity.distance_to(y.velocity)) for x,y in zip(a.bodies,b.bodies)}
    def relative(s, field):
        objects = {body.name: getattr(body, field) for body in s.bodies}
        return objects["Moon"].subtract(objects["Earth"])
    pair = dict(position_metres=relative(a,"position").distance_to(relative(b,"position")),
        velocity_metres_per_second=relative(a,"velocity").distance_to(relative(b,"velocity")))
    return dict(initial_sha256=initial, settings=asdict(state.settings), origin=asdict(state.origin),
        duration_seconds=a.time, results=rows, final_state_differences=differences,
        relative_earth_moon_difference=pair, independent_reference=False,
        output_cadence_changed=True, default_settings_changed=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("physics", "render", "partition"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--inputs", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Preserve previous profiling result")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    before = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
              for parent in (ROOT/"src/solar_simulator", ROOT/"rust/solar_core/src", ROOT/"rust/solar_native/src")
              for p in parent.rglob("*") if p.suffix in (".py", ".rs", ".json")}
    if args.mode == "physics":
        result = physics(args.output)
    elif args.mode == "partition":
        result = partition()
    else:
        result = render(args.inputs, args.output)
    assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == sha for name, sha in before.items())
    import scipy, matplotlib
    result = dict(protocol="docs/catalog-performance-protocol.md", mode=args.mode,
        source_sha256=before, script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        python=platform.python_version(), platform=platform.platform(),
        versions=dict(numpy=np.__version__, scipy=scipy.__version__, matplotlib=matplotlib.__version__), results=result)
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print("Saved "+str(args.output), flush=True)


if __name__ == "__main__":
    main()
