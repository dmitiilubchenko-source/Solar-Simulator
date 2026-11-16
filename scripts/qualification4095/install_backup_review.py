"""Narrow optional project-scoped backup hook; legacy scanner stays unchanged."""
from pathlib import Path
import hashlib,sys
BASE=Path('C:/Users/Admin/Documents/Codex/2026-10-29/files-pasted-by-the-user-codex/outputs')
W=Path('C:/Users/Admin/Documents/Codex/Solar4095-20261116');sys.path.insert(0,str(BASE));import backup

HOOK='''def review_source(src, project):
 cfg=project.get('portable_review4095')
 if not cfg or src.name!=cfg.get('name'):return core.review(src)
 try:
  if src.resolve()!=Path(cfg['source']).resolve() or core.sha(src)!=cfg['archive_sha256']:
   return 'PORTABLE4095_SOURCE_BINDING_MISMATCH'
  reviewer=Path(cfg['reviewer']);contract=Path(cfg['contract'])
  if core.sha(reviewer)!=cfg['reviewer_sha256'] or core.sha(contract)!=cfg['contract_sha256']:
   return 'PORTABLE4095_REVIEW_BINDING_MISMATCH'
  import importlib.util
  spec=importlib.util.spec_from_file_location('pinned_portable4095_review',reviewer)
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  return module.review(src,contract,cfg['contract_sha256'],core)
 except Exception as exc:return 'PORTABLE4095_REVIEW_FAILED:'+type(exc).__name__

'''
with backup.lock():
    path=BASE/'backup.py';raw=path.read_bytes();text=raw.decode('utf8')
    assert 'def review_source(' not in text and text.count('issue=core.review(src) if not held else None')==1
    before=W/'backup-before4095.py';before.write_bytes(raw)
    text=text.replace('def prepare(args):',HOOK+'def prepare(args):').replace('issue=core.review(src) if not held else None','issue=review_source(src,p) if not held else None')
    compile(text,str(path),'exec');path.write_text(text,encoding='utf8',newline='\n')
    (W/'backup-after4095.py').write_bytes(path.read_bytes())
print('Only explicit exact-source/project/reviewer/contract opt-in added; backup_core unchanged')
