"""One fresh cloud object, streamed to NEW local bytes; URL never persisted."""
import hashlib,json,os,sys,time,urllib.request
from pathlib import Path
W=Path('C:/Users/Admin/Documents/Codex/Solar409-20261111');ref=json.loads(os.environ.pop('SOLAR409_REF'));row=ref['expected'];label=ref['label'];out=W/'downloads';out.mkdir(exist_ok=True);path=out/(label+'.partial');h=hashlib.sha256();size=0;start=time.time();headers=None;failure=None
try:
 if (out/(label+'.bin')).exists() or path.exists():raise FileExistsError('Never overwrite a completed or partial readback')
 if not ref['url'].startswith('https://'):raise ValueError('HTTPS required')
 with path.open('xb') as f:
  with urllib.request.urlopen(ref['url'],timeout=300) as response:
   headers=dict(status=response.status,content_length=response.headers.get('Content-Length'),content_type=response.headers.get('Content-Type'))
   if response.status!=200:raise ValueError('Unexpected HTTP response status')
   for block in iter(lambda:response.read(64*1024),b''):
    size+=len(block);h.update(block);f.write(block);f.flush()
    if size>row['size']:raise ValueError('Cloud object exceeds pinned size')
  os.fsync(f.fileno())
 if size!=row['size'] or h.hexdigest()!=row['sha256']:raise ValueError('Cloud SHA256/size mismatch; preserve actual downloaded bytes')
 path.rename(out/(label+'.bin'));status='VERIFIED_SHA256_SIZE'
except BaseException as exc:
 status='FAILED_READBACK';failure=dict(type=type(exc).__name__,message=str(exc) if 'http' not in str(exc).lower() else 'HTTP/network failure; signed URL omitted')
finally:
 record=dict(label=label,id=row['id'],name=row['name'],expected_SHA256=row['sha256'],expected_size=row['size'],actual_SHA256=h.hexdigest(),actual_size=size,status=status,start_timestamp=start,end_timestamp=time.time(),response=headers,failure=failure,source='Independent HTTPS cloud bytes via freshconnectorreference; no localpart fallback')
 with (out/(label+'-completion.json')).open('x',encoding='utf8',newline='\n') as f:json.dump(record,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 print(json.dumps(record),flush=True)
raise SystemExit(0 if status=='VERIFIED_SHA256_SIZE' else 1)
