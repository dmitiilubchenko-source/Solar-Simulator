"""Predeclared max_step sensitivity using an immutable Decimal100 reference."""
import argparse
from decimal import Decimal as D
import hashlib
import json
from math import inf
from pathlib import Path
from unittest.mock import patch

import numpy as np

from scripts.assess_kepler_phase import ROOT, evaluate, fixture, fingerprints
from scripts.kepler_cache import load_receipt
from solar_simulator.error_control import PerBodyDOP853


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
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest, name
    with np.load(args.reference.with_suffix('.npz'),allow_pickle=False) as data:
        old_times=data['times'].copy();old=data['0.95_continuous'].copy()
    seed,times=fixture(.95)
    np.testing.assert_array_equal(times,old_times)
    np.testing.assert_array_equal(old[0],np.array([[b.position.x,b.position.y,b.position.z,
        b.velocity.x,b.velocity.y,b.velocity.z] for b in seed.bodies]))
    expected=[tuple(tuple(map(D,group)) for group in row)
              for row in reference['results']['0.95']['decimal_reference']]
    sources=fingerprints()
    for name in ('scripts/assess_kepler_steps.py','docs/kepler-step-protocol.md'):
        sources[name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    arrays={'times':times};results={}
    for divisor in (None,500,1000,2000,4000,8000):
        cap=inf if divisor is None else (times[-1]/2)/divisor
        def solver(*args,**kwargs):
            return PerBodyDOP853(*args,max_step=cap,**kwargs)
        with patch('solar_simulator.continuous.PerBodyDOP853',solver):
            values,metrics=evaluate(seed,times,expected)
        key='uncapped' if divisor is None else str(divisor)
        arrays[key]=values
        if divisor is None:
            np.testing.assert_array_equal(values,old)
        results[key]=dict(max_step_seconds=None if divisor is None else cap,**metrics)
        print(key,{k:v for k,v in results[key].items() if k!='sampled_errors'},flush=True)
    assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in sources.items())
    assert hashlib.sha256(args.reference.read_bytes()).hexdigest()==hashlib.sha256(raw).hexdigest()
    np.savez_compressed(output.with_suffix('.npz'),**arrays)
    receipt=dict(protocol='docs/kepler-step-protocol.md',source_sha256=sources,
        npz_sha256=hashlib.sha256(output.with_suffix('.npz').read_bytes()).hexdigest(),
        reference_sha256=hashlib.sha256(raw).hexdigest(),source_unchanged=True,
        uncapped_bitexact=True,results=results,runtime_modified=False,
        general_release_passed=False)
    with output.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(receipt,stream,indent=2,allow_nan=False);stream.write('\n')
    print('Saved',output,flush=True)


if __name__=='__main__':
    main()
