"""Exact saved-epoch comparison of an immediate parent and its edited branch.

No solver, interpolation, nearest-time matching or ephemeris fitting. The
bundle's immutable checkpoint, not a body's name or rounded JD, anchors time.
"""
from dataclasses import asdict
from fractions import Fraction
from math import hypot, isfinite
from pathlib import Path

from .sandbox import ExperimentBranch, _canonical, _digest
from .storage import _write_document, to_document


def _selected(states, times, side):
    """One saved side per epoch; an unavailable pre-event state stays missing."""
    selected = {}
    for index, state in enumerate(states):
        time = times[index]
        post_event = any(event.time == time for event in state.events)
        if side == 'before':
            if post_event:
                continue
            selected.setdefault(Fraction(time), index)
        else:
            selected[Fraction(time)] = index
    return selected


def _vector(body, attribute, reference):
    vector = getattr(body, attribute)
    values = (vector.x, vector.y, vector.z)
    if reference is not None:
        origin = getattr(reference, attribute)
        values = tuple(a-b for a, b in zip(values, (origin.x, origin.y, origin.z)))
    return values


class Comparison:
    def __init__(self, parent, child, *, event_side):
        if event_side not in ('before', 'after'):
            raise ValueError('Выберите сторону события: before или after')
        parent_states = [parent.frame(i)[0] for i in range(len(parent.times))]
        child_states = [child.frame(i)[0] for i in range(len(child.times))]
        _, snapshot = child.frame(0)
        if snapshot is None:
            raise ValueError('Дочерняя траектория должна содержать снимок родителя (bundle)')
        anchors = [i for i, state in enumerate(parent_states)
                   if _canonical(to_document(state)) == snapshot]
        if not anchors:
            raise ValueError('Снимок родителя ветки не найден в родительской траектории')
        self.parent = parent
        self.child = child
        self.anchor_index = anchors[0]
        self.anchor_time = parent.times[self.anchor_index]
        self.event_side = event_side
        self.parent_sha256 = _digest(snapshot)
        anchor = Fraction(self.anchor_time)
        selected_parent = {time-anchor: index for time, index in
                           _selected(parent_states, parent.times, event_side).items()}
        selected_child = _selected(child_states, child.times, event_side)
        shared = sorted(selected_parent.keys() & selected_child.keys())
        if not shared:
            raise ValueError('Нет совпадающих сохранённых эпох для выбранной стороны события')
        self.pairs = tuple((selected_parent[time], selected_child[time]) for time in shared)
        self.times = tuple(child.times[j] for _, j in self.pairs)
        self.origin = parent_states[self.anchor_index].origin
        self.body_names = tuple(sorted({name for i, j in self.pairs for name in
                                       ({b.name for b in parent_states[i].bodies} &
                                        {b.name for b in child_states[j].bodies})}))

    def sample(self, index, *, reference=None):
        """Signed 3D differences child-parent, after translating EACH system."""
        if reference is not None and (type(reference) is not str or not reference):
            raise ValueError('Опора должна быть именем тела или None')
        i, j = self.pairs[index]
        parent, _ = self.parent.frame(i)
        child, _ = self.child.frame(j)
        first = {body.name: body for body in parent.bodies}
        second = {body.name: body for body in child.bodies}
        common = sorted(first.keys() & second.keys())
        available = reference is None or reference in common
        row = dict(parent_index=i, child_index=j, parent_time_seconds=parent.time,
                   child_time_seconds=child.time, elapsed_since_branch_seconds=child.time,
                   reference=reference, reference_available=available,
                   parent_only=sorted(first.keys()-second.keys()),
                   child_only=sorted(second.keys()-first.keys()), common=common, bodies={})
        if not available:
            row['reason'] = 'reference-missing'
            return row
        ref_first = first.get(reference)
        ref_second = second.get(reference)
        for name in common:
            values = {}
            for attribute, suffix in (('position', 'm'), ('velocity', 'm_per_s')):
                a = _vector(first[name], attribute, ref_first)
                b = _vector(second[name], attribute, ref_second)
                delta = tuple(y-x for x, y in zip(a, b))
                norm = hypot(*delta)
                if not all(isfinite(v) for v in (*a, *b, *delta, norm)):
                    raise ValueError('Переполнение при сравнении координат/скоростей')
                values[f'parent_{attribute}_{suffix}'] = list(a)
                values[f'child_{attribute}_{suffix}'] = list(b)
                values[f'delta_{attribute}_{suffix}'] = list(delta)
                values[f'distance_{suffix}'] = norm
            row['bodies'][name] = values
        return row

    def report(self, *, reference=None):
        parent_used = {i for i, _ in self.pairs}
        child_used = {j for _, j in self.pairs}
        anchor, _ = self.parent.frame(self.anchor_index)
        child_start, snapshot = self.child.frame(0)
        return dict(format='solar-trajectory-comparison', schema_version=1, units='SI',
                    difference='child-parent', event_side=self.event_side,
                    epoch_match='exact-binary-times-with-exact-anchor-subtraction',
                    reference=reference, parent_directory=str(self.parent.directory),
                    child_directory=str(self.child.directory), parent_sha256=self.parent_sha256,
                    anchor_parent_index=self.anchor_index, anchor_parent_seconds=self.anchor_time,
                    origin=asdict(self.origin) if self.origin else None,
                    parent_settings=to_document(anchor)['settings'],
                    child_settings=to_document(child_start)['settings'],
                    changes=ExperimentBranch(snapshot, child_start).changes(),
                    parent_recording=self.parent.metadata, child_recording=self.child.metadata,
                    unmatched_parent_indices=sorted(set(range(len(self.parent.times)))-parent_used),
                    unmatched_child_indices=sorted(set(range(len(self.child.times)))-child_used),
                    samples=[self.sample(i, reference=reference) for i in range(len(self.pairs))])

    def save_report(self, path, *, reference=None):
        path = Path(path).resolve()
        if any(path.is_relative_to(track.directory) for track in (self.parent, self.child)):
            raise ValueError('Отчёт нужно сохранять вне обеих исходных траекторий')
        document = self.report(reference=reference)
        if not any(row['reference_available'] for row in document['samples']):
            raise ValueError('Опорное тело отсутствует на всех общих эпохах')
        _write_document(document, path)
