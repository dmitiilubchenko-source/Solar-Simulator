"""Exact crafted arithmetic and corruption controls for the337 recorder."""
from fractions import Fraction as F
import json
import struct

import numpy as np
import pytest

from scripts.assess_rust_trace import analyse_trace, coefficients, local_errors


def test_sum_rounding_is_distinct_from_state_addition():
    loss=local_errors(0.,1.,[1.,1.,1.],[2.**53,1.,-2.**53],0.,0.)
    assert loss==dict(dot=F(-1),multiply=F(0),addition=F(0),total=F(-1))
    for sign in (1.,-1.):
        loss=local_errors(sign*2.**53,1.,[1.],[sign],sign,sign*2.**53)
        assert loss['addition']==-F(sign)
        assert loss['dot']==loss['multiply']==0


def test_product_rounding_and_exact_zero_are_identified():
    value=.1*.1
    loss=local_errors(0.,.1,[1.],[.1],.1,value)
    assert loss['multiply']==F(value)-F(.1)**2!=0
    assert loss['dot']==loss['addition']==0
    assert all(x==0 for x in local_errors(0.,1.,[0.],[0.],0.,0.).values())
    with pytest.raises(ValueError):
        local_errors(0.,1.,[1.],[1.],2.,2.)


def valid_trace():
    flat=list(struct.unpack('>194d',coefficients()))
    header=dict(kind='header',schema=337,a=[flat[i:i+12] for i in range(0,144,12)],
        b=flat[144:156],c=flat[156:168],e3=flat[168:181],e5=flat[181:194])
    def weighted(row):
        # Python's built-in sum uses a different algorithm in this interpreter.
        value=0.
        for x in row:
            value+=x
        return value
    stage_sums=[[weighted(header['a'][s][:s])]*12 for s in range(1,12)]
    update=[weighted(header['b'])]*12
    row=dict(kind='attempt',time=0.,next=1.,h=1.,packet_end=1.,old=[0.]*12,
        k=[[1.]*12 for _ in range(13)],stage_sums=stage_sums,stages=stage_sums,
        update_sum=update,trial=update,error=0.,accepted=True)
    statistics=dict(accepted=1,rejected=0,packets=1,rhs_calls=14,failed=False)
    return [header,row,dict(kind='finish',statistics=statistics)],statistics


@pytest.mark.parametrize('damage',[None,'truncated','stage','acceptance','footer','coefficient'])
def test_stream_integrity_and_operation_replay(tmp_path,damage):
    rows,statistics=valid_trace()
    if damage=='truncated': rows.pop()
    elif damage=='stage':
        # Break the alias before changing the recorded result only.
        rows[1]['stages']=[row.copy() for row in rows[1]['stages']]
        rows[1]['stages'][0][3]=float(np.nextafter(rows[1]['stages'][0][3],np.inf))
    elif damage=='acceptance': rows[1]['accepted']=False
    elif damage=='footer': rows[-1]['statistics']={**statistics,'accepted':2}
    elif damage=='coefficient': rows[0]['b'][0]*=2
    path=tmp_path/'trace.jsonl'
    path.write_text(''.join(json.dumps(row)+'\n' for row in rows))
    if damage:
        with pytest.raises(ValueError):
            analyse_trace(path,[1.],statistics)
    else:
        result=analyse_trace(path,[1.],statistics)
        assert result['attempts']==1 and result['all_local_identities_exact']
        assert not result['global_error_bound']
