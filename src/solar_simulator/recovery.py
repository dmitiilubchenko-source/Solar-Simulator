"""Unique local recovery copies using the existing atomic experiment writer."""
from datetime import datetime, timezone
import os
from pathlib import Path
from uuid import uuid4

from .branch_io import save_experiment


def save_recovery(experiment, *, parent_snapshot=None, directory=None, reason='stopped'):
    if reason not in ('stopped', 'closed', 'interrupted', 'failed'):
        raise ValueError('Unknown recovery reason')
    if directory is None:directory = recovery_directory()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    folder = Path(directory).resolve()/f'solar-{reason}-{stamp}-{uuid4().hex}'
    folder.mkdir(parents=True, exist_ok=False)
    path = folder/'checkpoint.json'
    save_experiment(experiment, path, parent_snapshot=parent_snapshot)
    return path


def recovery_directory():
    base = Path(os.environ.get('LOCALAPPDATA', str(Path.home()/'.local/share')))
    return (base/'SolarSimulator/recovery').resolve()


def list_recoveries():
    """List local copies without parsing large or potentially damaged experiments."""
    root = recovery_directory()
    paths = [path for path in root.glob('solar-*/checkpoint.json')
             if path.is_file() and path.resolve().is_relative_to(root)]
    return tuple(sorted(paths, key=lambda path: (path.stat().st_mtime_ns, path.parent.name), reverse=True))
