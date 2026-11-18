"""Read-only independent raw snapshot checks; does not read executor PASS flags."""
from pathlib import Path
import json


def audit(root):
    records=[]
    for p in Path(root).rglob('supervisor.json'):
        r=json.loads(p.read_bytes());snap=r['post_termination_snapshots']
        pairs=[(s[k]['user_100ns'],s[k]['kernel_100ns'],s[k]['active']) for s in snap for k in ('job_before','job_after')]
        if r['complete']:
            assert r['exit_code']==0 and not r['error'] and r['final_job']['active']==0
            assert r['worker_CPU_seconds'] is not None
            assert pairs and len(set(pairs))==1
            assert all(not x['alive'] and x['job_membership_confirmed'] for x in r['processes'])
        records.append(dict(path=str(p),job=r['worker_CPU_seconds'],process_sum=sum(x['final_CPU_seconds'] for x in r['processes']),stable=bool(pairs) and len(set(pairs))==1))
    return records


if __name__=='__main__':
    import sys
    print(json.dumps(audit(sys.argv[1]),indent=2))
