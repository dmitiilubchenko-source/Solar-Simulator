"""Independent limits and input-integrity checks for the bounded shadow338."""
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import json
from math import cos,sin
import struct

import numpy as np
import pytest

from scripts.assess_kepler_force_rounding import decimal_acceleration
from scripts.assess_kepler_shadow import run
from scripts.assess_rust_trace import coefficients
from scripts.kepler_shadow import relative_rhs,rk_step,trace_grid,trajectory,exact_elapsed


def header():
    v=list(struct.unpack('>194d',coefficients()))
    return dict(kind='header',schema=337,a=[v[i:i+12] for i in range(0,144,12)],
        b=v[144:156],c=v[156:168],e3=v[168:181],e5=v[181:194])


def test_decimal_rhs_exact_radius_scaling_and_legacy_rounding():
    with localcontext() as context:
        context.prec=70
        for p,expected in (((3,4,0),(-3,-4,0)),((-6,-8,0),(.75,1,0)),((0,3,4),(0,-3,-4))):
            state=tuple(map(D,(*p,1,2,3)))
            assert relative_rhs(state,D(125))==tuple(map(D,(1,2,3,*expected)))
        p=[1.23e10,-4.56e9,7.89e8];mu=D('1.32712440018e20')
        rhs=relative_rhs(tuple(D.from_float(x) for x in (*p,1.,2.,3.)),mu)
        np.testing.assert_array_equal(list(map(float,rhs[3:])),decimal_acceleration(p,mu))
    with pytest.raises(ValueError): relative_rhs((D(0),)*6,D(1))
    with pytest.raises(ValueError): relative_rhs((D(1),)*6,D(-1))


def test_fixed_tableau_free_motion_and_oscillator():
    table=header()
    with localcontext() as context:
        context.prec=80
        a=tuple(tuple(D.from_float(x) for x in row) for row in table['a'])
        b=tuple(D.from_float(x) for x in table['b'])
        initial=tuple(map(D,(1,0,0,0,1,0)))
        free=lambda y:y[3:]+(D(0),)*3
        result=rk_step(initial,D(2),a,b,free)
        assert max(abs(x-D(y)) for x,y in zip(result,(1,2,0,0,1,0)))<D('1e-14')
        state=initial
        for _ in range(200):
            state=rk_step(state,D('.01'),a,b,lambda y:y[3:]+tuple(-x for x in y[:3]))
        assert abs(float(state[0])-cos(2))<1e-13
        assert abs(float(state[1])-sin(2))<1e-13


def test_elapsed_sum_is_exact_under_a_small_ambient_context():
    value=F(1)+F(1,2**70)
    with localcontext() as context:
        context.prec=9
        assert F(exact_elapsed(value))==value


def trace_rows():
    old=[0.,0.,0.,3.,4.,0.,0.,0.,0.,1.,0.,0.]
    trial=old.copy();trial[3]=3.5
    final=trial.copy();final[3]=4.
    row=lambda t,n,h,b,a,e:dict(kind='attempt',time=t,next=n,h=h,packet_end=1.,
        old=b,trial=a,error=e,accepted=e<1.)
    statistics=dict(accepted=2,rejected=1,packets=1,rhs_calls=40,failed=False)
    return [header(),row(0.,.5,.5,old,trial,0.),row(.5,1.,.5,trial,final,2.),
        row(.5,1.,.5,trial,final,0.),dict(kind='finish',statistics=statistics)],statistics


@pytest.mark.parametrize('damage',[None,'truncated','clock','uncommitted','coefficients'])
def test_grid_excludes_rejections_and_rejects_corruption(tmp_path,damage):
    rows,statistics=trace_rows()
    if damage=='truncated':rows.pop()
    elif damage=='clock':rows[3]['h']=.25
    elif damage=='uncommitted':rows[3]['old']=[0.]*12
    elif damage=='coefficients':rows[0]['b'][0]*=2
    path=tmp_path/'grid.jsonl';path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
    if damage:
        with pytest.raises(ValueError):trace_grid(path,[1.],statistics)
    else:
        table,initial,steps=trace_grid(path,[1.],statistics)
        assert steps==[(.5,.5),(1.,.5)]
        values,elapsed=trajectory(initial,steps,[0.,1.],table,D(1),50)
        assert len(values)==2 and elapsed==[D(0),D(1)]
        with pytest.raises(ValueError):trajectory(initial,steps,[0.,.25,1.],table,D(1),50)


@pytest.mark.parametrize('suffix',['.json','.npz'])
def test_existing_shadow_result_is_preserved(tmp_path,suffix):
    output=tmp_path/'kept.json';saved=output.with_suffix(suffix);saved.write_bytes(b'previous')
    with pytest.raises(FileExistsError):run(tmp_path/'missing.json',output)
    assert saved.read_bytes()==b'previous'
