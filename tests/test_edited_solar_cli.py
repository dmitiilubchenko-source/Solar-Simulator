"""CSV verification rejects partial, reordered or physically mislabeled packets."""
import csv

import numpy as np
import pytest

from scripts.verify_edited_solar_cli import read_snapshots, check_bits


def write_rows(path, corruption=None):
    rows=[]
    for time in (0.,21600.):
        for name,mass,x in (('A',2.,.125),('B',1.,-.25)):
            rows.append(dict(time_seconds=time,epoch_jd_tdb='',name=name,mass_kg=mass,
                x_m=x,y_m=2.,z_m=-3.,vx_m_s=4.,vy_m_s=-5.,vz_m_s=6.,orientation_work_joules=0.))
    if corruption=='drop':rows.pop()
    if corruption=='name':rows[1]['name']='A'
    if corruption=='time':rows[1]['time_seconds']=10800.
    if corruption=='mass':rows[1]['mass_kg']=2.
    if corruption=='nonfinite':rows[1]['x_m']='nan'
    if corruption=='epoch':rows[1]['epoch_jd_tdb']=2461321.5
    if corruption=='work':rows[1]['orientation_work_joules']=1.
    with path.open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def test_csv_reader_retains_exact_si_values_and_packet_order(tmp_path):
    path=tmp_path/'states.csv';write_rows(path)
    times,values=read_snapshots(path,('A','B'),(2.,1.))
    np.testing.assert_array_equal(times,[0.,21600.])
    expected=[[[.125,2.,-3.,4.,-5.,6.],[-.25,2.,-3.,4.,-5.,6.]]]*2
    np.testing.assert_array_equal(values,expected)


def test_cli_bit_guard_rejects_the_opposite_sign_of_zero():
    a,b=np.zeros((1,10,6)),np.zeros((1,10,6));b[0,0,0]=-0.
    assert np.array_equal(a,b)
    with pytest.raises(AssertionError):check_bits(a,b)
    check_bits(a,a.copy())


@pytest.mark.parametrize('corruption',('drop','name','time','mass','nonfinite','epoch','work'))
def test_invalid_csv_cannot_qualify_a_trajectory(tmp_path,corruption):
    path=tmp_path/'bad.csv';write_rows(path,corruption)
    with pytest.raises(ValueError):read_snapshots(path,('A','B'),(2.,1.))
