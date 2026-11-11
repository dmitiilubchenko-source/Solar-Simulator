"""Independent per-node JUnit census, preserving every original outcome."""
from pathlib import Path
import collections,csv,hashlib,json,re,xml.etree.ElementTree as ET
W=Path('C:/Users/Admin/Documents/Codex/Solar408-20261111')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    expected=json.loads((W/'test-inventory.json').read_bytes())['nodes'];keys={}
    for node in expected:
        bits=node.split('::');module=bits[0][:-3].replace('/','.');class_name='.'.join([module,*bits[1:-1]]);key=(class_name,bits[-1]);assert key not in keys;keys[key]=node
    root=ET.parse(W/'results/python.xml').getroot();observed=collections.defaultdict(list);unknown=[];raw_counts=collections.Counter();out=W/'failures';out.mkdir(exist_ok=False)
    for index,case in enumerate(root.iter('testcase')):
        key=case.get('classname'),case.get('name');node=keys.get(key)
        parts=[];status='PASS'
        for tag,label in [('failure','FAIL'),('error','ERROR'),('skipped','SKIP')]:
            for part in case.findall(tag):
                if label=='ERROR' or status=='PASS':status=label
                parts.append(dict(kind=tag,type=part.get('type'),message=part.get('message'),text=part.text or ''))
        if not node:unknown.append(dict(classname=key[0],name=key[1],status=status));continue
        raw_counts[status]+=1
        row=dict(nodeid=node,status=status,time_seconds=float(case.get('time',0)),messages=parts)
        if parts:
            raw=('\n\n'.join(p['text'] for p in parts)).encode();name=f'{index:04d}.txt';(out/name).write_bytes(raw);row.update(traceback_file='failures/'+name,traceback_SHA256=hashlib.sha256(raw).hexdigest())
        observed[node].append(row)
    outcomes=[];priority={'PASS':0,'SKIP':1,'FAIL':2,'ERROR':3};counts=collections.Counter()
    for node in expected:
        rows=observed.get(node,[]);status=max((r['status'] for r in rows),key=lambda x:priority[x]) if rows else 'MISSING';counts[status]+=1
        outcomes.append(dict(nodeid=node,status=status,xml_cases=rows))
    result=dict(counts=dict(counts),raw_JUnit_counts=dict(raw_counts),expected_nodes=len(expected),observed_unique_nodes=len(observed),raw_case_count=sum(raw_counts.values()),missing=[n for n in expected if n not in observed],unknown=unknown,duplicate_cases={n:len(v) for n,v in observed.items() if len(v)!=1},junit_SHA256=sha(W/'results/python.xml'),inventory_SHA256=sha(W/'test-inventory.json'),outcomes=outcomes)
    with (W/'python-outcomes.json').open('x',encoding='utf8',newline='\n') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    with (W/'python-outcomes.csv').open('x',encoding='utf8',newline='') as f:
        w=csv.writer(f);w.writerow(['nodeid','status','XMLcase_count','seconds','traceback_SHA256']);w.writerows((r['nodeid'],r['status'],len(r['xml_cases']),sum(x['time_seconds'] for x in r['xml_cases']),';'.join(x.get('traceback_SHA256','') for x in r['xml_cases'])) for r in outcomes)
    log=(W/'guard-full-stock/stdout.log').read_text(encoding='utf8');lines=log.splitlines();anomalies=[]
    for i,line in enumerate(lines):
        if any(s in line for s in ['invalid command name','Exception in Tkinter callback','bgerror failed','application has been destroyed']):anomalies.append(dict(log_line=i+1,context=lines[max(0,i-4):i+8]))
    (W/'stderr-anomalies.json').write_text(json.dumps(anomalies,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='outcomes'}));assert not unknown and not result['missing'],'Incomplete/foreign JUnit is not a full acceptance'
if __name__=='__main__':main()
