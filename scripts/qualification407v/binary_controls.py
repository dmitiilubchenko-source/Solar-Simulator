"""Fixed tiny binary contract, run independently under old/new qualified prefixes."""
from pathlib import Path
import json,sys
import solar_native as n
from solar_simulator.simulation import sun_earth
from scripts.two_q2_fixture380 import fixture
from solar_simulator.experiment import create_experiment,advance
from solar_simulator.storage import to_document
b,p=sun_earth(.6);m=[x.mass for x in b];r=[[x.position.x,x.position.y,x.position.z] for x in b];v=[[x.velocity.x,x.velocity.y,x.velocity.z] for x in b]
result=dict(newton=n.point_acceleration(m,r,v),EIH=n.point_acceleration(m,r,v,299792458.),verlet=n.evolve(m,r,v,p/4000,100),diagnostics=n.diagnostics(m,r,v))
b,q,s=fixture(backend='rust');result['twoQ2_short_document']=to_document(advance(create_experiment(b,s,rotations=q),2))
Path(sys.argv[1]).write_text(json.dumps(result,allow_nan=False,sort_keys=True)+'\n')
