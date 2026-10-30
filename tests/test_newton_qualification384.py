"""Observation must preserve states and leave useful data on interruption."""
from dataclasses import replace
import io,json
from pathlib import Path

import pytest

from scripts import check_runtime_reliability376 as driver
from scripts.qualify_newton384 import observe,array_read_guard
from solar_simulator import accuracy,native_forces
from solar_simulator.storage import to_document


def inputs():
    p=driver.read(driver.PROTOCOL)
    job=next(j for j in p['jobs'] if j['case']=='moderate' and j['backend']=='python')
    case=next(c for c in p['cases'] if c['id']==job['case'])
    return case,job


def test_observation_preserves_real_solver_state_and_production_parameters():
    case,job=inputs();seed=driver.seed_from(case,job)
    expected=driver.advance(replace(seed,settings=replace(seed.settings,dt=.125)),1)
    journal=io.StringIO()
    with observe(journal) as rows:
        seed=driver.seed_from(case,job)
        actual=driver.advance(replace(seed,settings=replace(seed.settings,dt=.125)),1)
    assert to_document(actual)==to_document(expected)
    row=rows[job['id']]
    assert row['solver_calls']==row['advance_calls']==1
    assert row['nfev']>0 and row['native_force_calls']==0
    assert not row['internal_steps_known']
    records=list(map(json.loads,journal.getvalue().splitlines()))
    assert records[-1]['document']==to_document(actual)


def test_interruption_retains_completed_packets_and_restores_callers():
    originals=driver.seed_from,driver.advance,accuracy.solve_ivp,native_forces.prepare
    case,job=inputs();journal=io.StringIO()
    with pytest.raises(KeyboardInterrupt),observe(journal):
        seed=driver.seed_from(case,job)
        driver.advance(replace(seed,settings=replace(seed.settings,dt=.125)),1)
        raise KeyboardInterrupt()
    assert originals==(driver.seed_from,driver.advance,accuracy.solve_ivp,native_forces.prepare)
    records=list(map(json.loads,journal.getvalue().splitlines()))
    assert [r['kind'] for r in records]==['initial','completed_packet']


def test_acquisition_rejects_old_arrays_but_allows_new_outputs(tmp_path):
    check=array_read_guard(tmp_path/'run')
    with pytest.raises(ValueError,match='Historical arrays'):
        check('open',(str(tmp_path/'historical.npz'),'rb',0))
    check('open',(str(tmp_path/'run/new.npz'),'rb',0))
    check('open',(str(tmp_path/'run/new.npz'),'wb',0))
    check('open',(str(tmp_path/'reference.json'),'rb',0))
