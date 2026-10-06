"""Пакетный PyO3-модуль; JSON-мост сохранён для независимого сравнения."""
import json
from pathlib import Path
import subprocess

from .simulation import Body
from .vector3 import Vector3


def evolve(bodies: list[Body], dt: float, steps: int, executable: Path | None = None) -> list[Body]:
    if type(steps) is not int or steps < 0:
        raise ValueError("steps должен быть неотрицательным целым числом")
    if executable is None:
        try:
            import solar_native
        except ModuleNotFoundError as error:
            raise RuntimeError("Build the native module: python scripts/build_native.py") from error
        positions, velocities = solar_native.evolve(
            [b.mass for b in bodies],
            [[b.position.x, b.position.y, b.position.z] for b in bodies],
            [[b.velocity.x, b.velocity.y, b.velocity.z] for b in bodies], dt, steps)
        return [Body(b.name, b.mass, Vector3(*position), Vector3(*velocity), b.radius,b.spin)
                for b, position, velocity in zip(bodies, positions, velocities)]
    payload = {"bodies": [{"name": b.name, "mass": b.mass,
                           "position": [b.position.x, b.position.y, b.position.z],
                           "velocity": [b.velocity.x, b.velocity.y, b.velocity.z],
                           "spin": [b.spin.x,b.spin.y,b.spin.z]}
                          for b in bodies], "dt": dt, "steps": steps}
    result = subprocess.run([str(executable.resolve())],
                            input=json.dumps(payload, allow_nan=False), text=True,
                            encoding="utf-8", capture_output=True, check=False)
    if result.returncode:
        raise ValueError(result.stderr.strip())
    output = json.loads(result.stdout)
    return [Body(b["name"], b["mass"], Vector3(*b["position"]), Vector3(*b["velocity"]), original.radius,original.spin)
            for b, original in zip(output["bodies"], bodies)]


def run_until_contact(bodies: list[Body], dt: float, steps: int):
    """Одна пакетная остановка при контакте, весь цикл и детектор в Rust."""
    from .contacts import Contact, RunResult
    if type(steps) is not int or steps < 0:
        raise ValueError("steps должен быть неотрицательным целым числом")
    try:
        import solar_native
    except ModuleNotFoundError as error:
        raise RuntimeError("Build the native module: python scripts/build_native.py") from error
    positions, velocities, time, event = solar_native.run_until_contact(
        [b.mass for b in bodies],
        [[b.position.x,b.position.y,b.position.z] for b in bodies],
        [[b.velocity.x,b.velocity.y,b.velocity.z] for b in bodies],
        [b.radius for b in bodies],dt,steps)
    state=[Body(b.name,b.mass,Vector3(*p),Vector3(*v),b.radius,b.spin)
           for b,p,v in zip(bodies,positions,velocities)]
    return RunResult(state,time,None if event is None else Contact(*event))


def resolve_contact(bodies: list[Body], first: int, second: int, restitution: float):
    """Нативный центральный импульс. Публичная проверка пары — в impacts.py."""
    from .impacts import ImpactResult
    try:
        import solar_native
    except ModuleNotFoundError as error:
        raise RuntimeError("Build the native module: python scripts/build_native.py") from error
    velocities,energy,impulse=solar_native.resolve_contact(
        [b.mass for b in bodies],
        [[b.position.x,b.position.y,b.position.z] for b in bodies],
        [[b.velocity.x,b.velocity.y,b.velocity.z] for b in bodies],
        [b.radius for b in bodies],first,second,restitution)
    return ImpactResult([Body(b.name,b.mass,b.position,Vector3(*v),b.radius,b.spin)
                         for b,v in zip(bodies,velocities)],energy,impulse)


def simulate_collisions(bodies, dt, steps, restitution, max_events):
    """Вся серия повторных ударов одним вызовом без Python внутри цикла."""
    from .contacts import Contact
    from .collisions import CollisionResult
    try:
        import solar_native
    except ModuleNotFoundError as error:
        raise RuntimeError("Build the native module: python scripts/build_native.py") from error
    try:
        positions,velocities,time,events,loss = solar_native.simulate_collisions(
            [b.mass for b in bodies],[[b.position.x,b.position.y,b.position.z] for b in bodies],
            [[b.velocity.x,b.velocity.y,b.velocity.z] for b in bodies],[b.radius for b in bodies],
            dt,steps,restitution,max_events)
    except ValueError as error:
        message = str(error)
        if "Impact limit" in message:
            raise RuntimeError("Достигнут лимит ударов; возможен неупругий коллапс") from error
        if "floating point resolution" in message:
            raise RuntimeError("Время удара меньше разрешения float") from error
        translations = {"Deep sphere overlap":"Глубокое перекрытие сфер",
                        "Resting contact":"Покоящийся контакт требует модели контактных сил",
                        "Simultaneous contacts":"Одновременный контакт нескольких пар пока не поддерживается"}
        for source,target in translations.items():
            if source in message:
                raise ValueError(target) from error
        raise
    state = [Body(b.name,b.mass,Vector3(*p),Vector3(*v),b.radius,b.spin)
             for b,p,v in zip(bodies,positions,velocities)]
    return CollisionResult(state,time,[Contact(*e) for e in events],loss)
