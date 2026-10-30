"""Independent observations of saved new runs; never manufacture a qualification."""
import hashlib
import json
from math import dist
from pathlib import Path
import re

import numpy as np
import pytest

from scripts.sandbox_checks.accept_sandbox import ROOT, CURRENT_RECEIPT, CURRENT_RECEIPT_SHA, check_receipts,audit_receipt_inputs
from test_sandbox_acceptance import historical_checkout


def evidence():
    raw=(ROOT/CURRENT_RECEIPT).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==CURRENT_RECEIPT_SHA
    report=json.loads(raw)
    raw=(ROOT/report['array_archive']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==report['array_sha256']
    with np.load(ROOT/report['array_archive'],allow_pickle=False) as data:
        return report,{key:data[key].copy() for key in data.files}


def maxima(actual,expected):
    # Scalar math.dist supplies a separate reduction from the NumPy producer.
    pairs=list(zip(np.asarray(actual).reshape(-1,6),np.asarray(expected).reshape(-1,6)))
    return max(dist(a[:3],b[:3]) for a,b in pairs), max(dist(a[3:],b[3:]) for a,b in pairs)


def test_new_year_holdout_and_reference_metrics_from_actual_arrays():
    report,data=evidence()
    assert report['solver_executed'] and report['current_runtime_qualified'] and not report['failed_criteria']
    assert len(report['epochs_jd_tdb'])==125 and len(report['holdout_times_seconds'])==9
    names=list(report['results']['python_strict20']['per_body'])
    earth,moon=names.index('Earth'),names.index('Moon')
    for grid in ('annual','holdout'):
        first,last=(data['reference_'+grid+'_level_'+str(i)] for i in (0,1))
        position,velocity=maxima(first,last)
        row=report['reference']['results'][grid]['convergence']
        assert position==pytest.approx(row['all_bodies']['maximum_position_metres'],abs=1e-12)
        assert velocity==pytest.approx(row['all_bodies']['maximum_velocity_m_per_s'],abs=1e-15)
        assert position<1
        relative=maxima(first[:,moon]-first[:,earth],last[:,moon]-last[:,earth])
        assert relative[0]==pytest.approx(row['moon_relative_to_earth']['maximum_position_metres'],abs=1e-12)
        assert relative[0]<.1
    for backend in ('python','rust'):
        for suffix in ('strict20','strict10','holdout20'):
            key=backend+'_'+suffix;actual=data['current_'+key+'_values']
            expected=data['reference_'+('holdout' if suffix=='holdout20' else 'annual')+'_level_1']
            row=report['results'][key]
            for i,name in enumerate(names):
                position,velocity=maxima(actual[:,i],expected[:,i])
                assert position==pytest.approx(row['per_body'][name]['position_metres'],abs=1e-12)
                assert velocity==pytest.approx(row['per_body'][name]['velocity_m_per_s'],abs=1e-15)
                assert position<10 and velocity<1e-4
            position,velocity=maxima(actual[:,moon]-actual[:,earth],expected[:,moon]-expected[:,earth])
            assert position==pytest.approx(row['earth_moon']['position_metres'],abs=1e-12)
            assert position<.1 and velocity<1e-5
            if suffix!='holdout20':
                position,velocity=maxima(actual[:,moon]-actual[:,earth],data['jpl_values'][:,moon]-data['jpl_values'][:,earth])
                assert position==pytest.approx(row['jpl']['moon_relative_jpl']['position_metres'],abs=1e-9)
                assert position<1000
            assert (backend=='rust')==(report['executed_jobs'][key]['native_force_calls']>0)


def test_accepted032_recomputed_regression_and_old_failure_retained():
    report,data=evidence()
    assert len(report['sandbox'])==12
    assert {(row['backend'],row['name']) for row in report['sandbox']}=={
        (backend,name) for backend in ('python','rust') for name in
        ('mass-double','slow-velocity','escape-velocity','eccentric-095','add-companion','remove-primary')}
    for backend in ('python','rust'):
        for suffix in ('strict20','holdout20'):
            key=backend+'_'+suffix
            for field in ('values','packets','final_document'):
                a,b=(data[version+'_'+key+'_'+field] for version in ('current','accepted032'))
                assert a.dtype==b.dtype and a.shape==b.shape and a.tobytes()==b.tobytes()
    for row in report['sandbox']:
        assert row['checks_passed'] and row['file_continue_exact'] and row['accepted032_trace_bitwise']
    assert not report['results']['rust_standard20']['checks_passed']
    assert report['results']['rust_standard20']['earth_moon']['position_metres']>.1
    old=json.loads((ROOT/'docs/qualification-grid-validation.json').read_bytes())
    assert not old['checks_passed']
    assert report['results']['rust_standard20']['earth_moon']['position_metres']==old['results']['rust']['relative_numerical_error']['position_metres']


def test_compute_and_assessment_dependencies_are_bound():
    from scripts.release_history import ui_historical_sha
    report,_=evidence()
    required={'src/solar_simulator/_numbers.py','src/solar_simulator/accuracy.py',
        'src/solar_simulator/oblateness.py','src/solar_simulator/coordinates.py',
        'scripts/fetch_ephemerides.py','scripts/assess_dense_jpl.py',
        'scripts/assess_current_runtime375.py','scripts/qualify_current_runtime375.py',
        'scripts/validation/eih_scalar.rs','scripts/independent_eih_rust.py',
        'scripts/independent_figure_vector.py','rust/solar_native/src/lib.rs'}
    assert required<=report['source_sha256'].keys()
    for name in required:
        # This test audits the saved375 result, not permission for a live job.
        assert ui_historical_sha(ROOT,name,report['source_sha256'][name])==report['source_sha256'][name]


@pytest.mark.parametrize('target',[CURRENT_RECEIPT,'scripts/current-runtime-375-protocol.json',
    'scripts/validation/current-runtime-375.npz','src/solar_simulator/_numbers.py'])
def test_single_evidence_or_dependency_corruption_rejected(historical_checkout,target):
    assert audit_receipt_inputs(historical_checkout)['source_inputs_intact']
    path=historical_checkout/target
    path.write_bytes(path.read_bytes()+b'changed')
    with pytest.raises(ValueError,match='changed: '+re.escape(target)):
        check_receipts(historical_checkout)


def test_changed_real_environment_cannot_reuse_qualification(historical_checkout,monkeypatch):
    receipt=audit_receipt_inputs(historical_checkout)['historical_receipt']
    recorded=receipt['environment']['numerical_environment']['OMP_NUM_THREADS']
    monkeypatch.setenv('OMP_NUM_THREADS','2' if recorded!='2' else '3')
    with pytest.raises(ValueError,match='environment/native changed'):
        check_receipts(historical_checkout)


def test_strict_gate_accepts_only_an_actual_matching_environment(historical_checkout):
    from solar_simulator.recipe import runtime_fingerprint
    receipt=audit_receipt_inputs(historical_checkout)['historical_receipt']
    actual=runtime_fingerprint('rust');actual.pop('package_files')
    if actual==receipt['environment']:
        assert check_receipts(historical_checkout)['current_qualification_passed']
    else:
        with pytest.raises(ValueError,match='environment/native changed'):check_receipts(historical_checkout)


def test_missing_native_cannot_produce_qualification(historical_checkout,monkeypatch):
    import solar_simulator.recipe as recipe
    def absent(*a):raise ImportError('controlled missing native')
    monkeypatch.setattr(recipe,'_native',absent)
    with pytest.raises(ImportError,match='missing native'):check_receipts(historical_checkout)
