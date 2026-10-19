"""Offline metrology of acceleration derivatives, exact seams and smooth changes."""
import argparse
from decimal import localcontext
import json
from pathlib import Path
import sys
from time import perf_counter
from zipfile import ZipFile

import numpy as np

from scripts import assess_lunar_inertia_field as field
from scripts import de441_power as power
from scripts import de441_reader as de
from scripts.newton_year import ROOT, hashes

PROTOCOL='docs/de441-acceleration-protocol.md'
TESTS='tests/test_de441_acceleration.py'
NAMES=(*de.NAMES,'MoonMinusEarth')
STEPS=np.array([1.,.1,.01,.001])
KINDS=('binary_precision','raw_precision','reader_binary','raw_binary')


def previous(path):
    path=Path(path).resolve();receipt=json.loads(path.read_bytes())
    if not receipt.get('complete') or not receipt.get('checks_passed') or receipt.get('preflight'):
        raise ValueError('Complete full-year force evidence required')
    for group in ('source_sha256','input_sha256'):
        if hashes(receipt[group])!=receipt[group]:raise ValueError('Frozen force source/input changed')
    if hashes([path.with_suffix('.npz')]).popitem()[1]!=receipt['npz_sha256']:
        raise ValueError('Force NPZ SHA differs')
    with np.load(path.with_suffix('.npz'),allow_pickle=False) as data:arrays={k:data[k] for k in data.files}
    if not field.qualification(arrays,receipt['arithmetic'],field.TIMES):
        raise ValueError('Raw force evidence does not meet original protocol')
    return receipt,arrays


def qualification(arrays,times,seams):
    n,m=len(times),len(seams)
    shapes=dict(times=(n,),seam_times=(m,),steps=(4,),reader_acceleration=(n,11,3),
        binary_acceleration=(n,11,3),raw_acceleration=(n,11,3),
        absolute_errors=(n,4,11),relative_errors=(n,4,11),
        seam_limits=(m,2,3,11,3),seam_jumps=(m,3,11,3),raw_seam_jumps=(m,3,11,3),
        actual_offsets=(m,4,2),smooth=(m,4,11,3),total_difference=(m,4,11,3),
        identity_errors=(m,4,11),finite_difference_errors=(m,4,11),negative_signals=(m,4,2,11),
        model_branch_defects=(m,4,2,11,3),branch_identity_errors=(m,4,11))
    if set(arrays)!=set(shapes) or any(np.shape(arrays[k])!=v or not np.isfinite(arrays[k]).all() for k,v in shapes.items()):
        return False
    if not np.array_equal(arrays['times'],times) or not np.array_equal(arrays['seam_times'],seams) or not np.array_equal(arrays['steps'],STEPS):
        return False
    absolute,relative=arrays['absolute_errors'],arrays['relative_errors']
    jumps=np.linalg.norm(arrays['seam_jumps'],axis=-1)
    return bool(n>0 and m>0 and np.all(absolute>=0) and np.all(relative>=0)
        and np.all(relative[:,:2]<1e-50) and np.all(absolute[:,2]<1e-15)
        and np.all(relative[:,2]<5e-13)
        and np.all(jumps < np.array([.01,1e-7,1e-9])[None,:,None])
        and np.all(arrays['identity_errors']>=0) and np.all(arrays['identity_errors']<1e-50)
        and np.all(arrays['finite_difference_errors']>=0) and np.all(arrays['finite_difference_errors']<2e-15)
        and np.all(arrays['branch_identity_errors']>=0) and np.all(arrays['branch_identity_errors']<2e-15)
        and np.all(arrays['negative_signals']>=0) and np.all(arrays['negative_signals'].max(axis=(0,1,3))>1e-3))


def metrics(arrays):
    result=dict(errors={},seams={},branches={})
    for k,name in enumerate(KINDS):
        result['errors'][name]=dict(absolute_maximum_per_body=dict(zip(NAMES,map(float,arrays['absolute_errors'][:,k].max(axis=0)))),
            relative_maximum_per_body=dict(zip(NAMES,map(float,arrays['relative_errors'][:,k].max(axis=0)))))
    jumps=np.linalg.norm(arrays['seam_jumps'],axis=-1)
    for order in range(3):
        result['seams'][str(order)]={name:dict(maximum_SI=float(jumps[:,order,i].max()),
            worst_seconds=float(arrays['seam_times'][jumps[:,order,i].argmax()])) for i,name in enumerate(NAMES)}
    for k,name in enumerate(field.CASES):
        result['branches'][name]={side:dict(maximum_relative_m_per_s2=float(np.linalg.norm(arrays['model_branch_defects'][:,k,j,-1],axis=1).max()),
            rms_relative_m_per_s2=float(np.sqrt(np.mean(np.sum(arrays['model_branch_defects'][:,k,j,-1]**2,axis=1)))))
            for j,side in enumerate(('left','right'))}
    result['maximum_identity_m_per_s2']=float(arrays['identity_errors'].max())
    result['maximum_float_difference_error_m_per_s2']=float(arrays['finite_difference_errors'].max())
    result['maximum_branch_identity_m_per_s2']=float(arrays['branch_identity_errors'].max())
    result['negative_controls_maximum']=arrays['negative_signals'].max(axis=(0,1,3)).tolist()
    result['steps']=[dict(seconds=float(h),max_relative_total_m_per_s2=float(np.linalg.norm(arrays['total_difference'][:,i,-1],axis=1).max()),
        max_relative_smooth_m_per_s2=float(np.linalg.norm(arrays['smooth'][:,i,-1],axis=1).max()),
        actual_minimum_offset_s=float(arrays['actual_offsets'][:,i].min()),
        actual_maximum_offset_s=float(arrays['actual_offsets'][:,i].max())) for i,h in enumerate(STEPS)]
    return result


def run(output,force_receipt,preflight=False):
    output=Path(output).resolve()
    if (not output.is_relative_to(ROOT/'.tools') or any(output.with_suffix(s).exists() for s in ('.json','.npz'))):
        raise ValueError('Fresh project .tools output required; preserve failures')
    _,old=previous(force_receipt)
    reader,_=de.load_archive(ROOT/de.ARCHIVE)
    with ZipFile(ROOT/de.ARCHIVE) as archive:raw=archive.read('de441-ten-year-records.txt')
    oracles=[power.Oracle(reader,raw,precision,binary) for binary in (True,False) for precision in (70,90)]
    all_seams=oracles[0].seams(field.TIMES[-1]);seams=all_seams[[0,len(all_seams)//2,-1]] if preflight else all_seams
    times=field.TIMES[field.PREFLIGHT] if preflight else field.TIMES.copy()
    n,m=len(times),len(seams)
    arrays=dict(times=times,seam_times=seams,steps=STEPS.copy(),reader_acceleration=np.empty((n,11,3)),
        binary_acceleration=np.empty((n,11,3)),raw_acceleration=np.empty((n,11,3)),
        absolute_errors=np.empty((n,4,11)),relative_errors=np.empty((n,4,11)),
        seam_limits=np.empty((m,2,3,11,3)),seam_jumps=np.empty((m,3,11,3)),raw_seam_jumps=np.empty((m,3,11,3)),
        actual_offsets=np.empty((m,4,2)),smooth=np.empty((m,4,11,3)),total_difference=np.empty((m,4,11,3)),
        identity_errors=np.empty((m,4,11)),finite_difference_errors=np.empty((m,4,11)),
        negative_signals=np.empty((m,4,2,11)),model_branch_defects=np.empty((m,4,2,11,3)),branch_identity_errors=np.empty((m,4,11)))
    sources={str(Path(module.__file__).resolve().relative_to(ROOT)) for module in tuple(sys.modules.values())
        if getattr(module,'__file__',None) and str(module.__file__).endswith('.py')
        and Path(module.__file__).resolve().is_relative_to(ROOT)
        and Path(module.__file__).resolve().parts[len(ROOT.parts)] in ('scripts','src')}
    sources=hashes(sorted(sources|{PROTOCOL,TESTS}))
    inputs=hashes([force_receipt,Path(force_receipt).with_suffix('.npz'),de.ARCHIVE])
    report=dict(complete=False,checks_passed=False,preflight=bool(preflight),source_sha256=sources,input_sha256=inputs,
        protocol=PROTOCOL,samples=n,seams=m,all_year_seams=len(all_seams),names=list(NAMES),units='SI',frame='Ecliptic J2000',
        center='SSB',epoch_jd_tdb=de.EPOCH,precision_digits=[70,90],
        coefficient_only_decimal_rounding_audited=True,frame_and_emrat_held_binary64=True,
        propagation_performed=False,runtime_modified=False,parameters_fitted=False,network_used=False,
        true_astronomical_acceleration_certified=False,real_orbit_error_cause_attributed=False,
        source_branch_selected_by_smallest_residual=False)
    output.parent.mkdir(parents=True,exist_ok=True);start=perf_counter()
    def save():output.with_suffix('.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf8')
    save()
    try:
        for i,t in enumerate(times):
            t=float(t);actual=np.vstack((reader.vectors(t,2),reader.relative(t,2)))
            b70,b90,r70,r90=[oracle.evaluate(t)[0] for oracle in oracles]
            arrays['reader_acceleration'][i]=actual
            arrays['binary_acceleration'][i]=np.asarray(b90,dtype=float)
            arrays['raw_acceleration'][i]=np.asarray(r90,dtype=float)
            for k,(a,b) in enumerate(((b70,b90),(r70,r90),(actual,b90),(r90,b90))):
                arrays['absolute_errors'][i,k],arrays['relative_errors'][i,k]=power.errors(a,b)
        for i,t in enumerate(seams):
            t=float(t);left,right=[oracles[1].evaluate(t,side,orders=(0,1,2)) for side in ('left','right')]
            raw_left,raw_right=[oracles[3].evaluate(t,side,orders=(0,1,2)) for side in ('left','right')]
            with localcontext() as context:
                context.prec=90
                jump=right-left
                arrays['seam_jumps'][i]=np.asarray(jump,dtype=float)
                arrays['raw_seam_jumps'][i]=np.asarray(raw_right-raw_left,dtype=float)
            arrays['seam_limits'][i]=np.asarray([left,right],dtype=float)
            for j,h in enumerate(STEPS):
                before,after=oracles[1].evaluate(t-float(h))[0],oracles[1].evaluate(t+float(h))[0]
                _,smooth,total,identity,missing=power.split_difference(left[2],right[2],before,after)
                arrays['actual_offsets'][i,j]=[t-(t-float(h)),t+float(h)-t]
                arrays['smooth'][i,j],arrays['total_difference'][i,j]=np.asarray(smooth,dtype=float),np.asarray(total,dtype=float)
                arrays['identity_errors'][i,j]=np.linalg.norm(np.asarray(identity,dtype=float),axis=1)
                a=np.vstack((reader.vectors(t+float(h),2),reader.relative(t+float(h),2)))
                b=np.vstack((reader.vectors(t-float(h),2),reader.relative(t-float(h),2)))
                arrays['finite_difference_errors'][i,j]=power.errors(a-b,total)[0]
                arrays['negative_signals'][i,j]=[missing,2*missing]
            index=int(np.searchsorted(field.TIMES,t))
            if field.TIMES[index]!=t:raise ValueError('Force evidence does not contain exact seam epoch')
            for k,name in enumerate(field.CASES):
                force=old['model_'+name][index]
                force=np.vstack((force,force[4]-force[3]))
                for j,reference in enumerate((left,right)):
                    arrays['model_branch_defects'][i,k,j]=force-np.asarray(reference[2],dtype=float)
                a=arrays['model_branch_defects'][i,k]
                arrays['branch_identity_errors'][i,k]=np.linalg.norm(a[1]-a[0]+np.asarray(jump[2],dtype=float),axis=1)
        if hashes(sources)!=sources or hashes(inputs)!=inputs:raise ValueError('Frozen source/input changed')
        report.update(complete=True,checks_passed=qualification(arrays,times,seams),measurements=metrics(arrays))
    except BaseException as error:
        report['failure']=dict(type=type(error).__name__,message=str(error));raise
    finally:
        np.savez_compressed(output.with_suffix('.npz'),**arrays)
        report['npz_sha256']=hashes([output.with_suffix('.npz')]).popitem()[1]
        report['wall_seconds']=perf_counter()-start;save()
    print('DE441 acceleration',n,'epochs',m,'seams passed',report['checks_passed'],'seconds',report['wall_seconds'],flush=True)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--force-receipt',type=Path,required=True)
    parser.add_argument('--preflight',action='store_true')
    args=parser.parse_args()
    if not run(args.output,args.force_receipt,args.preflight)['checks_passed']:
        raise RuntimeError('Acceleration protocol failed; evidence retained')


if __name__=='__main__':main()
