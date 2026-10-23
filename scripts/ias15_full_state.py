"""Trusted, same-process REBOUND 5.2.2 binary pilot, never Solar persistence.

The guard is constructed from a fresh owned basic simulation, not from a
sidecar supplied with a file. It accepts only this two-body model and ABI.
It is NOT a reader for arbitrary or malicious REBOUND files.
"""
import ctypes as C
from dataclasses import dataclass
import hashlib
import json
import struct
import sys
import warnings

import numpy as np

from scripts.ias15_reference import VERSION, EPSILONS, library_hashes
from scripts.ias15_restart import bits, checkpoint, restore, simulation, snapshot

PREFIX = 'integrator.ias15.'
SINGLE = ('at', 'x0', 'v0', 'a0', 'csx', 'csv', 'csa0')
DP7 = ('g', 'b', 'csb', 'e', 'br', 'er')
SCALARS = ('epsilon', 'min_dt', 'adaptive_mode', 'iterations_max_exceeded')
BUFFERS = SINGLE + DP7


class AllocationHeader(C.Structure):
    # Pinned integrator_ias15.h:27; inspect allocation, never mutate it.
    _fields_ = [('epsilon', C.c_double), ('min_dt', C.c_double),
                ('adaptive_mode', C.c_uint), ('iterations_max_exceeded', C.c_uint64),
                ('N_allocated', C.c_size_t)]
# These evolve during integration, or contain bookkeeping rather than a model.
VARIABLE = {'t', 'dt', 'dt_last_done', 'steps_done', 'walltime',
            'walltime_last_steps', 'rand_seed', 'did_modify_particles', 'particles',
            PREFIX+'iterations_max_exceeded'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def parse(raw):
    """Bounded Python-only scan of one full stream; never invoke the C reader."""
    if not isinstance(raw, bytes) or not 64 < len(raw) < 1_000_000:
        raise ValueError('Invalid pilot stream size/type')
    pos, fields = 64, {}
    while pos + 16 <= len(raw):
        n, size = struct.unpack_from('=QQ', raw, pos)
        pos += 16
        if not 1 < n <= 128 or pos+n+size > len(raw):
            raise ValueError('Invalid field bounds')
        encoded = raw[pos:pos+n]
        if encoded[-1:] != b'\0' or b'\0' in encoded[:-1]:
            raise ValueError('Invalid field name')
        try:
            name = encoded[:-1].decode('ascii')
        except UnicodeDecodeError as exc:
            raise ValueError('Non-ASCII field') from exc
        if name in fields:
            raise ValueError('Duplicate field: '+name)
        pos += n
        fields[name] = raw[pos:pos+size]
        pos += size
        if name == 'end':
            if size or raw[pos:] != bytes(12):
                raise ValueError('Expected one full zero-index blob, no append chain')
            return raw[:64], fields
    raise ValueError('Missing end field')


def pack(header, fields):
    """Used by negative tests and offline inspection, not by the C writer."""
    return header + b''.join(struct.pack('=QQ', len(n)+1, len(v)) +
        n.encode('ascii')+b'\0'+v for n, v in fields.items()) + bytes(12)


def reject_callbacks(sim):
    # Derive ALL declared function-pointer slots, including hooks not covered
    # by upstream's functionpointers flag (notably pre_timestep_modifications).
    for name, kind in sim._fields_:
        if issubclass(kind, C._CFuncPtr) and bool(getattr(sim, name)):
            raise ValueError('Unsupported callback: '+name)
    if sim.extras:
        raise ValueError('Unsupported extras pointer')
    if any(p.ap or p._name for p in sim.particles):
        raise ValueError('Pilot requires unnamed particles without user pointers')


def stream(library, sim):
    reject_callbacks(sim)
    pointer, size = C.c_void_p(), C.c_size_t()
    try:
        library.clibrebound.reb_binarydata_simulation_to_stream(
            C.byref(sim), C.byref(pointer), C.byref(size))
        if not pointer.value or not 64 < size.value < 1_000_000:
            raise ValueError('Invalid owned writer output')
        return C.string_at(pointer, size.value)
    finally:
        if pointer.value:
            library.clibrebound.reb_free(pointer)


def abi(library):
    def layout(kind):
        return (C.sizeof(kind), C.alignment(kind), tuple(
            (name, getattr(kind, name).offset, C.sizeof(field)) for name, field in kind._fields_))
    return repr((sys.byteorder, C.sizeof(C.c_void_p), C.sizeof(C.c_size_t),
                 layout(library.Simulation), layout(library.Particle), layout(AllocationHeader)))


@dataclass(frozen=True)
class FullSnapshot:
    binary: bytes
    digest: str
    physical_json: str
    physical_sha: str
    origin: str
    version: str
    abi: str
    library_sha: str
    identities: tuple


class FullStateGuard:
    """A locally trusted guard; do not reconstruct it from an input sidecar."""
    def __init__(self, library, masses, initial, packet_dt, epsilon, origin, pinned_files):
        if library.__version__ != VERSION or epsilon not in EPSILONS:
            raise ValueError('Unqualified library/epsilon')
        if library_hashes(library) != pinned_files:
            raise ValueError('Pinned library bytes differ')
        expected_particle = ('x', 'y', 'z', 'vx', 'vy', 'vz', 'ax', 'ay', 'az', 'm', 'r', '_name', 'ap', '_sim')
        if (C.sizeof(library.Particle) != 112 or C.sizeof(C.c_void_p) != 8
                or tuple(n for n, _ in library.Particle._fields_) != expected_particle
                or any(getattr(library.Particle, n).offset != i*8 for i, n in enumerate(expected_particle))):
            raise ValueError('Unqualified particle ABI')
        self.library, self.origin = library, origin
        self.masses = np.asarray(masses, dtype=float).copy()
        self.epsilon = epsilon
        self.identities = ('body[0]', 'body[1]')
        self.abi = abi(library)
        self.library_sha = sha(json.dumps(pinned_files, sort_keys=True).encode())
        self.pinned_files = dict(pinned_files)
        fresh = simulation(library, 0., self.masses, initial, packet_dt, epsilon)
        raw = stream(library, fresh)
        self.header, self.template = parse(raw)
        self.schema = {k: len(v) for k, v in self.template.items()}
        self.schema.update({PREFIX+k: 8*6*(7 if k in DP7 else 1) for k in BUFFERS})
        self.constants = {k: v for k, v in self.template.items() if k not in VARIABLE}
        self._archive_create, self._initialize = self._create_archive, self._init_simulation

    def capture(self, sim):
        if sim.integrator != 'ias15':
            raise ValueError('Expected IAS15')
        allocated = AllocationHeader.from_address(sim.integrator.state).N_allocated
        if allocated != (0 if sim.t == 0. else 6):
            raise ValueError('Unexpected IAS15 buffer allocation')
        raw = stream(self.library, sim)
        physical_json, physical_sha = checkpoint(float(sim.t), [p.m for p in sim.particles],
                                                  snapshot(sim), self.origin)
        result = FullSnapshot(raw, sha(raw), physical_json, physical_sha,
            self.origin, VERSION, self.abi, self.library_sha, self.identities)
        self.preflight(result, float(sim.t))
        return result

    def preflight(self, saved, expected_time):
        """All malformed-data tests must stop here, before any C load."""
        if (saved.origin != self.origin or saved.version != VERSION or saved.abi != self.abi
                or saved.library_sha != self.library_sha or saved.identities != self.identities):
            raise ValueError('Wrong origin/version/ABI/library/identity')
        if sha(saved.binary) != saved.digest:
            raise ValueError('Binary SHA mismatch')
        time, masses, state = restore(saved.physical_json, saved.physical_sha, self.origin)
        if bits(time) != bits(expected_time) or bits(masses) != bits(self.masses):
            raise ValueError('Wrong physical time/mass/order')
        header, fields = parse(saved.binary)
        if header != self.header:
            raise ValueError('Wrong binary build header')
        initial = time == 0.
        schema = {k: v for k, v in self.schema.items() if not (initial and k in {PREFIX+b for b in BUFFERS})}
        if {k: len(v) for k, v in fields.items()} != schema:
            raise ValueError('Wrong binary field inventory/length')
        expected_order = list(self.template)
        if not initial:
            index = expected_order.index('functionpointers')
            expected_order[index:index] = [PREFIX+k for k in BUFFERS]
        if list(fields) != expected_order:
            raise ValueError('Wrong binary field order')
        if any(fields[k] != value for k, value in self.constants.items()):
            raise ValueError('Changed binary model/settings')
        if fields['t'] != struct.pack('=d', time):
            raise ValueError('Binary/physical epoch mismatch')
        if int.from_bytes(fields['did_modify_particles'], sys.byteorder) not in (0, 1):
            raise ValueError('Invalid particle modification flag')
        for k in ('t', 'dt', 'dt_last_done', 'walltime', 'walltime_last_steps'):
            value, = struct.unpack('=d', fields[k])
            if not np.isfinite(value) or value < 0 or (k == 'dt' and value == 0):
                raise ValueError('Invalid numeric field: '+k)
        for k in BUFFERS if not initial else ():
            if not np.isfinite(np.frombuffer(fields[PREFIX+k], dtype='=f8')).all():
                raise ValueError('Nonfinite IAS15 buffer: '+k)
        # from_buffer_copy never dereferences the serialized pointer members.
        particle_bytes = fields['particles']
        for i in range(2):
            p = self.library.Particle.from_buffer_copy(particle_bytes[i*C.sizeof(self.library.Particle):])
            if (p.ap or p._name or p.r != 0 or bits(p.m) != bits(masses[i])
                    or bits([p.x, p.y, p.z, p.vx, p.vy, p.vz]) != bits(state[i])
                    or not np.isfinite([p.ax, p.ay, p.az]).all()):
                raise ValueError('Wrong particle payload/order/unsupported pointer')
        return fields

    def _create_archive(self, raw, mask):
        function = self.library.clibrebound.reb_simulationarchive_create_from_buffer_with_messages
        # Opaque pointer avoids Simulationarchive.__del__ taking ownership too.
        function.restype = C.c_void_p
        return function(C.c_char_p(raw), C.c_size_t(len(raw)), C.byref(mask))

    def _init_simulation(self, sim, archive, mask):
        self.library.clibrebound.reb_simulation_init_from_simulationarchive_with_messages(
            C.byref(sim), C.c_void_p(archive), C.c_int64(0), C.byref(mask))

    def restore(self, saved, expected_time):
        self.preflight(saved, expected_time)
        archive = None
        masks = []
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            try:
                mask = C.c_int(0)
                archive = self._archive_create(saved.binary, mask)
                masks.append(mask.value)
                if mask.value or not archive:
                    raise ValueError('C archive warning mask: '+str(mask.value))
                sim = self.library.Simulation()
                mask = C.c_int(0)
                self._initialize(sim, archive, mask)
                masks.append(mask.value)
                if mask.value:
                    raise ValueError('C simulation warning mask: '+str(mask.value))
                sim.process_messages()
                if caught:
                    raise ValueError('Unexpected Python warning: '+str(caught[0].message))
                result = self.capture(sim)
                if numeric_fields(saved) != numeric_fields(result):
                    raise ArithmeticError('Full state changed during restore')
                return sim, tuple(masks)
            finally:
                # Keep saved.binary alive until the memory-backed stream is closed.
                if archive:
                    self.library.clibrebound.reb_simulationarchive_free(C.c_void_p(archive))


def numeric_fields(saved, *, independent_control=False):
    """Restore preserves seed too; separately created controls have fresh seeds."""
    _, fields = parse(saved.binary)
    result = {k: v for k, v in fields.items()
              if k not in ('walltime', 'walltime_last_steps', 'particles')
              and not (independent_control and k == 'rand_seed')}
    # Particle struct has 11 numeric doubles followed by three pointer slots.
    result['particles'] = b''.join(fields['particles'][i*112:i*112+88] for i in range(2))
    return result


class CommittedFullState:
    """Research transaction: never publish a candidate that failed its reload."""
    def __init__(self, guard, sim):
        self.guard, self.sim = guard, sim
        self.current = guard.capture(sim)
        self.failed = False
        self.packets = 0
        self.masks = []
        self.cost = dict(integration=0., serialization=0., reading_validation=0.)

    def next(self, end):
        from time import perf_counter
        if self.failed or self.sim is None:
            raise RuntimeError('Full-state controller failed/closed')
        if not np.isfinite(end) or end <= self.sim.t:
            raise ValueError('Expected increasing finite endpoint')
        try:
            start = perf_counter()
            self.sim.integrate(end, exact_finish_time=1)
            self.cost['integration'] += perf_counter()-start
            if bits(self.sim.t) != bits(end):
                raise ArithmeticError('Wrong exact endpoint')
            start = perf_counter()
            candidate = self.guard.capture(self.sim)
            self.cost['serialization'] += perf_counter()-start
            start = perf_counter()
            restored, masks = self.guard.restore(candidate, end)
            self.cost['reading_validation'] += perf_counter()-start
        except BaseException:
            self.failed, self.sim = True, None
            raise
        self.sim, self.current = restored, candidate
        self.packets += 1
        self.masks.append(masks)
        return candidate
