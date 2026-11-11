from pathlib import Path
import subprocess,sys,json,hashlib,os
R=Path(__file__).resolve().parents[2];W=Path('C:/Users/Admin/Documents/Codex/Solar407V-20261111');S=Path('C:/Users/Admin/Desktop/Solar-candidate-040-version-407v')
# Use cwd for scripts imports, explicit module invocation with existing source-binding pth.
for name,py,source in [('old',Path('C:/Users/Admin/Documents/Codex/Solar407-20261110/env/Scripts/python.exe'),Path('C:/Users/Admin/Desktop/Solar-candidate-033-blockers-407')),('new',Path(sys.executable),S)]:
    code="import sys;sys.path.insert(0,"+repr(str(R))+ ");import runpy;runpy.run_path("+repr(str(R/'scripts/qualification407v/binary_controls.py'))+",run_name='__main__')"
    if (W/f'binary-{name}.json').exists():continue  # completed fixed controls, retained without rerun
    subprocess.run([str(py),'-I','-X','utf8','-B','-c',code,str(W/f'binary-{name}.json')],cwd=source,check=True)
a=(W/'binary-old.json').read_bytes();b=(W/'binary-new.json').read_bytes();assert a==b,'Real numerical difference: preserve both results'
report=json.loads((R/'docs/compatibility-389-validation.json').read_bytes());old=R/'.tools/qualification389'
from solar_simulator.storage import load,to_document,from_document,save
from solar_simulator.branch_io import open_experiment,save_experiment
rows=[]
for p in sorted((old/'inputs').glob('*.json')):
    expected=report['input_binding']['inputs_SHA256'][p.name];assert hashlib.sha256(p.read_bytes()).hexdigest()==expected
    if p.stem in ('corrupt','unsupported'):
        try:load(p)
        except (ValueError,KeyError):rows.append(dict(name=p.name,expected_rejection=True));continue
        raise AssertionError('Bad historical file accepted')
    doc=to_document(load(p));assert to_document(from_document(doc))==doc
    rows.append(dict(name=p.name,SHA256=expected,roundtrip=True))
for name,expected in report['raw_SHA256'].items():
    if name.startswith('accepted/') and (('/frame-' in name and name.endswith('.json')) or name=='accepted/branch.json'):
        p=old/name;assert hashlib.sha256(p.read_bytes()).hexdigest()==expected
        e,parent=open_experiment(p);out=W/('legacy407v-'+str(len(rows))+'.json');save_experiment(e,out,parent_snapshot=parent);e2,p2=open_experiment(out)
        assert to_document(e2)==to_document(e) and p2==parent
        rows.append(dict(name=name,SHA256=expected,roundtrip=True))
(W/'compatibility.json').write_text(json.dumps(dict(binary_contract_exact=True,comparison_SHA256=hashlib.sha256(a).hexdigest(),historical_files=rows,limitations='No all-version guarantee; strict recipes remain source-bound; dynamicQ2 branching unsupported unchanged'),indent=2)+'\n')
os.environ['SOLAR_HISTORICAL376_BUNDLE']='C:/Users/Admin/Documents/Codex/Solar407-20261110/historical376-inputs.zip'
subprocess.run([sys.executable,'-X','utf8','-B','-m','pytest','-q','-p','no:cacheprovider','-p','scripts.native_audit','--junitxml='+str(W/'compatibility-tests.xml'),'tests/test_two_q2_gui.py','tests/test_sandbox_gui.py::test_edit_cancel_disk_failure_fork_load_and_reset','tests/test_app_workflows.py::test_scenario_selection_prepares_valid_controls_without_replacing_current_experiment','tests/test_app_workflows.py::test_ready_lunar_profile_preserves_previously_packaged_settings_and_provenance','tests/test_release_history.py'],cwd=S,check=True)
