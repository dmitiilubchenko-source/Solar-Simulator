from pathlib import Path
import ast,json,subprocess,sys
R=Path(__file__).resolve().parents[2]
for p in (R/'scripts/qualification407v').glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
for p in [R/'docs/version-migration-407v.json',*(R/'scripts/qualification407v').glob('*.json')]:json.loads(p.read_bytes())
subprocess.run([sys.executable,'-X','utf8','-B','scripts/project_inventory.py','--write'],cwd=R,check=True)
sys.path.insert(0,str(R));from scripts.check_project import check_links;check_links()
subprocess.run(['git','diff','--check'],cwd=R,check=True)
print('DEV AST/JSON/inventory/file-line links/diff PASS; no full test suite')
