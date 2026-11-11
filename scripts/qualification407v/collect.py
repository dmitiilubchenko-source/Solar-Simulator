"""Collection only: preserve3073 exact nodeids; does not run the suite."""
import os,sys,json,hashlib
from pathlib import Path
import pytest
R=Path(__file__).resolve().parents[2];S=Path('C:/Users/Admin/Desktop/Solar-candidate-040-version-407v');W=Path('C:/Users/Admin/Documents/Codex/Solar407V-20261111')
os.chdir(S);sys.path.insert(0,str(S));os.environ['SOLAR_HISTORICAL376_BUNDLE']='C:/Users/Admin/Documents/Codex/Solar407-20261110/historical376-inputs.zip'
class Inventory:
    def pytest_collection_finish(self,session):
        old=json.loads((R/'scripts/qualification407/inventory407.json').read_bytes());nodes=[x.nodeid for x in session.items]
        assert len(nodes)==len(set(nodes));missing=set(old['nodes'])-set(nodes);assert not missing,sorted(missing)
        added=sorted(set(nodes)-set(old['nodes']));assert all(x.startswith('tests/test_version407v.py::') for x in added)
        result=dict(nodes=nodes,node_count=len(nodes),old3073_preserved=len(old['nodes']),removed=[],added=added,old_inventory_SHA256=hashlib.sha256((R/'scripts/qualification407/inventory407.json').read_bytes()).hexdigest(),test_sources={p.relative_to(S).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((S/'tests').glob('*.py'))},collection_only=True)
        (W/'inventory408.json').write_text(json.dumps(result,indent=2)+'\n')
raise SystemExit(pytest.main(['--collect-only','-q','-p','no:cacheprovider','-p','scripts.native_audit'],plugins=[Inventory()]))
