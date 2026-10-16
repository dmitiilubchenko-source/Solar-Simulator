"""The exact original 60-epoch Kepler gate, separately from 82-epoch cases."""
import argparse
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path

import numpy as np

from scripts.assess_ias15 import metrics,source_hashes
from scripts.assess_kepler_phase import ROOT,fixture
from scripts.ias15_reference import load_library,library_hashes,ias_trajectory,dop_trajectory,EPSILONS,VERSION
from scripts.kepler_cache import load_receipt


def run(reference_path,output,library):
    if output.exists() or output.with_suffix('.npz').exists():
        raise FileExistsError('Preserve previous results')
    reference,raw=load_receipt(reference_path,ROOT)
    with np.load(reference_path.with_suffix('.npz'),allow_pickle=False) as data:
        cached={key:data[key].copy() for key in data.files}
    sources=source_hashes()
    for name in ('scripts/assess_ias15_original_grid.py','docs/ias15-original-grid-protocol.md'):
        sources[name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    external=library_hashes(library)
    arrays={};results={}
    for eccentricity in (0.,.5,.95):
        seed,times=fixture(eccentricity)
        np.testing.assert_array_equal(times,cached['times'])
        old=cached[f'{eccentricity}_continuous']
        expected=[tuple(tuple(map(D,group)) for group in row)
                  for row in reference['results'][str(eccentricity)]['decimal_reference']]
        rows={};bounds=None
        for epsilon in (None,*EPSILONS):
            key='dop853' if epsilon is None else f'ias15_{epsilon}'
            if epsilon is None:
                values,stats=dop_trajectory(seed,times)
                np.testing.assert_array_equal(values,old)
                bounds=stats['packet_endpoints']
            else:
                values,stats=ias_trajectory(seed,times,library,epsilon)
                repeat,_=ias_trajectory(seed,times,library,epsilon)
                np.testing.assert_array_equal(values,repeat)
            np.testing.assert_array_equal(values[0],old[0])
            assert stats['packet_endpoints']==bounds and len(bounds)==112
            rows[key]=dict(**metrics(seed,times,values,expected),**stats)
            arrays[f'{eccentricity}_{key}']=values
            print(eccentricity,key,{k:v for k,v in rows[key].items() if k not in ('sampled_errors','packet_endpoints')},flush=True)
        results[str(eccentricity)]=dict(samples=len(times),methods=rows)
    arrays['times']=cached['times']
    assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in sources.items())
    assert external==library_hashes(library)
    assert hashlib.sha256(reference_path.read_bytes()).hexdigest()==hashlib.sha256(raw).hexdigest()
    np.savez_compressed(output.with_suffix('.npz'),**arrays)
    checks={f'ias15_{epsilon}':all(row['methods'][f'ias15_{epsilon}']['checks_passed'] for row in results.values())
            for epsilon in EPSILONS}
    result=dict(protocol='docs/ias15-original-grid-protocol.md',source_sha256=sources,
        npz_sha256=hashlib.sha256(output.with_suffix('.npz').read_bytes()).hexdigest(),
        reference_sha256=hashlib.sha256(raw).hexdigest(),library_files_sha256=external,
        rebound_version=VERSION,source_unchanged=True,library_unchanged=True,
        dop_control_bitexact=True,repeats_bitexact=True,identical_packet_boundaries=True,
        per_method_checks_passed=checks,checks_passed=all(checks.values()),
        results=results,runtime_modified=False,general_release_passed=False)
    with output.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print('Saved',output,'checks_passed',result['checks_passed'],flush=True)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,required=True)
    parser.add_argument('--library',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();output=args.output.resolve()
    output.parent.mkdir(parents=True,exist_ok=True)
    result=run(args.reference.resolve(),output,load_library(args.library))
    if not result['checks_passed']:
        raise SystemExit(1)


if __name__=='__main__':
    main()
