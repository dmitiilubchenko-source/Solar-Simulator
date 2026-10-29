"""Historical data replay only: never qualifies a changed installed runtime."""
from copy import deepcopy
from decimal import Decimal as D,localcontext
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pytest
from scripts.release_history import evidence_path

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'docs/runtime-step-379-validation.json'
ARRAYS=ROOT/'scripts/validation/runtime-step-379.npz'


def verify_saved(report,path=ARRAYS):
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    if digest(path)!=report['arrays_SHA256']:raise ValueError('Array SHA mismatch')
    plan_path=ROOT/'scripts/runtime-step-379-plan.json'
    if digest(plan_path)!=report['plan_SHA256']:raise ValueError('Plan SHA mismatch')
    plan=json.loads(plan_path.read_bytes())
    for name,sha in plan['input_SHA256'].items():
        if digest(evidence_path(ROOT,name))!=sha:raise ValueError('Historical input SHA mismatch')
    reference=json.loads((ROOT/'docs/runtime-reliability-376-validation.json').read_bytes())['references']
    if [(r['job'],r['variant']) for r in report['runs']]!=[(j,v) for v in plan['variants'] for j in plan['jobs']]:
        raise ValueError('Missing or duplicate rows')
    with np.load(path,allow_pickle=False) as data,np.load(ROOT/'scripts/validation/runtime-reliability-376.npz',allow_pickle=False) as old:
        for row in report['runs']:
            name=row['job']['id']+'__'+row['variant'];case=next(c for c in plan['cases'] if c['id']==row['job']['case'])
            states=data[name+'__states']
            assert states.shape==(49,2,6) and np.isfinite(states).all() and np.array_equal(states[0],case['initial'])
            assert np.array_equal(data[case['id']+'__epochs'],case['epochs'])
            if row['variant']=='disabled':assert states.tobytes()==old[row['job']['id']+'__states'].tobytes()
            maxima=[D(0),D(0)]
            with localcontext() as ctx:
                ctx.prec=120
                for state,ref in zip(states,reference[case['id']]['values']):
                    for group in range(2):
                        diff=[D.from_float(float(state[1,j+3*group]))-D.from_float(float(state[0,j+3*group]))-D(ref[group][j]) for j in range(3)]
                        maxima[group]=max(maxima[group],sum(x*x for x in diff).sqrt())
            for actual,key in zip(maxima,('r','v')):
                stored=row['maxima'][key]
                if not math.isfinite(stored) or abs(float(actual)-stored)>8*math.ulp(stored):raise ValueError('Raw relative error disagrees')
    assert report['current_runtime_qualified'] is False
    # Source digests describe the frozen execution, not authorization of today's code.


def test_historical_raw_states_recompute_errors_without_current_code_qualification():
    verify_saved(json.loads(REPORT.read_bytes()))


def test_successful_flags_do_not_hide_a_false_measurement():
    proof=json.loads(REPORT.read_bytes());proof['runs'][0]['maxima']['r']+=1
    with pytest.raises(ValueError,match='Raw relative error'):verify_saved(proof)


def test_changed_archive_is_rejected_before_using_success_flags(tmp_path):
    changed=tmp_path/'changed.npz';changed.write_bytes(ARRAYS.read_bytes()+b'corrupt')
    with pytest.raises(ValueError,match='Array SHA'):verify_saved(json.loads(REPORT.read_bytes()),changed)
