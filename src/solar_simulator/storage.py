"""Версионные контрольные точки SI, строгая загрузка и атомарная запись."""
from dataclasses import asdict
from copy import deepcopy
import json
from math import isfinite
import os
from pathlib import Path
import tempfile

from .experiment import Event, Experiment, Settings, validate_start
from .simulation import Body, total_energy
from .vector3 import Vector3
from .ephemerides import EphemerisOrigin
from .oblateness import (FixedJ2, PrescribedQuadrupole, prescribed, validate_figures,
                         validate_orientation_origin)
from .coordinates import prepare_pair

SCHEMA_VERSION = 9
MAX_BYTES = 10_000_000


def _body(b):
    return dict(name=b.name,mass=b.mass,radius=b.radius,
                position=[b.position.x,b.position.y,b.position.z],
                velocity=[b.velocity.x,b.velocity.y,b.velocity.z],spin=[b.spin.x,b.spin.y,b.spin.z])


def to_document(experiment: Experiment) -> dict:
    document = dict(schema_version=SCHEMA_VERSION,units="SI",model=experiment.settings.physics+"-"+experiment.settings.integrator,
        settings=asdict(experiment.settings),initial=[_body(b) for b in experiment.initial],
        bodies=[_body(b) for b in experiment.bodies],time=experiment.time,
        dissipated_energy=experiment.dissipated_energy,halted=experiment.halted,
        model_energy_offset=experiment.model_energy_offset, orientation_work=experiment.orientation_work,
        events=[asdict(e) for e in experiment.events], origin=asdict(experiment.origin) if experiment.origin else None)
    document["settings"]["figures"] = [dict(asdict(f), axis=list(f.axis)) if isinstance(f, FixedJ2)
                                        else dict(asdict(f), kind="prescribed-q2") for f in experiment.settings.figures]
    document["settings"]["relative_pair"] = list(experiment.settings.relative_pair) if experiment.settings.relative_pair else None
    if experiment.settings.figures:
        document["model"] += "-prescribed-q2" if prescribed(experiment.settings.figures) else "-fixed-j2"
    if experiment.rotations or experiment.initial_rotations:
        from .nbody_rotation import validate_experiment
        validate_experiment(experiment)
        document["schema_version"] = 10
        document["model"] += "-dynamic-q2"
        document["initial_rotations"] = [_rotation_document(r) for r in experiment.initial_rotations]
        document["rotations"] = [_rotation_document(r) for r in experiment.rotations]
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
    if type(document) is dict and type(document.get("schema_version")) is int and document["schema_version"] == 10:
        _keys(document,("schema_version","units","model","settings","initial","bodies",
            "time","dissipated_energy","halted","events","model_energy_offset","origin","orientation_work",
            "initial_rotations","rotations"))
        if type(document["model"]) is not str or not document["model"].endswith("-dynamic-q2"):
            raise ValueError("Схема 10 требует динамическое Q2")
        initial_rotations, rotations = _rotations(document["initial_rotations"]), _rotations(document["rotations"])
        legacy = deepcopy(document)
        del legacy["initial_rotations"], legacy["rotations"]
        legacy["schema_version"] = 9
        legacy["model"] = legacy["model"][:-len("-dynamic-q2")]
        from dataclasses import replace
        result = replace(from_document(legacy), initial_rotations=initial_rotations, rotations=rotations)
        from .nbody_rotation import validate_experiment
        validate_experiment(result)
        return result
    if type(document) is dict and type(document.get("schema_version")) is int and document["schema_version"]==1:
        _keys(document,("schema_version","units","model","settings","initial","bodies",
                        "time","dissipated_energy","halted","events"))
        document=deepcopy(document)
        document["schema_version"]=2
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
    if type(document) is dict and type(document.get("schema_version")) is int and document["schema_version"] == 2:
        _keys(document,("schema_version","units","model","settings","initial","bodies",
                        "time","dissipated_energy","halted","events","model_energy_offset"))
        _keys(document["settings"], ("dt", "backend", "contact_mode", "restitution"))
        if document["model"] != "newtonian-verlet":
            raise ValueError("Неподдерживаемая физическая модель")
        document = deepcopy(document)
        document["schema_version"] = 3
        document["settings"].update(integrator="verlet", rtol=1e-13, position_atol=1e-3, velocity_atol=1e-9)
    if type(document) is dict and type(document.get("schema_version")) is int and document["schema_version"] == 3:
        _keys(document,("schema_version","units","model","settings","initial","bodies",
                        "time","dissipated_energy","halted","events","model_energy_offset"))
        document=deepcopy(document)
        document["schema_version"]=4
        document["origin"]=None
    if type(document) is dict and type(document.get("schema_version")) is int and document["schema_version"] == 4:
        _keys(document,("schema_version","units","model","settings","initial","bodies",
                        "time","dissipated_energy","halted","events","model_energy_offset","origin"))
        _keys(document["settings"],("dt","backend","contact_mode","restitution","integrator",
                                    "rtol","position_atol","velocity_atol"))
        if document["model"] != "newtonian-"+str(document["settings"]["integrator"]):
            raise ValueError("Неподдерживаемая физическая модель старой схемы")
        document=deepcopy(document)
        document["schema_version"]=5
        document["settings"]["physics"]="newtonian"
    if type(document) is dict and type(document.get("schema_version")) is int and document["schema_version"] == 5:
        _keys(document,("schema_version","units","model","settings","initial","bodies",
                        "time","dissipated_energy","halted","events","model_energy_offset","origin"))
        _keys(document["settings"],("dt","backend","contact_mode","restitution","integrator",
                                    "rtol","position_atol","velocity_atol","physics"))
        document=deepcopy(document)
        document["schema_version"]=6
        document["settings"]["figures"]=[]
    if type(document) is dict and type(document.get("schema_version")) is int and document["schema_version"] == 6:
        _keys(document,("schema_version","units","model","settings","initial","bodies",
                        "time","dissipated_energy","halted","events","model_energy_offset","origin"))
        if type(document["settings"]) is not dict or type(document["settings"].get("figures")) is not list:
            raise ValueError("Неверные параметры фигур старой схемы")
        for figure in document["settings"]["figures"]:
            _keys(figure,("body","coefficient","reference_radius","axis","provenance"))
        document=deepcopy(document)
        document["schema_version"]=7
        document["orientation_work"]=0.0
    if type(document) is dict and type(document.get("schema_version")) is int and document["schema_version"] == 7:
        _keys(document,("schema_version","units","model","settings","initial","bodies",
                        "time","dissipated_energy","halted","events","model_energy_offset","origin","orientation_work"))
        _keys(document["settings"],("dt","backend","contact_mode","restitution","integrator",
                                    "rtol","position_atol","velocity_atol","physics","figures"))
        document=deepcopy(document)
        document["schema_version"]=8
        document["settings"]["relative_pair"]=None
    if type(document) is dict and type(document.get("schema_version")) is int and document["schema_version"] == 8:
        _keys(document,("schema_version","units","model","settings","initial","bodies",
                        "time","dissipated_energy","halted","events","model_energy_offset","origin","orientation_work"))
        _keys(document["settings"],("dt","backend","contact_mode","restitution","integrator",
                                    "rtol","position_atol","velocity_atol","physics","figures","relative_pair"))
        document=deepcopy(document)
        document["schema_version"]=9
        document["settings"]["error_control"]="global-rms"
    _keys(document,("schema_version","units","model","settings","initial","bodies",
                    "time","dissipated_energy","halted","events","model_energy_offset","origin","orientation_work"))
    origin=None
    if document["origin"] is not None:
        _keys(document["origin"],("epoch_jd_tdb","frame","center","ephemeris","dataset_sha256","gm_sha256"))
        origin=EphemerisOrigin(**document["origin"])
    if (type(document["schema_version"]) is not int or document["schema_version"]!=SCHEMA_VERSION
            or document["units"]!="SI"):
        raise ValueError("Неподдерживаемая версия, единицы или физическая модель")
    _keys(document["settings"],("dt","backend","contact_mode","restitution","integrator","rtol","position_atol","velocity_atol","physics","figures","relative_pair","error_control"))
    values=document["settings"]["figures"]
    if type(values) is not list or len(values)>1000:
        raise ValueError("Неверный список фигур J2")
    figures=[]
    for value in values:
        if type(value) is dict and value.get("kind") == "prescribed-q2":
            _keys(value,("kind","body","coefficient","reference_radius","c22","orientation","profile_sha256","provenance"))
            figures.append(PrescribedQuadrupole(**{k:v for k,v in value.items() if k != "kind"}))
        else:
            _keys(value,("body","coefficient","reference_radius","axis","provenance"))
            if type(value["axis"]) is not list or len(value["axis"])!=3:
                raise ValueError("Неверная ось J2")
            figures.append(FixedJ2(**dict(value,axis=tuple(value["axis"]))))
    pair = document["settings"]["relative_pair"]
    if pair is not None and (type(pair) is not list or len(pair) != 2):
        raise ValueError("Неверная относительная пара в контрольной точке")
    # Persisted documents remain builtin-only even when constructors accept NumPy.
    for name in ("dt", "restitution", "rtol", "position_atol", "velocity_atol"):
        _number(document["settings"][name])
    settings = Settings(**dict(document["settings"],figures=tuple(figures),relative_pair=tuple(pair) if pair is not None else None))
    suffix = ("-prescribed-q2" if prescribed(figures) else "-fixed-j2") if figures else ""
    if document["model"] != settings.physics+"-"+settings.integrator+suffix:
        raise ValueError("Физическая модель не соответствует интегратору")
    initial,bodies = _bodies(document["initial"]),_bodies(document["bodies"])
    prepare_pair(initial,settings.relative_pair)
    prepare_pair(bodies,settings.relative_pair)
    validate_figures(initial, settings.figures)
    validate_figures(bodies, settings.figures)
    if settings.integrator == "dop853" and any(b.radius > 0 for b in initial+bodies):
        raise ValueError("DOP853 поддерживает только точечные тела без контактов")
    if settings.physics == "eih-1pn":
        from .relativity import validate_bodies
        validate_bodies(initial)
        validate_bodies(bodies)
    time = _number(document["time"],nonnegative=True)
    validate_figures(bodies, settings.figures, time)
    if prescribed(settings.figures) and origin is not None:
        from .perturbers import SUPPLEMENTS, BASE_DATASET_SHA256
        if origin.dataset_sha256 not in SUPPLEMENTS and origin.dataset_sha256 != BASE_DATASET_SHA256:
            # Register verified ring provenance only for a checkpoint that needs it.
            from .kuiper_ring import RING_SPECS
    validate_orientation_origin(settings.figures, origin)
    work = _number(document["orientation_work"])
    if work != 0 and (not prescribed(settings.figures) or time == 0):
        raise ValueError("Работа ориентации требует продолжающегося расчёта с заданными осями")
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
    result = Experiment(initial,bodies,settings,time,loss,tuple(events),document["halted"],offset,origin,work)
    validate_start(result)
    return result


def _rotation_document(rotation):
    return dict(body=rotation.body, figure=dict(mass=rotation.figure.mass,
        moments=list(rotation.figure.moments), bounding_radius=rotation.figure.bounding_radius),
        quaternion=list(rotation.quaternion), angular_momentum=list(rotation.angular_momentum),
        quaternion_atol=rotation.quaternion_atol, momentum_atol=rotation.momentum_atol,
        provenance=rotation.provenance)


def _rotations(values):
    from .nbody_rotation import RotationState
    from .rotation import RigidFigure
    if type(values) is not list or len(values) != 1:
        raise ValueError("Схема 10 требует одну динамическую фигуру")
    result = []
    for value in values:
        _keys(value,("body","figure","quaternion","angular_momentum","quaternion_atol","momentum_atol","provenance"))
        figure = value["figure"]
        _keys(figure,("mass","moments","bounding_radius"))
        for key, size in (("quaternion",4),("angular_momentum",3)):
            if type(value[key]) is not list or len(value[key]) != size:
                raise ValueError("Неверная размерность вращательного состояния")
            for number in value[key]:
                _number(number)
        if type(figure["moments"]) is not list or len(figure["moments"]) != 3:
            raise ValueError("Нужны три главных момента инерции")
        inertia = RigidFigure(_number(figure["mass"]), tuple(_number(n) for n in figure["moments"]),
            _number(figure["bounding_radius"]))
        result.append(RotationState(value["body"], inertia, tuple(value["quaternion"]),
            tuple(value["angular_momentum"]), _number(value["quaternion_atol"]),
            _number(value["momentum_atol"]), value["provenance"]))
    return tuple(result)


def save(experiment: Experiment, path: str | Path):
    _write_document(to_document(experiment), path)


def _write_document(document: dict, path: str | Path):
    """Bounded atomic JSON write shared by checkpoints and experiment bundles."""
    path = Path(path)
    data = json.dumps(document,ensure_ascii=False,allow_nan=False,indent=2).encode("utf-8")
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
    try:
        return from_document(_read_document(path))
    except (TypeError,OverflowError,UnicodeDecodeError) as error:
        raise ValueError("Неверный формат контрольной точки") from error


def _read_document(path: str | Path) -> dict:
    """Bounded JSON with duplicate keys and nonfinite constants rejected."""
    with Path(path).open("rb") as file:
        data = file.read(MAX_BYTES+1)
    if len(data)>MAX_BYTES:
        raise ValueError("Контрольная точка слишком велика")
    def reject_constant(value):
        raise ValueError("NaN/Infinity в JSON запрещены")
    try:
        document = json.loads(data,object_pairs_hook=_unique_pairs,parse_constant=reject_constant)
        return document
    except (TypeError,OverflowError,UnicodeDecodeError) as error:
        raise ValueError("Неверный формат контрольной точки") from error
