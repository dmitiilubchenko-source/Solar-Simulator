"""Regular spherical harmonic-coordinate benchmark, not an ADM/lunar map.

M/R/t are gravitational mass, areal surface radius and asymptotic time.
The numerical chart benchmark deliberately requires 1e-4<=C<=0.3.
"""
import numpy as np

from scripts.continuum_sphere import background, radius_grid, scalar
from scripts.external_metric import array, finite_outputs

SERIES_TERMS=128


def harmonic_compactness(value):
    c=scalar(value,'harmonic compactness')
    if not 1e-4<=c<=.3:raise ValueError('Harmonic benchmark 1e-4<=C<=0.3 required')
    return c


def rhs(radius_fraction,state,c):
    """Raw F/Fprime for H=sF, exact regular origin without a cutoff."""
    s=scalar(radius_fraction,'radial fraction');c=harmonic_compactness(c)
    f,first=array(state,(2,),'raw F/Fprime');bg=background(s,c)
    u=np.sqrt(bg['radial_inverse_metric']);n=bg['lapse']
    b=c/(u*n)-6*c/(u*u)
    if s==0.:
        if first!=0.:raise ValueError('Regular centre requires Fprime=0')
        second=-b*f/5
    else:
        a=c*s/(u*n)-2*c*s/(u*u)
        second=-(4/s+a)*first-b*f
    values=np.array([first,second]);finite_outputs(values)
    return values


def exterior_radii(value):
    raw=np.asarray(value)
    if raw.dtype.kind not in 'fiu':raise ValueError('Real exterior radii required')
    s=np.array(raw,dtype=float,copy=True)
    if np.any(~np.isfinite(s)) or np.any(s<1):raise ValueError('Exterior s>=1 required')
    return s


def exterior_basis(radius_fraction,c):
    """Positive decaying vacuum solution D, Dprime, Dsecond via stable series.

    Scaled truncation bounds do not include float64 summation roundoff.
    """
    s=exterior_radii(radius_fraction);c=harmonic_compactness(c)
    inv=1/s;q=2*c*inv;power=np.ones_like(s)
    total=np.zeros_like(s);first=np.zeros_like(s);second=np.zeros_like(s)
    for j in range(SERIES_TERMS):
        coefficient=6*(j+1)/((j+2)*(j+3));term=coefficient*power
        total+=term;first-=(j+2)*term;second+=(j+2)*(j+3)*term
        power*=q
    values=(total*inv**2,first*inv**3,second*inv**4);finite_outputs(*values)
    return values


def basis_tail_bounds(radius_fraction,c):
    """Absolute analytic omitted-tail bounds for D/Dprime/Dsecond, no roundoff."""
    s=exterior_radii(radius_fraction);c=harmonic_compactness(c);inv=1/s;q=2*c*inv
    tail=q**SERIES_TERMS
    values=(tail/(1-q)*inv**2,6*tail/(1-q)*inv**3,
            6*tail*((SERIES_TERMS+1)/(1-q)+q/(1-q)**2)*inv**4)
    finite_outputs(*values)
    return values


from dataclasses import dataclass


@dataclass(frozen=True)
class MatchedChart:
    compactness: float
    scale: float
    residual_gauge: float
    matching_condition: float

    def __post_init__(self):
        c=harmonic_compactness(self.compactness)
        a=scalar(self.scale,'positive chart scale',positive=True)
        b=scalar(self.residual_gauge,'residual gauge')
        condition=scalar(self.matching_condition,'matching condition',positive=True)
        if condition>=1e8:raise ValueError('Ill-conditioned chart matching')
        for name,value in [('compactness',c),('scale',a),('residual_gauge',b),('matching_condition',condition)]:
            object.__setattr__(self,name,value)


def match(surface_state,c):
    """Selected smooth-chart value/derivative matching; not a Darmois law."""
    c=harmonic_compactness(c);f,first=array(surface_state,(2,),'surface F/Fprime')
    if f<=0:raise ValueError('Positive regular raw surface F required')
    d,dp,_=exterior_basis(1.,c)
    matrix=np.array([[f,-d],[f+first,-dp]])
    condition=float(np.linalg.cond(matrix))
    if not np.isfinite(condition) or condition>=1e8:raise ValueError('Ill-conditioned chart matching')
    scale,gauge=np.linalg.solve(matrix,np.array([1-c,1.]))
    finite_outputs(scale,gauge)
    if scale<=0 or scale*(f+first)<=0:raise ValueError('Positive chart and radial Jacobian required')
    return MatchedChart(c,float(scale),float(gauge),condition)


def interior_geometry(fractional_radius,raw_states,chart):
    """H/Hprime, metric eigenvalues and Cartesian current-density weight.

    Raw states must come from a separately verified regular solution. All
    origin values are analytic limits, without H/s or a clipped radius.
    """
    if not isinstance(chart,MatchedChart):raise ValueError('Explicit matched harmonic chart required')
    s=radius_grid(fractional_radius);states=array(raw_states,s.shape+(2,),'radius-shaped F/Fprime')
    f=states[...,0];first=states[...,1]
    if np.any(f<=0) or np.any((s==0)&(first!=0)):raise ValueError('Positive regular raw F profile required')
    tangent=chart.scale*f;radial=chart.scale*(f+s*first)
    if np.any(radial<=0):raise ValueError('Positive radial Jacobian required')
    bg=background(s,chart.compactness);u=np.sqrt(bg['radial_inverse_metric'])
    determinant=radial*tangent*tangent
    values=dict(harmonic_radius_fraction=s*tangent,radius_derivative=radial,
        tangent_jacobian=tangent,cartesian_jacobian_determinant=determinant,
        metric_radial=1/(u*u*radial*radial),metric_tangent=1/(tangent*tangent),
        current_volume_weight=1/(u*determinant),lapse=bg['lapse'])
    finite_outputs(*values.values())
    return values


def exterior_geometry(radius_fraction,chart):
    if not isinstance(chart,MatchedChart):raise ValueError('Explicit matched harmonic chart required')
    s=exterior_radii(radius_fraction);d,dp,dpp=exterior_basis(s,chart.compactness)
    h=s-chart.compactness+chart.residual_gauge*d
    first=1+chart.residual_gauge*dp;second=chart.residual_gauge*dpp
    if np.any(h<=0) or np.any(first<=0):raise ValueError('Positive exterior chart and Jacobian required')
    tangent=h/s;u=np.sqrt(1-2*chart.compactness/s);determinant=first*tangent*tangent
    values=dict(harmonic_radius_fraction=h,radius_derivative=first,radius_second_derivative=second,
        tangent_jacobian=tangent,cartesian_jacobian_determinant=determinant,
        metric_radial=1/(u*u*first*first),metric_tangent=1/(tangent*tangent),
        current_volume_weight=1/(u*determinant),lapse=u)
    finite_outputs(*values.values())
    return values
