"""Версионные контрольные точки SI, строгая загрузка и атомарная запись."""
from dataclasses import asdict
from copy import deepcopy
import json
from math import isfinite
import os
from pathlib import Path
import tempfile

from .experiment import Event, Experiment, Settings
from .simulation import Body, total_energy
from .vector3 import Vector3

SCHEMA_VERSION = 2
MAX_BYTES = 10_000_000


def _body(b):
    return dict(name=b.name,mass=b.mass,radius=b.radius,
                position=[b.position.x,b.position.y,b.position.z],
                velocity=[b.velocity.x,b.velocity.y,b.velocity.z],spin=[b.spin.x,b.spin.y,b.spin.z])


def to_document(experiment: Experiment) -> dict:
    document = dict(schema_version=SCHEMA_VERSION,units="SI",model="newtonian-verlet",
        settings=asdict(experiment.settings),initial=[_body(b) for b in experiment.initial],
        bodies=[_body(b) for b in experiment.bodies],time=experiment.time,
        dissipated_energy=experiment.dissipated_energy,halted=experiment.halted,
        model_energy_offset=experiment.model_energy_offset,
        events=[asdict(e) for e in experiment.events])
    from_document(document)  # Одинаковые гарантии при записи и чтении.
    return document


def _keys(value, keys):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError("Неверные поля контрольной точки")


def _number(value, *, nonnegative=False):
    if type(value) not in (float,int) or not isfinite(value) or (nonnegative and value<0):
        raise ValueError("Неверное конечное число в контрольной точке")
    return value


def _bodies(values):
    if type(values) is not list or not 1 <= len(values) <= 1000:
        raise ValueError("В контрольной точке нужно от 1 до 1000 тел")
    bodies = []
    for b in values:
        _keys(b,("name","mass","radius","position","velocity","spin"))
        if type(b["name"]) is not str or not b["name"].strip():
            raise ValueError("Неверное имя тела")
        for field in ("position","velocity","spin"):
            if type(b[field]) is not list or len(b[field]) != 3:
                raise ValueError("Нужен вектор из трёх чисел")
            for value in b[field]:
                _number(value)
        bodies.append(Body(b["name"],_number(b["mass"]),Vector3(*b["position"]),
                           Vector3(*b["velocity"]),_number(b["radius"],nonnegative=True),Vector3(*b["spin"])))
    if len({b.name for b in bodies}) != len(bodies):
        raise ValueError("Имена тел должны быть уникальными")
    if not isfinite(total_energy(bodies)):
        raise ValueError("Энергия должна быть конечной")
    return bodies


def from_document(document: dict) -> Experiment:
    if type(document) is dict and type(document.get("schema_version")) is int and document["schema_version"]==1:
        _keys(document,("schema_version","units","model","settings","initial","bodies",
                        "time","dissipated_energy","halted","events"))
        document=deepcopy(document)
        document["schema_version"]=SCHEMA_VERSION
        document["model_energy_offset"]=0.0
        for field in ("initial","bodies"):
            if type(document[field]) is not list:
                raise ValueError("Неверный список тел")
            for body in document[field]:
                _keys(body,("name","mass","radius","position","velocity"))
                body["spin"]=[0,0,0]
        if type(document["events"]) is not list:
            raise ValueError("Неверный журнал событий")
        for event in document["events"]:
            _keys(event,("first","second","time"))
            event.update(outcome="contact",result=None)
    _keys(document,("schema_version","units","model","settings","initial","bodies",
                    "time","dissipated_energy","halted","events","model_energy_offset"))
    if (type(document["schema_version"]) is not int or document["schema_version"]!=SCHEMA_VERSION
            or document["units"]!="SI" or document["model"]!="newtonian-verlet"):
        raise ValueError("Неподдерживаемая версия, единицы или физическая модель")
    _keys(document["settings"],("dt","backend","contact_mode","restitution"))
    settings = Settings(**document["settings"])
    initial,bodies = _bodies(document["initial"]),_bodies(document["bodies"])
    time = _number(document["time"],nonnegative=True)
    loss = _number(document["dissipated_energy"],nonnegative=True)
    offset = _number(document["model_energy_offset"])
    if type(document["halted"]) is not bool or type(document["events"]) is not list or len(document["events"])>100000:
        raise ValueError("Неверные состояние остановки или журнал событий")
    active = {b.name:(b.mass,b.radius) for b in initial}
    events = []
    previous = 0.0
    for e in document["events"]:
        _keys(e,("first","second","time","outcome","result"))
        event_time = _number(e["time"],nonnegative=True)
        if (type(e["first"]) is not str or type(e["second"]) is not str
                or e["first"] not in active or e["second"] not in active or e["first"]==e["second"]
                or not previous <= event_time <= time):
            raise ValueError("Неверное событие контакта")
        previous = event_time
        if e["outcome"]=="merge":
            name=e["result"]
            if type(name) is not str or not name.strip() or name in active:
                raise ValueError("Неверное имя результата слияния")
            m1,r1=active.pop(e["first"])
            m2,r2=active.pop(e["second"])
            scale=max(r1,r2)
            if scale<=0:
                raise ValueError("Для слияния нужны радиусы")
            active[name]=(m1+m2,scale*((r1/scale)**3+(r2/scale)**3)**(1/3))
        elif e["outcome"]!="contact" or e["result"] is not None:
            raise ValueError("Неверный тип события")
        events.append(Event(**e))
    if set(active)!={b.name for b in bodies} or any(active[b.name]!=(b.mass,b.radius) for b in bodies):
        raise ValueError("Состав тел не соответствует истории слияний")
    if document["halted"] and (not events or settings.contact_mode!="stop"
                               or events[-1].time!=time or events[-1].outcome!="contact"):
        raise ValueError("Остановка должна соответствовать последнему контакту")
    return Experiment(initial,bodies,settings,time,loss,tuple(events),document["halted"],offset)


def save(experiment: Experiment, path: str | Path):
    path = Path(path)
    data = json.dumps(to_document(experiment),ensure_ascii=False,allow_nan=False,indent=2).encode("utf-8")
    if len(data)>MAX_BYTES:
        raise ValueError("Контрольная точка слишком велика")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent,prefix=".solar-",suffix=".tmp",delete=False) as file:
            temporary = Path(file.name)
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary,path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _unique_pairs(pairs):
    result = {}
    for key,value in pairs:
        if key in result:
            raise ValueError("Повторяющееся поле JSON")
        result[key] = value
    return result


def load(path: str | Path) -> Experiment:
    with Path(path).open("rb") as file:
        data = file.read(MAX_BYTES+1)
    if len(data)>MAX_BYTES:
        raise ValueError("Контрольная точка слишком велика")
    def reject_constant(value):
        raise ValueError("NaN/Infinity в JSON запрещены")
    try:
        document = json.loads(data,object_pairs_hook=_unique_pairs,parse_constant=reject_constant)
        return from_document(document)
    except (TypeError,OverflowError,UnicodeDecodeError) as error:
        raise ValueError("Неверный формат контрольной точки") from error
