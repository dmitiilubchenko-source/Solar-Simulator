"""Cross-language oracle checks, including amplified 1PN and pair geometry."""
from pathlib import Path
import numpy as np
import pytest
from scripts.independent_eih_rust import load_oracle
from scripts.assess_relativity import independent_acceleration


@pytest.fixture(scope='module')
def oracle():
    if not (Path.home()/'.cargo/bin/rustc.exe').exists(): pytest.skip('Developer Rust compiler absent')
    return load_oracle()


@pytest.mark.parametrize('count',[2,3,14,27])
def test_rust_scalar_matches_python_including_visible_1pn(oracle,count):
    rng=np.random.default_rng(772+count)
    for _ in range(12):
        p=rng.normal(size=(count,3))*5;v=rng.normal(size=(count,3))*.02
        mu=np.exp(rng.uniform(-5,0,count))
        for c in (300.,63241.):
            for pair in (None,(0,count-1,p[-1]-p[0]+np.array([.001,-.002,.0003]))):
                expected=independent_acceleration(p,v,mu,c,pair)
                actual=oracle(p,v,mu,c,pair)
                np.testing.assert_allclose(actual,expected,rtol=8e-14,atol=1e-16)
                # Compare the 1PN correction too, rather than hiding it under Newton.
                if c==300.:
                    newton=independent_acceleration(p,v,mu,1e100,pair)
                    np.testing.assert_allclose(actual-newton,expected-newton,rtol=2e-7,atol=3e-16)


def test_oracle_rejects_invalid_shapes_singularities_and_pair_indices(oracle):
    p=np.array([[0.,0.,0.],[1.,0.,0.]]);v=np.zeros_like(p);mu=np.ones(2)
    for a,b,m,pair in ((p[:1],v,mu,None),(np.zeros_like(p),v,mu,None),
            (p,v,np.array([0.,1.]),None),(p,v,mu,(0,2,np.ones(3))),
            (p,v,mu,(0,1,np.ones(2))),(p,v,mu,(0,1,np.zeros(3)))):
        with pytest.raises(ValueError): oracle(a,b,m,300.,pair)


def test_unaligned_numpy_inputs_are_copied_before_rust_slice_access(oracle):
    buffer=bytearray(49)
    p=np.ndarray((2,3),dtype=np.float64,buffer=buffer,offset=1)
    p[:]=[[0.,0.,0.],[1.,2.,3.]]
    assert not p.flags.aligned
    np.testing.assert_allclose(oracle(p,p,np.ones(2),300.),
        independent_acceleration(p.copy(),p.copy(),np.ones(2),300.),rtol=1e-14)
