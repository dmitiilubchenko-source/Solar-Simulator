"""Read-only helpers for the isolated394 prototype; not a runtime optimizer."""
import hashlib
import math
from pathlib import Path
import statistics
import struct

BASE_COMMIT='fe0f456f2c7ba3a077eac21fc8413937d6e84fac'
PROTOTYPE_COMMIT='896030c3206b1010175d6a491e1f5d7063abdcf5'
PATCH_SHA256='df958f9f4c41ad9f3ed57ec2851c30de8b55e608287bd4ebeecfb2f902abbdc6'
SOURCES={
    'baseline':{'rotation.py':'245087dc0b1f5cc64e8c3fbbd1c34fe9e8f80266069ceafb8081906f8dfd4f80',
                'nbody_rotation.py':'7cdbf09b398aa467ec5badabcf4428c88dfc62ac81f49b73c988ae8c81c9ce7c'},
    'prototype':{'rotation.py':'0cec73448d8bbd3a29656d04be7f74aa04338be6df40055548910557f29412c6',
                 'nbody_rotation.py':'9126ae10a8f41849f09acc83ae152fe8aea0abe85f99f79f183db5f86b79a6a2'}}


def verify_sources(root,role):
    """Check the two bound files. Caller must also attest checkout/environment.

    This is not a security boundary for executing an arbitrary source tree.
    """
    if role not in SOURCES:raise ValueError('Unknown prototype role')
    for name,digest in SOURCES[role].items():
        file=Path(root)/'src/solar_simulator'/name
        if hashlib.sha256(file.read_bytes()).hexdigest()!=digest:raise ValueError('Source SHA mismatch: '+name)
    return dict(SOURCES[role])


def capture_rhs(module,state):
    """Capture the existing RHS before solve_ivp runs; discard no trajectory.

    The temporary module hook is restored even on failure; no cache survives.
    Use only in a single-threaded diagnostic worker, never a running app.
    """
    class Captured(Exception):pass
    result={};original=module.solve_ivp
    def intercept(fun,span,y0,**kwargs):
        result.update(fun=fun,span=span,y0=y0.copy(),kwargs=kwargs)
        raise Captured
    module.solve_ivp=intercept
    try:
        s=state.settings
        try:module.integrate(state.bodies,state.rotations,[0.,s.dt],rtol=s.rtol,
            position_atol=s.position_atol,velocity_atol=s.velocity_atol,
            relative_pair=s.relative_pair,backend=s.backend)
        except Captured:pass
        if not result:raise ValueError('No RHS captured')
        return result
    finally:module.solve_ivp=original


def numeric_state(state):
    """Owned builtin numbers, including raw q/S; no normalization."""
    return dict(positions=[[b.position.x,b.position.y,b.position.z] for b in state.bodies],
        velocities=[[b.velocity.x,b.velocity.y,b.velocity.z] for b in state.bodies],
        quaternions=[list(s.quaternion) for s in state.rotations],
        spins=[list(s.angular_momentum) for s in state.rotations])


def numeric_bytes(values):
    """Unambiguous binary64 layout for explicit saved-state fields."""
    out=bytearray()
    for key,width in (('positions',3),('velocities',3),('quaternions',4),('spins',3)):
        rows=values[key];out.extend(struct.pack('<Q',len(rows)))
        for row in rows:
            if len(row)!=width:raise ValueError('Invalid saved-state shape')
            for value in row:
                if type(value) not in (int,float) or not math.isfinite(value):raise ValueError('Invalid saved-state number')
                out.extend(struct.pack('<d',value))
    return bytes(out)


def paired_summary(pairs):
    """Paired series, not individual dependent RHS samples.

    Exact one-sided sign probability assumes independent series and a fair
    null sign. Windows scheduling does not guarantee that assumption.
    """
    if not isinstance(pairs,(list,tuple)) or not 3<=len(pairs)<=100:raise ValueError('Need3..100paired series')
    for pair in pairs:
        if type(pair) not in (list,tuple) or len(pair)!=2:raise ValueError('Invalid pair')
        if any(type(x) not in (int,float) or not math.isfinite(x) or x<=0 for x in pair):raise ValueError('Invalid elapsed time')
    a,b=zip(*pairs);gain=[x-y for x,y in pairs];ratios=[x/y for x,y in pairs]
    positives=sum(x>0 for x in gain);non_ties=sum(x!=0 for x in gain)
    p=sum(math.comb(non_ties,k) for k in range(positives,non_ties+1))/2**non_ties
    def spread(x):
        q=statistics.quantiles(x,n=4,method='inclusive')
        return dict(median=statistics.median(x),minimum=min(x),maximum=max(x),IQR=q[2]-q[0])
    return dict(baseline=spread(a),prototype=spread(b),absolute_saving=spread(gain),speedup=spread(ratios),
        series_pairs=pairs,positive_series=positives,non_tied_series=non_ties,one_sided_sign_p=p,
        sign_test_caveat='Independent series/fair null sign assumed; timing evidence on this PC only.')
