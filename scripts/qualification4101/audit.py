"""Independent read-only recalculation from raw receipts, never launches workers."""
from pathlib import Path
import hashlib,json,subprocess,sys,time
import psutil

R=Path(__file__).resolve().parents[2];W=Path('C:/Users/Admin/Documents/Codex/Solar4101-20261117')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_bytes())


def run():
    cases=[];survivors=[];cpu=wall=0;peak=0;CPU_discrepancies=[]
    for suite in [W/'suite.json',*(W/f'attempt{i}/suite.json' for i in (2,3,4))]:
        data=read(suite);cpu+=data['worker_CPU_seconds']+data['parent_CPU_seconds']+1 # missing write receipt conservative allowance
        wall+=data['wall_seconds']
        for result in data['results']:
            rec=result['record'];folder=suite.parent/result['name']
            if rec:
                assert rec==read(folder/'guard/supervisor.json')
                peak=max(peak,rec['peak_private_tree_sampled'])
                if rec['complete']:
                    assert rec['exit_code']==0 and rec['final_job']['active']==0 and rec['worker_CPU_seconds'] is not None and not rec['error']
                if suite.parent.name=='attempt4':
                    assert rec['final_job']['active']==0
                    retained=sum(x['final_CPU_seconds'] for x in rec['processes'])
                    if rec['worker_CPU_seconds']<retained:
                        CPU_discrepancies.append(dict(case=result['name'],job_CPU=rec['worker_CPU_seconds'],retained_CPU=retained,difference=retained-rec['worker_CPU_seconds'],status='UNRESOLVED; no acceptance tolerance introduced'))
            for pidfile in folder.glob('*.pid.json'):
                p=read(pidfile)
                try:
                    q=psutil.Process(p['pid'])
                    if q.create_time()==p['creation_time'] and q.is_running():survivors.append(p)
                except psutil.NoSuchProcess:pass
            cases.append(dict(attempt=suite.parent.name,case=result['name'],executor_contract=result['contract_check'],record_sha=sha(folder/'guard/supervisor.json') if rec else None))
    assert not survivors
    old=read(W/'attempt4/old-false-complete/original-monitor/supervisor.json');false=read(W/'attempt4/old-false-complete/old-false-complete.json')
    assert old['complete'] and false['complete'] and false['live']
    baseline='ebde749d11405c0fdeca640d9d515be6db61a59b'
    for p in ['src','rust','pyproject.toml','scripts/qualification409','scripts/qualification410','scripts/qualification4095']:
        assert not subprocess.check_output(['git','-C',str(R),'diff',baseline,'--',p])
    archive=Path('C:/Users/Admin/Documents/Codex/Solar4095-20261116/SolarSimulator-0.4.0-20261116-4095.zip')
    assert sha(archive)=='33114f5ac2234e01e1e248fae757187a50a81020e2b225ee6b746e28e1073e33'
    # Independent ledger: each job kernel total ONCE plus parent; never sum handles again.
    resource=dict(synthetic_CPU_including_four_missing_receipt_allowances=cpu,synthetic_wall=wall,review_CPU_allowance=15,review_wall_allowance=30,final_CPU_allowance=10,final_wall_allowance=20,backup_CPU_reserved=20,backup_wall_reserved=40,charged_CPU_with_backup_reserve=cpu+45,charged_wall_with_backup_reserve=wall+90,peak_fixture_private_sampled=peak,CPU_fully_measured=False,all_stage_private_peak=None,connector_remote_CPU=None,missing_write_receipt_allowance_each=1)
    assert resource['charged_CPU_with_backup_reserve']<96 and resource['charged_wall_with_backup_reserve']<240
    result=dict(status='PARTIAL_NO_GO',raw_suites=4,probes=cases,last_suite_expected_outcomes=20,old_false_complete_reproduced=True,all_recorded_fixture_processes_gone=True,CPU_discrepancies=CPU_discrepancies,job_CPU_not_double_counted=True,runtime_and_frozen_paths_unchanged=True,portable_SHA256=sha(archive),old_monitor_SHA256=sha('C:/Users/Admin/Desktop/Solar-simulator/scripts/qualification409/monitor200.py'),new_monitor_SHA256=sha(R/'scripts/qualification4101/monitor.py'),resources=resource,unresolved=['Final CPU reconciliation failed for short-parent; no new tolerance or repeat to seek PASS. Investigate kernel accounting finalization/tick resolution independently before admission.','Native CreateProcess launcher is a changed launch path; no stdout capture or explicit sanitized environment block yet; existing acceptance wrappers/parsers have NOT been changed or qualified.','Probes13/14/15/19 do not fully demonstrate deterministic cleanup/discovery/PIDreuse/repeated termination races; injected exceptions are narrower evidence.','Actual unrelated-process survival, abrupt supervisor loss, cleanup failure, missing receipts/finalCPU negative consumer controls still need qualification.','No exhaustive individual process lifecycle log for processes between samples; group CPU and individual process CPU have an observed unresolved discrepancy.','Assign/nested job/breakaway and host policy compatibility not comprehensively qualified.'])
    with (W/'independent-audit.json').open('x',encoding='utf8') as f:json.dump(result,f,indent=2)
    print(json.dumps({k:result[k] for k in ['status','old_false_complete_reproduced','all_recorded_fixture_processes_gone','resources']}))


if __name__=='__main__':run()
