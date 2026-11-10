"""Run the sealed original73 nodeids verbatim, safe POSIX JUnit paths."""
import json,subprocess,sys
from pathlib import Path
W=Path('C:/Users/Admin/Documents/Codex/Solar407-20261110');p=json.loads((W/'plan.json').read_bytes())
nodes=json.loads((W/'original73.json').read_bytes())['nodes'];assert len(nodes)==73
command=[sys.executable,'-X','utf8','-B','-m','pytest','-vv','-ra','-p','no:cacheprovider','-p','scripts.native_audit','--junitxml='+str(W/((sys.argv[1] if len(sys.argv)>1 else 'targeted73')+'.xml')).replace('\\','/'),*[r['nodeid'] for r in nodes]]
with (W/((sys.argv[1] if len(sys.argv)>1 else 'targeted73')+'-command.json')).open('x') as f:json.dump(command,f,indent=2)
subprocess.run(command,cwd=p['candidate_source'],check=True)
