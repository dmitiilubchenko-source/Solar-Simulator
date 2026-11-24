"""Public documentary view only; original evidence and numerical values unchanged."""
from pathlib import Path
import re,json,hashlib,csv,io,base64
PROFILE=re.compile(r"C:[\\/]+Users[\\/]+Admin",re.I)
def digest(b):return hashlib.sha256(b).hexdigest()
def numbers(x):
 if isinstance(x,dict):return [v for t in x.values() for v in numbers(t)]
 if isinstance(x,list):return [v for t in x for v in numbers(t)]
 return [x.hex() if isinstance(x,float) else x] if isinstance(x,(float,int)) else []
def export_public(root):
 root=Path(root);changes={};planned=[]
 for p in sorted(root.rglob("*")):
  if not p.is_file() or p.suffix not in {".json",".md",".txt",".py",".cfg",".csv",".pth"}:continue
  rel=p.relative_to(root);raw=p.read_bytes()
  try:text=raw.decode("utf8")
  except UnicodeError:continue
  if not PROFILE.search(text):continue
  sbom="sboms" in rel.parts and rel.suffix==".json"
  if rel.parts[0]=="verification" or rel.parts[0]=="runtime" and not sbom:
   raise ValueError("Do not rewrite qualified scientific/runtime source: "+str(rel))
  new=PROFILE.sub("local-profile:",text).encode("utf8")
  if p.suffix==".json":assert numbers(json.loads(raw))==numbers(json.loads(new))
  changes[rel.as_posix()]=dict(original_SHA256=digest(raw),public_SHA256=digest(new),numeric_values_unchanged=True)
  planned.append((p,new))
 for p,new in planned:p.write_bytes(new)
 # Keep installed wheel RECORD internally consistent after public SBOM metadata export.
 for record in root.glob("runtime/Lib/site-packages/*.dist-info/RECORD"):
  rows=list(csv.reader(io.StringIO(record.read_text(encoding="utf8"))));touched=False
  for row in rows:
   full=record.parent.parent/row[0]
   if full.is_file() and full.relative_to(root).as_posix() in changes:
    raw=full.read_bytes();row[1]="sha256="+base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).decode().rstrip("=");row[2]=str(len(raw));touched=True
  if touched:
   with record.open("w",encoding="utf8",newline="") as f:csv.writer(f,lineterminator="\n").writerows(rows)
 result=dict(kind="public_documentary_export419",original_evidence_modified=False,files=changes,
 scope="Derived metadata views; exact historical originals remain in source/418archive. Numericalvalues, hashesinside scientificrecords, criteria and verification unchanged.")
 (root/"PUBLIC-DOCUMENT-EXPORT-419.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
 return result
