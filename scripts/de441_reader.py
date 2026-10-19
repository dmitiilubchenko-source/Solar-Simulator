"""Read prescribed DE441 polynomials offline; never a simulation force or IC fit."""
from io import BytesIO
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

import numpy as np
from numpy.polynomial.chebyshev import chebder, chebval

from scripts.fetch_figure_profile import decode_header

EPOCH = 2461321.5
DAY = 86400.
DURATION = 315576000.
ARCHIVE = 'docs/de441-reader-inputs.zip'
ARCHIVE_SHA256 = 'eaf32db3d18daffc1ec7fd0193c8811b05e2cc2013f34918aca541cbb6e9ee06'
HEADER_SHA256 = '376cd6f6766356ba0f4c25dc5a7ff8130ea2826f3c34149e33c1e6ac970d6e7c'
NAMES = ('Sun', 'Mercury', 'Venus', 'Earth', 'Moon', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune')
SLOTS = (10, 0, 1, 2, 9, 3, 4, 5, 6, 7)


def ecliptic_matrix():
    angle = 84381.448*np.pi/(180*3600)
    return np.array([[1., 0., 0.], [0., np.cos(angle), np.sin(angle)], [0., -np.sin(angle), np.cos(angle)]])


def polynomial(coefficients, x, span_seconds, order=0):
    """Coefficients per row; native km, km/s, km/s² for orders0/1/2."""
    c = np.asarray(coefficients, dtype=float)
    if (c.ndim != 2 or not c.shape[1] or not np.isfinite(c).all()
            or type(order) is not int or order not in (0, 1, 2)
            or not np.isfinite(x) or not -1. <= x <= 1.
            or not np.isfinite(span_seconds) or span_seconds <= 0.):
        raise ValueError('Invalid polynomial, derivative order, time or interval')
    return chebval(x, chebder(c, m=order, axis=1).T)*(2/span_seconds)**order


class Reader:
    """Nominal seconds from EPOCH; at most ten years, no extrapolation."""

    def __init__(self, header, raw):
        self.constants = decode_header(header)
        self.layout = np.array([list(map(int, row.split())) for row in header.decode('ascii').split(
            'GROUP   1050')[1].split('GROUP   1070')[0].strip().splitlines()])
        if (self.layout.shape != (3, 15) or self.constants['EMRAT'] <= 0
                or not np.isfinite(self.constants['EMRAT'])):
            raise ValueError('Invalid DE441 coefficient index or Earth/Moon mass ratio')
        intervals = []
        for slot, (start, count, parts) in enumerate(self.layout.T):
            if count == 0 and parts == 0:
                if slot < 11:
                    raise ValueError('Required positional coefficients missing')
                continue
            components = 2 if slot == 11 else 1 if slot == 14 else 3
            end = start-1+components*count*parts
            if start < 3 or count <= 0 or parts <= 0 or end > 1018:
                raise ValueError('Invalid coefficient offset/count')
            if any(start-1 < b and end > a for a, b in intervals):
                raise ValueError('Overlapping coefficient blocks')
            intervals.append((start-1, end))
        tokens = raw.decode('ascii').split()
        if not tokens or len(tokens) % 1020:
            raise ValueError('Incomplete DE441 record')
        rows, numbers = [], []
        for offset in range(0, len(tokens), 1020):
            number, count = map(int, tokens[offset:offset+2])
            values = np.array([float(t.replace('D', 'E')) for t in tokens[offset+2:offset+1020]])
            if (count != 1018 or not np.isfinite(values).all() or values[1]-values[0] != 32.
                    or (numbers and (number != numbers[-1]+1 or values[0] != rows[-1][1]))):
                raise ValueError('Invalid record count/sequence, coefficients or epochs')
            numbers.append(number)
            rows.append(values)
        self.records = np.asarray(rows)
        self.offset_seconds = (EPOCH-self.records[0, 0])*DAY
        self.duration = min(DURATION, (self.records[-1, 1]-EPOCH)*DAY)
        if self.offset_seconds < 0 or self.duration <= 0:
            raise ValueError('Records do not cover nominal epoch')
        self.layout.setflags(write=False)
        self.records.setflags(write=False)
        self.frame = ecliptic_matrix()

    def locate(self, slot, seconds):
        if (type(slot) is not int or slot not in range(11)
                or isinstance(seconds, (bool, np.bool_)) or not isinstance(seconds, (int, float, np.integer, np.floating))
                or not np.isfinite(seconds) or not 0 <= seconds <= self.duration):
            raise ValueError('Unsupported positional slot or time outside DE441 reserve')
        elapsed = self.offset_seconds+float(seconds)
        record = min(int(elapsed//(32*DAY)), len(self.records)-1)
        local = elapsed-record*32*DAY
        _, _, parts = self.layout[:, slot]
        span = 32*DAY/int(parts)
        segment = min(int(local//span), int(parts)-1)
        x = 2*(local-segment*span)/span-1
        return record, segment, x, span

    def coefficients(self, record, slot, segment):
        if (type(record) is not int or type(slot) is not int or slot not in range(11)
                or type(segment) is not int):
            raise ValueError('Unsupported positional coefficient block')
        start, count, parts = map(int, self.layout[:, slot])
        if not 0 <= segment < parts or not 0 <= record < len(self.records):
            raise ValueError('Coefficient block outside reserve')
        first = start-1+segment*3*count
        return self.records[record, first:first+3*count].reshape(3, count)

    def component(self, slot, seconds, order=0):
        """Raw ICRF barycentre/geocentric component in km/s**order."""
        record, segment, x, span = self.locate(slot, seconds)
        return polynomial(self.coefficients(record, slot, segment), x, span, order)

    def vectors(self, seconds, order=0):
        native = np.array([self.component(slot, seconds, order) for slot in SLOTS])
        earth = native[3]-native[4]/(1+self.constants['EMRAT'])
        native[4] += earth
        native[3] = earth
        return native @ self.frame.T*1000.

    def states(self, seconds):
        return np.concatenate((self.vectors(seconds), self.vectors(seconds, 1)), axis=1)

    def relative(self, seconds, order=0):
        """Direct Moon−Earth vector in SI/EclipticJ2000, without AU subtraction."""
        return self.frame @ self.component(9, seconds, order)*1000.


def load_archive(path):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != ARCHIVE_SHA256:
        raise ValueError('DE441 input archive SHA changed')
    with ZipFile(BytesIO(raw)) as archive:
        names = archive.namelist()
        expected = {'de441-header.txt', 'de441-ten-year-records.txt', 'de-ascii-format.txt',
            'horizons-manual.html', 'provenance.json'}
        if len(names) != len(expected) or set(names) != expected:
            raise ValueError('DE441 archive inventory mismatch')
        files = {name: archive.read(name) for name in names}
    metadata = json.loads(files['provenance.json'])
    if (metadata['reserve_manifest_sha256'] != '9bb19c96de7c5be71fb97fccff39c4ea8ced1fe8100d19a294a18a91e48a5b75'
            or hashlib.sha256(files['de441-header.txt']).hexdigest() != HEADER_SHA256
            or {r['file'] for r in metadata['files']} != expected-{'provenance.json'}):
        raise ValueError('DE441 provenance/header mismatch')
    for row in metadata['files']:
        if hashlib.sha256(files[row['file']]).hexdigest() != row['sha256']:
            raise ValueError('DE441 individual source SHA mismatch')
    return Reader(files['de441-header.txt'], files['de441-ten-year-records.txt']), metadata
