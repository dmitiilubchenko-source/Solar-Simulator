"""Extract one year of DE441 lunar librations with bounded HTTPS byte ranges.

Only orientation is exported, never future positions. ERFA coefficient tables
provide Vondrak precession; their full redistribution notice is retained.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

import numpy as np

if __package__:
    from .fetch_ephemerides import fetch
    from .fetch_figure_profile import decode_header, HEADER_SHA, HEADER_URL
else:
    from fetch_ephemerides import fetch
    from fetch_figure_profile import decode_header, HEADER_SHA, HEADER_URL

URL = "https://ssd.jpl.nasa.gov/ftp/eph/planets/ascii/de441/ascp02000.441"
START, END = 2461321.5, 2461686.75
STRIDE, FIRST = 26821, 2451536.5
BYTE_START, BYTE_END = 8180405, 8529077
SOURCE_SHA = {
    "range": "1699167f07cf3ec4ee5d5827b99e2ada335ccb32b5ddec939c24eb50f81a21ab",
    "ltpequ": "8b6db221ef3203e1ba9e4af96b58caeadd2e1978b8b7c6be8c49aed52aa4570f",
    "ltpecl": "13e4936ac97abe110b75cbdbbcba04c37cb6bcb59952c0f727ccabab1d55e9cf",
}


def parse_records(data, header):
    table = np.array([list(map(int, row.split())) for row in
        header.decode("ascii").split("GROUP   1050")[1].split("GROUP   1070")[0].strip().splitlines()])
    if table.shape != (3, 15) or tuple(table[:, 12]) != (899, 10, 4):
        raise ValueError("Unexpected DE441 libration layout")
    tokens = data.decode("ascii").split()
    records = []
    index = 0
    while index < len(tokens):
        number, count = map(int, tokens[index:index+2]); index += 2
        if count != 1018 or number != 306+len(records):
            raise ValueError("Unexpected DE record ID/count")
        values = np.array([float(v.replace("D", "E")) for v in tokens[index:index+count]])
        index += count
        if len(values) != count or not np.isfinite(values).all():
            raise ValueError("Truncated or nonfinite DE record")
        start, end = values[:2]
        if start != FIRST+(number-1)*32 or end-start != 32:
            raise ValueError("Unexpected DE record epoch")
        records.append(dict(start_jd_tdb=float(start), end_jd_tdb=float(end),
                            coefficients=values[898:1018].reshape(4, 3, 10).tolist()))
    if len(records) != 13 or not records[0]["start_jd_tdb"] <= START < END <= records[-1]["end_jd_tdb"]:
        raise ValueError("Incomplete one-year orientation coverage")
    return records


def erfa_tables(data, polynomial, periodic):
    text = data.decode("ascii")
    def matrix(name):
        block = re.search(r"\b"+name+r"[^=]*=\s*\{(.*?)\n\s*\};", text, re.S).group(1)
        rows = re.findall(r"\{([^}]+)\}", block)
        return [[float(v.strip()) for v in row.split(",")] for row in rows]
    return dict(polynomial=matrix(polynomial), periodic=matrix(periodic))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cached", action="store_true")
    parser.add_argument("--output", default="src/solar_simulator/data/orientation-de441-20261008.json")
    args = parser.parse_args()
    cache = Path(".tools"); cache.mkdir(exist_ok=True)
    header_path = cache/"de441-header.txt"
    header = header_path.read_bytes() if args.cached else fetch(HEADER_URL)
    if hashlib.sha256(header).hexdigest() != HEADER_SHA:
        raise ValueError("DE441 header changed")
    if not args.cached:
        header_path.write_bytes(header)
    path = cache/"de441-year-records.txt"
    if not args.cached:
        headers = cache/"de441-year.headers"
        subprocess.run(["curl.exe", "--fail", "--silent", "--show-error", "--max-time", "45",
            "--proto", "=https", "--max-filesize", "2000000", "--range", f"{BYTE_START}-{BYTE_END}",
            "--dump-header", str(headers), "--output", str(path), URL], check=True)
    response = (cache/"de441-year.headers").read_text()
    if not re.search(r"HTTP/\S+ 206", response) or f"bytes {BYTE_START}-{BYTE_END}/306161715" not in response:
        raise ValueError("Server did not return the requested bounded range")
    raw = path.read_bytes()
    if len(raw) != BYTE_END-BYTE_START+1:
        raise ValueError("Incomplete HTTP range")
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA["range"]:
        raise ValueError("Pinned DE441 orientation records changed")
    records = parse_records(raw, header)
    sources = [dict(url=HEADER_URL, sha256=HEADER_SHA),
               dict(url=URL, byte_range=[BYTE_START, BYTE_END], sha256=hashlib.sha256(raw).hexdigest())]
    tables = {}
    notice = None
    for name, poly, periodic in (("ltpequ", "xypol", "xyper"), ("ltpecl", "pqpol", "pqper")):
        url = f"https://raw.githubusercontent.com/liberfa/erfa/v2.0.1/src/{name}.c"
        path = cache/(name+".c")
        data = path.read_bytes() if args.cached else fetch(url)
        if not args.cached:
            path.write_bytes(data)
        if hashlib.sha256(data).hexdigest() != SOURCE_SHA[name]:
            raise ValueError("Pinned ERFA coefficient tables changed")
        sources.append(dict(url=url, sha256=hashlib.sha256(data).hexdigest()))
        tables[name] = erfa_tables(data, poly, periodic)
        notice = data.decode("ascii").split("/*----------------------------------------------------------------------")[1]
    constants = decode_header(header)
    profile = dict(schema_version=1, frame="Ecliptic J2000", epoch_jd_tdb=START,
        start_jd_tdb=START, end_jd_tdb=END, ephemeris="DE441",
        dataset_sha256="d58227299b10b217246aa5c63f33da51b0fd331b5c7a75bee400d577d6d1f702",
        obliquity_arcsec=84381.448, sources=sources, lunar_records=records, precession=tables,
        figures=dict(Earth=dict(j2=constants["J2E"], c22=0.0, radius_metres=1000*constants["RE"]),
                     Moon=dict(j2=constants["J2M"], c22=constants["C22M"], radius_metres=1000*constants["AM"])),
        limitation="Prescribed orientation, not self-consistent spin dynamics. Constant nominal J2/C22; no tidal deformation or higher harmonics. Earth Vondrak precession plus dominant 18.6-year nutation, small fitted DE441 frame offsets omitted.")
    output = Path(args.output)
    output.write_text(json.dumps(profile, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    notice = "\n".join(line.removeprefix("**").strip() for line in notice.splitlines()).strip().removesuffix("*/").strip()
    (output.parent/"ERFA-LICENSE.txt").write_text(notice+"\n", encoding="utf-8")
    print(output, hashlib.sha256(output.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
