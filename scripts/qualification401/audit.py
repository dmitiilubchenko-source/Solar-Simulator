"""Offline independent401 merger; no integration or accuracy-threshold changes."""
import hashlib,json
from pathlib import Path
import sys
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R));sys.path.insert(0,str(Path(__file__).parent))
from qualify import W,plan,activate,seed,lf_profile
from scripts import q2_execution398 as q
from scripts.q2_interface_recovery401 import authenticated_archive,canonical,validate_legacy_point


def main():
    import numpy as np
    p=plan();m,identity,fp=activate('candidate')
    if fp!=json.loads((W/'candidate-environment.json').read_bytes()):raise ValueError('Audit environment changed')
    recovery=json.loads((W/'recovery.json').read_bytes());delta=json.loads((W/'delta.json').read_bytes())
    _,members,archive_binding=authenticated_archive(p['archive400'])
    before={str(x.relative_to(W)):q.sha(x) for x in (W/'jobs').rglob('*') if x.is_file()}
    expected=set(p['new_jobs']);actual={x.name for x in (W/'jobs').iterdir() if x.is_dir()}
    if actual!=expected or list((W/'jobs').rglob('*.partial')):raise ValueError('Missing/foreign/partial new jobs')
    rows={};owners={}
    for job in p['recovered_jobs']:
        row=recovery['rows'][job];payload=json.loads(members[row['archive_member']]);checkpoint=json.loads(members[row['checkpoint_member']])
        expected_doc=m['storage'].to_document(seed(m,'point',payload['backend']))
        proof=validate_legacy_point(payload,checkpoint,expected_doc)
        if proof['raw_binary64_SHA256']!=row['raw_binary64_SHA256'] or q.canonical(row['provenance'])!=q.canonical(archive_binding):raise ValueError('Recovered binding changed')
        rows[job]=dict(payload=payload,checkpoint=checkpoint,counters=dict(solver_calls=delta['legacy_solver_call_proof']['solver_invocations_per_completed_legacy_point_case'],native_calls=payload['native_calls'],nfev=None,RHS=None),counter_kind='source-proven3invocations; recorded native count; historical RHS/nfev absent')
        owners[job]=dict(origin='authenticated400archive',binding=row)
    for job in p['new_jobs']:
        directory=W/'jobs'/job;receipt=q.read_envelope(directory/'complete.json');binding=receipt['binding'];role,case,backend=job.split('__')
        if binding['job']!=job or binding['source']['commit']!=p[role] or binding['plan_SHA256']!=q.sha(W/'plan.json') or binding['tool_manifest_SHA256']!=q.sha(W/'tools-v3.json') or binding['epochs_seconds']!=[0.,2.,4.]:raise ValueError('Wrong new job ownership')
        if binding['driver_SHA256']!=q.sha(Path(__file__).with_name('qualify.py')) or binding['adapter_SHA256']!=q.sha(R/'scripts/q2_interface_recovery401.py'):raise ValueError('Changed executor/adapter')
        if set(x.name for x in directory.iterdir())!={'started.json','payload.json','checkpoint.json','counters.json','complete.json'}:raise ValueError('Unowned job file')
        for name,meta in receipt['files'].items():
            raw=(directory/name).read_bytes()
            if len(raw)!=meta['size'] or hashlib.sha256(raw).hexdigest()!=meta['sha256']:raise ValueError('New payload SHA mismatch')
        if q.read_envelope(directory/'started.json')!=binding:raise ValueError('Started binding changed')
        payload=json.loads((directory/'payload.json').read_bytes());checkpoint=json.loads((directory/'checkpoint.json').read_bytes());count=json.loads((directory/'counters.json').read_bytes())
        initial=m['storage'].to_document(seed(m,case,backend))
        if canonical(payload['documents'][0])!=canonical(initial) or binding['initial_SHA256']!=hashlib.sha256(canonical(initial)).hexdigest():raise ValueError('Wrong actual IC/settings')
        if checkpoint!=payload['documents'][1] or payload['epochs_seconds']!=[0.,2.,4.] or not payload['resume_exact']:raise ValueError('Checkpoint/epoch mismatch')
        if count['solver_calls']!=3 or count['RHS']!=count['nfev'] or count['native_calls']!=payload['native_calls'] or count['native_calls']!=(count['RHS'] if backend=='rust' else 0):raise ValueError('Counter contract mismatch')
        rows[job]=dict(payload=payload,checkpoint=checkpoint,counters=count,counter_kind='measured401instrumentation');owners[job]=dict(origin='new401run',complete_SHA256=q.sha(directory/'complete.json'),binding=binding)
    def arrays(documents):
        T=len(documents);N=len(documents[0]['bodies']);K=len(documents[0].get('rotations',[]))
        return {name:np.asarray(values,dtype='<f8').reshape(shape) for name,values,shape in [
            ('p',[[b['position'] for b in d['bodies']] for d in documents],(T,N,3)),
            ('v',[[b['velocity'] for b in d['bodies']] for d in documents],(T,N,3)),
            ('q',[[r['quaternion'] for r in d.get('rotations',[])] for d in documents],(T,K,4)),
            ('S',[[r['angular_momentum'] for r in d.get('rotations',[])] for d in documents],(T,K,3))]}
    pairs=[]
    for case in ('point','one','two'):
        for backend in ('python','rust'):
            a=rows['base__'+case+'__'+backend];b=rows['candidate__'+case+'__'+backend]
            aa=arrays(a['payload']['documents']);bb=arrays(b['payload']['documents'])
            if not all(np.isfinite(x).all() and x.shape==bb[k].shape and x.tobytes()==bb[k].tobytes() for k,x in aa.items()):raise ValueError('Exact raw binary64 source mismatch')
            if canonical(a['payload'])!=canonical(b['payload']) or canonical(a['checkpoint'])!=canonical(b['checkpoint']):raise ValueError('Payload/checkpoint source mismatch')
            for key in ('solver_calls','native_calls'):
                if a['counters'][key]!=b['counters'][key]:raise ValueError('Common solver/native counter mismatch')
            if case!='point' and canonical(a['counters'])!=canonical(b['counters']):raise ValueError('Measured full solver counters mismatch')
            diagnostics=[]
            for da,db in zip(a['payload']['documents'],b['payload']['documents']):
                sa=m['storage'].from_document(da);sb=m['storage'].from_document(db)
                ra=m['cli'].report(sa);rb=m['cli'].report(sb)
                if canonical(ra)!=canonical(rb):raise ValueError('Numerical diagnostics differ')
                diagnostics.append(ra)
            pairs.append(dict(case=case,backend=backend,exact_p_v_q_S=True,full_payload_exact=True,checkpoint_exact=True,same_packet_restart_exact=True,
                dimensions={k:list(v.shape) for k,v in aa.items()},common_counters_equal=True,base_counters=a['counters'],candidate_counters=b['counters'],base_counter_kind=a['counter_kind'],
                historical_RHS_nfev_comparison='UNRECORDED_NOT_INVENTED' if case=='point' else 'MEASURED_EXACT',numerical_diagnostics=diagnostics))
    if before!={str(x.relative_to(W)):q.sha(x) for x in (W/'jobs').rglob('*') if x.is_file()}:raise ValueError('Audit changed original results')
    q.atomic_json(W/'independent-audit.json',dict(status='PASS_EXACT_SIX_STATE_CONTRASTS_AND_KNOWN_COUNTER_CONTRACT',pairs=pairs,owners=owners,
        legacy_counters_limitation='Historical nfev/RHS not recorded;3solver invocations are a static source proof, not labelled measured. No claim about unrecorded internal steps.',
        recovered_cases=2,new_cases=10,source_arrays_and_checkpoints_unchanged=True,integrations_in_this_audit=0,
        presentation_delta=delta['status'],candidate_environment_LF_SHA256=lf_profile(fp),application_A_D1_approved=False,release_readiness='NO-GO'))
    print('PASS independent offline merger:2authenticated old+10new,6exact contrasts, counter provenance separated; no integrations',flush=True)


if __name__=='__main__':main()
