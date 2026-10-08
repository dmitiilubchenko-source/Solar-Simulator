"""Strict offline snapshots of JPL geometric barycentric states, in SI."""
from dataclasses import dataclass
import hashlib
from importlib.resources import files
import json
from math import isfinite
import re

from .simulation import Body, G
from .vector3 import Vector3

DATASET_NAME = "solar-system-20261008.json"
EXPECTED_IDS = (10, 1, 2, 3, 4, 5, 6, 7, 8)
NAMES = ("Sun", "Mercury", "Venus", "Earth-Moon", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune")
SOURCE_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"
GM_URL = "https://ssd.jpl.nasa.gov/ftp/xfr/gm_Horizons.pck"

RESOLVED_DATASET_NAME = "solar-system-moon-20261008.json"
RESOLVED_IDS = (10, 1, 2, 399, 301, 4, 5, 6, 7, 8)
RESOLVED_NAMES = ("Sun", "Mercury", "Venus", "Earth", "Moon", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune")


@dataclass(frozen=True)
class EphemerisOrigin:
    epoch_jd_tdb: float
    frame: str
    center: str
    ephemeris: str
    dataset_sha256: str
    gm_sha256: str

    def __post_init__(self):
        if type(self.epoch_jd_tdb) not in (int, float) or not isfinite(self.epoch_jd_tdb):
            raise ValueError("Неверная эпоха TDB")
        if self.frame != "Ecliptic J2000" or self.center != "Solar System Barycenter" or self.ephemeris != "DE441":
            raise ValueError("Несогласованные система координат или эфемерида")
        for digest in (self.dataset_sha256, self.gm_sha256):
            if type(digest) is not str or re.fullmatch(r"[a-f0-9]{64}", digest) is None:
                raise ValueError("Неверная контрольная сумма источника")


def decode_snapshot(data: bytes):
    """No network; reject wrong units, body IDs, frames, epochs and nonfinite values."""
    if not isinstance(data, bytes) or len(data) > 100_000:
        raise ValueError("Неверный размер снимка эфемерид")
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Повторяющееся поле снимка")
            result[key] = value
        return result
    def bad_constant(value):
        raise ValueError("Неконечное число в снимке")
    doc = json.loads(data, object_pairs_hook=pairs, parse_constant=bad_constant)
    required = {"schema", "source", "gm_source", "gm_sha256", "epoch_jd_tdb", "frame", "center",
                "ephemeris", "units", "vector_correction", "bodies"}
    if type(doc) is not dict or set(doc) != required:
        raise ValueError("Неверные поля снимка эфемерид")
    if type(doc["schema"]) is not int or doc["schema"] != 1 or doc["units"] != "SI":
        raise ValueError("Неверные версия или единицы снимка")
    if doc["source"] != SOURCE_URL or doc["gm_source"] != GM_URL or doc["vector_correction"] != "NONE":
        raise ValueError("Нужны геометрические векторы JPL без световых поправок")
    origin = EphemerisOrigin(doc["epoch_jd_tdb"], doc["frame"], doc["center"], doc["ephemeris"],
                             hashlib.sha256(data).hexdigest(), doc["gm_sha256"])
    if type(doc["bodies"]) is not list or len(doc["bodies"]) not in (9, 10):
        raise ValueError("Нужны девять планетных систем или десять тел с отдельной Луной")
    ids, names = (EXPECTED_IDS, NAMES) if len(doc["bodies"]) == 9 else (RESOLVED_IDS, RESOLVED_NAMES)
    bodies = []
    for record, body_id, name in zip(doc["bodies"], ids, names):
        if type(record) is not dict or set(record) != {"id", "name", "gm_m3_s2", "position", "velocity"}:
            raise ValueError("Неверная запись тела")
        if type(record["id"]) is not int or record["id"] != body_id or record["name"] != name:
            raise ValueError("Нужны согласованные барицентры планетных систем")
        gm = record["gm_m3_s2"]
        if type(gm) not in (int, float) or not isfinite(gm) or gm <= 0:
            raise ValueError("Неверный GM")
        vectors = []
        for key in ("position", "velocity"):
            v = record[key]
            if type(v) is not list or len(v) != 3 or any(type(x) not in (int, float) or not isfinite(x) for x in v):
                raise ValueError("Неверный вектор SI")
            vectors.append(Vector3(*v))
        # G*mass recovers the measured GM; masses are equivalent model values.
        bodies.append(Body(name, gm/G, *vectors))
    return bodies, origin


def solar_system(*, resolved_moon=False):
    if type(resolved_moon) is not bool:
        raise ValueError("resolved_moon должен быть bool")
    try:
        data=files("solar_simulator.data").joinpath(RESOLVED_DATASET_NAME if resolved_moon else DATASET_NAME).read_bytes()
    except FileNotFoundError as error:
        raise RuntimeError("Начальные данные JPL ещё не загружены; используйте scripts/fetch_ephemerides.py") from error
    return decode_snapshot(data)
