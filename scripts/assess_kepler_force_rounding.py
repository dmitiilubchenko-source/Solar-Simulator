"""Independent two-body force rounding experiment, not a native backend."""
import argparse
from decimal import Decimal as D, localcontext
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import numpy as np

from scripts.assess_kepler_holdout import CASES, holdout_fixture
from scripts.assess_kepler_phase import ROOT, differences, evaluate, fingerprints, maximum, decimal_relative
from scripts.kepler_cache import load_receipt
from scripts.assess_sandbox_planets import states
from scripts.kepler_reference import propagate
from scripts.kepler_roundoff import solver_class
from solar_simulator.continuous import ContinuousRun
from solar_simulator.simulation import G


def decimal_acceleration(relative,mu):
    with localcontext() as context:
        context.prec=70
        p=tuple(D.from_float(float(x)) for x in relative)
        radius=sum(x*x for x in p).sqrt()
        return np.array([float(-mu*x/radius**3) for x in p])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--holdout',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();output=args.output.resolve()
    if output.exists() or output.with_suffix('.npz').exists():
        raise FileExistsError('Preserve previous results')
    holdout,raw=load_receipt(args.holdout,ROOT)
    for name,digest in holdout['source_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
    with np.load(args.holdout.with_suffix('.npz'),allow_pickle=False) as data:
        old={name:data[name].copy() for name in data.files}
    sources=fingerprints()
    for name in ('scripts/assess_kepler_force_rounding.py','scripts/assess_kepler_holdout.py',
                 'scripts/kepler_roundoff.py','docs/kepler-force-rounding-protocol.md'):
        sources[name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    results={};arrays={}
    for name,e,anomaly,permuted in CASES:
        seed,times=holdout_fixture(e,anomaly,permuted)
        np.testing.assert_array_equal(times,old[f'{name}_times'])
        np.testing.assert_array_equal(states(seed.bodies),old[f'{name}_carry'][0])
        expected=[tuple(tuple(map(D,group)) for group in row)
                  for row in holdout['results'][name]['decimal_reference']]
        with localcontext() as context:
            context.prec=110
            mu=D.from_float(G)*sum(D.from_float(float(b.mass)) for b in seed.bodies)
            encoded=tuple(D.from_float(float(x)) for x in states(seed.bodies)[1]-states(seed.bodies)[0])
            encoded_reference=[propagate(encoded[:3],encoded[3:],mu,D.from_float(float(t))) for t in times]
        reference_effect=maximum([differences(a,b) for a,b in zip(encoded_reference,expected)])

        class DecimalForceRun(ContinuousRun):
            def _rhs(self,time,state):
                # Exactly two bodies and the first/second pair are required.
                assert self._count==2 and self._pair.first==0 and self._pair.second==1
                result=np.zeros(12)
                result[:6]=state[6:12]
                result[9:12]=decimal_acceleration(state[3:6],mu)
                return result

        rows={};arrays[f'{name}_times']=times
        for mode in ('native','decimal_force'):
            solver=solver_class(accurate_sums=False,compensated=True,divisor=64,
                                mu=G*sum(b.mass for b in seed.bodies))
            selected=ContinuousRun if mode=='native' else DecimalForceRun
            with patch('solar_simulator.continuous.PerBodyDOP853',solver),\
                    patch('scripts.assess_kepler_phase.ContinuousRun',selected):
                values,metrics=evaluate(seed,times,expected)
            if mode=='native':
                np.testing.assert_array_equal(values,old[f'{name}_carry'])
            encoded_errors=[]
            with localcontext() as context:
                context.prec=110
                for state,reference in zip(values,encoded_reference):
                    relative=decimal_relative(state)
                    encoded_errors.append(differences((relative[:3],relative[3:]),reference))
            metrics['errors_against_encoded_initial_model']=maximum(encoded_errors)
            arrays[f'{name}_{mode}']=values;rows[mode]=metrics
            print(name,mode,{k:v for k,v in metrics.items() if k!='sampled_errors'},flush=True)
        results[name]=dict(initial_relative_encoding_effect=reference_effect,results=rows)
    assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in sources.items())
    assert hashlib.sha256(args.holdout.read_bytes()).hexdigest()==hashlib.sha256(raw).hexdigest()
    np.savez_compressed(output.with_suffix('.npz'),**arrays)
    with output.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(dict(protocol='docs/kepler-force-rounding-protocol.md',source_sha256=sources,
            npz_sha256=hashlib.sha256(output.with_suffix('.npz').read_bytes()).hexdigest(),
            holdout_sha256=hashlib.sha256(raw).hexdigest(),source_unchanged=True,
            native_controls_bitexact=True,results=results,runtime_modified=False,
            general_release_passed=False),stream,indent=2,allow_nan=False);stream.write('\n')
    print('Saved',output,flush=True)


if __name__=='__main__':
    main()
