"""Current/cotangent/coordinate-moment snapshots under an equivariant radial map.

SI masses, positions, coordinate velocities and covariant momenta on one
specified static-time slice. No recentring, EOS or physical PN inertia inferred.
"""
import numpy as np

from scripts.density_moments import mass_positions, mass_moments
from scripts.external_metric import array, finite_outputs


def positive_field(value,count,name):
    raw=np.asarray(value)
    if raw.shape==():out=np.full(count,float(array(raw,(),name)))
    else:out=array(raw,(count,),name)
    if np.any(out<=0):raise ValueError('Positive '+name+' required')
    return out


def current_density_pullback(areal_coordinate_density,determinant):
    raw=np.asarray(determinant)
    if raw.ndim!=1 or not len(raw):raise ValueError('Nonempty determinant vector required')
    det=positive_field(raw,len(raw),'Jacobian determinant')
    density=array(areal_coordinate_density,(len(raw),),'areal coordinate density')
    if np.any(density<0):raise ValueError('Nonnegative current density required')
    result=density/det;finite_outputs(result)
    return result


def snapshot(masses,positions,velocities,covariant_momenta,radial_jacobian,tangent_jacobian,areal_metric_radial,lapse):
    """Map positions/vectors/oneforms/metric and report coordinate moments.

    Momentum is supplied independently; kinetic quadratic form does not
    assert the supplied momentum satisfies a particle or fluid Hamiltonian.
    """
    m,x=mass_positions(masses,positions);count=len(m)
    v=array(velocities,(count,3),'coordinate velocities');p=array(covariant_momenta,(count,3),'covariant momenta')
    radial=positive_field(radial_jacobian,count,'radial Jacobian');tangent=positive_field(tangent_jacobian,count,'tangent Jacobian')
    gr=positive_field(areal_metric_radial,count,'areal radial metric');n=positive_field(lapse,count,'lapse')
    radius=np.linalg.norm(x,axis=1);finite_outputs(radius)
    centre=radius==0.
    if np.any(centre&((radial!=tangent)|(gr!=1.))):raise ValueError('Regular isotropic centre geometry required')
    condition=np.maximum(radial/tangent,tangent/radial)
    if np.any(condition>=1e8):raise ValueError('Ill-conditioned radial differential')
    directions=np.zeros_like(x);directions[~centre]=x[~centre]/radius[~centre,None]
    projector=directions[:,:,None]*directions[:,None,:];identity=np.eye(3)
    jacobian=tangent[:,None,None]*identity+(radial-tangent)[:,None,None]*projector
    oldmetric=identity+(gr-1)[:,None,None]*projector
    inverse=np.linalg.inv(jacobian)
    mapped=tangent[:,None]*x
    newvelocity=np.einsum('nij,nj->ni',jacobian,v)
    newmomentum=np.linalg.solve(jacobian.transpose(0,2,1),p[...,None])[...,0]
    newmetric=inverse.transpose(0,2,1)@oldmetric@inverse
    determinant=radial*tangent*tangent
    oldmoments=mass_moments(m,x);newmoments=mass_moments(m,mapped)
    oldkin=.5*np.sum(m/n*np.einsum('ni,nij,nj->n',v,oldmetric,v))
    newkin=.5*np.sum(m/n*np.einsum('ni,nij,nj->n',newvelocity,newmetric,newvelocity))
    values=dict(mapped_positions_m=mapped,mapped_velocities_m_s=newvelocity,mapped_momenta_kg_m_s=newmomentum,
        jacobians=jacobian,determinants=determinant,areal_metrics=oldmetric,mapped_metrics=newmetric,
        areal_second_moment_kg_m2=oldmoments[0],mapped_second_moment_kg_m2=newmoments[0],
        mapped_Euclidean_C_kg_m2=newmoments[1],mapped_STF_M_kg_m2=newmoments[2],
        areal_first_moment_kg_m=np.sum(m[:,None]*x,axis=0),mapped_first_moment_kg_m=np.sum(m[:,None]*mapped,axis=0),
        areal_axial_charge_kg_m2_s=np.sum(np.cross(x,p),axis=0),mapped_axial_charge_kg_m2_s=np.sum(np.cross(mapped,newmomentum),axis=0),
        areal_pairing_kg_m2_s2=np.sum(p*v,axis=1),mapped_pairing_kg_m2_s2=np.sum(newmomentum*newvelocity,axis=1),
        areal_quadratic_kinetic_j=float(oldkin),mapped_quadratic_kinetic_j=float(newkin))
    finite_outputs(*values.values())
    return values
