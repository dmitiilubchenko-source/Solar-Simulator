"""Analytic angular / radial quadrature oracles for tracer current snapshots.

No production current/map/moment imports. Reference radial H is provided
by the independent Riccati solution; sigma_n is a supplied slice measure.
"""
import numpy as np

from scripts.independent_conventions_reference import gauss_nodes
from scripts.independent_harmonic_reference import boundary,profile


def shape_matrix(policy):
    angle=policy['shape_rotation_z_rad'];c=np.cos(angle);s=np.sin(angle)
    rotate=np.array([[c,-s,0.],[s,c,0.],[0.,0.,1.]])
    return rotate@np.diag(policy['shape_diagonal'])@rotate.T


def angular_grid(polar,azimuthal):
    z,w=np.polynomial.legendre.leggauss(polar);phi=np.arange(azimuthal)*2*np.pi/azimuthal
    zz,pp=np.meshgrid(z,phi,indexing='ij');r=np.sqrt(1-zz*zz)
    directions=np.stack([r*np.cos(pp),r*np.sin(pp),zz],axis=-1).reshape(-1,3)
    weights=np.repeat(w,azimuthal)*2*np.pi/azimuthal
    return directions,weights


def analytic_snapshot(c,solution,policy,order):
    s,w=gauss_nodes(order);u=np.sqrt(1-2*c*s*s);n=(3*np.sqrt(1-2*c)-u)/2
    a0,a2=policy['radial_density_coefficients'];density=a0+a2*s*s
    matched=boundary(solution.sol(1.),c);h,_=profile(s,solution.sol(s).T,matched)
    angular=np.eye(3)/3+2*shape_matrix(policy)/15;dipole=np.array(policy['shape_dipole'])
    m=policy['gravitational_mass_kg'];r=policy['areal_radius_m'];omega=np.array(policy['angular_velocity_s_inv']);rate=policy['radial_rate_s_inv']
    mass=3*m*np.dot(w,s*s*density/u)
    first=m*r*dipole*np.dot(w,s**3*density/u)
    first_h=m*r*dipole*np.dot(w,s*s*h*density/u)
    second=3*m*r*r*angular*np.dot(w,s**4*density/u)
    second_h=3*m*r*r*angular*np.dot(w,s*s*h*h*density/u)
    dclock=3*m*r*r*angular*np.dot(w,s**4*density/(u*n))
    inertia=np.trace(dclock)*np.eye(3)-dclock;axial=inertia@omega
    kinetic=.5*omega@inertia@omega+1.5*m*r*r*rate**2*np.dot(w,s**4*density/(u**3*n))
    return dict(mass_kg=float(mass),areal_first_kg_m=first,harmonic_first_kg_m=first_h,
        areal_second_kg_m2=second,harmonic_second_kg_m2=second_h,axial_kg_m2_s=axial,quadratic_kinetic_j=float(kinetic),
        harmonic_Euclidean_C_kg_m2=np.trace(second_h)*np.eye(3)-second_h,
        harmonic_STF_M_kg_m2=second_h-np.trace(second_h)*np.eye(3)/3)
