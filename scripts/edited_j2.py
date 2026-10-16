"""Research contracts for edited EIH+fixed-J2 models, independent of GUI."""
from dataclasses import replace
import hashlib
import json

import numpy as np

from scripts.fixed_j2_ias import model,validate,entries,scales,balances
from scripts.newton_year import errors
from scripts.assess_sandbox_planets import states
from solar_simulator.experiment import create_experiment,copy_bodies
from solar_simulator.sandbox import branch_experiment,to_branch_document
from solar_simulator.storage import to_document,from_document
from solar_simulator.time_control import advance_towards
from solar_simulator.vector3 import Vector3

CASES = tuple(f'{action}_{phase}' for phase in ('start','quarter')
    for action in ('mass','position','velocity'))


def digest(document):
    raw=json.dumps(document,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def fixture(case):
    if case not in CASES:raise ValueError('Undeclared edited EIH/J2 case')
    action,phase=case.split('_')
    parent,times,period=model('eih_two')
    # Historical research fixtures use numpy scalars; checkpoint numbers are
    # deliberately ordinary Python floats. Conversion preserves binary values.
    initial=states(parent.bodies)
    bodies=[replace(b,position=Vector3(*map(float,q[:3])),velocity=Vector3(*map(float,q[3:])))
        for b,q in zip(parent.bodies,initial)]
    parent=create_experiment(bodies,parent.settings)
    np.testing.assert_array_equal(states(parent.bodies),initial)
    if phase=='quarter':
        while parent.time<period/4:parent=advance_towards(parent,period/4,20)
    alpha,beta=parent.bodies
    if action=='mass':replacement=(alpha.name,replace(alpha,mass=1.25*alpha.mass))
    if action=='position':replacement=(beta.name,replace(beta,
        position=beta.position.add(Vector3(3e6,-2e6,4e6))))
    if action=='velocity':replacement=(beta.name,replace(beta,
        velocity=alpha.velocity.add(beta.velocity.subtract(alpha.velocity).multiply(.9))))
    branch=branch_experiment(parent,replacements=(replacement,))
    return parent,branch,times,period


def verify_branch(parent,branch):
    document=to_branch_document(branch)
    if document['parent']!=to_document(parent) or branch.child.time!=0 or branch.child.origin is not None:
        raise ValueError('Wrong parent/child boundary')
    if branch.child.settings!=parent.settings or len(branch.changes())!=1:
        raise ValueError('Expected one explicit edit with unchanged settings')
    return dict(parent_sha256=branch.parent_sha256,parent_checkpoint_sha256=digest(document['parent']),
        child_checkpoint_sha256=digest(document['child']),parent_time_seconds=parent.time,
        changes=branch.changes(),origin=None)


def variants(seed):
    # Only the force backend varies; keep exact child initial states/settings.
    return {backend:create_experiment(copy_bodies(seed.bodies),replace(seed.settings,backend=backend))
        for backend in ('python','rust')}


def legacy_trajectory(seed,times):
    times=validate(seed,times)
    current=from_document(to_document(seed));values=[];bounds=[]
    for target in times:
        while current.time<target:
            current=advance_towards(current,float(target),20);bounds.append(current.time)
        if current.time!=target:raise ValueError('Wrong legacy output epoch')
        values.append(states(current.bodies))
    return np.array(values),dict(packet_endpoints=bounds,packets=len(bounds),finished=True,
        failed=False,rhs_calls=None,controller_restarted_per_packet=True)


def checkpoint_check(seed,target):
    current=seed
    while current.time<target:current=advance_towards(current,float(target),20)
    restored=from_document(to_document(current))
    next_target=float(target+seed.settings.dt*20)
    expected=advance_towards(current,next_target,20)
    actual=advance_towards(restored,next_target,20)
    if to_document(expected)!=to_document(actual):raise ValueError('Legacy checkpoint continuation differs')
    return True


def agreement(actual,expected,names):
    actual,expected=np.asarray(actual),np.asarray(expected)
    if (actual.shape!=expected.shape or actual.ndim!=3 or actual.shape[1:]!=(len(names),6)
            or not np.isfinite(actual).all() or not np.isfinite(expected).all()):
        raise ValueError('Invalid comparison shape/finite values')
    first,second=names.index('Alpha'),names.index('Beta')
    return dict(all_bodies=errors(actual,expected),per_body={name:errors(actual[:,i],expected[:,i])
        for i,name in enumerate(names)},relative_pair=errors(actual[:,second]-actual[:,first],
            expected[:,second]-expected[:,first]))


def within(error,position,velocity):
    return error['position_metres']<position and error['velocity_m_per_s']<velocity


def reference_gate(previous,last,previous_budgets,last_budgets,seed):
    names=[b.name for b in seed.bodies];m=np.array([b.mass for b in seed.bodies])
    comparison=agreement(previous,last,names)
    initial=agreement(last[:1],states(seed.bodies)[None],names)
    scale=scales(states(seed.bodies),m,entries(seed),seed.settings.physics)
    shape=(len(last),3,7)
    if (previous_budgets.shape!=shape or last_budgets.shape!=shape
            or not np.isfinite(last_budgets).all() or not np.isfinite(previous_budgets).all()
            or not np.isfinite(scale).all() or not (scale>0).all()):
        raise ValueError('Invalid reference budgets/scales')
    budget_difference=float(abs((last_budgets-previous_budgets)/scale).max())
    passed=(within(comparison['all_bodies'],.01,1e-5) and within(comparison['relative_pair'],.01,1e-5)
        and within(initial['all_bodies'],1e-6,1e-8) and np.array_equal(last_budgets[0],np.zeros((3,7)))
        and budget_difference<1e-10)
    return dict(**comparison,initial_roundtrip=initial,maximum_scaled_budget_component=budget_difference,
        checks_passed=bool(passed))


def metrics(values,expected,budgets,seed,reference_passed):
    comparison=agreement(values,expected,[b.name for b in seed.bodies])
    if budgets.shape!=(len(values),3,7) or not np.isfinite(budgets).all():
        raise ValueError('Invalid source budget shape/finite values')
    balance=balances(values,budgets,seed)
    numeric=(all(within(e,.1,1e-4) for e in comparison['per_body'].values())
        and within(comparison['relative_pair'],.1,1e-4))
    return dict(**comparison,balance=balance,numerical_targets_passed=bool(numeric),
        checks_passed=bool(reference_passed and numeric and max(balance['corrected'].values())<1e-9))
