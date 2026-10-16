"""Controlled stage-summation/carry experiment on the original failed orbit."""
import argparse
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import numpy as np

from scripts.assess_kepler_phase import ROOT, evaluate, fixture, fingerprints
from scripts.kepler_cache import load_receipt
from scripts.kepler_roundoff import solver_class
from solar_simulator.simulation import G


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,required=True)
    parser.add_argument('--dynamic',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();output=args.output.resolve()
    if output.exists() or output.with_suffix('.npz').exists():
        raise FileExistsError('Preserve previous results')
    reference,raw=load_receipt(args.reference,ROOT)
    for name,digest in reference['source_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
    dynamic,dynamic_raw=load_receipt(args.dynamic,ROOT)
    assert dynamic['reference_sha256']==hashlib.sha256(raw).hexdigest()
    for name,digest in dynamic['source_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
    seed,times=fixture(.95)
    expected=[tuple(tuple(map(D,group)) for group in row)
              for row in reference['results']['0.95']['decimal_reference']]
    sources=fingerprints()
    for name in ('scripts/assess_kepler_roundoff.py','scripts/kepler_roundoff.py',
                 'docs/kepler-roundoff-protocol.md'):
        sources[name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    with np.load(args.reference.with_suffix('.npz'),allow_pickle=False) as data:
        np.testing.assert_array_equal(times,data['times']);old=data['0.95_continuous'].copy()
    with np.load(args.dynamic.with_suffix('.npz'),allow_pickle=False) as data:
        np.testing.assert_array_equal(times,data['times'])
        controls={32:data['32'].copy(),64:data['64'].copy(),None:old}
    np.testing.assert_array_equal(old[0],np.array([[b.position.x,b.position.y,b.position.z,
        b.velocity.x,b.velocity.y,b.velocity.z] for b in seed.bodies]))
    mu=G*sum(b.mass for b in seed.bodies)
    results={};arrays={'times':times}
    for divisor in (None,32,64):
        for accurate_sums,compensated in ((False,False),(True,False),(False,True),(True,True)):
            cls=solver_class(accurate_sums=accurate_sums,compensated=compensated,divisor=divisor,mu=mu)
            with patch('solar_simulator.continuous.PerBodyDOP853',cls):
                values,metrics=evaluate(seed,times,expected)
            key=f'{divisor}_sum{int(accurate_sums)}_carry{int(compensated)}'
            if not accurate_sums and not compensated:
                np.testing.assert_array_equal(values,controls[divisor])
            arrays[key]=values;results[key]=metrics
            print(key,{k:v for k,v in metrics.items() if k!='sampled_errors'},flush=True)
    assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in sources.items())
    assert hashlib.sha256(args.reference.read_bytes()).hexdigest()==hashlib.sha256(raw).hexdigest()
    assert hashlib.sha256(args.dynamic.read_bytes()).hexdigest()==hashlib.sha256(dynamic_raw).hexdigest()
    np.savez_compressed(output.with_suffix('.npz'),**arrays)
    with output.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(dict(protocol='docs/kepler-roundoff-protocol.md',source_sha256=sources,
            npz_sha256=hashlib.sha256(output.with_suffix('.npz').read_bytes()).hexdigest(),
            reference_sha256=hashlib.sha256(raw).hexdigest(),source_unchanged=True,
            controls_bitexact=True,results=results,runtime_modified=False,
            general_release_passed=False),stream,indent=2,allow_nan=False);stream.write('\n')
    print('Saved',output,flush=True)


if __name__=='__main__':
    main()
