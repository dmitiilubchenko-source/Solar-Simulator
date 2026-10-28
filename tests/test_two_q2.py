"""Conservative degree-two model; synthetic inputs, independent scalar potential."""
from dataclasses import replace

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from scripts.two_q2_fixture380 import fixture
from solar_simulator.experiment import create_experiment,advance
from solar_simulator.storage import to_document,from_document


def test_two_rotations_are_advanced_and_persisted_without_a_new_schema():
    b,r,s=fixture();state=create_experiment(b,s,rotations=r)
    result=advance(state,1);doc=to_document(result)
    assert doc['schema_version']==10 and len(doc['rotations'])==2
    assert to_document(from_document(doc))==doc
    assert all(a.quaternion!=c.quaternion for a,c in zip(state.rotations,result.rotations))
    assert state.rotations==r and len(result.rotations)==2


def test_reports_and_convergence_cover_both_spins():
    from solar_simulator.cli import report
    from solar_simulator.inspection import report as explain
    from solar_simulator.convergence import compare_tolerances
    b,r,s=fixture();state=create_experiment(b,s,rotations=r)
    info=report(state)
    assert len(info['dynamic_spin_torques_by_body'])==2
    assert 'Q2-Q2 omitted' in info['conservation_scope']
    assert 'двумя' in explain(state)['numerical_reliability']['model']['description']
    comparison=compare_tolerances(state,1)
    assert [x['body'] for x in comparison['rotation_comparison']['per_body']]==['A','B']


def independent_potential(positions,masses,states,matrices=None):
    """MacCullagh principal-I scalar form; no runtime Q or force routines."""
    result=0.
    if matrices is None:matrices=[Rotation.from_quat(np.roll(s.quaternion,-1)).as_matrix() for s in states]
    from solar_simulator.simulation import G
    names=['A','B','C'][:len(masses)]
    for state,matrix in zip(states,matrices):
        source=names.index(state.body);inertia=np.array(state.figure.moments)
        for j in range(len(masses)):
            if j==source:continue
            vector=positions[j]-positions[source];distance=np.linalg.norm(vector);local=matrix.T@vector
            result+=G*masses[j]*(3*np.dot(inertia*local,local)-sum(inertia)*distance**2)/(2*distance**5)
    return result


@pytest.mark.parametrize('third',[False,True])
def test_field_from_independent_position_and_attitude_gradients(third):
    from solar_simulator.nbody_rotation import corrections
    b,r,_=fixture(third);p=np.array([[b.position.x,b.position.y,b.position.z] for b in b]);m=np.array([b.mass for b in b])
    a,torques,potential=corrections(p,m,(0,1),r);forces=a*m[:,None]
    assert potential==pytest.approx(independent_potential(p,m,r),rel=1e-13)
    fd=np.zeros_like(p);h=.02
    for i in range(len(b)):
        for j in range(3):
            plus=p.copy();minus=p.copy();plus[i,j]+=h;minus[i,j]-=h
            fd[i,j]=-(independent_potential(plus,m,r)-independent_potential(minus,m,r))/(2*h)
    assert np.linalg.norm(fd-forces)/np.linalg.norm(forces)<2e-6
    matrices=[Rotation.from_quat(np.roll(s.quaternion,-1)).as_matrix() for s in r];angle=1e-6
    for i in range(2):
        gradient=[]
        for axis in np.eye(3):
            plus=list(matrices);minus=list(matrices)
            plus[i]=Rotation.from_rotvec(axis*angle).as_matrix()@matrices[i]
            minus[i]=Rotation.from_rotvec(-axis*angle).as_matrix()@matrices[i]
            gradient.append(-(independent_potential(p,m,r,plus)-independent_potential(p,m,r,minus))/(2*angle))
        assert np.linalg.norm(np.array(gradient)-torques[i])/np.linalg.norm(torques[i])<2e-6
    assert np.linalg.norm(forces.sum(axis=0))/np.linalg.norm(forces)<1e-13
    balance=np.sum(np.cross(p,forces),axis=0)+np.sum(torques,axis=0)
    assert np.linalg.norm(balance)/sum(np.linalg.norm(t) for t in torques)<2e-12


def test_covariance_under_rotation_and_translation():
    from solar_simulator.nbody_rotation import corrections
    b,r,_=fixture(True);p=np.array([[x.position.x,x.position.y,x.position.z] for x in b]);m=np.array([x.mass for x in b])
    a,t,u=corrections(p,m,(0,1),r);turn=Rotation.from_rotvec([.2,-.3,.1]);matrix=turn.as_matrix()
    other=tuple(replace(s,quaternion=tuple(np.roll((turn*Rotation.from_quat(np.roll(s.quaternion,-1))).as_quat(),1))) for s in r)
    aa,tt,uu=corrections(p@matrix.T+[1000.,-2000.,3000.],m,(0,1),other)
    assert np.allclose(aa,a@matrix.T,rtol=1e-12,atol=1e-20)
    assert np.allclose(tt,np.asarray(t)@matrix.T,rtol=1e-12)
    assert uu==pytest.approx(u,rel=1e-13)


def test_zero_quadrupoles_have_no_correction_and_both_free_spherical_spins():
    from solar_simulator.nbody_rotation import corrections,integrate
    from solar_simulator.rotation import rotation_matrix
    b,r,s=fixture();r=tuple(replace(x,figure=replace(x.figure,moments=(sum(x.figure.moments)/3,)*3)) for x in r)
    p=np.array([[x.position.x,x.position.y,x.position.z] for x in b]);m=np.array([x.mass for x in b])
    a,t,u=corrections(p,m,(0,1),r)
    assert not np.any(a) and not np.any(t) and u==0
    samples=integrate(b,r,[0.,100.,200.],rtol=3e-13,position_atol=1e-8,velocity_atol=1e-12,relative_pair=('A','B'))
    for time,(_,states) in zip([0.,100.,200.],samples):
        for initial,actual in zip(r,states):
            matrix=Rotation.from_rotvec(np.array(initial.angular_momentum)/initial.figure.moments[0]*time).as_matrix()
            assert np.linalg.norm(rotation_matrix(actual.quaternion)-matrix@rotation_matrix(initial.quaternion))<1e-9
            assert actual.angular_momentum==initial.angular_momentum


@pytest.mark.parametrize('change',['duplicate','third','mass','initial_q','overlap'])
def test_invalid_two_figure_setup_is_rejected(change):
    from solar_simulator.vector3 import Vector3
    b,r,s=fixture()
    if change=='duplicate':r=(r[0],replace(r[1],body='A'))
    if change=='third':r=r+(r[0],)
    if change=='mass':r=(r[0],replace(r[1],figure=replace(r[1].figure,mass=r[1].figure.mass*.5)))
    if change=='initial_q':r=(r[0],replace(r[1],quaternion=tuple(x*(1+1e-10) for x in r[1].quaternion)))
    if change=='overlap':b[1]=replace(b[1],position=b[0].position.add(Vector3(1500.,0.,0.)))
    with pytest.raises(ValueError):create_experiment(b,s,rotations=r)


@pytest.mark.parametrize('backend',['python','rust'])
def test_same_packets_save_resume_and_reset_are_exact(tmp_path,backend):
    if backend=='rust':pytest.importorskip('solar_native')
    from solar_simulator.storage import save,load
    from solar_simulator.experiment import reset
    b,r,s=fixture(backend=backend);initial=create_experiment(b,s,rotations=r)
    middle=advance(initial,2);path=tmp_path/'two.json';save(middle,path)
    loaded=load(path);original=to_document(middle)
    assert to_document(advance(loaded,2))==to_document(advance(middle,2))
    assert to_document(middle)==original
    assert to_document(reset(loaded))==to_document(initial)


@pytest.mark.parametrize('index',[0,1])
def test_metadata_of_each_saved_spin_is_checked(index):
    b,r,s=fixture();doc=to_document(advance(create_experiment(b,s,rotations=r),1))
    doc['rotations'][index]['provenance']='tampered'
    with pytest.raises(ValueError,match='происхождение'):from_document(doc)


def test_second_spin_error_is_not_diluted_by_other_blocks():
    from solar_simulator.nbody_rotation import RotationDOP853
    values=[]
    for count in (2,100):
        y=np.zeros(6*count+14);y[6*count]=y[6*count+7]=1
        solver=RotationDOP853(lambda t,y:np.zeros_like(y),0.,y,1.,body_count=count,rotation_count=2)
        k=np.zeros((len(solver.E5),len(y)));k[0,-1]=2.
        values.append(solver._estimate_error_norm(k,.2,np.ones_like(y)))
    assert values[0]>0 and values[0]==values[1]


def test_integrated_covariance_of_both_orientations_and_spins():
    from solar_simulator.vector3 import Vector3
    from solar_simulator.rotation import rotation_matrix
    b,r,s=fixture(True);turn=Rotation.from_rotvec([.2,-.3,.1]);R=turn.as_matrix();shift=np.array([1000.,-2000.,3000.])
    vector=lambda x:np.array([x.x,x.y,x.z])
    other_b=[replace(x,position=Vector3(*(R@vector(x.position)+shift)),velocity=Vector3(*(R@vector(x.velocity)))) for x in b]
    other_r=tuple(replace(x,quaternion=tuple(np.roll((turn*Rotation.from_quat(np.roll(x.quaternion,-1))).as_quat(),1)),
        angular_momentum=tuple(R@np.array(x.angular_momentum))) for x in r)
    final=advance(create_experiment(b,s,rotations=r),4)
    transformed=advance(create_experiment(other_b,s,rotations=other_r),4)
    for x,y in zip(final.bodies,transformed.bodies):
        assert np.linalg.norm(vector(y.position)-(R@vector(x.position)+shift))<1e-6
        assert np.linalg.norm(vector(y.velocity)-R@vector(x.velocity))<1e-9
    for x,y in zip(final.rotations,transformed.rotations):
        assert np.linalg.norm(rotation_matrix(y.quaternion)-R@rotation_matrix(x.quaternion))<1e-9
        assert np.linalg.norm(np.array(y.angular_momentum)-R@np.array(x.angular_momentum))/np.linalg.norm(x.angular_momentum)<1e-10
