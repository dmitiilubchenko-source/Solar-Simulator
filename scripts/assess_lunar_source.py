"""Arithmetic qualification of the unchanged rigid surrogate, not PN certification.

Definitions were reviewed against Williams2014 section5, Park2021 sections2.4/4,
Klioner2010 sections2/7. The executable check cannot verify those publications.
"""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from solar_simulator.spin_initial import lunar_solid_equivalent_initial, PROFILE_SHA256


def assess():
    figure, _, _, profile = lunar_solid_equivalent_initial()
    # Independent transcription; do not infer the source constants from the profile.
    k = np.array([.392728-.00011260, .392728-.00002289, .392728+.00013549])
    expected = profile['moon_gm_m3_s2']/profile['gravitational_constant_m3_kg_s2']*1738000.**2*k
    inertia_error = float(np.max(abs(np.array(figure.moments)-expected)/expected))
    a,b,c = np.array(figure.moments)/(figure.mass*1738000.**2)
    j2, c22 = c-(a+b)/2, (b-a)/4
    q2_error = float(max(abs(j2/.000203235-1), abs(c22/.0000224275-1)))
    radius_error = float(abs((1737151./1738000.)**2-1))
    checks = dict(inertia_arithmetic=inertia_error<1e-12, q2_arithmetic=q2_error<1e-12,
        wrong_radius_control=radius_error>1e-4)
    return dict(change=69, kind='lunar-source-qualification', profile_sha256=PROFILE_SHA256,
        criteria=dict(inertia_relative=1e-12,q2_relative=1e-12,wrong_radius_relative_minimum=1e-4),
        measurements=dict(inertia_relative=inertia_error,q2_relative=q2_error,
            surrogate_J2=float(j2),surrogate_C22=float(c22),wrong_radius_relative=radius_error,
            common_mean_relative_sensitivity=.000012/.392728),
        checks=checks, arithmetic_passed=all(checks.values()), physical_mapping_certified=False,
        qualified=['mean permanent solid moments and gravity-reference radius, Williams2014 section5',
            'global TDB derivative of the pinned PA attitude, existing DE441 loader',
            'same effective I in kinetic energy and Q2; translational mass is whole GM/G'],
        unresolved=['time-compatible dimensional inertia and radius for a local lunar PN frame',
            'mean-solid axes versus undistorted mantle PA axes, including off-diagonal permanent tide',
            'harmonic centres to full canonical ADM centres, SSC and local tetrad/spin',
            'PN inertia and multipoles, fluid-core and tidal deformation model'],
        limitations=['Arithmetic passage does not certify physical mapping or ephemeris accuracy',
            'Common mean sensitivity is not a covariance or uncertainty interval',
            'Surrogate solid-I Q2 is not the published whole-Moon gravity field',
            'No clock/basis/geodetic correction added to the already-global attitude derivative'],
        primary_sources=[dict(url='https://agupubs.onlinelibrary.wiley.com/doi/full/10.1002/2013JE004559',
            location='sections4-5, Table4, solid/permanent/tide-removed definitions; no TDB match in full-text search'),
            dict(url='https://ssd.jpl.nasa.gov/doc/Park.2021.AJ.DE440.pdf',location='sections2.3-2.4 and4.1-4.2'),
            dict(url='https://arxiv.org/pdf/1001.0915',location='sections2 and7, especially7.5-7.9')],
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())


if __name__ == '__main__':
    report = assess(); text = json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    if len(sys.argv)!=2: raise SystemExit('Usage: assess_lunar_source.py NEW_REPORT.json')
    with Path(sys.argv[1]).open('x',encoding='utf-8',newline='\n') as stream: stream.write(text)
    print('arithmetic_passed=',report['arithmetic_passed'],'physical_mapping_certified=False')
    if not report['arithmetic_passed']: raise SystemExit(1)
