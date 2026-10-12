"""Evaluate frozen whole-season cases with independent and station-night error models.

No holdout-dependent model selection, rejection or tuning. Unavailable cases and
numerically failed fits are retained explicitly. Coverage is descriptive.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter

import numpy as np

from solar_simulator.orbit_determination import (fit_dataset,decode_dataset,
    predict_directions,angular_residuals)
from assess_orbit_observations import independent_directions


def run_case(case,policy):
    if case['status'] != 'prepared':
        return dict(designation=case['designation'],status=case['status'],reason=case['reason'])
    path = Path(case['dataset'])
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != case['dataset_sha256']:
        raise ValueError('Frozen manifest/dataset checksum mismatch')
    document = json.loads(raw)
    training,holdout,background = decode_dataset(document)
    result = dict(designation=case['designation'],status='evaluated',selection=case['selection'],
        stations=case['stations'],dataset_sha256=case['dataset_sha256'],models={})
    for name,tau in [('independent',0.),('station_night',policy['night_systematic_arcsec'])]:
        started = perf_counter()
        try:
            fitted = fit_dataset(path,night_systematic_arcsec=tau)
            state = fitted['fit']['state_au_day']
            all_obs = training+holdout
            standard = angular_residuals(predict_directions(state,all_obs,background),all_obs)
            reference = angular_residuals(independent_directions(state,all_obs,document),all_obs)
            strict = angular_residuals(predict_directions(state,all_obs,background,rtol=3e-13,atol=3e-14),all_obs)
            controls = dict(independent_rk45_max_arcsec=float(np.linalg.norm(standard-reference,axis=1).max()),
                            stricter_tolerances_max_arcsec=float(np.linalg.norm(standard-strict,axis=1).max()))
            fitted['numerical_controls'] = controls
            fitted['checks_passed'] = bool(fitted['fit']['rank']==6 and all(v<.001 for v in controls.values()))
            fitted['elapsed_seconds'] = perf_counter()-started
            result['models'][name] = fitted
            print(case['designation'],name,'training',fitted['training']['rms_arcsec'],
                  'holdout',fitted['holdout']['rms_arcsec'],'night95',fitted['holdout_coverage']['station_night_95_fraction'],flush=True)
        except (ValueError,RuntimeError,OverflowError) as error:
            result['models'][name] = dict(checks_passed=False,status='fit_failed',reason=str(error))
            result['status'] = 'fit_failed'
            print(case['designation'],name,'FAILED',error,flush=True)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,default=Path('docs/orbit-cohort-manifest.json'))
    parser.add_argument('--output',type=Path,default=Path('docs/orbit-cohort-validation.json'))
    args = parser.parse_args(argv)
    raw = args.manifest.read_bytes()
    manifest = json.loads(raw)
    policy = manifest['policy']
    result = dict(schema_version=1,manifest_sha256=hashlib.sha256(raw).hexdigest(),
        policy_sha256=manifest['policy_sha256'],policy=policy,cases=[],
        scope='Measured-astrometry prediction of whole withheld seasons for a small declared sample. JPL observers/background remain prescribed. Fixed station-night sigma is a sensitivity assumption, not a calibrated instrument model.',
        comparison='Both error models frozen before fitting; every available holdout used unchanged. RMS and interval coverage reported separately. No selection by forecast quality.',
        versions=dict(python=sys.version,numpy=np.__version__,scipy=__import__('scipy').__version__))
    # Persist progress after every case, including failures, for unattended runs.
    for case in manifest['cases']:
        result['cases'].append(run_case(case,policy))
        args.output.write_text(json.dumps(result,ensure_ascii=False,allow_nan=False,indent=2)+'\n',encoding='utf-8')
    evaluated = [c for c in result['cases'] if c['status']=='evaluated']
    result['summary'] = dict(declared_cases=len(manifest['cases']),evaluated_cases=len(evaluated),
        unavailable_cases=sum(c['status']=='unavailable' for c in result['cases']),
        failed_cases=sum(c['status']=='fit_failed' for c in result['cases']))
    result['checks_passed'] = bool(len(evaluated)>=2 and all(m['checks_passed']
        for c in evaluated for m in c['models'].values()) and not result['summary']['failed_cases'])
    result['code_sha256'] = {str(p).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in
        [Path('src/solar_simulator/orbit_determination.py'),Path(__file__).relative_to(Path.cwd()),
         Path('scripts/fetch_orbit_cohort.py'),Path('scripts/fetch_orbit_observations.py'),Path('scripts/assess_orbit_observations.py')]}
    args.output.write_text(json.dumps(result,ensure_ascii=False,allow_nan=False,indent=2)+'\n',encoding='utf-8')
    print('Summary:',result['summary'],'numerical checks:',result['checks_passed'],flush=True)
    if not result['checks_passed']:
        raise SystemExit('Cohort evaluation incomplete or numerical checks failed; all failures retained')


if __name__=='__main__':
    main()
