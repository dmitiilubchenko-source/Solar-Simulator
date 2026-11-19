"""Independent evidence audit. Parses the pinned wrapper and reads ZIP data only."""
import ast
import hashlib
import io
import json
from pathlib import Path
import time
import zipfile

import numpy as np

HERE = Path(__file__).resolve().parent
RAW = Path("C:/Users/Admin/Documents/Codex/Solar 410R 20261119")


def block(node, name, kind):
    return next(value for value in node.body if isinstance(value, kind) and value.name == name)


def dotted(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return dotted(node.value) + "." + node.attr
    return ""


def audit():
    start, cpu = time.perf_counter(), time.process_time()
    plan = json.loads((HERE/"execution-plan.json").read_bytes())
    pins = plan["bindings"]
    wrapper = Path(pins["acceptance_tool"]["path"])
    data = wrapper.read_bytes()
    assert hashlib.sha256(data).hexdigest() == pins["acceptance_tool"]["SHA256"]
    tree = ast.parse(data)
    continuous = block(tree, "check_continuous", ast.FunctionDef)
    main = block(tree, "main", ast.FunctionDef)
    probe = next(statement.value for statement in continuous.body if
                 isinstance(statement, ast.Assign) and any(isinstance(t, ast.Name) and t.id=="probe"
                 for t in statement.targets))
    assert isinstance(probe, ast.Constant)
    sub = ast.parse(probe.value)
    calls = [x for x in ast.walk(sub) if isinstance(x, ast.Call)]
    call_names = sorted({dotted(c.func) for c in calls} - {""})
    assert {"ContinuousRun", "session.next", "values.append", "run", "print"}.issubset(call_names)
    assert "continuous-catalog-check/snapshots.csv" in probe.value
    year_array = [x for x in sub.body if isinstance(x, ast.Assign) and ast.unparse(x.value) == "np.array(values)"]
    assert len(year_array) == 1
    first_year = next(x for x in sub.body if isinstance(x, ast.Assign) and ast.unparse(x.value).startswith("ContinuousRun("))
    write_like = {"np.save", "np.savez", "np.savez_compressed", "open", "write", "Path.write_bytes",
                  "Path.write_text", "save", "tofile", "csv.writer", "csv.DictWriter", "json.dump"}
    for node in sub.body[sub.body.index(first_year):]:
        assert not any(isinstance(c, ast.Call) and dotted(c.func) in write_like for c in ast.walk(node))
    printed = next(x for x in calls if dotted(x.func) == "print")
    dump = printed.args[0]
    assert dotted(dump.func) == "json.dumps"
    fields = list(x.arg for x in dump.args[0].keywords)
    assert fields == ["catalog_reproduction","year_reproduction","relative_independent",
                      "catalog_rhs_calls","catalog_packets","year_statistics",
                      "experimental","isolated","general_release_passed"]
    returned_stdout = [x for x in continuous.body if isinstance(x, ast.Return)]
    assert len(returned_stdout)==1 and ast.unparse(returned_stdout[0].value) == "json.loads(process.stdout)"
    assert any(isinstance(x, ast.Assign) and ast.unparse(x.value) == "check_continuous(folder, environment)"
               for x in main.body)
    archive = Path(pins["archive"]["archive"])
    read_preflight = json.loads((RAW/"input-preflight.json").read_bytes())
    assert read_preflight["identity"]=="PASS" and not read_preflight["attempt_started"]
    assert not (wrapper.parents[1]/".tools").exists()
    assert not any(Path(plan["output"][k]).exists() for k in ("guard","temp"))
    with zipfile.ZipFile(archive) as z:
        folder = z.namelist()[0].split("/",1)[0] + "/"
        ref = z.read(folder+"docs/continuous-integration-reference.npz")
        receipt = json.loads(z.read(folder+"docs/continuous-integration-validation.json"))
        assert hashlib.sha256(ref).hexdigest() == receipt["public_reference_sha256"]
        with np.load(io.BytesIO(ref), allow_pickle=False) as array:
            arrays = {key:list(array[key].shape) for key in
                      ("year_continuous","year_independent","catalog_continuous","year_times","catalog_times")}
    status = dict(decision="STOP_BEFORE_EXECUTION", reason="CONTINUOUS_YEAR_RAW_ACTUAL_STATES_NOT_EXPORTED",
                  source_sha=pins["acceptance_tool"]["SHA256"],
                  source_lines=dict(stock_call=[main.lineno,main.end_lineno], continuous=[continuous.lineno,continuous.end_lineno],
                      probe=[probe.lineno,probe.end_lineno], annual_array=probe.lineno+year_array[0].lineno-1),
                  exported_summary_fields=fields, annual_array_written=False,
                  catalogs_have_csv=True, reference_shapes=arrays, reference_sha=receipt["public_reference_sha256"],
                  audit_scope="Static audit of the evidence channel. No portable worker outcome or scientific claim.",
                  tool_executions=0, scientific_propagations=0,
                  cpu_seconds=time.process_time()-cpu, wall_seconds=time.perf_counter()-start)
    with (RAW/"independent-audit.json").open("x",encoding="utf8") as f:
        json.dump(status,f,indent=2)
    print(json.dumps(status))


if __name__ == "__main__":
    audit()
