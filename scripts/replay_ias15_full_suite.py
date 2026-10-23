"""Replay all nine full-state experiments offline; no optional C library."""
import argparse
import base64
import json
from pathlib import Path
import struct

import numpy as np

from scripts.assess_ias15 import metrics
from scripts.assess_ias15_restart import load_cases
from scripts.assess_ias15_full_suite import CASES, totals, check_baseline
from scripts.ias15_full_state import parse, numeric_fields, sha, PREFIX, BUFFERS, DP7, SCALARS, FullSnapshot
from scripts.ias15_restart import restore, bits
from scripts.kepler_transport import ROOT
from solar_simulator.simulation import G

REPORT = 'docs/ias15-full-suite-validation.json'
ARRAYS = 'docs/ias15-full-suite-samples.npz'


def validate_report(report):
    if (not report['complete'] or report['runtime_modified'] or report['production_eligible']
            or report['protocol'] != 'docs/ias15-full-suite-protocol.md'
            or tuple(report['results']) != CASES or tuple(report['requests']) != CASES
            or tuple(report['origins']) != CASES):
        raise ValueError('Incomplete/wrong full-suite model or case inventory')
    if any(tuple(row) != ('1e-09', '1e-11') for row in report['results'].values()):
        raise ValueError('Wrong epsilon inventory')
    actual = totals(report['results'])
    if actual != report['aggregate'] or actual['attempted'] != 18 or actual['completed'] != 18:
        raise ValueError('Incomplete variants or false aggregate gate')
    return actual


def validate_pair(warm, full, text_warm, text_full, case, epoch, state, epsilon, initial):
    saved = []
    for raw, text in ((warm, text_warm), (full, text_full)):
        time, masses, physical = restore(text, sha(text.encode()), case['origin'])
        if (bits(time) != bits(epoch) or bits(masses) != bits(case['request']['masses'])
                or bits(physical) != bits(state)):
            raise ValueError('Physical packet time/mass/state differs')
        header, fields = parse(raw)
        if not header.startswith(b'REBOUND Binary File. Version: 5.2.2\0'):
            raise ValueError('Wrong binary version')
        invariants = {'t': struct.pack('=d', time), 'G': struct.pack('=d', G),
            'softening': bytes(8), 'N': struct.pack('=Q', 2), 'N_var': bytes(8),
            'gravity': struct.pack('=i', 1), 'collision': bytes(4), 'boundary': bytes(4),
            'functionpointers': bytes(4), 'integrator.name': b'ias15\0',
            PREFIX+'epsilon': struct.pack('=d', epsilon), PREFIX+'min_dt': bytes(8),
            PREFIX+'adaptive_mode': struct.pack('=I', 2)}
        if any(fields.get(k) != v for k, v in invariants.items()):
            raise ValueError('Wrong binary model/epoch/settings')
        if len(fields['particles']) != 224:
            raise ValueError('Wrong particle payload length')
        for i in range(2):
            components = struct.unpack_from('=11d', fields['particles'], i*112)
            name_pointer, user_pointer, _ = struct.unpack_from('=3Q', fields['particles'], i*112+88)
            if (bits(components[:6]) != bits(physical[i]) or bits(components[9]) != bits(masses[i])
                    or components[10] != 0. or name_pointer or user_pointer
                    or not np.isfinite(components).all()):
                raise ValueError('Wrong binary physical payload or unsupported particle pointers')
        expected = {PREFIX+k for k in SCALARS+(BUFFERS if not initial else ())}
        if {k for k in fields if k.startswith(PREFIX)} != expected:
            raise ValueError('Incomplete IAS15 field inventory')
        lengths = {'epsilon': 8, 'min_dt': 8, 'adaptive_mode': 4, 'iterations_max_exceeded': 8}
        lengths.update({k: 48*(7 if k in DP7 else 1) for k in BUFFERS if not initial})
        for k, length in lengths.items():
            if len(fields[PREFIX+k]) != length:
                raise ValueError('Wrong IAS15 field length/allocation: '+k)
            if k in BUFFERS and not np.isfinite(np.frombuffer(fields[PREFIX+k], dtype='=f8')).all():
                raise ValueError('Nonfinite IAS15 buffer')
        saved.append(FullSnapshot(raw, '', '', '', '', '', '', '', ()))
    if numeric_fields(saved[0], independent_control=True) != numeric_fields(saved[1], independent_control=True):
        raise ValueError('Warm/full binary fields differ')


def replay(root=ROOT, report_path=REPORT, arrays_path=ARRAYS):
    root = Path(root)
    report = json.loads((root/report_path).read_bytes())
    aggregate = validate_report(report)
    for name, digest in (report['source_sha256'] | report['input_sha256']).items():
        if sha((root/name).read_bytes()) != digest:
            raise ValueError('Changed full-suite source/input: '+name)
    if sha((root/arrays_path).read_bytes()) != report['array_archive_sha256']:
        raise ValueError('Full-suite arrays SHA mismatch')
    cases, _ = load_cases(root)
    with np.load(root/arrays_path, allow_pickle=False) as archive:
        data = {n: archive[n].copy() for n in archive.files}
    with np.load(root/'docs/ias15-restart-samples.npz', allow_pickle=False) as archive:
        old = {n: archive[n].copy() for n in archive.files}
    expected_keys, packets, snapshots, failed_cold = set(), 0, 0, []
    variant_keys = ('warm', 'full', 'packet_states', 'packet_endpoints', 'warm_binary_base64',
        'warm_physical_json', 'full_binary_base64', 'full_physical_json', 'cold',
        'cold_packet_endpoints', 'cold_packet_states', 'cold_checkpoint_json', 'cold_checkpoint_sha256')
    for name, case in cases.items():
        if report['requests'][name] != case['request'] or report['origins'][name] != case['origin']:
            raise ValueError('Changed actual-IC request/origin')
        expected_keys.update((name+'__times', name+'__oracle100'))
        if bits(data[name+'__times']) != bits(case['times']):
            raise ValueError('Changed output epochs')
        if not np.array_equal(data[name+'__oracle100'], np.asarray([[str(v) for v in row] for row in case['expected']])):
            raise ValueError('Changed independent actual-IC oracle')
        expected = [(v[:3], v[3:]) for v in case['expected']]
        for epsilon, row in report['results'][name].items():
            prefix = name+'__'+epsilon+'__'
            expected_keys.update(prefix+k for k in variant_keys)
            values = {k: data[prefix+k] for k in variant_keys}
            check_baseline(name, float(epsilon), values, old)
            if not row['previous353_bitexact']:
                raise ValueError('Previous353 flag false')
            for mode in ('warm', 'full', 'cold'):
                recalculated = metrics(case['seed'], case['times'], values[mode], expected)
                if recalculated != row['metrics'][mode]:
                    raise ValueError('Independent analytic/invariant metrics differ')
            if not row['metrics']['cold']['checks_passed']:
                failed_cold.append((name, epsilon))
            ends, stats = values['packet_endpoints'], row['statistics']
            if (stats['packets'] != len(ends)-1 or stats['restored_snapshots'] != len(ends)-1
                    or stats['raw_c_masks'] != [[0, 0]]*(len(ends)-1)
                    or stats['ias15_written_fields'] != 17 or stats['N_allocated'] != 6
                    or not stats['all_packet_fields_bitexact'] or not stats['all_restored_fields_bitexact']):
                raise ValueError('Invalid restore metadata')
            guards = row['guards']
            if len(guards) != 56 or len({g['name'] for g in guards}) != 56 or not all(
                    g.get('rejected_before_c') or g.get('rejected_before_export') or g.get('rejected') for g in guards):
                raise ValueError('Negative guards missing/false')
            if len(values['packet_states']) != len(ends) or not np.isfinite(values['packet_states']).all():
                raise ValueError('Incomplete/nonfinite packet states')
            for mode in ('warm', 'full'):
                if any(len(values[mode+suffix]) != len(ends) for suffix in ('_binary_base64', '_physical_json')):
                    raise ValueError('Incomplete binary archive')
            sizes = []
            for index, epoch in enumerate(ends):
                warm_raw = base64.b64decode(str(values['warm_binary_base64'][index]), validate=True)
                full_raw = base64.b64decode(str(values['full_binary_base64'][index]), validate=True)
                validate_pair(warm_raw, full_raw,
                    str(values['warm_physical_json'][index]), str(values['full_physical_json'][index]),
                    case, epoch, values['packet_states'][index], float(epsilon), index == 0)
                snapshots += 2
                sizes.append(len(full_raw))
            if stats['stream_bytes'] != dict(initial=sizes[0], minimum_committed=min(sizes[1:]), maximum_committed=max(sizes[1:])):
                raise ValueError('Recorded stream sizes differ from actual payloads')
            cost = stats['cost_seconds']
            if (set(cost) != {'warm_integration', 'integration', 'serialization', 'reading_validation'}
                    or not all(type(t) is float and np.isfinite(t) and t > 0 for t in cost.values())):
                raise ValueError('Invalid measured cost metadata')
            cold_ends = values['cold_packet_endpoints']
            if not all(len(values[k]) == len(cold_ends) for k in ('cold_packet_states', 'cold_checkpoint_json', 'cold_checkpoint_sha256')):
                raise ValueError('Incomplete cold checkpoint archive')
            for time, state, text, digest in zip(cold_ends, values['cold_packet_states'],
                                               values['cold_checkpoint_json'], values['cold_checkpoint_sha256']):
                restored_time, masses, restored_state = restore(str(text), str(digest), case['origin'])
                if bits(restored_time) != bits(time) or bits(restored_state) != bits(state) or bits(masses) != bits(case['request']['masses']):
                    raise ValueError('Cold physical checkpoint differs')
            packets += len(ends)-1
    if set(data) != expected_keys or packets != aggregate['packets']:
        raise ValueError('Wrong array inventory or packet aggregate')
    original = json.loads((root/'docs/ias15-restart-validation.json').read_bytes())
    old_cold_failed = [(n, e) for n in CASES for e in ('1e-09', '1e-11')
                       if not original['results'][n]['modes'][e+'__every-packet']['metrics']['checks_passed']]
    if failed_cold != old_cold_failed:
        raise ValueError('Previous cold failures changed')
    return dict(cases=9, variants=18, **aggregate, arrays=len(data), archived_snapshots=snapshots,
        preserved_cold_failures=failed_cold, independent_metrics_reproduced=True,
        scope='offline evidence replay; no C load or integration', runtime_modified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--report', default=REPORT)
    parser.add_argument('--arrays', default=ARRAYS)
    args = parser.parse_args()
    print(json.dumps(replay(args.root, args.report, args.arrays), indent=2))


if __name__ == '__main__':
    main()
