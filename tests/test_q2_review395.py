"""Offline reviewer errors fail closed without modifying archives."""
import copy,hashlib
import pytest
from scripts.q2_review395 import read_archive,timing_audit


def samples():
    return [dict(series=i,order=order,rows=[dict(id=case,
        micro=[dict(role=role,wall_seconds=1. if role=='A' else .9,calls=512) for role in order],
        macro=[dict(role=role,wall_seconds=2. if role=='A' else 1.8,rollouts=8,packets_per_rollout=2) for role in order])
        for case in ['one-python','two-python','one-rust','two-rust']]) for i,order in enumerate(['ABBA','BAAB','ABBA','BAAB','ABBA'])]


def test_independent_medians_pairs_and_sign_probability_preserve_inputs():
    rows=samples();before=copy.deepcopy(rows);r=timing_audit(rows)
    assert rows==before and not r['losing_case_series']
    assert r['levels']['micro']['aggregate']['median_speedup']==pytest.approx(1/.9)
    assert r['levels']['macro']['aggregate']['sign_p_exact']=='1/32'
    assert r['levels']['micro']['aggregate']['median_paired_saving']==pytest.approx(.8)


@pytest.mark.parametrize('change',['bool','nan','inf','zero','huge','order','workload','case','missing'])
def test_invalid_timing_or_reordered_workload_is_rejected(change):
    rows=samples()
    if change in ('bool','nan','inf','zero','huge'):rows[0]['rows'][0]['micro'][0]['wall_seconds']={'bool':True,'nan':float('nan'),'inf':float('inf'),'zero':0.,'huge':10**500}[change]
    if change=='order':rows[0]['rows'][0]['macro'][0]['role']='B'
    if change=='workload':rows[0]['rows'][0]['micro'][0]['calls']=1
    if change=='case':rows[0]['rows'].reverse()
    if change=='missing':rows.pop()
    with pytest.raises(ValueError):timing_audit(rows)


def test_losing_series_is_kept_instead_of_selected_away():
    rows=samples();rows[2]['rows'][0]['macro'][0]['wall_seconds']=.01
    r=timing_audit(rows);assert r['losing_case_series'][0]['series']==2


def test_bad_archive_fails_before_decompression_and_leaves_bytes(tmp_path):
    p=tmp_path/'not-valid.zip';p.write_bytes(b'not an archive');before=p.read_bytes()
    with pytest.raises(ValueError,match='SHA'):read_archive(p)
    assert p.read_bytes()==before
