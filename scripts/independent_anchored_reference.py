"""RK45 reference with constant per-body position origins, preserving pair rho.

Only internal numerical coordinates change. Every force receives reconstructed
SSB positions, original masses, velocities and the independently stored lunar
relative vector. No future reference vectors or production force are used.
"""
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp
from solar_simulator.relativity import C
from solar_simulator.simulation import AU,G
from scripts.assess_relativity import YEAR
from scripts.assess_resolved_moon import states,errors
from scripts.assess_relative_coordinates import relative_states


def independent_reference(initial,figures,times,*,levels,cache_name,acceleration_function,figure_acceleration_function):
    """Integrate displacement from a fixed origin for each non-relative row."""
    times=np.asarray(times,dtype=float)
    names=[b.name for b in initial]
    if (times.ndim!=1 or len(times)<2 or times[0]!=0 or not np.all(np.isfinite(times))
            or np.any(np.diff(times)<=0) or len(levels)<2 or len(set(names))!=len(names)):
        raise ValueError('Finite increasing reference grid and two levels required')
    e,m=names.index('Earth'),names.index('Moon')
    fraction=initial[m].mass/(initial[e].mass+initial[m].mass)
    q=states(initial);delta=q[m]-q[e]
    q[e]+=fraction*delta;q[m]=delta
    q[:,:3]/=AU;q[:,3:]*=YEAR/AU
    # The small Moon row already has a physical nearby origin: keep rho directly.
    origins=q[:,:3].copy();origins[m]=0.
    q[:,:3]-=origins
    mu=np.array([G*b.mass*YEAR**2/AU**3 for b in initial])
    def rhs(t,y):
        state=y.reshape(len(initial),6)
        internal=state.copy();internal[:,:3]+=origins
        absolute=internal.copy()
        absolute[e]=internal[e]-fraction*internal[m]
        absolute[m]=internal[e]+(1-fraction)*internal[m]
        pair=e,m,internal[m,:3]
        a=acceleration_function(absolute[:,:3],absolute[:,3:],mu,C*YEAR/AU,pair)
        a+=figure_acceleration_function(absolute[:,:3],mu,figures,names,t*YEAR,pair)
        relative=a[m]-a[e]
        a[e]=(1-fraction)*a[e]+fraction*a[m];a[m]=relative
        return np.concatenate((state[:,3:],a),axis=1).ravel()
    results=[]
    for tolerance,maximum_step in levels:
        if not np.isfinite(tolerance) or tolerance<=0 or not np.isfinite(maximum_step) or maximum_step<=0:
            raise ValueError('Positive finite reference tolerances/steps required')
        solution=solve_ivp(rhs,(0,times[-1]/YEAR),q.ravel(),method='RK45',t_eval=times/YEAR,
            rtol=tolerance,atol=1e-17,max_step=maximum_step/YEAR)
        if not solution.success or solution.t[-1]!=times[-1]/YEAR:
            raise RuntimeError(solution.message)
        internal=solution.y.T.reshape(len(times),len(initial),6).copy()
        internal[:,:,:3]+=origins
        value=internal.copy()
        value[:,e]=internal[:,e]-fraction*internal[:,m]
        value[:,m]=internal[:,e]+(1-fraction)*internal[:,m]
        value[:,:,:3]*=AU;value[:,:,3:]*=AU/YEAR
        results.append(value)
        Path('.tools').mkdir(exist_ok=True)
        np.savez_compressed(Path('.tools')/(cache_name+'.npz'),times=times,
            **{f'level_{i}':result for i,result in enumerate(results)})
        print('Independent anchored RK45',tolerance,'max step',maximum_step,'finished',flush=True)
    convergence=dict(all_bodies=errors(results[-2],results[-1]),
        moon_relative_to_earth=errors(relative_states(results[-2],initial),relative_states(results[-1],initial)))
    return results[-1],convergence
