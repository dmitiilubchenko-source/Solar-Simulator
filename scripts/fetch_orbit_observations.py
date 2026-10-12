"""Prepare a frozen optical-astrometry case. Never request the asteroid's orbit.

MPC ADES supplies measured angles. Horizons supplies *only* known observer and
perturber states, including UTC->TDB and Earth orientation. Requests are serial.
The default selection and chronological split are fixed before any fit.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import urllib.parse

import numpy as np

from fetch_ephemerides import fetch, gm_values, GM_URL, SOURCE_URL

MPC_URL = 'https://data.minorplanetcenter.net/api/'
IDS = (10, 1, 2, 399, 301, 4, 5, 6, 7, 8, 9)
NAMES = ('Sun', 'Mercury', 'Venus', 'Earth', 'Moon', 'Mars', 'Jupiter',
         'Saturn', 'Uranus', 'Neptune', 'Pluto system')
AU_KM = 149597870.7
EPOCH = 2458900.5


def utc_jd(value):
    """Modern UTC Gregorian timestamp; leap-second exposures are unsupported."""
    stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if stamp.tzinfo is None or stamp.utcoffset().total_seconds() != 0:
        raise ValueError('Observation timestamp must explicitly use UTC')
    return 2440587.5 + stamp.timestamp() / 86400


def select_observations(records, designation='13270', station='T08'):
    """Selection by date/station/format only, independent of fitted residuals."""
    selected = [r for r in records if r.get('permid') == designation
                and r.get('stn') == station
                and '2020-01-01' <= r.get('obstime', '') < '2020-06-01'
                and r.get('Obstype') == 'optical' and r.get('mode') == 'CCD'
                and r.get('astcat') == 'Gaia2' and r.get('subfrm') is None
                and r.get('deprecated') in (None, False)
                and r.get('rmsra') is not None and r.get('rmsdec') is not None]
    selected.sort(key=lambda r: (r['obstime'], r['obsid']))
    if len({r['obsid'] for r in selected}) != len(selected) or len(selected) < 10:
        raise ValueError('Insufficient or duplicate measurements')
    return selected


def mpc_fetch(endpoint, body):
    result = subprocess.run(['curl.exe', '--fail', '--silent', '--show-error',
        '--request', 'GET', '--header', 'Content-Type: application/json',
        '--data-binary', json.dumps(body), '--max-time', '60',
        '--max-filesize', '25000000', MPC_URL + endpoint],
        capture_output=True, timeout=65)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace'))
    return result.stdout


def vector_rows(payload, target, center, epochs, time_type='TDB', delta=False):
    """Reject wrong frame, corrections, units, identity or time tags."""
    if payload.get('error') or payload.get('signature', {}).get('source') != 'NASA/JPL Horizons API':
        raise ValueError('Invalid Horizons response')
    if payload.get('signature',{}).get('version') not in ('1.2','1.3'):
        raise ValueError('Unsupported Horizons API version')
    text = payload.get('result', '')
    aliases = {target} | ({199} if target == 1 else {299} if target == 2 else set())
    match = re.search(r'Target body name:.*?\((\d+)\).*?\{source:\s*([^}]+)\}', text)
    required = ('Output units    : AU-D', 'Reference frame : ICRF',
                'GEOMETRIC cartesian states', 'JDUT' if time_type == 'UT' else 'JDTDB')
    if not match or int(match[1]) not in aliases or match[2].strip() != 'DE441':
        raise ValueError('Wrong target or ephemeris')
    if any(s not in text for s in required) or '$$SOE' not in text or '$$EOE' not in text:
        raise ValueError('Wrong Horizons frame, units or time scale')
    if center == '500@0':
        if 'Center body name: Solar System Barycenter (0)' not in text:
            raise ValueError('Wrong background center')
    elif re.fullmatch(r'[A-Za-z0-9]{3}@399', center):
        if ('Center body name: Earth (399)' not in text or 'Center-site name:' not in text
                or 'Center cylindric:' not in text):
            raise ValueError('Wrong observatory')
    else:
        raise ValueError('Unsupported observer center; verify site explicitly')
    rows = list(csv.reader(text.split('$$SOE')[1].split('$$EOE')[0].strip().splitlines()))
    expected = 10 if delta else 9
    if len(rows) != len(epochs):
        raise ValueError('Wrong number of Horizons epochs')
    states, offsets = [], []
    for row, epoch in zip(rows, epochs):
        if len(row) != expected or row[-1].strip() or abs(float(row[0]) - epoch) > 1e-8:
            raise ValueError('Malformed or mismatched vector epoch')
        values = [float(v) for v in row[3:9]] if delta else [float(v) for v in row[2:8]]
        offset = float(row[2]) if delta else 0.
        if not np.isfinite(values + [offset]).all():
            raise ValueError('Nonfinite vector')
        states.append(values)
        offsets.append(offset)
    return np.array(states), np.array(offsets)


def horizons(cache, name, target, center, epochs, cached=False, time_type='TDB', delta=False):
    params = dict(format='json', COMMAND=f"'{target}'", OBJ_DATA="'NO'", MAKE_EPHEM="'YES'",
        EPHEM_TYPE="'VECTORS'", CENTER=f"'{center}'", TLIST="'"+' '.join(f'{t:.12f}' for t in epochs)+"'",
        TLIST_TYPE="'JD'", REF_SYSTEM="'ICRF'", REF_PLANE="'FRAME'", VEC_CORR="'NONE'",
        VEC_TABLE="'2'", OUT_UNITS="'AU-D'", CSV_FORMAT="'YES'", TIME_TYPE=f"'{time_type}'",
        VEC_DELTA_T="'YES'" if delta else "'NO'")
    path = cache / name
    if not cached and not path.exists():
        path.write_bytes(fetch(SOURCE_URL + '?' + urllib.parse.urlencode(params)))
    return vector_rows(json.loads(path.read_bytes()), target, center, epochs, time_type, delta)


def verify_observatory(mpc, horizons_payload):
    """Check that Horizons uses the same physical site as MPC (10 m rounding allowance)."""
    if not re.fullmatch(r'[A-Za-z0-9]{3}',mpc.get('obscode','')) or mpc.get('observations_type') != 'optical':
        raise ValueError('Wrong or unsupported MPC station')
    text = horizons_payload['result']
    match = re.search(r'Center cylindric:\s*([\d.]+),\s*([\d.]+),\s*([+\-\d.]+)',text)
    if not match:
        raise ValueError('No explicit station coordinates in Horizons')
    longitude, rho, z = map(float,match.groups())
    # MPC parallax factors use the IAU 1976 equatorial Earth radius 6378.14 km.
    mpc_rho, mpc_z = float(mpc['rhocosphi'])*6378.14, float(mpc['rhosinphi'])*6378.14
    differences = [abs(longitude-float(mpc['longitude']))*np.pi/180*mpc_rho,
                   abs(rho-mpc_rho),abs(z-mpc_z)]
    if max(differences) > .01:
        raise ValueError('MPC/Horizons station coordinates differ by more than 10 m')
    return dict(station=mpc['obscode'], coordinate_differences_metres=[v*1000 for v in differences],
                allowance_metres=10., earth_radius_km=6378.14,
                note='Rounded published MPC parallax factors compared to the explicit Horizons station coordinates.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=Path('.tools/orbit-observations-13270'))
    parser.add_argument('--output', type=Path, default=Path('src/solar_simulator/data/orbit-observations-13270.json'))
    parser.add_argument('--cached', action='store_true')
    args = parser.parse_args(argv)
    args.cache.mkdir(parents=True, exist_ok=True)
    if not args.cached:
        raw_probe = Path('.tools/mpc-13270-raw.json')
        (args.cache/'mpc-observations.json').write_bytes(raw_probe.read_bytes() if raw_probe.exists()
            else mpc_fetch('get-obs', {'desigs':['13270'], 'output_format':['ADES_DF']}))
        (args.cache/'mpc-observatory.json').write_bytes(mpc_fetch('obscodes', {'obscode':'T08'}))
        (args.cache/'gm.pck').write_bytes(fetch(GM_URL))
    rows = select_observations(json.loads((args.cache/'mpc-observations.json').read_bytes())[0]['ADES_DF'])
    utc = [utc_jd(r['obstime']) for r in rows]
    # SSB relative to observatory => negate to obtain observatory relative to SSB.
    observer_parts, delta_parts = [], []
    for start in range(0, len(utc), 30):
        part, offset = horizons(args.cache, f'observer-{start}.json', 0, 'T08@399', utc[start:start+30],
                               args.cached, time_type='UT', delta=True)
        observer_parts.extend(part.tolist())
        delta_parts.extend(offset.tolist())
    observer, delta = np.array(observer_parts), np.array(delta_parts)
    station_check = verify_observatory(json.loads((args.cache/'mpc-observatory.json').read_bytes()),
                                      json.loads((args.cache/'observer-0.json').read_bytes()))
    times = np.array(utc) - EPOCH + delta/86400
    grid = np.arange(np.floor(min(times))-2, np.ceil(max(times))+2.01, .5)
    gms = gm_values((args.cache/'gm.pck').read_bytes(), IDS)
    bodies = []
    # Split long TLIST into bounded URLs, retaining exact original epochs.
    for body_id, name in zip(IDS, NAMES):
        parts = []
        for start in range(0, len(grid), 30):
            epochs = EPOCH + grid[start:start+30]
            state, _ = horizons(args.cache, f'body-{body_id}-{start}.json', body_id, '500@0', epochs, args.cached)
            parts.extend(state.tolist())
        state = np.array(parts)
        bodies.append(dict(name=name, gm_au3_day2=gms[body_id]*86400**2/(AU_KM*1000)**3,
                           positions_au=state[:,:3].tolist(), velocities_au_day=state[:,3:].tolist()))
        print('Prepared background:', name, flush=True)
    observations = []
    for r, t, site, dt in zip(rows, times, observer, delta):
        observations.append(dict(id=r['obsid'], utc=r['obstime'], night=r['obstime'][:10],
            time_days=float(t), ra_deg=float(r['ra']), dec_deg=float(r['dec']),
            sigma_ra_arcsec=float(r['rmsra']), sigma_dec_arcsec=float(r['rmsdec']),
            correlation=float(r['rmscorr'] or 0), sigma_source='MPC ADES rmsRA/rmsDec',
            observer_position_au=(-site[:3]).tolist(), observer_velocity_au_day=(-site[3:]).tolist(),
            utc_to_tdb_seconds=float(dt), station=r['stn'],
            split='train' if r['obstime'] < '2020-04-01' else 'holdout'))
    hashes = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(args.cache.glob('*')) if p.is_file()}
    doc = dict(schema_version=1, frame='ICRF', center='SSB', units='AU-D', time_scale='TDB',
        epoch_jd_tdb=EPOCH, designation='13270',
        selection=dict(station='T08', start_utc='2020-01-01', end_utc_exclusive='2020-06-01',
            holdout_start_utc='2020-04-01', catalog='Gaia2', mode='CCD',
            policy='All matching nondeprecated optical CCD measurements with reported uncertainties; no residual clipping'),
        provenance=dict(observations_url=MPC_URL+'get-obs', observatory_url=MPC_URL+'obscodes',
            observer_and_background_url=SOURCE_URL, gm_url=GM_URL, raw_sha256=hashes,
            station_check=station_check,
            dependency='Target angles are MPC measurements; observer, UTC/TDB and perturbing bodies use JPL DE441/EOP. No target ephemeris or orbital elements requested.'),
        observations=observations, background=dict(times_days=grid.tolist(), bodies=bodies))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, allow_nan=False, indent=2)+'\n', encoding='utf-8')
    print('Saved', args.output, len(observations), 'observations')


if __name__ == '__main__':
    main()
