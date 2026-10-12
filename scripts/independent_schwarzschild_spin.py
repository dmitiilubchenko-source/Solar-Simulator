"""Independent spherical Schwarzschild covector oracle on a circular orbit.

Standard areal metric (-f,1/f,R²,R²sin²theta), equator; Bini et al. (2005)
(2.1),(2.7). Inputs SI. Integrates scaled covector [S0,SR,Stheta/R,Sphi/R]
against orbital phase, separately from Cartesian Christoffel/root machinery.
No production metric/transport functions, matrix normalization, or projection.
"""
import numpy as np


def constants(gm, rho, c):
    u = gm/(2*c**2*rho)
    radius = rho*(1+u)**2
    epsilon = gm/(c**2*radius)
    frequency = np.sqrt(gm/radius**3)
    return u, radius, epsilon, frequency


def spherical_generator(gm, rho, c):
    _, radius, epsilon, frequency = constants(gm, rho, c)
    f = 1-2*epsilon
    matrix = np.zeros((4, 4))
    matrix[0, 1] = c*f*epsilon/(radius*frequency)
    matrix[1, 0] = c*epsilon/(radius*f*frequency)
    matrix[1, 3] = 1.
    matrix[3, 1] = -f
    return matrix


def initial_covectors(gm, rho, c):
    u, radius, epsilon, frequency = constants(gm, rho, c)
    f = 1-2*epsilon
    radial_root = (1+u)**-2
    tangential_root = np.sqrt(radial_root**2-(frequency*rho/c)**2/f)
    cartesian = np.diag([1/radial_root, 1/tangential_root, 1/radial_root])
    spherical = np.zeros((4, 3))
    spherical[0] = -frequency*rho/c*cartesian[1]
    spherical[1] = cartesian[0]/(1-u**2)
    spherical[2] = -rho/radius*cartesian[2]
    spherical[3] = rho/radius*cartesian[1]
    return spherical


def euclidean_basis(phase, covectors, gm, rho, c):
    """Exact coordinate Jacobian and analytic scalar boost eigenvalues.

    Does not call production positive-root/metric/Christoffel routines.
    """
    u, radius, epsilon, frequency = constants(gm, rho, c)
    radial = np.array([np.cos(phase), np.sin(phase), 0.])
    tangent = np.array([-np.sin(phase), np.cos(phase), 0.])
    vertical = np.array([0., 0., 1.])
    cartesian = ((1-u**2)*np.outer(radial, covectors[1])
                 -radius/rho*np.outer(vertical, covectors[2])
                 +radius/rho*np.outer(tangent, covectors[3]))
    h_radial = (1+u)**-2
    h_tangent = np.sqrt(h_radial**2-(frequency*rho/c)**2/(1-2*epsilon))
    # H = h_radial I + (h_tangent-h_radial) ephi ephi^T.
    return h_radial*cartesian+(h_tangent-h_radial)*np.outer(tangent, tangent@cartesian)


def invariants(covectors, gm, rho, c):
    _, radius, epsilon, frequency = constants(gm, rho, c)
    f = 1-2*epsilon
    gram = covectors.T@np.diag([-1/f, f, 1., 1.])@covectors
    ssc = covectors[0]+frequency*radius/c*covectors[3]
    return gram, ssc
