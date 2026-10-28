"""Compare complete pre380 zero/one-figure documents/reports, without writes."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile
from scripts.two_q2_fixture380 import fixture
from solar_simulator.experiment import create_experiment,preset,advance
from solar_simulator.application_profiles import lunar_rotation
from solar_simulator.storage import to_document
from solar_simulator.cli import report
from solar_simulator.inspection import report as explain

ROOT=Path(__file__).resolve().parents[1]


def check():
    cases={}
    for backend in ('python','rust'):
        for method in ('verlet','dop853'):
            state=preset('sun-earth',backend=backend)
            cases['points-'+backend+'-'+method]=replace(state,settings=replace(state.settings,integrator=method,dt=60.))
        b,r,s=fixture(backend=backend)
        cases['single-'+backend]=create_experiment(b,s,rotations=r[:1])
        state=lunar_rotation()
        cases['lunar-'+backend]=replace(state,settings=replace(state.settings,backend=backend,dt=50.))
    results={}
    for name,state in cases.items():
        states=[]
        for count in (0,1,2):
            if count:state=advance(state,count)
            states.append(dict(document=to_document(state),report=report(state),explanation=explain(state)))
        results[name]=states
    with ZipFile(ROOT/'scripts/validation/two-q2-380-compatibility.zip') as archive:baseline=archive.read('baseline.json')
    assert hashlib.sha256(baseline).hexdigest()=='01f383c0e091acc859063b9661317f5ebae0c6aa7d21eccd32f3505b39b581c9'
    current=json.dumps(results,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf8')
    assert current==baseline,'Pre380 canonical states/reports differ; environment-specific numerical check, not portable equivalence theorem'
    return dict(cases=len(cases),snapshots=sum(map(len,results.values())),byte_exact=True)


if __name__=='__main__':print(check())
