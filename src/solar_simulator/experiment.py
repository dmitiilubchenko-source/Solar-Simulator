"""Состояние воспроизводимого эксперимента, независимо от CLI и интерфейса."""
from dataclasses import dataclass, replace
from math import isfinite

from .collisions import simulate_collisions
from .contacts import run_until_contact
from .simulation import Body, G, step, sun_earth, total_energy
from .scenarios import binary_star, earth_moon, sun_earth_moon
from .vector3 import Vector3
from .ephemerides import EphemerisOrigin
from .oblateness import FixedJ2, PrescribedQuadrupole, validate_figures, validate_orientation_origin


@dataclass(frozen=True)
class Settings:
    dt: float
    backend: str = "python"
    contact_mode: str = "stop"
    restitution: float = 1.0
    integrator: str = "verlet"
    rtol: float = 1e-13
    position_atol: float = 1e-3
    velocity_atol: float = 1e-9
    physics: str = "newtonian"
    figures: tuple[FixedJ2 | PrescribedQuadrupole, ...] = ()

    def __post_init__(self):
        if (type(self.figures) is not tuple or any(not isinstance(f, (FixedJ2, PrescribedQuadrupole)) for f in self.figures)
                or len({f.body for f in self.figures}) != len(self.figures)):
            raise ValueError("Неверные параметры фигур J2")
        if self.figures and (self.integrator != "dop853" or self.backend != "python"):
            raise ValueError("J2 требует Python/DOP853")
        if self.physics not in ("newtonian", "eih-1pn"):
            raise ValueError("Физика: newtonian или eih-1pn")
        if self.physics == "eih-1pn" and (self.integrator != "dop853" or self.backend != "python"):
            raise ValueError("1PN требует Python/DOP853")
        if self.integrator not in ("verlet", "dop853"):
            raise ValueError("Интегратор: verlet или dop853")
        for value in (self.rtol, self.position_atol, self.velocity_atol):
            if type(value) not in (int, float) or not isfinite(value) or value <= 0:
                raise ValueError("Допуски должны быть положительными конечными числами")
        if not 3e-14 <= self.rtol <= 1e-2:
            raise ValueError("rtol должен быть от 3e-14 до 1e-2")
        if self.integrator == "dop853" and self.backend != "python":
            raise ValueError("DOP853 использует Python/SciPy; выберите ядро python")
        if type(self.dt) not in (int,float) or not isfinite(self.dt) or self.dt <= 0:
            raise ValueError("dt должен быть положительным конечным числом")
        if self.backend not in ("python","rust"):
            raise ValueError("Неизвестное ядро")
        if self.contact_mode not in ("stop","bounce","merge"):
            raise ValueError("Режим контакта: stop, bounce или merge")
        if type(self.restitution) not in (int,float) or not isfinite(self.restitution) or not 0 <= self.restitution <= 1:
            raise ValueError("Упругость должна быть в диапазоне [0,1]")


@dataclass(frozen=True)
class Event:
    first: str
    second: str
    time: float
    outcome: str = "contact"
    result: str | None = None


@dataclass(frozen=True)
class Experiment:
    initial: list[Body]
    bodies: list[Body]
    settings: Settings
    time: float = 0.0
    dissipated_energy: float = 0.0
    events: tuple[Event,...] = ()
    halted: bool = False
    model_energy_offset: float = 0.0
    origin: EphemerisOrigin | None = None
    orientation_work: float = 0.0


def copy_bodies(bodies):
    return [Body(b.name,b.mass,Vector3(b.position.x,b.position.y,b.position.z),
                 Vector3(b.velocity.x,b.velocity.y,b.velocity.z),b.radius,
                 Vector3(b.spin.x,b.spin.y,b.spin.z)) for b in bodies]


def create_experiment(bodies: list[Body], settings: Settings, *, origin: EphemerisOrigin | None = None) -> Experiment:
    if not bodies or len({b.name for b in bodies}) != len(bodies):
        raise ValueError("Нужны тела с уникальными именами")
    if settings.integrator == "dop853" and any(b.radius > 0 for b in bodies):
        raise ValueError("DOP853 поддерживает только точечные тела без контактов")
    if settings.physics == "eih-1pn":
        from .relativity import validate_bodies
        validate_bodies(bodies)
    validate_figures(bodies, settings.figures)
    validate_orientation_origin(settings.figures, origin)
    if not isfinite(total_energy(bodies)):
        raise ValueError("Энергия исходной системы должна быть конечной")
    if origin is not None and not isinstance(origin, EphemerisOrigin):
        raise ValueError("Неверное происхождение начального состояния")
    return Experiment(copy_bodies(bodies),copy_bodies(bodies),settings,origin=origin)


def reset(experiment: Experiment) -> Experiment:
    return create_experiment(experiment.initial,experiment.settings,origin=experiment.origin)


def advance(experiment: Experiment, steps: int) -> Experiment:
    if type(steps) is not int or steps < 0:
        raise ValueError("steps должен быть неотрицательным целым")
    if experiment.halted or steps == 0:
        return experiment
    settings = experiment.settings
    duration = settings.dt*steps
    if not isfinite(duration) or not isfinite(experiment.time+duration):
        raise ValueError("Переполнение времени")
    if experiment.time+duration == experiment.time:
        raise ValueError("Шаг меньше разрешения времени float")
    has_radii = any(b.radius>0 for b in experiment.bodies)
    if settings.integrator == "dop853":
        from .accuracy import evolve_accurate
        bodies, work = evolve_accurate(experiment.bodies, duration, rtol=settings.rtol,
                                position_atol=settings.position_atol, velocity_atol=settings.velocity_atol,
                                physics=settings.physics, figures=settings.figures,
                                start_time=experiment.time, return_work=True)
        work += experiment.orientation_work
        if not isfinite(work):
            raise ValueError("Переполнение работы заданной ориентации")
        return replace(experiment, bodies=bodies, time=experiment.time+duration, orientation_work=work)
    if has_radii and settings.contact_mode == "merge":
        return _advance_mergers(experiment,steps)
    events = []
    loss = 0.0
    halted = False
    if has_radii and settings.contact_mode == "bounce":
        result = simulate_collisions(experiment.bodies,settings.dt,steps,
                                     backend=settings.backend,restitution=settings.restitution)
        bodies,duration,events,loss = result.bodies,result.time,result.events,result.dissipated_energy
    elif has_radii:
        result = run_until_contact(experiment.bodies,settings.dt,steps,backend=settings.backend)
        bodies,duration = result.bodies,result.time
        if result.contact is not None:
            events = [result.contact]
            halted = True
    elif settings.backend == "rust":
        from .rust_backend import evolve
        bodies = evolve(experiment.bodies,settings.dt,steps)
    else:
        bodies = list(experiment.bodies)
        for _ in range(steps):
            bodies = step(bodies,settings.dt)
    history = experiment.events+tuple(Event(experiment.bodies[e.first].name,
        experiment.bodies[e.second].name,experiment.time+e.time) for e in events)
    dissipated = experiment.dissipated_energy+loss
    if not isfinite(dissipated):
        raise ValueError("Переполнение суммы потерь энергии")
    return replace(experiment,bodies=bodies,time=experiment.time+duration,
                   dissipated_energy=dissipated,events=history,halted=halted)


def _advance_mergers(experiment,steps):
    from .mergers import merge_contact
    bodies=list(experiment.bodies)
    settings=experiment.settings
    history=list(experiment.events)
    offset=experiment.model_energy_offset
    for index in range(steps):
        consumed=0.0
        while consumed<settings.dt:
            remaining=settings.dt-consumed
            result=run_until_contact(bodies,remaining,1,backend=settings.backend)
            bodies=result.bodies
            consumed+=result.time
            if result.contact is None:
                break
            e=result.contact
            touching=0
            for i,a in enumerate(bodies):
                for b in bodies[i+1:]:
                    if a.radius+b.radius>0 and a.position.distance_to(b.position)<=(a.radius+b.radius)*(1+1e-7):
                        touching+=1
            if touching!=1:
                raise ValueError("Одновременное слияние нескольких пар не поддерживается")
            first,second=bodies[e.first].name,bodies[e.second].name
            merger=merge_contact(bodies,e.first,e.second)
            bodies=merger.bodies
            offset+=merger.energy_offset
            if not isfinite(offset):
                raise ValueError("Переполнение энергетического скачка модели")
            history.append(Event(first,second,experiment.time+index*settings.dt+consumed,"merge",merger.merged_name))
            # Число тел уменьшается на один: даже события t=0 завершаются.
            # Нельзя автоматически сливать перекрытия, возникшие после замены.
            for i,a in enumerate(bodies):
                for b in bodies[i+1:]:
                    if a.radius+b.radius>0 and a.position.distance_to(b.position)<(a.radius+b.radius)*(1-1e-7):
                        raise ValueError("Слияние создало перекрытие; нужна модель множественного контакта")
    return replace(experiment,bodies=bodies,time=experiment.time+settings.dt*steps,
                   events=tuple(history),model_energy_offset=offset)


PRESETS = ("sun-earth","earth-moon","binary-star","sun-earth-moon","spheres","solar-system","solar-system-moon")


def preset(name: str, *, backend: str = "python", eccentricity: float = 0.0) -> Experiment:
    if name in ("solar-system", "solar-system-moon"):
        from .ephemerides import solar_system
        bodies,origin=solar_system(resolved_moon=name=="solar-system-moon")
        return create_experiment(bodies,Settings(3600,backend,integrator="dop853" if backend=="python" else "verlet"),origin=origin)
    if name == "sun-earth":
        bodies,period = sun_earth(eccentricity)
    elif name == "earth-moon":
        bodies,period = earth_moon()
    elif name == "binary-star":
        bodies,period = binary_star()
    elif name == "sun-earth-moon":
        bodies,period = sun_earth_moon()
    elif name == "spheres":
        bodies = [Body("A",1/G,Vector3(-5,0,0),Vector3(0,0,0),1),
                  Body("B",1/G,Vector3(5,0,0),Vector3(0,0,0),1)]
        return create_experiment(bodies,Settings(.05,backend,"bounce"))
    else:
        raise ValueError("Неизвестный сценарий")
    return create_experiment(bodies,Settings(period/4000,backend))
