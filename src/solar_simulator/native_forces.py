"""Working Rust force adapter; SciPy integration and figures stay in Python."""
import numpy as np


def prepare(masses):
    try:
        import solar_native
    except ModuleNotFoundError as error:
        raise RuntimeError('Соберите Rust-модуль: python scripts/build_native.py') from error
    function = getattr(solar_native, 'point_acceleration', None)
    if function is None:
        raise RuntimeError('Обновите Rust-модуль: python scripts/build_native.py')
    values = np.asarray(masses, dtype=float)
    if values.ndim != 1 or not values.size or not np.all(np.isfinite(values)) or np.any(values <= 0):
        raise ValueError('Нужны конечные положительные массы')
    owned_masses = values.tolist()
    def acceleration(positions, velocities, light_speed=None, relative_pair=None):
        if light_speed is not None and type(light_speed) not in (int, float):
            raise ValueError('Неверная скорость света')
        p, v = np.asarray(positions, dtype=float), np.asarray(velocities, dtype=float)
        if p.shape != (len(owned_masses), 3) or v.shape != p.shape:
            raise ValueError('Неверные формы координат/скоростей')
        pair = None
        if relative_pair is not None:
            first, second, rho = relative_pair
            if (type(first) is not int or type(second) is not int
                    or not 0 <= first < len(owned_masses) or not 0 <= second < len(owned_masses) or first == second):
                raise ValueError('Индексы пары должны быть целыми')
            rho = np.asarray(rho, dtype=float)
            if rho.shape != (3,): raise ValueError('Неверная форма относительного вектора')
            pair = (first, second, rho.tolist())
        return np.array(function(owned_masses, p.tolist(), v.tolist(), light_speed, pair), dtype=float)
    return acceleration
