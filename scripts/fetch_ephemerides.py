"""Download a pinned geometric state matrix; never change DNS/security settings.

Requests are sequential to respect JPL's API usage policy. The simulator uses
only the resulting offline snapshot. Raw responses and GM kernel are archived
in the caller's cache; checksums record exact input files.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from math import isfinite
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request

from solar_simulator.ephemerides import EXPECTED_IDS, NAMES, SOURCE_URL, GM_URL, decode_snapshot

EPOCH = 2451544.5+(datetime(2026,10,8)-datetime(2000,1,1)).days
# Initial state plus 12 monthly-like samples ending exactly at one Julian year.
EPOCHS = [EPOCH+365.25*i/12 for i in range(13)]


def parse_result(payload, body_id, epochs):
    if type(payload) is not dict or payload.get("error"):
        raise ValueError("JPL сообщил ошибку запроса")
    signature = payload.get("signature", {})
    if type(signature) is not dict or signature.get("source") != "NASA/JPL Horizons API":
        raise ValueError("Неверная подпись источника JPL")
    if signature.get("version") != "1.2" and signature.get("version") != "1.3":
        raise ValueError("Неподдерживаемая версия API JPL; проверьте документацию")
    result = payload.get("result", "")
    if type(result) is not str:
        raise ValueError("Неверная таблица JPL")
    target = re.search(r"Target body name:.*?\((\d+)\).*?\{source:\s*([^}]+)\}", result)
    # Horizons reports the coincident Mercury/Venus barycentres as 199/299.
    accepted_ids={body_id} | ({199} if body_id==1 else {299} if body_id==2 else set())
    expected_alias="Mercury Barycenter" if body_id==1 else "Venus Barycenter"
    alias_ok=target and (int(target[1])==body_id or expected_alias in target[0])
    if not target or int(target[1]) not in accepted_ids or not alias_ok or target[2].strip() != "DE441":
        raise ValueError("Не тот объект или несогласованная эфемерида")
    required = ("Center body name: Solar System Barycenter (0)", "Output units    : KM-S", "Ecliptic of J2000.0", "GEOMETRIC cartesian states", "JDTDB")
    if any(value not in result for value in required):
        raise ValueError("Неожиданные центр, единицы или система координат в ответе JPL")
    if "$$SOE" not in result or "$$EOE" not in result:
        raise ValueError("Нет таблицы векторов JPL")
    table = result.split("$$SOE", 1)[1].split("$$EOE", 1)[0]
    records = []
    for row in csv.reader(table.strip().splitlines()):
        if len(row) != 9 or row[-1].strip():
            raise ValueError("Неверный формат CSV векторов")
        jd = float(row[0])
        values = [float(x) for x in row[2:8]]
        if not all(isfinite(x) for x in [jd]+values):
            raise ValueError("Неконечные векторы JPL")
        records.append(dict(jd_tdb=jd,position=[x*1000 for x in values[:3]],velocity=[x*1000 for x in values[3:]]))
    if len(records) != len(epochs) or any(abs(r['jd_tdb']-jd)>1e-8 for r,jd in zip(records, epochs)):
        raise ValueError("Несогласованные эпохи TDB в таблице JPL")
    return records


def gm_values(data, ids=EXPECTED_IDS):
    text = data.decode("ascii")
    values = {}
    for body_id in ids:
        match = re.search(rf"BODY{body_id}_GM\s*=\s*\(\s*([+\-0-9.eEdD]+)\s*\)", text)
        if not match:
            raise ValueError("Нет GM планетной системы в официальном ядре")
        value = float(match[1].replace("D", "E").replace("d", "e"))*1e9
        if not isfinite(value) or value <= 0:
            raise ValueError("Неверный GM")
        values[body_id] = value
    return values


def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"SolarSimulator/0.2 ephemeris research"})
    curl=shutil.which("curl.exe") if sys.platform=="win32" else None
    if curl:
        # Schannel uses Windows certificate validation; no insecure flags or
        # changes to global trust/DNS. urllib/OpenSSL can differ in chain handling.
        version=subprocess.check_output([curl,"--version"],text=True)
        if "Schannel" not in version:
            raise RuntimeError("Нужен штатный curl Windows с проверкой сертификатов Schannel")
        result=subprocess.run([curl,"--fail","--silent","--show-error","--max-time","45",
            "--proto","=https","--max-filesize","2000000",url],capture_output=True,timeout=50)
        if result.returncode:
            raise RuntimeError("Ошибка безопасной загрузки JPL: "+result.stderr.decode(errors="replace"))
        data=result.stdout
    else:
        with urllib.request.urlopen(req,timeout=45) as response:
            data=response.read(2_000_001)
    if len(data)>2_000_000:
        raise ValueError("Ответ источника слишком велик")
    return data


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache",type=Path,default=Path(".tools/jpl-20261008"))
    parser.add_argument("--output",type=Path,default=Path("src/solar_simulator/data/solar-system-20261008.json"))
    parser.add_argument("--reference",type=Path,default=Path("docs/solar-system-reference.json"))
    parser.add_argument("--cached",action="store_true",help="Only use previously saved official responses")
    args=parser.parse_args()
    args.cache.mkdir(parents=True,exist_ok=True)
    gm_file=args.cache/"gm_Horizons.pck"
    if not args.cached:
        gm_file.write_bytes(fetch(GM_URL))
    gm_data=gm_file.read_bytes();gm=gm_values(gm_data)
    trajectories=[]
    for body_id,name in zip(EXPECTED_IDS,NAMES):
        params=dict(format="json",COMMAND=f"'{body_id}'",OBJ_DATA="'NO'",MAKE_EPHEM="'YES'",
            EPHEM_TYPE="'VECTORS'",CENTER="'500@0'",TLIST="'"+" ".join(f"{jd:.12f}" for jd in EPOCHS)+"'",
            TLIST_TYPE="'JD'",REF_SYSTEM="'ICRF'",REF_PLANE="'ECLIPTIC'",VEC_CORR="'NONE'",
            VEC_TABLE="'2'",OUT_UNITS="'KM-S'",CSV_FORMAT="'YES'",TIME_TYPE="'TDB'")
        url=SOURCE_URL+"?"+urllib.parse.urlencode(params)
        file=args.cache/f"horizons-{body_id}.json"
        if not args.cached:
            file.write_bytes(fetch(url))
        raw=file.read_bytes()
        rows=parse_result(json.loads(raw),body_id,EPOCHS)
        trajectories.append(dict(id=body_id,name=name,gm_m3_s2=gm[body_id],states=rows,
                                 response_sha256=hashlib.sha256(raw).hexdigest(),request_url=url))
        print(f"Validated {name}, {len(rows)} epochs",flush=True)
    snapshot=dict(schema=1,source=SOURCE_URL,gm_source=GM_URL,gm_sha256=hashlib.sha256(gm_data).hexdigest(),
        epoch_jd_tdb=EPOCH,frame="Ecliptic J2000",center="Solar System Barycenter",ephemeris="DE441",
        units="SI",vector_correction="NONE",bodies=[dict(id=x['id'],name=x['name'],gm_m3_s2=x['gm_m3_s2'],
            position=x['states'][0]['position'],velocity=x['states'][0]['velocity']) for x in trajectories])
    data=(json.dumps(snapshot,indent=2,allow_nan=False)+'\n').encode()
    decode_snapshot(data)  # Production-format validation before writing.
    reference=dict(schema=1,generated_utc=datetime.now(timezone.utc).isoformat(),source=SOURCE_URL,
        dataset_sha256=hashlib.sha256(data).hexdigest(),frame=snapshot['frame'],center=snapshot['center'],
        ephemeris="DE441",units="SI",epochs_jd_tdb=EPOCHS,bodies=trajectories)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.reference.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_bytes(data)
    args.reference.write_text(json.dumps(reference,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(f"Offline dataset written: {args.output}")


if __name__=="__main__":
    main()
