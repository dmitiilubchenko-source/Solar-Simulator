"""Offline numerical replay of sealed384 evidence, never live qualification."""
import hashlib,json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'scripts/validation/newton384'
MANIFEST_SHA='f7f352816e5d715f66fa580a1173c6053427691b289bc7d08fc7816db846a978'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit(directory=EVIDENCE):
    from scripts.assess_runtime_reliability376 import independent_metrics,close_metric
    from solar_simulator.simulation import G
    directory=Path(directory);read=lambda name:json.loads((directory/name).read_bytes())
    if sha(directory/'manifest.json')!=MANIFEST_SHA:raise ValueError('384 manifest changed')
    manifest=read('manifest.json')
    for name,digest in manifest['assets'].items():
        path=(directory/name).resolve()
        if not path.is_relative_to(directory.resolve()) or sha(path)!=digest:
            raise ValueError('384 evidence changed: '+name)
    p=read('protocol.json');freeze=read('freeze.json');proof=read('proof.json');trace=read('execution-trace.json')
    if (p['base_commit']!=freeze['candidate_commit'] or p['base_commit']!=manifest['candidate_commit'] or
            sha(directory/'protocol.json')!=freeze['protocol_SHA256'] or
            sha(directory/'environment.json')!=freeze['environment_SHA256'] or
            sha(directory/'source-manifest.json')!=freeze['source_manifest_SHA256'] or
            read('source-manifest.json')!=freeze['source_SHA256'] or p['source_SHA256']!=freeze['source_SHA256'] or
            read('environment.json')!=p['environment'] or G.hex()!=freeze['G_hex']):
        raise ValueError('384 recorded provenance inconsistent')
    if (not trace['complete'] or trace['failure'] is not None or not trace['source_environment_unchanged'] or
            trace['freeze_SHA256']!=sha(directory/'freeze.json') or
            trace['protocol_SHA256']!=freeze['protocol_SHA256'] or
            proof['arrays_SHA256']!=sha(directory/'summary.npz') or
            proof['protocol_SHA256']!=freeze['protocol_SHA256'] or
            [r['job'] for r in proof['runs']]!=p['jobs']):
        raise ValueError('384 incomplete/unbound results')
    observations=0;moderate=[];restarts=0
    with np.load(directory/'summary.npz',allow_pickle=False) as arrays:
        for row in proof['runs']:
            job=row['job'];case=next(c for c in p['cases'] if c['id']==job['case'])
            values=arrays[job['id']+'__states'];epochs=arrays[job['id']+'__epochs']
            expected_epochs=case['epochs'] if job['schedule']=='grid' else [0.,case['epochs'][-1]]
            if (values.shape!=(len(expected_epochs),2,6) or not np.isfinite(values).all() or
                    not np.array_equal(values[0],case['initial']) or not np.array_equal(epochs,expected_epochs)):
                raise ValueError('384 IC/grid/state mismatch')
            ref=proof['references'][case['id']]['values'];ref=ref if job['schedule']=='grid' else [ref[0],ref[-1]]
            maximum,per_epoch=independent_metrics(values,ref,case['masses'])
            if len(per_epoch)!=len(row['per_epoch']):raise ValueError('384 missing epoch metrics')
            for key in ('r','v','E','L','P'):
                close_metric(maximum[key],row['maxima'][key],job['id']+'/'+key)
                for i,v in enumerate(per_epoch):close_metric(v[key],row['per_epoch'][i][key],job['id']+'/'+str(i)+'/'+key)
            gate=None if case['id']!='moderate' else maximum['r']<100 and maximum['v']<1e-3 and maximum['E']<1e-10
            if gate is not row['moderate_existing_criterion_PASS']:raise ValueError('384 wrong accuracy label')
            if gate is not None:moderate.append(gate)
            if row['exact_file_restart'] is True:restarts+=1
            count=trace['jobs'][job['id']]
            if (count['solver_calls']<=0 or count['nfev']<=0 or
                    count['native_force_calls']!=(count['nfev'] if job['backend']=='rust' else 0)):
                raise ValueError('384 execution/backend inconsistent')
            observations+=len(values)
    return dict(jobs=len(proof['runs']),state_observations=observations,moderate_passes=sum(moderate),
        recorded_exact_restart_cases=restarts,independent_raw_metrics=True,
        high_e_accuracy_gate='not defined in376; diagnostic only',
        source_mode='saved evidence replay',actual_current_environment_checked=False,current_runtime_qualified=False,
        limitations='Shared Newton/IC/G and saved analytical f/g reference; Fraction/Decimal reduction is independent of producer arithmetic. No new integration or external peer review.')


if __name__=='__main__':
    print(json.dumps(audit(),indent=2))
