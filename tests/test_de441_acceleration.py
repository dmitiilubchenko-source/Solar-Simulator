"""Known polynomial limits, independent selection and jump sensitivity."""
from decimal import Decimal,localcontext
from zipfile import ZipFile

import numpy as np
import pytest

from scripts import assess_de441_acceleration as audit
from scripts import de441_power as power


def test_known_cubic_conversion_and_derivatives_have_analytic_coefficients():
    # 5+2T1+3T2+4T3 = 2-10x+6x²+16x³.
    coefficients=power.power_basis([5,2,3,4])
    assert coefficients==(2,-10,6,16)
    assert power.horner(coefficients,Decimal(1))==14
    assert power.horner(power.derivative(coefficients,1),Decimal(1))==50
    assert power.horner(power.derivative(coefficients,2),Decimal(1))==108
    # For an eight-second segment dx/dt=1/4, so d²p/dt²=108/16.
    assert power.horner(power.derivative(coefficients,2),Decimal(1))*(Decimal(2)/8)**2==Decimal('6.75')


def test_constant_and_linear_polynomials_have_exact_zero_acceleration():
    for c in ([7],[2,3]):
        assert power.horner(power.derivative(power.power_basis(c),2),Decimal('.123'))==0


@pytest.mark.parametrize('side,index',[('left',0),('right',1)])
def test_exact_join_selection_is_explicit_and_does_not_use_epsilon(side,index):
    assert power.choose([Decimal(0),Decimal(4)],[Decimal(4),Decimal(8)],Decimal(4),side)==index


@pytest.mark.parametrize('time,side',[(-1,'right'),(9,'left'),(4,'middle')])
def test_missing_block_or_ambiguous_side_is_rejected(time,side):
    with pytest.raises(ValueError):power.choose([Decimal(0),Decimal(4)],[Decimal(4),Decimal(8)],Decimal(time),side)


def test_smooth_motion_and_true_jump_are_separated_vectorially():
    left=np.array([[Decimal(1),Decimal(0),Decimal(0)]],dtype=object)
    right=np.array([[Decimal(3),Decimal(0),Decimal(0)]],dtype=object)
    before=left-np.array([[Decimal('.1'),Decimal(0),Decimal(0)]],dtype=object)
    after=right+np.array([[Decimal('.2'),Decimal(0),Decimal(0)]],dtype=object)
    j,s,d,e,signal=power.split_difference(left,right,before,after)
    assert (j[0,0],s[0,0],d[0,0],e[0,0])==(Decimal(2),Decimal('.3'),Decimal('2.3'),Decimal(0))
    assert signal[0]==pytest.approx(2/2.3)
    assert d[0,0]-s[0,0] != 0 # Omitting J is detected.
    assert d[0,0]-s[0,0]+j[0,0]==4 # Wrong jump sign is detected.


def test_jump_and_smooth_change_can_cancel_without_a_monotone_norm():
    a=np.array([[Decimal(0),Decimal(0),Decimal(0)]],dtype=object)
    b=np.array([[Decimal(1),Decimal(0),Decimal(0)]],dtype=object)
    j,s,total,identity,_=power.split_difference(a,b,a,a)
    assert j[0,0]==1 and s[0,0]==-1 and total[0,0]==identity[0,0]==0


def test_subtraction_precedes_float_and_keeps_sub_ulp_difference():
    with localcontext() as context:
        context.prec=90
        a=np.array([[Decimal('1.00000000000000000001'),Decimal(0),Decimal(0)]],dtype=object)
        b=np.array([[Decimal(1),Decimal(0),Decimal(0)]],dtype=object)
        assert float(a[0,0])==float(b[0,0])
        absolute,relative=power.errors(a,b)
        assert absolute[0]==relative[0]==1e-20


def test_own_norm_retains_a_small_outer_body_error():
    b=np.array([[1,0,0],[Decimal('1e-30'),0,0]],dtype=object);a=b.copy();a[1,0]*=2
    absolute,relative=power.errors(a,b)
    assert absolute[1]==1e-30 and relative[1]==1


@pytest.mark.parametrize('values',[[],[Decimal('NaN')],[Decimal('Infinity')]])
def test_invalid_polynomial_is_rejected(values):
    with pytest.raises(ValueError):power.power_basis(values)


@pytest.mark.parametrize('order',[-1,3,True])
def test_unsupported_derivative_is_rejected(order):
    with pytest.raises(ValueError):power.derivative([Decimal(1)],order)


def test_real_oracle_does_not_call_reader_selector_or_chebyshev_evaluator(monkeypatch):
    reader,_=audit.de.load_archive(audit.ROOT/audit.de.ARCHIVE)
    with ZipFile(audit.ROOT/audit.de.ARCHIVE) as z:raw=z.read('de441-ten-year-records.txt')
    oracle=power.Oracle(reader,raw,90,True)
    def forbidden(*a,**k):raise AssertionError('Shared reader algorithm called')
    monkeypatch.setattr(reader,'locate',forbidden);monkeypatch.setattr(audit.de,'polynomial',forbidden)
    assert oracle.evaluate(0.).shape==(1,11,3)
    assert len(oracle.seams(audit.field.TIMES[-1]))>0


def test_raw_decimal_token_retains_information_lost_in_binary64():
    token='1.00000000000000001'
    assert Decimal(token)!=power.decimal(float(token))


def test_existing_output_is_rejected_before_loading_scientific_sources(tmp_path,monkeypatch):
    monkeypatch.setattr(audit,'ROOT',tmp_path);path=tmp_path/'.tools/old.json';path.parent.mkdir();path.write_text('{}')
    with pytest.raises(ValueError,match='Fresh'):audit.run(path,tmp_path/'absent.json')


def test_missing_raw_inventory_cannot_qualify_by_success_flags():
    assert not audit.qualification({},np.array([0.]),np.array([1.]))
