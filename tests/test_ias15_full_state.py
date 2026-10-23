"""No optional library import: hostile framing and failed-commit checks."""
from dataclasses import dataclass
import struct
from types import SimpleNamespace

import pytest

from scripts.ias15_full_state import parse, pack, CommittedFullState, reject_callbacks


@pytest.fixture
def raw():
    return pack(bytes(64), {'particles': bytes(224), 'integrator.ias15.b': bytes(336), 'end': b''})


@pytest.mark.parametrize('kind', ['short', 'no-end', 'overrun', 'huge-name', 'huge-data',
                                  'nul-name', 'non-ascii', 'duplicate', 'append', 'nonzero-blob'])
def test_corrupt_framing_rejected_before_c(raw, kind):
    if kind == 'short':
        raw = raw[:64]
    elif kind == 'no-end':
        raw = raw[:64+16+10+224]
    elif kind == 'overrun':
        raw = raw[:-20]
    elif kind == 'huge-name':
        raw = raw[:64]+struct.pack('=Q', 2**63)+raw[72:]
    elif kind == 'huge-data':
        raw = raw[:72]+struct.pack('=Q', 2**63)+raw[80:]
    elif kind == 'nul-name':
        raw = raw[:80]+b'\0'+raw[81:]
    elif kind == 'non-ascii':
        raw = raw[:80]+b'\xff'+raw[81:]
    elif kind == 'duplicate':
        raw = raw[:64]+raw[64:64+16+10+224]+raw[64:]
    elif kind == 'append':
        raw += b'another blob'
    else:
        raw = raw[:-1]+b'\x01'
    with pytest.raises(ValueError):
        parse(raw)


@dataclass(frozen=True)
class Saved:
    time: float


@pytest.mark.parametrize('failure', ['integration', 'serialization', 'reading', 'wrong-endpoint'])
def test_failure_preserves_last_committed_snapshot(failure):
    class Sim:
        t = 0.
        def integrate(self, end, **kwargs):
            self.t = end if failure != 'wrong-endpoint' else end-1.
            if failure == 'integration':
                raise ArithmeticError('injected integration failure')
    class Guard:
        def capture(self, sim):
            if sim.t and failure == 'serialization':
                raise OSError('injected writer failure')
            return Saved(sim.t)
        def restore(self, saved, end):
            if failure == 'reading':
                raise ValueError('injected preflight/load failure')
            return SimpleNamespace(t=end), (0, 0)
    session = CommittedFullState(Guard(), Sim())
    last = session.current
    with pytest.raises((ArithmeticError, OSError, ValueError)):
        session.next(2.)
    assert session.current is last and session.current.time == 0.
    assert session.failed and session.sim is None and session.packets == 0
    with pytest.raises(RuntimeError, match='failed/closed'):
        session.next(3.)


def test_callback_not_covered_by_upstream_flag_rejected():
    import ctypes as C
    callback = C.CFUNCTYPE(None)
    class Sim(C.Structure):
        _fields_ = [('_pre_timestep_modifications', callback)]
    sim = Sim(callback(lambda: None))
    with pytest.raises(ValueError, match='pre_timestep_modifications'):
        reject_callbacks(sim)


def test_parse_keeps_order_and_bytes(raw):
    header, fields = parse(raw)
    assert list(fields) == ['particles', 'integrator.ias15.b', 'end']
    assert len(fields['integrator.ias15.b']) == 336
    assert pack(header, fields) == raw


def test_public_offline_pilot_replays_all_packets_without_rebound():
    from scripts.replay_ias15_full_state import replay
    result = replay()
    assert result['variants'] == 2 and result['packets'] == 262
    assert result['archived_warm_full_snapshots'] == 528
    assert result['independent_metrics_reproduced']


@pytest.mark.parametrize('failure', ['incomplete', 'source', 'array-sha'])
def test_offline_replay_rejects_wrong_evidence(tmp_path, failure):
    import json
    from pathlib import Path
    from scripts.replay_ias15_full_state import REPORT, ARRAYS, replay
    root = Path(__file__).resolve().parents[1]
    report = json.loads((root/REPORT).read_bytes())
    (tmp_path/'docs').mkdir()
    if failure == 'incomplete':
        report['complete'] = False
        message = 'completed'
    elif failure == 'source':
        report['source_sha256'] = {'wrong-source': '0'*64}
        report['input_sha256'] = {}
        (tmp_path/'wrong-source').write_bytes(b'different source')
        message = 'source/input'
    else:
        report['source_sha256'] = report['input_sha256'] = {}
        (tmp_path/ARRAYS).write_bytes(b'corrupt archive')
        message = 'archive SHA'
    (tmp_path/REPORT).write_text(json.dumps(report), encoding='utf-8')
    with pytest.raises(ValueError, match=message):
        replay(tmp_path)
