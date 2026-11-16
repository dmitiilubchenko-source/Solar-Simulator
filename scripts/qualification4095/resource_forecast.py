"""Offline measurement-based410 estimate; no new orbit and no guarantee of cost."""
from pathlib import Path
from dataclasses import asdict
import hashlib,json,os
import numpy as np
from solar_simulator.storage import from_document
R=Path(__file__).resolve().parents[2];A=Path('C:/Users/Admin/Documents/Codex/Solar4095-20261116');F=A/'SolarSimulator-0.4.0-4095'
paths={'strict385':R/'.tools/qualification385/retry/run-current/rust_strict20-receipt.json',
       'continuous':R/'docs/continuous-integration-validation.json',
       'source408':R/'docs/release-source-acceptance-408.json'}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
old=json.loads(paths['strict385'].read_bytes());initial=json.loads((F/'verification/initial.json').read_bytes())
for key in ['initial','bodies','settings','origin','units']:assert old['initial_document'][key]==initial[key]
assert old['packet_max_steps']==20 and old['packets']==499 and old['exact_times'] and old['settings_preserved']
h=json.loads(paths['continuous'].read_bytes());year=h['outcomes']['year']
assert year['settings']==initial['settings'] and year['origin']==initial['origin'] and year['samples']==125
catalog_doc=json.loads((F/'scenarios/solar-system-asteroids-catalog-rust-1pn-solar-q2-relative.json').read_bytes())
state=from_document(catalog_doc)
# Diagnostic asdict omits class discriminators. It is NOT a loadable checkpoint.
assert json.loads(json.dumps(asdict(state.settings)))==h['outcomes']['catalog']['settings']
assert catalog_doc['origin']==h['outcomes']['catalog']['origin']
with np.load(F/'docs/continuous-integration-reference.npz',allow_pickle=False) as z:
    actual=np.array([[b.position.x,b.position.y,b.position.z,b.velocity.x,b.velocity.y,b.velocity.z] for b in state.bodies])
    assert np.array_equal(actual,z['catalog_continuous'][0]) and actual.shape==(354,6)
cost=h['outcomes']['catalog']['cost']['physics_with_report']
catalog_seconds=max(max(v['raw_seconds']) for v in cost.values())  # Slower restart controls included, not the best sample.
numeric_base=old['seconds']+year['wall_seconds']+catalog_seconds
assert 4*numeric_base+100<250
ratios=[]
for name in ['current-preflight','verifier-negatives','security-tests3','independent-audit']:
    m=json.loads((A/(name+'-resources.json')).read_bytes())['record']
    ratios.append(m['parent_supervision_CPU_seconds']/m['wall_seconds'])
assert max(ratios)<.8
source408=json.loads(paths['source408'].read_bytes())
assert source408['resources']['peak_private_worker_tree_sampled']==1004916736
forecast=dict(CPU_seconds=650,active_wall_seconds=450,private_bytes=int(1.5*1024**3),new_data_bytes=1024**3)
result=dict(kind='resource-forecast410-v1',status='ENGINEERING_PREFLIGHT_GO_NOT_EXECUTION_OR_COST_GUARANTEE',
 inputs={k:dict(path=str(p),sha256=sha(p)) for k,p in paths.items()},
 measurements=dict(strict385_wall_seconds=old['seconds'],strict385_packets=499,continuous_year_wall_seconds=year['wall_seconds'],catalog_worst_measured_wall_seconds=catalog_seconds,supervision_CPU_per_wall_max=max(ratios),source408_sampled_private_peak=source408['resources']['peak_private_worker_tree_sampled']),
 comparability=dict(strict_IC_settings_origin_units_exact=True,continuous_year_settings_origin_exact=True,catalog_settings_dataclass_normalization_exact=True,catalog_354_IC_matches_saved_first_state=True,ABI_and_numerical_dependencies_same_family=True,native040_binary_differs_from_old_measurement=True),
 calculation=dict(numeric_base_wall=numeric_base,numeric_variation_allowance=4,GUI_bindings_replay_copy_IO_worker_allowance_CPU=100,rounded_worker_CPU_budget=250,operational_wall_allowance=450,supervisor_CPU_rate_allowance=.8,supervisor_CPU_budget=360,final_CPU_allowance=40,total_CPU=650),
 forecast=forecast,
 assumptions=['Factor4 is an engineering variability allowance, not an empirical quantile or a proven bound for040.',
 'Thread variables OMP/OPENBLAS/MKL=1; at least2 available logical CPUs, no concurrent qualification.',
 'Monitor only a fresh dedicated relocated output root; at most14000 files. Current measured max ratio0.768 rounded to0.8.',
 '1.5GiB private allowance exceeds the observed exact040 source408 peak (~1.005GB); imports are already verified in packaged040.',
 '1GiB disk allowance exceeds ZIP+one ~321MB runtime, workflows/raw/logs; full source tests/duplicated test runtime are excluded.',
 'Before start recheck environment/load/freeRAM/disk and absence of stale receipts. Abort rather than extend budgets or skip probes.'],
 limitations=['Historical timings are not measurements of completed040 full410.',
 'No hard statistical upper cost bound; sampled memory is not an OS quota.',
 'Actual resource or scientific FAIL must be retained without automatic retries/criteria changes.'],
 no_new_integrations=True,no_source_or_physical_criteria_changes=True)
assert forecast['CPU_seconds']<720 and forecast['active_wall_seconds']<960 and forecast['private_bytes']<1.8*1024**3 and forecast['new_data_bytes']<1.8*1024**3
result['current_logical_cpu_count']=os.process_cpu_count()
assert result['current_logical_cpu_count']>=2
(R/'scripts/qualification4095/resource-forecast410.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\r\n')
print(json.dumps(result['measurements']));print('Measurement-based engineering forecast650CPU450wall/1.5GiB1GiB fits early720/960; not a guarantee or authorization')
