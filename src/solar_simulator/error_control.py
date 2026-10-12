"""DOP853 acceptance from the worst position/velocity block, independent of N.

The state layout is [all positions, all velocities, optional scaled work].
Each three-vector has its own dimensionless 5(3) estimate. Relative coordinates
retain separate barycentre and internal-orbit blocks. This bounds local
estimates only; convergence and independent global checks remain necessary.
"""
import numpy as np
from scipy.integrate import DOP853


ERROR_CONTROLS = ("global-rms", "per-body")


def validate_error_control(value):
    if type(value) is not str or value not in ERROR_CONTROLS:
        raise ValueError("Контроль ошибки: global-rms или per-body")


class PerBodyDOP853(DOP853):
    """Keep SciPy stages/dense output; replace its scalar acceptance norm.

    `_estimate_error_norm` is a SciPy implementation hook. Analytic tests cover
    its integration behavior and independence from added inactive equations.
    """

    def __init__(self, fun, t0, y0, t_bound, **kwargs):
        size = np.size(y0)
        if size < 6 or size % 6 not in (0, 1):
            raise ValueError("Нужны 6N координат и скоростей и необязательная работа")
        self.orbit_size = size - size % 6
        super().__init__(fun, t0, y0, t_bound, **kwargs)

    def _estimate_error_norm(self, K, h, scale):
        e5 = (K.T @ self.E5) / scale
        e3 = (K.T @ self.E3) / scale
        if not np.all(np.isfinite(e5)) or not np.all(np.isfinite(e3)):
            raise ValueError("Неконечная оценка локальной ошибки DOP853")
        # Three-vector norm is unchanged by rotation of the scaled components.
        # Stable hypot avoids squaring huge/tiny estimates before division.
        a = np.hypot.reduce(e5[:self.orbit_size].reshape(-1, 3), axis=1)
        b = np.hypot.reduce(e3[:self.orbit_size].reshape(-1, 3), axis=1)
        denominator = np.hypot(a, .1*b)
        ratio = np.divide(a, denominator, out=np.zeros_like(a), where=denominator != 0)
        worst = float(np.max((abs(h) * a) * ratio / np.sqrt(3.)))
        if len(scale) != self.orbit_size:
            a, b = abs(e5[-1]), abs(e3[-1])
            denominator = np.hypot(a, .1*b)
            work = (abs(h) * a) * (a/denominator) if denominator else 0.
            worst = max(worst, float(work))
        if not np.isfinite(worst):
            raise ValueError("Неконечная оценка локальной ошибки DOP853")
        return worst
