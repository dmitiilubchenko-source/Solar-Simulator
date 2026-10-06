"""Мгновенный импульс между касающимися гладкими сферами, без трения."""
from dataclasses import dataclass
from math import isfinite

from .simulation import Body


@dataclass(frozen=True)
class ImpactResult:
    bodies: list[Body]
    dissipated_energy: float
    impulse: float


def resolve_contact(bodies: list[Body], first: int, second: int, restitution: float = 1.0,
                    *, backend: str = "python") -> ImpactResult:
    """Возвращает новые скорости при контакте; входное состояние не меняется.

    restitution=1: упругий удар; 0: равные нормальные скорости после удара.
    Слияния, трения, вращения и исправления глубокого перекрытия здесь нет.
    """
    if not isfinite(restitution) or not 0 <= restitution <= 1:
        raise ValueError("Коэффициент восстановления должен быть в диапазоне [0,1]")
    if (type(first) is not int or type(second) is not int or first == second
            or not 0 <= first < len(bodies) or not 0 <= second < len(bodies)):
        raise ValueError("Нужны индексы двух разных тел")
    if backend == "rust":
        from .rust_backend import resolve_contact as native_resolve
        return native_resolve(bodies,first,second,restitution)
    if backend != "python":
        raise ValueError("Неизвестное ядро")
    a,b = bodies[first],bodies[second]
    delta = b.position.subtract(a.position)
    distance = delta.magnitude()
    radius = a.radius+b.radius
    if not isfinite(radius) or radius <= 0 or distance == 0:
        raise ValueError("Нужны касающиеся сферы с определённой нормалью")
    if abs(distance-radius) > 1e-7*max(distance,radius):
        raise ValueError("Тела не касаются или глубоко перекрываются")
    normal = delta.divide(distance)
    speed = b.velocity.subtract(a.velocity).dot(normal)
    if speed >= 0:
        return ImpactResult(list(bodies),0.0,0.0)
    scale = max(a.mass,b.mass)
    fraction_a = a.mass/scale
    fraction_b = b.mass/scale
    total = fraction_a+fraction_b
    reduced_mass = min(a.mass,b.mass)/(1+min(a.mass,b.mass)/scale)
    change = -(1+restitution)*speed
    impulse = reduced_mass*change
    dissipated = 0.5*reduced_mass*(1-restitution**2)*speed*speed
    if not isfinite(impulse) or not isfinite(dissipated):
        raise ValueError("Переполнение при расчёте удара")
    state = list(bodies)
    state[first] = Body(a.name,a.mass,a.position,
                        a.velocity.subtract(normal.multiply(change*fraction_b/total)),a.radius,a.spin)
    state[second] = Body(b.name,b.mass,b.position,
                         b.velocity.add(normal.multiply(change*fraction_a/total)),b.radius,b.spin)
    return ImpactResult(state,dissipated,impulse)
