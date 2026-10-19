"""Offline-safe Horizons time/provenance checks for the frozen nominal grid."""
import csv
from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlencode

import numpy as np

from scripts.fetch_ephemerides import fetch, parse_result
from solar_simulator.ephemerides import SOURCE_URL

PROTOCOL = 'docs/nominal-jpl440-protocol.md'
EPOCH = Fraction('2461321.5')
CALENDAR = datetime(2026, 10, 8)
TIME_ENVELOPE = Fraction(1, 10000)
MONTHS = {name: i for i, name in enumerate(
    ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'), 1)}


def seconds_grid(times):
    values = np.asarray(times, dtype=float)
    if (values.ndim != 1 or not len(values) or not np.isfinite(values).all()
            or (values < 0).any() or (values > 31557600).any()
            or (values != np.floor(values)).any() or not (np.diff(values) > 0).all()):
        raise ValueError('Require increasing integer nominal seconds inside the year')
    return [int(t) for t in values]


def jd_text(second):
    exact = EPOCH + Fraction(second, 86400)
    with localcontext() as ctx:
        ctx.prec = 40
        return format(Decimal(exact.numerator) / Decimal(exact.denominator), '.15f')


def request_url(body_id, times, kind):
    seconds = seconds_grid(times)
    params = dict(format='json', COMMAND=f"'{body_id}'", OBJ_DATA="'NO'", MAKE_EPHEM="'YES'",
        EPHEM_TYPE="'VECTORS'", CENTER="'500@0'", REF_SYSTEM="'ICRF'", REF_PLANE="'ECLIPTIC'",
        VEC_CORR="'NONE'", VEC_TABLE="'2'", OUT_UNITS="'KM-S'", CSV_FORMAT="'YES'",
        TIME_TYPE="'TDB'", TIME_DIGITS="'FRACSEC'", CAL_TYPE="'GREGORIAN'")
    if kind == 'regular':
        if len(seconds) < 2 or any(b-a != 72000 for a, b in zip(seconds, seconds[1:])):
            raise ValueError('Regular request must have twenty-hour intervals')
        params.update(START_TIME="'"+(CALENDAR+timedelta(seconds=seconds[0])).isoformat(' ')+"'",
            STOP_TIME="'"+(CALENDAR+timedelta(seconds=seconds[-1])).isoformat(' ')+"'", STEP_SIZE="'20h'")
    elif kind == 'jd':
        params.update(TLIST=' '.join("'"+jd_text(s)+"'" for s in seconds), TLIST_TYPE="'JD'")
    else:
        raise ValueError('Unknown request kind')
    return SOURCE_URL+'?'+urlencode(params)


def calendar_seconds(text):
    match = re.fullmatch(r'A\.D\.\s+(\d{4})-([A-Za-z]{3})-(\d{2})\s+(\d{2}):(\d{2}):(\d{2})(\.\d+)?', text.strip())
    if not match or match[2] not in MONTHS:
        raise ValueError('Unsupported Horizons Gregorian calendar field')
    year, day, hour, minute, second = (int(match[i]) for i in (1, 3, 4, 5, 6))
    delta = datetime(year, MONTHS[match[2]], day, hour, minute, second)-CALENDAR
    return Fraction(delta.days*86400+delta.seconds)+Fraction(match[7] or '0')


def parse_vectors(payload, body_id, times):
    seconds = seconds_grid(times)
    rows = parse_result(payload, body_id, [float(EPOCH+Fraction(s, 86400)) for s in seconds])
    result = payload['result']
    if 'Calendar Date (TDB)' not in result or result.count('$$SOE') != 1 or result.count('$$EOE') != 1:
        raise ValueError('Require unambiguous TDB calendar/vector table')
    fields = list(csv.reader(result.split('$$SOE')[1].split('$$EOE')[0].strip().splitlines()))
    for row, field, second in zip(rows, fields, seconds):
        jd = Fraction(field[0].strip())
        calendar = calendar_seconds(field[1])
        jd_seconds = (jd-EPOCH)*86400
        errors = (jd_seconds-second, calendar-second, jd_seconds-calendar)
        if any(abs(error) > TIME_ENVELOPE for error in errors):
            raise ValueError('TDB time representation exceeds 100 microseconds')
        row.update(nominal_seconds=second, printed_jd_tdb=field[0].strip(),
            printed_calendar_tdb=field[1].strip(), jd_offset_seconds=float(errors[0]),
            calendar_offset_seconds=float(errors[1]), jd_calendar_offset_seconds=float(errors[2]))
    return rows


def response(path, body_id, times, kind, cached=False):
    """Keep raw failures too; cached mode never fetches a missing response."""
    path = Path(path)
    manifest = path.with_suffix('.request.json')
    url = request_url(body_id, times, kind)
    if path.exists() != manifest.exists():
        raise ValueError('Incomplete raw request provenance')
    if not path.exists():
        if cached:
            raise FileNotFoundError('Offline JPL response missing: '+str(path))
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            raw = fetch(url)
        except Exception as error:
            failure = path.with_suffix('.failure.json')
            with failure.open('x', encoding='utf-8') as stream:
                json.dump(dict(url=url, at=datetime.now(timezone.utc).isoformat(),
                    error_type=type(error).__name__, message=str(error)), stream, indent=2)
            raise
        with path.open('xb') as stream:
            stream.write(raw)
        with manifest.open('x', encoding='utf-8') as stream:
            json.dump(dict(url=url, sha256=hashlib.sha256(raw).hexdigest(),
                fetched_utc=datetime.now(timezone.utc).isoformat()), stream, indent=2)
    raw = path.read_bytes()
    record = json.loads(manifest.read_bytes())
    if record['url'] != url or record['sha256'] != hashlib.sha256(raw).hexdigest():
        raise ValueError('Raw response/request SHA or URL changed')
    return parse_vectors(json.loads(raw), body_id, times), record


def vectors(rows):
    result = np.array([r['position']+r['velocity'] for r in rows], dtype=float)
    if result.shape != (len(rows), 6) or not np.isfinite(result).all():
        raise ValueError('Invalid vector matrix')
    return result
