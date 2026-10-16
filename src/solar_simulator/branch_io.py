"""Read a checkpoint plus its optional immutable immediate-parent snapshot."""
import json

from .sandbox import from_branch_document
from .storage import _read_document, from_document


def open_experiment(path):
    document=_read_document(path)
    try:
        if type(document) is dict and document.get("format")=="solar-experiment-branch":
            branch=from_branch_document(document)
            return branch.child,branch.parent_snapshot
        return from_document(document),None
    except (TypeError,OverflowError,UnicodeDecodeError) as error:
        raise ValueError("Неверный формат опыта") from error


def parent_experiment(snapshot):
    if snapshot is None:raise ValueError("В этом опыте нет сохранённого родителя; откройте файл ветки")
    return from_document(json.loads(snapshot))
