"""Цикл последовательных ударов на Python или одним вызовом Rust."""
from dataclasses import dataclass
from math import isfinite

from .contacts import Contact, first_contact
from .impacts import resolve_contact
from .simulation import Body, step


@dataclass(frozen=True)
class CollisionResult:
    bodies: list[Body]
    time: float
    events: list[Contact]
    dissipated_energy: float


def simulate_collisions(bodies: list[Body], dt: float, steps: int, *,
                        restitution: float = 1.0, backend: str = "python",
                        max_events: int = 10000) -> CollisionResult:
    """Разбивает каждый шаг в моменты ударов, сохраняя остаток времени.

    Неподдерживаемые покоящиеся/одновременные контакты вызывают ошибку.
    Ограничение событий защищает от неупругого коллапса (накопления ударов).
    """
    if (not isfinite(dt) or dt <= 0 or type(steps) is not int or steps < 0
            or not isfinite(dt*steps)):
        raise ValueError("Нужны конечное время, положительный dt и целое steps >= 0")
    if not isfinite(restitution) or not 0 <= restitution <= 1:
        raise ValueError("Коэффициент восстановления должен быть в диапазоне [0,1]")
    if type(max_events) is not int or max_events <= 0:
        raise ValueError("max_events должен быть положительным целым")
    if backend not in ("python", "rust"):
        raise ValueError("Неизвестное ядро")
    if backend == "rust":
        from .rust_backend import simulate_collisions as native_run
        return native_run(bodies,dt,steps,restitution,max_events)
    advance = step
    state = list(bodies)
    events = []
    loss = 0.0
    for index in range(steps):
        consumed = 0.0
        while consumed < dt:
            remaining = dt-consumed
            event = first_contact(state, remaining, incoming_only=True)
            if event is None:
                state = advance(state, remaining)
                break
            if len(events) >= max_events:
                raise RuntimeError("Достигнут лимит ударов; возможен неупругий коллапс")
            if event.time > 0:
                if consumed+event.time == consumed:
                    raise RuntimeError("Время удара меньше разрешения float")
                state = advance(state, event.time)
                consumed += event.time
            # Любой другой касающийся партнёр требует решения совместных связей.
            touching = []
            for i, a in enumerate(state):
                for j in range(i+1, len(state)):
                    radius = a.radius+state[j].radius
                    if radius > 0 and a.position.distance_to(state[j].position) <= radius*(1+1e-7):
                        touching.append((i,j))
            if touching != [(event.first,event.second)]:
                raise ValueError("Одновременный контакт нескольких пар пока не поддерживается")
            impact = resolve_contact(state,event.first,event.second,restitution,backend=backend)
            if impact.impulse <= 0:
                raise RuntimeError("Детектор не дал сближающийся удар")
            state = impact.bodies
            loss += impact.dissipated_energy
            if not isfinite(loss):
                raise ValueError("Переполнение потерь энергии")
            events.append(Contact(event.first,event.second,index*dt+consumed))
    return CollisionResult(state,dt*steps,events,loss)
