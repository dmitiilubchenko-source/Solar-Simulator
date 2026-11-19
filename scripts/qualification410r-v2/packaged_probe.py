"""Bounded, read-only packaged imports and binary64 metric check, with an I/O marker."""
import ast
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import sysconfig

import numpy as np
import solar_native
import solar_simulator

binding = json.loads(sys.argv[1])
root = Path.cwd().resolve()
writer_file = Path(sys.argv[2])
auditor_file = writer_file.with_name("audit.py")
output = Path(sys.argv[3])
assert sys.flags.isolated and sys.flags.dont_write_bytecode
assert Path(sys.executable).resolve() == root/"runtime/python.exe"
assert Path(sys.prefix).resolve() == root/"runtime"
assert not output.resolve().is_relative_to(root)
assert sys.argv[4] == 'Эпоха "тест"'
assert not any(k in os.environ for k in ("PYTHONPATH","PYTHONHOME"))
assert all(os.environ[k] == "1" for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS"))
for module in (solar_native, solar_simulator, np):
    assert Path(module.__file__).resolve().is_relative_to(root/"runtime")
manifest = json.loads((root/"verification-current040/manifest-v1.json").read_bytes())
assert manifest["SOABI"] == sysconfig.get_config_var("SOABI")
assert manifest["free_threaded"] == bool(sysconfig.get_config_var("Py_GIL_DISABLED"))
writer = runpy.run_path(str(writer_file))
audit = runpy.run_path(str(auditor_file))
observed = writer["observe_inputs"](root, binding)
assert observed == binding["input_hashes"]
with np.load(root/"docs/continuous-integration-reference.npz", allow_pickle=False) as reference:
    assert reference["year_continuous"].shape == (125,10,6) and reference["catalog_continuous"].shape == (11,354,6)
    assert reference["year_times"].shape == (125,) and reference["year_times"].dtype == np.dtype("float64")
    assert np.isfinite(reference["year_continuous"]).all()

tree = ast.parse(Path(binding["wrapper"]).read_bytes())
function = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="check_continuous")
probe = ast.parse(function.body[1].value.value)
old_metric = next(n for n in probe.body if isinstance(n,ast.FunctionDef) and n.name=="difference")
context = {"np":np}
exec(compile(ast.Module(body=[old_metric], type_ignores=[]),"pinned wrapper difference","exec"),context)
rng = np.random.default_rng(41002)
reference = rng.normal(size=(9,10,6))
actual = reference + rng.normal(scale=1e-8,size=reference.shape)
actual_rel = actual[:,4]-actual[:,3]
reference_rel = reference[:,4]-reference[:,3]
for got, wanted in ((actual,reference),(actual_rel,reference_rel),(actual[:,4],reference[:,4])):
    assert audit["maxima"](got,wanted) == context["difference"](got,wanted)
writer["_atomic_write"](output/"unicode-output.json", lambda handle: handle.write(
    'Состояние\n'.encode("utf8")))
assert (output/"unicode-output.json").read_text(encoding="utf8") == 'Состояние\n'
child = subprocess.run([sys.executable,"-I","-B","-c","import sys; print(sys.flags.isolated)"],
                       capture_output=True,text=True,check=True,timeout=8)
assert child.stdout.strip()=="1"
print(json.dumps(dict(packaged_executable=sys.executable,abi=manifest["SOABI"],native_module=solar_native.__file__,
    loaded_writer_sha=hashlib.sha256(writer_file.read_bytes()).hexdigest(),numpy=np.__version__,inputs=observed,
    exact_norm_roundtrip=True,external_unicode_marker=True,child_isolated=True,solver_runs=0),ensure_ascii=False))
