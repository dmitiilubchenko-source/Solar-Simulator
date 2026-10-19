"""Bounded local source reserve; never modify runtime data or query future fits."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

import numpy as np

from scripts.fetch_figure_profile import HEADER_SHA, HEADER_URL, PCK_SHA, PCK_URL, decode_header
from scripts.fetch_orientation_data import URL, SOURCE_SHA, STRIDE, FIRST
from scripts.newton_year import ROOT

FIRST_RECORD, LAST_RECORD = 306, 420
BYTE_START, BYTE_END = 8180405, 11264819
END_JD = 2464974.0  # Ten Julian years after the unchanged nominal epoch.
DOCUMENTS = {
    'Park2021-DE440-DE441.pdf': 'https://ssd.jpl.nasa.gov/doc/Park.2021.AJ.DE440.pdf',
    'Vines-EIH-Lagrangian.pdf': 'https://fiteoweb.unige.ch/~maggiore/GWVol1/EIHLagrangian.pdf',
    'horizons-api.html': 'https://ssd-api.jpl.nasa.gov/doc/horizons.html',
    'horizons-manual.html': 'https://ssd.jpl.nasa.gov/horizons/manual.html',
    'de-ascii-format.txt': 'https://ssd.jpl.nasa.gov/ftp/eph/planets/ascii/ascii_format.txt',
    'de441-tech-comments.txt': 'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de441_tech-comments.txt',
    'pck-required-reading.html': 'https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/pck.html',
}
API_FALLBACK = ('horizons-batch-instructions.txt', 'https://ssd.jpl.nasa.gov/ftp/ssd/horizons_batch.txt')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def validate_records(raw, header, previous):
    if len(raw) != BYTE_END-BYTE_START+1 or not raw.startswith(previous):
        raise ValueError('Wrong DE441 range length or changed one-year overlap')
    constants = decode_header(header)
    layout = np.array([list(map(int, row.split())) for row in header.decode('ascii').split(
        'GROUP   1050')[1].split('GROUP   1070')[0].strip().splitlines()])
    if layout.shape != (3, 15) or constants['EMRAT'] <= 0:
        raise ValueError('Unexpected DE441 index/EMRAT')
    for column, (offset, count, parts) in enumerate(layout.T):
        components = 2 if column == 11 else 3
        if count and (offset < 3 or parts < 1 or offset-1+components*count*parts > 1018):
            raise ValueError('DE441 coefficient pointer exceeds record')
    for number in range(FIRST_RECORD, LAST_RECORD+1):
        offset = (number-FIRST_RECORD)*STRIDE
        tokens = raw[offset:offset+STRIDE].decode('ascii').split()
        if len(tokens) != 1020 or tuple(map(int, tokens[:2])) != (number, 1018):
            raise ValueError('DE441 record ID/count/stride mismatch')
        values = np.array([float(x.replace('D', 'E')) for x in tokens[2:]])
        if (not np.isfinite(values).all() or values[0] != FIRST+(number-1)*32
                or values[1] != FIRST+number*32):
            raise ValueError('Nonfinite coefficients or discontinuous DE441 epoch')
    if not FIRST+(FIRST_RECORD-1)*32 <= 2461321.5 < END_JD <= FIRST+LAST_RECORD*32:
        raise ValueError('Ten-year DE441 coverage incomplete')
    return dict(records=115, coefficients_per_record=1018, interval_days=32,
        raw_start_jd_tdb=FIRST+(FIRST_RECORD-1)*32, raw_end_jd_tdb=FIRST+LAST_RECORD*32,
        intended_start_jd_tdb=2461321.5, intended_end_jd_tdb=END_JD,
        old_one_year_overlap_bytes=len(previous), old_overlap_bitexact=True,
        ephemeris='DE441', native_frame='ICRF', native_position_units='km', time_scale='TDB',
        includes_system_barycentres=True, includes_geocentric_moon=True,
        includes_lunar_librations=True, standalone_reader_qualified=False,
        simulator_ten_year_accuracy_qualified=False)


def download(path, url, byte_range=None):
    """Retain partial downloads and failure receipts; TLS stays enabled."""
    if any(p.exists() for p in (path, path.with_suffix(path.suffix+'.part'), path.with_suffix('.headers'))):
        raise FileExistsError('Preserve previous download attempt: '+str(path))
    part = path.with_suffix(path.suffix+'.part')
    headers = path.with_suffix('.headers')
    command = ['curl.exe', '--fail', '--silent', '--show-error', '--max-time', '55',
        '--proto', '=https', '--max-filesize', '10000000', '--dump-header', str(headers),
        '--output', str(part)]
    if byte_range:
        command += ['--range', f'{byte_range[0]}-{byte_range[1]}']
    command.append(url)
    process = subprocess.run(command, capture_output=True, timeout=60)
    if process.returncode:
        raise RuntimeError('Source download failed: '+process.stderr.decode(errors='replace'))
    raw = part.read_bytes()
    if not raw or len(raw) > 10_000_000:
        raise ValueError('Empty or oversized source')
    if byte_range:
        text = headers.read_text(encoding='ascii')
        if not re.search(r'HTTP/\S+ 206', text) or f'bytes {BYTE_START}-{BYTE_END}/306161715' not in text:
            raise ValueError('Server did not return exact requested DE441 range')
    if path.suffix == '.pdf' and not raw.startswith(b'%PDF-'):
        raise ValueError('Publication download is not a PDF')
    if path.suffix == '.html' and b'<html' not in raw.lower():
        raise ValueError('Documentation download is not HTML')
    part.rename(path)
    return dict(file=path.name, url=url, bytes=len(raw), sha256=sha(raw),
        fetched_utc=datetime.now(timezone.utc).isoformat(), byte_range=byte_range,
        http_headers_file=headers.name, http_headers_sha256=sha(headers.read_bytes()))


def verify_reserve(directory):
    directory = Path(directory).resolve()
    manifest = json.loads((directory/'manifest.json').read_bytes())
    if not manifest['complete'] or manifest['source_sha256'] != sha(Path(__file__).read_bytes()):
        raise ValueError('Incomplete reserve or prefetch source changed')
    names = set()
    for row in manifest['files']:
        name = row['file']
        if Path(name).name != name or name in names:
            raise ValueError('Ambiguous reserve filename')
        names.add(name)
        raw = (directory/name).read_bytes()
        if len(raw) != row['bytes'] or sha(raw) != row['sha256']:
            raise ValueError('Reserve source checksum changed: '+name)
        if row.get('http_headers_file'):
            if sha((directory/row['http_headers_file']).read_bytes()) != row['http_headers_sha256']:
                raise ValueError('HTTP range/header provenance changed')
        for part in row.get('fragments', []):
            path = (directory/part['file']).resolve()
            if not path.is_relative_to(directory) or sha(path.read_bytes()) != part['sha256']:
                raise ValueError('Resumed transfer fragment changed')
            if 'headers' in part and sha((directory/part['headers']).read_bytes()) != part['headers_sha256']:
                raise ValueError('Resumed transfer HTTP provenance changed')
    required = {*DOCUMENTS, 'de441-header.txt', 'de441-year-records.txt', 'de441-year.headers',
        'de441-ten-year-records.txt', 'pck00011.tpc', 'ltpequ.c', 'ltpecl.c', 'gm_Horizons-original.pck', 'ERFA-LICENSE.txt'}
    if API_FALLBACK[0] in names:
        required = (required-{'horizons-api.html'}) | {API_FALLBACK[0]}
        if manifest.get('missing_preferred_documents') != ['horizons-api.html']:
            raise ValueError('Official fallback must disclose missing preferred API page')
    if names != required:
        raise ValueError('Source reserve inventory differs from declared scope')
    header = (directory/'de441-header.txt').read_bytes()
    previous = (directory/'de441-year-records.txt').read_bytes()
    if sha(header) != HEADER_SHA or sha(previous) != SOURCE_SHA['range']:
        raise ValueError('Pinned DE441 predecessor changed')
    result = validate_records((directory/'de441-ten-year-records.txt').read_bytes(), header, previous)
    if result != manifest['de441_validation']:
        raise ValueError('Stored DE441 validation mismatch')
    return manifest


def resume_download(directory, name, url, byte_range):
    """Join preserved prefix with small, individually verified HTTPS ranges."""
    target = directory/name
    prefix = target.with_suffix(target.suffix+'.part')
    headers = target.with_suffix('.headers')
    attempt = directory/('resume-'+name)
    attempt.mkdir(exist_ok=False)
    if not prefix.exists() or not prefix.stat().st_size:
        row = download(attempt/name, url, byte_range)
        shutil.copy2(attempt/name, target)
        row['http_headers_file'] = (attempt/row['http_headers_file']).relative_to(directory).as_posix()
        return row
    text = headers.read_text(encoding='ascii')
    offset, last = byte_range or (0, int(re.search(r'(?im)^Content-Length:\s*(\d+)', text)[1])-1)
    whole = 306161715 if byte_range else last+1
    etag = re.search(r'(?im)^ETag:\s*(.+?)\s*$', text)
    data = bytearray(prefix.read_bytes())
    if not 0 < len(data) <= last-offset+1:
        raise ValueError('Invalid preserved prefix size')
    if byte_range and not data.startswith((directory/'de441-year-records.txt').read_bytes()):
        raise ValueError('Preserved DE441 prefix does not match pinned old records')
    fragments = [dict(file=prefix.name, sha256=sha(data), partial_response=True)]
    while offset+len(data) <= last:
        begin = offset+len(data)
        end = min(begin+262144-1, last)
        chunk = attempt/f'bytes-{begin}-{end}'
        http = chunk.with_suffix('.headers')
        command = ['curl.exe', '--fail', '--silent', '--show-error', '--connect-timeout', '10',
            '--max-time', '35', '--proto', '=https', '--max-filesize', '262144',
            '--range', f'{begin}-{end}', '--dump-header', str(http), '--output', str(chunk), url]
        process = subprocess.run(command, capture_output=True, timeout=40)
        if process.returncode:
            raise RuntimeError('Small-range retry failed: '+process.stderr.decode(errors='replace'))
        raw = chunk.read_bytes()
        response_headers = http.read_text(encoding='ascii')
        if (len(raw) != end-begin+1 or not re.search(r'HTTP/\S+ 206', response_headers)
                or f'bytes {begin}-{end}/{whole}' not in response_headers
                or (etag and etag[0] not in response_headers)):
            raise ValueError('Resume range, object ETag or size mismatch')
        fragments.append(dict(file=chunk.relative_to(directory).as_posix(), sha256=sha(raw),
            headers=http.relative_to(directory).as_posix(), headers_sha256=sha(http.read_bytes()),
            byte_range=[begin, end]))
        data.extend(raw)
        print(name, len(data), '/', last-offset+1, 'bytes recovered', flush=True)
    if target.suffix == '.pdf' and not data.startswith(b'%PDF-'):
        raise ValueError('Recovered publication is not PDF')
    with target.open('xb') as stream:
        stream.write(data)
    return dict(file=name, url=url, bytes=len(data), sha256=sha(data), byte_range=byte_range,
        fetched_utc=datetime.now(timezone.utc).isoformat(), recovered_from_timeout=True,
        http_headers_file=headers.name, http_headers_sha256=sha(headers.read_bytes()), fragments=fragments)


def run(directory, cached=False, resume=False):
    directory = Path(directory).resolve()
    if not directory.is_relative_to(ROOT/'.tools'):
        raise ValueError('Keep source reserve in project .tools')
    if cached:
        result = verify_reserve(directory)
        print('offline reserve verified:', len(result['files']), 'sources', flush=True)
        return result
    if resume:
        manifest = json.loads((directory/'manifest.json').read_bytes())
        if manifest['complete']:
            raise ValueError('Reserve already complete; use --cached')
        for row in manifest['files']:
            if sha((directory/row['file']).read_bytes()) != row['sha256']:
                raise ValueError('Existing successful source changed')
        manifest.setdefault('previous_source_sha256', []).append(manifest['source_sha256'])
        manifest['source_sha256'] = sha(Path(__file__).read_bytes())
    else:
        directory.mkdir(parents=True, exist_ok=False)
        manifest = dict(complete=False, source_sha256=sha(Path(__file__).read_bytes()), files=[], failures=[],
            purpose='Local offline source reserve, not new runtime data or accuracy qualification')
    if 'Schannel' not in subprocess.check_output(['curl.exe', '--version'], text=True):
        raise RuntimeError('Use Windows curl with normal Schannel certificate verification')

    def save():
        (directory/'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False)+'\n', encoding='utf-8')

    save()
    reused = [
        ('de441-header.txt', ROOT/'.tools/de441-header.txt', HEADER_URL, HEADER_SHA),
        ('de441-year-records.txt', ROOT/'.tools/de441-year-records.txt', URL, SOURCE_SHA['range']),
        ('de441-year.headers', ROOT/'.tools/de441-year.headers', URL, None),
        ('pck00011.tpc', ROOT/'.tools/pck00011.tpc', PCK_URL, PCK_SHA),
        ('ltpequ.c', ROOT/'.tools/ltpequ.c', 'https://raw.githubusercontent.com/liberfa/erfa/v2.0.1/src/ltpequ.c', SOURCE_SHA['ltpequ']),
        ('ltpecl.c', ROOT/'.tools/ltpecl.c', 'https://raw.githubusercontent.com/liberfa/erfa/v2.0.1/src/ltpecl.c', SOURCE_SHA['ltpecl']),
        ('gm_Horizons-original.pck', ROOT/'.tools/jpl-20261008/gm_Horizons.pck', 'https://ssd.jpl.nasa.gov/ftp/xfr/gm_Horizons.pck', None),
        ('ERFA-LICENSE.txt', ROOT/'src/solar_simulator/data/ERFA-LICENSE.txt', 'Preserved ERFA redistribution notice', None),
    ]
    for name, source, url, expected in reused:
        if resume:
            continue
        raw = source.read_bytes()
        if expected and sha(raw) != expected:
            raise ValueError('Pinned reusable source changed: '+name)
        shutil.copy2(source, directory/name)
        manifest['files'].append(dict(file=name, url=url, bytes=len(raw), sha256=sha(raw),
            reused_from=str(source), copied_utc=datetime.now(timezone.utc).isoformat()))
    save()
    jobs = [('de441-ten-year-records.txt', URL, [BYTE_START, BYTE_END]),
        *((name, url, None) for name, url in DOCUMENTS.items())]
    for name, url, byte_range in jobs:
        if any(row['file'] == name for row in manifest['files']):
            continue
        fallback = name == 'horizons-api.html' and resume
        if fallback:
            name, url = API_FALLBACK
            manifest['missing_preferred_documents'] = ['horizons-api.html']
            manifest['full_preferred_source_plan_complete'] = False
        try:
            row = (resume_download(directory, name, url, byte_range)
                if resume and not fallback else download(directory/name, url, byte_range))
            manifest['files'].append(row)
            print(name, row['bytes'], 'downloaded', flush=True)
        except Exception as error:
            manifest['failures'].append(dict(file=name, url=url, type=type(error).__name__, message=str(error)))
            print(name, type(error).__name__, str(error), flush=True)
        save()
    if len(manifest['files']) == len(reused)+len(jobs):
        manifest['de441_validation'] = validate_records((directory/'de441-ten-year-records.txt').read_bytes(),
            (directory/'de441-header.txt').read_bytes(), (directory/'de441-year-records.txt').read_bytes())
        manifest['complete'] = True
        save()
        verify_reserve(directory)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--cached', action='store_true')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if args.cached and args.resume:
        parser.error('Choose either --cached or --resume')
    if not run(args.directory, args.cached, args.resume)['complete']:
        raise RuntimeError('Source reserve incomplete; failures and partial files preserved')


if __name__ == '__main__':
    main()
