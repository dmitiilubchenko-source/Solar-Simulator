"""Freeze several measured-astrometry cases, whole withheld seasons and shared DE441 inputs.

Case policy is versioned before fitting. Failed declared cases stay in manifest.
No fitted target ephemeris is requested. All network calls are sequential.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import urllib.parse

import numpy as np

from fetch_orbit_observations import (mpc_fetch, utc_jd, horizons, vector_rows,
    verify_observatory, fetch, gm_values, IDS, NAMES, AU_KM, GM_URL, SOURCE_URL, MPC_URL)

BASE_EPOCH = 2458849.5


def choose_seasons(records, designation, policy):
    """Use timestamps, station, catalog and format; never fit/residual criteria."""
    eligible = [r for r in records if r.get('permid')==designation
        and r.get('stn') in policy['stations']
        and policy['start_utc'] <= r.get('obstime','') < policy['end_utc_exclusive']
        and r.get('Obstype')=='optical' and r.get('mode')==policy['mode']
        and r.get('astcat')==policy['catalog'] and r.get('subfrm') is None
        and r.get('deprecated') in (None,False)
        and r.get('rmsra') is not None and r.get('rmsdec') is not None]
    eligible.sort(key=lambda r:(r['obstime'],r['obsid']))
    if len({r['obsid'] for r in eligible}) != len(eligible):
        raise ValueError('Duplicate MPC observations')
    seasons = []
    for row in eligible:
        if not seasons or utc_jd(row['obstime'])-utc_jd(seasons[-1][-1]['obstime']) >= policy['season_gap_days']:
            seasons.append([])
        seasons[-1].append(row)
    nights = lambda rows:len({r['obstime'][:10] for r in rows})
    for index in range(len(seasons)-1):
        training,holdout = seasons[index:index+2]
        if (len(training)>=policy['min_training_measurements'] and nights(training)>=policy['min_training_nights']
                and len(holdout)>=policy['min_holdout_measurements'] and nights(holdout)>=policy['min_holdout_nights']):
            return training,holdout,dict(eligible_count=len(eligible),season_counts=[len(s) for s in seasons],
                chosen_season_indices=[index,index+1],training_nights=nights(training),holdout_nights=nights(holdout),
                gap_days=utc_jd(holdout[0]['obstime'])-utc_jd(training[-1]['obstime']))
    raise ValueError('No consecutive seasons meet the frozen count/night criteria: '+str([len(s) for s in seasons]))


def background_grid(cache, epochs, cached=False):
    """Regular output interval avoids hundreds of long-URL requests."""
    cache.mkdir(exist_ok=True,parents=True)
    gm_path = cache/'gm.pck'
    if not gm_path.exists() and not cached:
        gm_path.write_bytes(fetch(GM_URL))
    gms = gm_values(gm_path.read_bytes(),IDS)
    bodies = []
    for body_id,name in zip(IDS,NAMES):
        p = cache/f'body-{body_id}.json'
        if not p.exists() and not cached:
            params = dict(format='json',COMMAND=f"'{body_id}'",OBJ_DATA="'NO'",MAKE_EPHEM="'YES'",
                EPHEM_TYPE="'VECTORS'",CENTER="'500@0'",START_TIME=f"'JD{epochs[0]:.9f}'",
                STOP_TIME=f"'JD{epochs[-1]:.9f}'",STEP_SIZE="'1 d'",REF_SYSTEM="'ICRF'",
                REF_PLANE="'FRAME'",VEC_CORR="'NONE'",VEC_TABLE="'2'",OUT_UNITS="'AU-D'",
                CSV_FORMAT="'YES'",TIME_TYPE="'TDB'",VEC_DELTA_T="'NO'")
            p.write_bytes(fetch(SOURCE_URL+'?'+urllib.parse.urlencode(params)))
        values,_ = vector_rows(json.loads(p.read_bytes()),body_id,'500@0',epochs)
        bodies.append(dict(name=name,gm_au3_day2=gms[body_id]*86400**2/(AU_KM*1000)**3,
            positions_au=values[:,:3].tolist(),velocities_au_day=values[:,3:].tolist()))
        print('Background:',name,flush=True)
    return bodies


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy',type=Path,default=Path('scripts/orbit-cohort-policy.json'))
    parser.add_argument('--cache',type=Path,default=Path('.tools/orbit-cohort-2020-2021'))
    parser.add_argument('--output',type=Path,default=Path('src/solar_simulator/data'))
    parser.add_argument('--manifest',type=Path,default=Path('docs/orbit-cohort-manifest.json'))
    parser.add_argument('--cached',action='store_true')
    args = parser.parse_args(argv)
    policy_raw = args.policy.read_bytes()
    policy = json.loads(policy_raw)
    args.cache.mkdir(parents=True,exist_ok=True)
    args.output.mkdir(parents=True,exist_ok=True)
    # Background fixed for whole declared calendar interval, including light time.
    grid = np.arange(utc_jd(policy['start_utc']+'T00:00:00Z')-2,
        utc_jd(policy['end_utc_exclusive']+'T00:00:00Z')+2.01,1.)
    bodies = background_grid(args.cache/'background',grid,args.cached)
    manifest = dict(schema_version=1,policy=policy,policy_sha256=hashlib.sha256(policy_raw).hexdigest(),cases=[])
    for designation in policy['designations']:
        cache = args.cache/designation
        cache.mkdir(exist_ok=True)
        raw_file = cache/'mpc-observations.json'
        if not raw_file.exists() and not args.cached:
            probe = Path(f'.tools/orbit-cohort-raw/mpc-{designation}.json')
            raw_file.write_bytes(probe.read_bytes() if probe.exists() else
                mpc_fetch('get-obs',{'desigs':[designation],'output_format':['ADES_DF']}))
        try:
            train,holdout,selection = choose_seasons(json.loads(raw_file.read_bytes())[0]['ADES_DF'],designation,policy)
        except ValueError as error:
            manifest['cases'].append(dict(designation=designation,status='unavailable',reason=str(error)))
            continue
        rows = train+holdout
        epoch = float(np.floor(np.median([utc_jd(r['obstime']) for r in train]))+.5)
        prepared = {}
        station_checks = {}
        for station in sorted({r['stn'] for r in rows}):
            records = [r for r in rows if r['stn']==station]
            station_file = cache/f'observatory-{station}.json'
            if not station_file.exists() and not args.cached:
                station_file.write_bytes(mpc_fetch('obscodes',{'obscode':station}))
            for start in range(0,len(records),30):
                chunk = records[start:start+30]
                name = f'observer-{station}-{start}.json'
                values,offsets = horizons(cache,name,0,station+'@399',[utc_jd(r['obstime']) for r in chunk],
                    args.cached,time_type='UT',delta=True)
                station_checks[station] = verify_observatory(json.loads(station_file.read_bytes()),
                                                             json.loads((cache/name).read_bytes()))
                for row,value,offset in zip(chunk,values,offsets):
                    prepared[row['obsid']] = (value,offset)
            print(designation,'station',station,len(records),flush=True)
        train_ids = {r['obsid'] for r in train}
        observations = []
        for r in rows:
            value,offset = prepared[r['obsid']]
            observations.append(dict(id=r['obsid'],utc=r['obstime'],night=r['obstime'][:10],station=r['stn'],
                time_days=utc_jd(r['obstime'])-epoch+float(offset)/86400,
                ra_deg=float(r['ra']),dec_deg=float(r['dec']),sigma_ra_arcsec=float(r['rmsra']),
                sigma_dec_arcsec=float(r['rmsdec']),correlation=float(r['rmscorr'] or 0),
                sigma_source='MPC ADES rmsRA/rmsDec',observer_position_au=(-value[:3]).tolist(),
                observer_velocity_au_day=(-value[3:]).tolist(),utc_to_tdb_seconds=float(offset),
                split='train' if r['obsid'] in train_ids else 'holdout'))
        all_files = list(cache.glob('*.json'))+list((args.cache/'background').glob('*'))
        hashes = {p.relative_to(args.cache).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in all_files}
        doc = dict(schema_version=1,frame='ICRF',center='SSB',units='AU-D',time_scale='TDB',epoch_jd_tdb=epoch,
            designation=designation,selection=selection | dict(policy=policy,policy_sha256=manifest['policy_sha256']),
            provenance=dict(observations_url=MPC_URL+'get-obs',observatory_url=MPC_URL+'obscodes',
                observer_and_background_url=SOURCE_URL,gm_url=GM_URL,raw_sha256=hashes,station_checks=station_checks,
                dependency='Measured target angles from MPC; only observers/UTC-TDB/perturbers from JPL DE441/EOP. No target orbit requested.'),
            error_model=dict(night_systematic_arcsec=policy['night_systematic_arcsec']),observations=observations,
            background=dict(times_days=(grid-epoch).tolist(),bodies=bodies))
        output = args.output/f'orbit-cohort-{designation}.json'
        output.write_text(json.dumps(doc,ensure_ascii=False,allow_nan=False,indent=2)+'\n',encoding='utf-8')
        manifest['cases'].append(dict(designation=designation,status='prepared',dataset=output.as_posix(),
            dataset_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),selection=selection,
            counts=dict(training=len(train),holdout=len(holdout)),stations=dict(Counter(r['stn'] for r in rows))))
        print('Saved',output,len(train),len(holdout),selection['gap_days'],flush=True)
    args.manifest.write_text(json.dumps(manifest,ensure_ascii=False,allow_nan=False,indent=2)+'\n',encoding='utf-8')
    print('Manifest:',args.manifest,flush=True)


if __name__=='__main__':
    main()
