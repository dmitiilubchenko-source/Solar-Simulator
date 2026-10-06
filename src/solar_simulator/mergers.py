"""Учебное слияние: масса, импульс, объём и полный угловой момент."""
from dataclasses import dataclass
from math import isfinite

from .simulation import Body, total_energy


@dataclass(frozen=True)
class MergerResult:
    bodies: list[Body]
    merged_name: str
    energy_offset: float
    relative_kinetic_energy: float


def merge_contact(bodies: list[Body], first: int, second: int) -> MergerResult:
    """energy_offset=E_before-E_after, включая изменение внешней гравитации.

    Spin хранит внутренний угловой момент, но вращательная энергия,
    собственная гравитационная энергия и тепло в этой модели не разрешены.
    energy_offset — подписанный скачок модели, а не вычисленная температура.
    """
    if (type(first) is not int or type(second) is not int or first==second
            or not 0<=first<len(bodies) or not 0<=second<len(bodies)):
        raise ValueError("Нужны индексы двух разных тел")
    a,b=bodies[first],bodies[second]
    delta=b.position.subtract(a.position)
    distance=delta.magnitude()
    radius=a.radius+b.radius
    if not isfinite(radius) or radius<=0 or distance==0 or abs(distance-radius)>1e-7*max(distance,radius):
        raise ValueError("Слияние требует касающиеся сферы с определённой нормалью")
    total=a.mass+b.mass
    if not isfinite(total):
        raise ValueError("Переполнение массы слияния")
    fa,fb=a.mass/total,b.mass/total
    position=a.position.multiply(fa).add(b.position.multiply(fb))
    velocity=a.velocity.multiply(fa).add(b.velocity.multiply(fb))
    relative=b.velocity.subtract(a.velocity)
    reduced=min(a.mass,b.mass)/(1+min(a.mass,b.mass)/max(a.mass,b.mass))
    spin=a.spin.add(b.spin).add(delta.cross(relative).multiply(reduced))
    scale=max(a.radius,b.radius)
    merged_radius=scale*((a.radius/scale)**3+(b.radius/scale)**3)**(1/3)
    name=f"{a.name}+{b.name}"
    existing={body.name for i,body in enumerate(bodies) if i not in (first,second)}
    while name in existing:
        name += "+"
    merged=Body(name,total,position,velocity,merged_radius,spin)
    state=[body for i,body in enumerate(bodies) if i not in (first,second)]
    state.insert(min(first,second),merged)
    relative_energy=.5*reduced*relative.dot(relative)
    offset=total_energy(bodies)-total_energy(state)
    if not isfinite(offset) or not isfinite(relative_energy):
        raise ValueError("Переполнение энергетического скачка слияния")
    return MergerResult(state,name,offset,relative_energy)
