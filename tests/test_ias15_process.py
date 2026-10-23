"""Wire, field masking, subprocess failures and committed-file lifecycle."""
from copy import deepcopy
from dataclasses import replace
import json
import os
from pathlib import Path
import sys

import pytest

from scripts.ias15_process import (context, request_for, validate_context, read_request, sha,
    signature, persist, launch, validate_child, verify_files, validate_identity)
from scripts.ias15_full_state import parse, pack, PREFIX, SCALARS, BUFFERS


@pytest.fixture(scope='module')
def ctx():
    return context('holdout_circular', '1e-09')


@pytest.fixture
def wire(ctx):
    return request_for(ctx, 'first', os.getpid(), 'test-launch', {'scripts/ias15_process.py': '0'*64},
                       {'docs/ias15-full-suite-validation.json': '0'*64})


@pytest.mark.parametrize('key', ['version', 'abi', 'library_sha', 'digest', 'physical_sha', 'origin',
                                  'masses', 'identities', 'time', 'index', 'case'])
def test_metadata_mismatch_rejected_without_c(ctx, wire, key):
    wrong = deepcopy(wire)
    if key in ('time', 'index'):
        wrong[key] += 1
    elif key in ('masses', 'identities'):
        wrong[key] = list(reversed(wrong[key]))
    else:
        wrong[key] = 'different metadata'
    with pytest.raises(ValueError, match='frozen'):
        validate_context(wrong, ctx)


@pytest.mark.parametrize('mutation', ['sha', 'size', 'duplicate', 'missing', 'boolean-index', 'nan-time'])
def test_wire_corruption_before_science_import(tmp_path, wire, mutation):
    value = deepcopy(wire)
    if mutation == 'missing':
        del value['origin']
    elif mutation == 'boolean-index':
        value['index'] = True
    elif mutation == 'nan-time':
        value['time'] = float('nan')
    raw = json.dumps(value).encode()
    if mutation == 'size':
        raw = b' ' * 100001
    elif mutation == 'duplicate':
        raw = raw[:-1]+b',"point":"midpoint"}'
    path = tmp_path/'request.json'
    path.write_bytes(raw)
    with pytest.raises((ValueError, KeyError)):
        read_request(path, '0'*64 if mutation == 'sha' else sha(raw))


@pytest.mark.parametrize('field', SCALARS+BUFFERS)
def test_every_ias15_payload_changes_canonical_signature(ctx, field):
    saved = ctx['saved'](1)
    header, fields = parse(saved.binary)
    raw = bytearray(fields[PREFIX+field])
    raw[0] ^= 1
    fields[PREFIX+field] = bytes(raw)
    assert signature(replace(saved, binary=pack(header, fields))) != signature(saved)


def test_only_clock_and_particle_address_changes_are_masked(ctx):
    saved = ctx['saved'](1)
    header, fields = parse(saved.binary)
    raw = bytearray(fields['particles'])
    raw[104] ^= 1  # p.sim address, not a physical double or user pointer.
    fields['particles'] = bytes(raw)
    fields['walltime'] = bytes(8)
    fields['walltime_last_steps'] = bytes(8)
    assert signature(replace(saved, binary=pack(header, fields))) == signature(saved)


@pytest.mark.parametrize('failure', ['field-mismatch', 'write-error'])
def test_failed_candidate_keeps_prior_commit_and_candidate_evidence(ctx, tmp_path, monkeypatch, failure):
    saved = ctx['saved'](1)
    persist(tmp_path, 1, saved, saved)
    old = (tmp_path/'0001.bin').read_bytes()
    candidate = saved
    if failure == 'field-mismatch':
        header, fields = parse(saved.binary)
        raw = bytearray(fields[PREFIX+'b'])
        raw[0] ^= 1
        fields[PREFIX+'b'] = bytes(raw)
        encoded = pack(header, fields)
        candidate = replace(saved, binary=encoded, digest=sha(encoded))
    else:
        def injected(*args, **kwargs):
            raise OSError('injected candidate write failure')
        monkeypatch.setattr(json, 'dump', injected)
    with pytest.raises((ArithmeticError, OSError)):
        persist(tmp_path, 2, candidate, saved)
    assert (tmp_path/'0001.committed').is_file()
    assert (tmp_path/'0001.bin').read_bytes() == old
    assert (tmp_path/'0002.bin').is_file() and not (tmp_path/'0002.committed').exists()


@pytest.mark.parametrize('failure', ['nonzero', 'timeout'])
def test_subprocess_failure_preserves_logs_and_last_snapshot(tmp_path, failure):
    marker = tmp_path/'last-committed.bin'
    marker.write_bytes(b'previous committed evidence')
    command = [sys.executable, '-X', 'utf8', '-B', '-c',
               'import sys,time; print("worker output",flush=True); time.sleep(10)' if failure == 'timeout'
               else 'import sys; print("worker output"); sys.exit(7)']
    result = launch(command, tmp_path, timeout=.2 if failure == 'timeout' else 10.)
    assert result['returncode'] != 0 and result['timed_out'] == (failure == 'timeout')
    assert marker.read_bytes() == b'previous committed evidence'
    assert (tmp_path/'stdout.log').is_file() and (tmp_path/'stderr.log').is_file()


@pytest.mark.parametrize('mutation', ['pid', 'ppid', 'launch_id', 'request_sha256', 'mask', 'imported', 'returncode', 'timeout'])
def test_stale_or_unsuccessful_child_result_rejected(mutation):
    request = dict(parent_pid=100, launch_id='fresh')
    launched = dict(pid=200, returncode=0, timed_out=False)
    row = dict(complete=True, pid=200, ppid=100, os_name='posix', supervisor_pid=100, launched_pid=200,
               launch_id='fresh', request_sha256='0'*64,
               rebound_already_imported=False, restore_masks=[0, 0], c_restore_started=True)
    if mutation in ('pid', 'ppid'):
        row[mutation] += 1
    elif mutation in ('launch_id', 'request_sha256'):
        row[mutation] = 'stale'
    elif mutation == 'mask':
        row['restore_masks'] = [0, 2048]
    elif mutation == 'imported':
        row['rebound_already_imported'] = True
    elif mutation == 'returncode':
        launched['returncode'] = 7
    else:
        launched['timed_out'] = True
    with pytest.raises(ValueError):
        validate_child(row, request, '0'*64, launched)


def test_file_binding_cannot_escape_project(tmp_path):
    with pytest.raises(ValueError, match='outside'):
        verify_files({'../outside.txt': '0'*64}, tmp_path)


def test_windows_launcher_chain_and_false_chain():
    row = dict(pid=300, ppid=200, os_name='nt', supervisor_pid=100, launched_pid=200, launch_id='fresh')
    request, launched = dict(parent_pid=100, launch_id='fresh'), dict(pid=200)
    validate_identity(row, request, launched)
    with pytest.raises(ValueError):
        validate_identity(dict(row, ppid=999), request, launched)


def test_actual_python_child_identity_chain(tmp_path):
    program = ('import os,sys,json; m=json.loads(sys.stdin.readline()); '
               'print(json.dumps(dict(pid=os.getpid(),ppid=os.getppid(),os_name=os.name,**m)))')
    launched = launch([sys.executable, '-X', 'utf8', '-B', '-c', program], tmp_path, launch_id='actual-launch')
    row = json.loads((tmp_path/'stdout.log').read_bytes())
    validate_identity(row, dict(parent_pid=os.getpid(), launch_id='actual-launch'), launched)
    assert launched['returncode'] == 0 and row['pid'] != os.getpid()


def test_public_process_evidence_replay():
    from scripts.replay_ias15_process import replay
    result = replay()
    assert result['positive_children'] == 36 and result['negative_children'] == 4
    assert result['continued_steps'] == 3336 and result['packet_records'] == 3372
    assert result['arrays'] == 108 and result['all_checks_passed']
