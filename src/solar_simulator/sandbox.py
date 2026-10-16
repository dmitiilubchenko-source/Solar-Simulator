"""Detached point-mass experiments with an immutable immediate-parent snapshot.

No force formulas or GUI dependencies. Bundle v1 wraps ordinary checkpoints;
the child uses its own energy baseline and makes no claim of unchanged JPL data.
"""
from dataclasses import dataclass
import hashlib
import json

from .experiment import Experiment, create_experiment
from .oblateness import prescribed
from .simulation import Body
from .storage import (MAX_BYTES, _body, _keys, _read_document, _write_document,
                      from_document, to_document)


def _canonical(document):
    return json.dumps(document, ensure_ascii=False, allow_nan=False,
                      sort_keys=True, separators=(",", ":"))


def _digest(snapshot):
    return hashlib.sha256(snapshot.encode("utf-8")).hexdigest()


def _supported(parent):
    if prescribed(parent.settings.figures) or parent.initial_rotations or parent.rotations:
        raise ValueError("Ветки не поддерживают заданную ориентацию и динамическое вращение")


@dataclass(frozen=True)
class ExperimentBranch:
    parent_snapshot: str
    child: Experiment

    @property
    def parent(self):
        """Every access returns a detached copy, including position/velocity."""
        return from_document(json.loads(self.parent_snapshot))

    @property
    def parent_sha256(self):
        return _digest(self.parent_snapshot)

    def changes(self):
        """Exact before/after body records; rename is removal plus addition."""
        before = {b.name: _body(b) for b in self.parent.bodies}
        after = {b.name: _body(b) for b in self.child.initial}
        return [dict(name=name, before=before.get(name), after=after.get(name))
                for name in sorted(before.keys() | after.keys())
                if before.get(name) != after.get(name)]


def branch_experiment(parent: Experiment, *, replacements=(), additions=(), removals=()):
    """Fork current state. Replacements are (existing name, new Body) pairs.

    Inertial SI coordinates and velocities are explicit; no automatic orbit,
    recentering, mass compensation or softening is applied.
    """
    snapshot = _canonical(to_document(parent))
    _supported(parent)
    if type(replacements) is not tuple or type(additions) is not tuple or type(removals) is not tuple:
        raise ValueError("Правки должны быть кортежами")
    changed = {}
    names = {b.name for b in parent.bodies}
    for item in replacements:
        if (type(item) is not tuple or len(item) != 2 or type(item[0]) is not str
                or item[0] not in names or item[0] in changed or not isinstance(item[1], Body)):
            raise ValueError("Неверная замена тела")
        changed[item[0]] = item[1]
    if (any(type(n) is not str or n not in names or n in changed for n in removals)
            or len(set(removals)) != len(removals)
            or any(not isinstance(b, Body) for b in additions)):
        raise ValueError("Неверное добавление или удаление тела")
    bodies = [changed.get(b.name, b) for b in parent.bodies if b.name not in removals]
    bodies.extend(additions)
    child = create_experiment(bodies, parent.settings)
    _supported(child)
    branch = ExperimentBranch(snapshot, child)
    to_branch_document(branch)  # Same limits and guarantees as persisted files.
    return branch


def to_branch_document(branch):
    if not isinstance(branch, ExperimentBranch) or type(branch.parent_snapshot) is not str:
        raise ValueError("Неверная ветка опыта")
    if len(branch.parent_snapshot.encode("utf-8")) > MAX_BYTES:
        raise ValueError("Родительская контрольная точка слишком велика")
    parent = branch.parent
    parent_document = to_document(parent)
    if _canonical(parent_document) != branch.parent_snapshot:
        raise ValueError("Родительская контрольная точка должна быть канонической")
    child_document = to_document(branch.child)
    _supported(parent)
    _supported(branch.child)
    if branch.child.origin is not None or branch.child.settings != parent.settings:
        raise ValueError("Дочерний опыт должен иметь собственный старт и прежние настройки")
    document = dict(format="solar-experiment-branch", version=1,
                    parent=parent_document, parent_sha256=branch.parent_sha256,
                    child=child_document, changes=branch.changes())
    if len(_canonical(document).encode("utf-8")) > MAX_BYTES:
        raise ValueError("Ветка опыта слишком велика")
    return document


def from_branch_document(document):
    _keys(document, ("format", "version", "parent", "parent_sha256", "child", "changes"))
    if document["format"] != "solar-experiment-branch" or type(document["version"]) is not int or document["version"] != 1:
        raise ValueError("Неподдерживаемый формат ветки опыта")
    snapshot = _canonical(document["parent"])
    if _digest(snapshot) != document["parent_sha256"]:
        raise ValueError("Изменена родительская контрольная точка")
    branch = ExperimentBranch(snapshot, from_document(document["child"]))
    if to_branch_document(branch) != document:
        raise ValueError("Несогласованная история правок ветки")
    return branch


def save_branch(branch, path):
    _write_document(to_branch_document(branch), path)


def load_branch(path):
    try:
        return from_branch_document(_read_document(path))
    except (TypeError, OverflowError, UnicodeDecodeError) as error:
        raise ValueError("Неверный формат ветки опыта") from error


def load_experiment(path):
    """Open an ordinary checkpoint or the child in a branch bundle."""
    document = _read_document(path)
    try:
        if type(document) is dict and document.get("format") == "solar-experiment-branch":
            return from_branch_document(document).child
        return from_document(document)
    except (TypeError, OverflowError, UnicodeDecodeError) as error:
        raise ValueError("Неверный формат опыта") from error
