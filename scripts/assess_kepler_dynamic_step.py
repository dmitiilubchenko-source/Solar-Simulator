"""Offline dynamical-time step restriction; not imported by runtime."""
import argparse
from dataclasses import replace
from decimal import Decimal as D
import hashlib
import json
from math import sqrt
from pathlib import Path
from unittest.mock import patch

import numpy as np

from scripts.assess_kepler_phase import ROOT, evaluate, fixture, fingerprints
from scripts.kepler_cache import load_receipt
from solar_simulator.error_control import PerBodyDOP853
from solar_simulator.simulation import G


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    output=args.output.resolve()
    if output.exists() or output.with_suffix('.npz').exists():
        raise FileExistsError('Preserve previous results')
    reference,raw=load_receipt(args.reference,ROOT)
    for name,digest in reference['source_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
    seed,times=fixture(.95)
    with np.load(args.reference.with_suffix('.npz'),allow_pickle=False) as cache:
        np.testing.assert_array_equal(times,cache['times'])
        np.testing.assert_array_equal(cache['0.95_continuous'][0],np.array([
            [b.position.x,b.position.y,b.position.z,b.velocity.x,b.velocity.y,b.velocity.z]
            for b in seed.bodies]))
    expected=[tuple(tuple(map(D,group)) for group in row)
              for row in reference['results']['0.95']['decimal_reference']]
    sources=fingerprints()
    for name in ('scripts/assess_kepler_dynamic_step.py','docs/kepler-dynamic-step-protocol.md'):
        sources[name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    mu=G*sum(b.mass for b in seed.bodies)
    arrays={'times':times};results={}
    for divisor in (32,64,128,256,512,None):
        class DynamicStep(PerBodyDOP853):
            def _step_impl(self):
                radius=float(np.linalg.norm(self.y[3:6]))
                self.max_step=sqrt(radius**3/mu)/divisor
                return super()._step_impl()
        current_seed=(seed if divisor else replace(seed,settings=replace(seed.settings,rtol=1e-12)))
        selected=DynamicStep if divisor else PerBodyDOP853
        with patch('solar_simulator.continuous.PerBodyDOP853',selected):
            values,metrics=evaluate(current_seed,times,expected)
        key=str(divisor) if divisor else 'loose_uncapped'
        arrays[key]=values;results[key]=metrics
        print(key,{k:v for k,v in metrics.items() if k!='sampled_errors'},flush=True)
    assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in sources.items())
    assert hashlib.sha256(args.reference.read_bytes()).hexdigest()==hashlib.sha256(raw).hexdigest()
    np.savez_compressed(output.with_suffix('.npz'),**arrays)
    receipt=dict(protocol='docs/kepler-dynamic-step-protocol.md',source_sha256=sources,
        npz_sha256=hashlib.sha256(output.with_suffix('.npz').read_bytes()).hexdigest(),
        reference_sha256=hashlib.sha256(raw).hexdigest(),source_unchanged=True,
        results=results,runtime_modified=False,general_release_passed=False)
    with output.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(receipt,stream,indent=2,allow_nan=False);stream.write('\n')
    print('Saved',output,flush=True)


if __name__=='__main__':
    main()
