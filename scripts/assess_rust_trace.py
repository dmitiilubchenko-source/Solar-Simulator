"""Frozen335 replay and exact-operand local roundoff analysis; research only."""
import argparse
from fractions import Fraction as F
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import struct
import subprocess
from time import perf_counter

import numpy as np

from scripts.assess_kepler_phase import ROOT
from scripts.assess_rust_adaptive import provenance, sources, validate_response

PROTOCOL='docs/rust-adaptive-trace-protocol.md'
EVIDENCE='docs/rust-adaptive-prototype-validation.json'
OLD_COMMIT='c60e1e22335d4e5faf0471f2b35e1c133bd6c44a'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bits(value):
    return struct.pack('>d',value)


def local_errors(base,h,coefficients,operands,observed_sum,result):
    """Exact identity for stored float operands, not an ODE truncation error."""
    if len(coefficients)!=len(operands) or not all(math.isfinite(x) for x in
            (base,h,observed_sum,result,*coefficients,*operands)):
        raise ValueError('Invalid local operation')
    repeated=0.
    for a,k in zip(coefficients,operands):
        repeated+=a*k
    increment=h*observed_sum
    if bits(repeated)!=bits(observed_sum) or bits(base+increment)!=bits(result):
        raise ValueError('Recorded binary64 operation does not replay exactly')
    exact=sum((F(a)*F(k) for a,k in zip(coefficients,operands)),F(0))
    dot=F(h)*(F(observed_sum)-exact)
    multiply=F(increment)-F(h)*F(observed_sum)
    addition=F(result)-F(base)-F(increment)
    total=F(result)-F(base)-F(h)*exact
    if dot+multiply+addition!=total:
        raise ValueError('Exact local error decomposition failed')
    return dict(dot=dot,multiply=multiply,addition=addition,total=total)


def coefficients():
    text=(ROOT/'rust/solar_adaptive/src/coefficients.rs').read_text()
    return b''.join(bytes.fromhex(x) for x in re.findall(r'from_bits\(0x([0-9a-f]{16})\)',text))


def analyse_trace(path,endpoints,statistics):
    maxima={group:{part:dict(position_metres=0.,velocity_m_per_s=0.)
                    for part in ('dot','multiply','addition','total')}
            for group in ('stages','accepted_update','rejected_update')}
    signed=[F(0) for _ in range(6)]
    absolute=signed.copy()
    accepted=rejected=attempts=packet=0
    current=None
    time=0.
    with Path(path).open(encoding='utf-8') as stream:
        header=json.loads(next(stream))
        if header.get('kind')!='header' or header.get('schema')!=337:
            raise ValueError('Invalid trace header')
        a,b=header['a'],header['b']
        ordered=[x for row in a for x in row]+b+header['c']+header['e3']+header['e5']
        if b''.join(bits(x) for x in ordered)!=coefficients():
            raise ValueError('Trace coefficient bits changed')
        footer=None
        for line in stream:
            row=json.loads(line)
            if row.get('kind')=='finish':
                footer=row
                if stream.read():
                    raise ValueError('Unexpected records after trace finish')
                break
            if row.get('kind')!='attempt' or packet>=len(endpoints):
                raise ValueError('Unexpected trace attempt')
            n=12
            sizes={'old':(n,), 'trial':(n,), 'update_sum':(n,), 'k':(13,n),
                   'stage_sums':(11,n), 'stages':(11,n)}
            for key,shape in sizes.items():
                array=np.asarray(row[key],dtype=float)
                if array.shape!=shape or not np.isfinite(array).all():
                    raise ValueError('Invalid trace shape/finiteness: '+key)
            if (row['time']!=time or row['packet_end']!=endpoints[packet]
                    or not time<row['next']<=row['packet_end']
                    or row['h']!=row['next']-time or not math.isfinite(row['error'])
                    or row['error']<0 or type(row['accepted']) is not bool
                    or row['accepted']!=(row['error']<1.)):
                raise ValueError('Invalid trace chronology or acceptance')
            if current is not None and b''.join(map(bits,row['old']))!=current:
                raise ValueError('Trace state changed without an accepted update')
            current=b''.join(map(bits,row['old']))
            attempts+=1
            stages=[(a[s][:s],row['stage_sums'][s-1],row['stages'][s-1],s,'stages')
                    for s in range(1,12)]
            category='accepted_update' if row['accepted'] else 'rejected_update'
            stages.append((b,row['update_sum'],row['trial'],12,category))
            for weights,sums,values,count,group in stages:
                for i in range(n):
                    losses=local_errors(row['old'][i],row['h'],weights,
                        [row['k'][j][i] for j in range(count)],sums[i],values[i])
                    if i not in (3,4,5,9,10,11):
                        continue
                    quantity='position_metres' if i<6 else 'velocity_m_per_s'
                    for part,loss in losses.items():
                        maxima[group][part][quantity]=max(maxima[group][part][quantity],float(abs(loss)))
                    if group=='accepted_update':
                        index=i-3 if i<6 else i-6
                        signed[index]+=losses['addition']
                        absolute[index]+=abs(losses['addition'])
            if row['accepted']:
                accepted+=1
                current=b''.join(map(bits,row['trial']))
                time=row['next']
                if time==row['packet_end']:
                    packet+=1
            else:
                rejected+=1
        if (footer is None or footer.get('statistics')!=statistics or packet!=len(endpoints)
                or accepted!=statistics['accepted'] or rejected!=statistics['rejected']):
            raise ValueError('Missing/inconsistent trace finish, packets or counters')
    return dict(attempts=attempts,accepted=accepted,rejected=rejected,packets=packet,
        max_abs_relative_component=maxima,
        accepted_addition_signed_component_sum=[float(x) for x in signed],
        accepted_addition_absolute_component_sum=[float(x) for x in absolute],
        units_of_sums=['m']*3+['m/s']*3,
        global_error_bound=False,all_recorded_operations_replayed_bitexact=True,
        all_local_identities_exact=True)


def run(plain,trace,output):
    plain,trace,output=map(lambda p:Path(p).resolve(),(plain,trace,output))
    if output.exists():
        raise FileExistsError('Preserve previous trace audit')
    if not output.is_relative_to((ROOT/'.tools').resolve()):
        raise ValueError('Use a fresh project .tools output')
    evidence=json.loads((ROOT/EVIDENCE).read_text(encoding='utf-8'))
    if not evidence['complete'] or evidence['checks_passed'] or evidence['production_eligible']:
        raise ValueError('Expected complete frozen335 FAIL')
    historical={}
    for name,expected in evidence['source_sha256'].items():
        if sha(ROOT/name)!=expected:
            historical[name]=subprocess.check_output(['git','show',OLD_COMMIT+':'+name],cwd=ROOT)
            if hashlib.sha256(historical[name]).hexdigest()!=expected:
                raise ValueError('Historical335 source bytes unavailable: '+name)
    archive=ROOT/evidence['sample_archive']
    if sha(archive)!=evidence['npz_sha256']:
        raise ValueError('Changed335 archive')
    with np.load(archive,allow_pickle=False) as data:
        cached={k:data[k].copy() for k in data.files}
    fingerprints=sources()
    for name in (PROTOCOL,'scripts/assess_rust_trace.py'):
        fingerprints[name]=sha(ROOT/name)
    binaries={str(p):sha(p) for p in (plain,trace)}
    inputs={EVIDENCE:sha(ROOT/EVIDENCE),evidence['sample_archive']:sha(archive)}
    snapshot=provenance(output.parent/(output.stem+'-sources'))
    report=dict(protocol=PROTOCOL,complete=False,all_modes_bitexact=False,
        runtime_modified=False,production_eligible=False,source_sha256=fingerprints,
        historical_source_commit=OLD_COMMIT,historical_sources_verified=list(historical),
        binary_sha256=binaries,input_sha256=inputs,provenance=snapshot,
        environment=dict(python=platform.python_version(),numpy=np.__version__,
            build_flags={k:os.environ.get(k) for k in ('RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS',
                'CARGO_PROFILE_RELEASE_OPT_LEVEL','CARGO_PROFILE_RELEASE_LTO','CARGO_PROFILE_RELEASE_CODEGEN_UNITS')}),
        results={})
    def save():
        output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    start=perf_counter()
    save()
    try:
        # Finish the transparency gate for ALL cases before analysing local errors.
        for name,old in evidence['results'].items():
            request=old['input_request']
            raw=json.dumps(request,allow_nan=False)
            if hashlib.sha256(raw.encode()).hexdigest()!=old['input_request_sha256']:
                raise ValueError('Serialized335 input changed: '+name)
            (output.parent/(name+'-request.json')).write_text(raw,encoding='utf-8')
            values=cached[name+'_rust']
            trace_path=output.parent/(name+'-trace.jsonl')
            modes={}
            for mode,binary,args in (('plain',plain,[]),('feature_idle',trace,[]),
                                    ('recording',trace,['--trace',str(trace_path)])):
                stamp=perf_counter()
                child=subprocess.run([str(binary),*args],input=raw,text=True,
                    capture_output=True,cwd=ROOT,timeout=120)
                seconds=perf_counter()-stamp
                (output.parent/(name+'-'+mode+'-stdout.json')).write_text(child.stdout,encoding='utf-8')
                (output.parent/(name+'-'+mode+'-stderr.txt')).write_text(child.stderr,encoding='utf-8')
                if child.returncode:
                    raise RuntimeError(f'{name}/{mode} worker exit{child.returncode}: {child.stderr}')
                response=json.loads(child.stdout)
                actual=validate_response(response,cached[name+'_times'],values[0],
                    old['baseline_statistics']['packet_endpoints'])
                if (actual.astype('>f8').tobytes()!=values.astype('>f8').tobytes()
                        or response['statistics']!=old['rust_statistics']):
                    raise ValueError('Trace changed335 numerical path: '+name+'/'+mode)
                modes[mode]=dict(bitexact=True,process_seconds=seconds)
            report['results'][name]=dict(modes=modes,original_gate_passed=old['rust']['checks_passed'],
                trace_path=trace_path.relative_to(ROOT).as_posix(),trace_sha256=sha(trace_path),
                trace_bytes=trace_path.stat().st_size)
            save()
            print(name,'all3 modes bitexact335',flush=True)
        report['all_modes_bitexact']=True
        save()
        for name,row in report['results'].items():
            old=evidence['results'][name]
            stamp=perf_counter()
            row['local_analysis']=analyse_trace(ROOT/row['trace_path'],
                old['baseline_statistics']['packet_endpoints'],old['rust_statistics'])
            row['analysis_seconds']=perf_counter()-stamp
            if sha(ROOT/row['trace_path'])!=row['trace_sha256']:
                raise ValueError('Trace changed during analysis')
            save()
            print(name,'exact local arithmetic analysed',flush=True)
        if (any(sha(ROOT/n)!=h for n,h in fingerprints.items())
                or any(sha(p)!=h for p,h in binaries.items())
                or any(sha(ROOT/n)!=h for n,h in inputs.items())):
            raise ValueError('Sources/binaries/inputs changed during audit')
        report.update(complete=True,source_unchanged=True,input_unchanged=True,
            original_passed_cases=sum(v['original_gate_passed'] for v in report['results'].values()),
            original_failed_cases=sum(not v['original_gate_passed'] for v in report['results'].values()))
    except BaseException as error:
        report['failure']=dict(type=type(error).__name__,message=str(error))
        raise
    finally:
        report['wall_seconds']=perf_counter()-start
        save()
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plain',type=Path,required=True)
    parser.add_argument('--trace',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    run(args.plain,args.trace,args.output)


if __name__=='__main__':
    main()
