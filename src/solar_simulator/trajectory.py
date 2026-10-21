"""Full, committed packet endpoints; no new integration or interpolation scheme."""
import hashlib
import json
from math import isfinite
from pathlib import Path

from .branch_io import save_experiment
from .sandbox import ExperimentBranch, from_branch_document, to_branch_document
from .storage import MAX_BYTES, _read_document, _unique_pairs, _write_document, from_document, to_document
from .time_control import advance_towards, validate_target


def _decode(raw):
    document=json.loads(raw,object_pairs_hook=_unique_pairs)
    if type(document) is dict and document.get('format')=='solar-experiment-branch':
        branch=from_branch_document(document)
        return branch.child,branch.parent_snapshot
    return from_document(document),None


def record_trajectory(experiment,directory,target,*,packet_steps=20,parent_snapshot=None,stop_requested=None):
    """Commit immutable checkpoints and an atomic index in a NEW directory.

    A stopped/failed index is still readable. A file not published in the index
    is not a frame. On failure the latest calculated state also gets recovery.
    """
    validate_target(experiment,target,packet_steps)
    document=(to_document(experiment) if parent_snapshot is None else
              to_branch_document(ExperimentBranch(parent_snapshot,experiment)))
    current,parent_snapshot=_decode(json.dumps(document,allow_nan=False).encode('utf-8'))
    directory=Path(directory).resolve()
    directory.mkdir(parents=True,exist_ok=False)
    manifest=dict(format='solar-trajectory',schema_version=1,units='SI',
                  engine='advance-towards-packets',packet_steps=packet_steps,
                  start_time_seconds=current.time,requested_target_seconds=float(target),
                  status='recording',frames=[])
    latest=current
    fingerprint_start=None
    fingerprint_end=None
    from .recipe import runtime_fingerprint, write_recipe
    def publish(state):
        name=f'frame-{len(manifest["frames"]):06d}.json';path=directory/name
        if path.exists():raise FileExistsError('Файл кадра уже существует: '+str(path))
        save_experiment(state,path,parent_snapshot=parent_snapshot)
        entry=dict(file=name,time_seconds=state.time,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        updated=dict(manifest,frames=manifest['frames']+[entry])
        _write_document(updated,directory/'manifest.json')
        manifest.update(updated)
    try:
        fingerprint_start=runtime_fingerprint(current.settings.backend)
        write_recipe(directory,manifest,fingerprint_start,None)
        publish(current)
        while current.time<target and not current.halted:
            if stop_requested is not None and stop_requested():break
            latest=advance_towards(current,target,packet_steps)
            if latest.time<current.time or (latest.time==current.time and not latest.halted):
                raise RuntimeError('Пакет не продвинул время')
            publish(latest)
            current=latest
        manifest['status']=('complete' if current.time==target else 'halted' if current.halted else 'stopped')
        _write_document(manifest,directory/'manifest.json')
        fingerprint_end=runtime_fingerprint(current.settings.backend)
        write_recipe(directory,manifest,fingerprint_start,fingerprint_end)
        if fingerprint_start!=fingerprint_end:
            raise RuntimeError('Код или окружение изменились во время записи; recipe не подтверждён')
    except (KeyboardInterrupt,Exception) as error:
        interrupted=isinstance(error,KeyboardInterrupt)
        detail=''
        if manifest['frames']:
            try:_write_document(dict(manifest,status='interrupted' if interrupted else 'failed'),directory/'manifest.json')
            except (OSError,ValueError,RuntimeError,OverflowError) as failure:detail=f'; индекс не обновлён: {failure}'
            if fingerprint_start is not None:
                try:
                    if fingerprint_end is None:
                        fingerprint_end=runtime_fingerprint(current.settings.backend)
                    write_recipe(directory,dict(manifest,status='interrupted' if interrupted else 'failed'),
                                 fingerprint_start,fingerprint_end)
                except (OSError,ValueError,RuntimeError,OverflowError,ImportError) as failure:
                    detail+=f'; recipe не завершён: {failure}'
        from .recovery import save_recovery
        try:
            recovery=save_recovery(latest,parent_snapshot=parent_snapshot,reason='interrupted' if interrupted else 'failed')
        except (OSError,ValueError,RuntimeError,OverflowError) as failure:
            raise RuntimeError(f'{error}{detail}; recovery также не сохранена: {failure}; каталог: {directory}') from error
        if interrupted:
            error.add_note(f'recovery: {recovery}{detail}; траектория: {directory}')
            raise
        raise RuntimeError(f'{error}{detail}; recovery: {recovery}; траектория: {directory}') from error
    return dict(directory=str(directory),status=manifest['status'],samples=len(manifest['frames']),
                last_committed_time_seconds=current.time,requested_target_seconds=float(target),
                target_reached=current.time==target,packet_steps=packet_steps)


class Trajectory:
    """Verify the entire recording once; keep its verified bytes detached from disk.

    frame() decodes a fresh full experiment so callers cannot mutate the recording.
    This first format loads all frames into memory; it is intended for modest runs.
    """
    def __init__(self,directory,*,progress=None,stop_requested=None):
        from concurrent.futures import CancelledError
        if stop_requested is not None and stop_requested():raise CancelledError()
        self.directory=Path(directory).resolve()
        document=_read_document(self.directory/'manifest.json')
        keys={'format','schema_version','units','engine','packet_steps','start_time_seconds',
              'requested_target_seconds','status','frames'}
        if (type(document) is not dict or set(document)!=keys or document['format']!='solar-trajectory'
                or type(document['schema_version']) is not int or document['schema_version']!=1
                or document['units']!='SI' or document['engine']!='advance-towards-packets'
                or document['status'] not in ('recording','complete','halted','stopped','failed','interrupted')
                or type(document['frames']) is not list or not document['frames']):
            raise ValueError('Неверный индекс траектории')
        start,target=document['start_time_seconds'],document['requested_target_seconds']
        if type(start) not in (int,float) or type(target) not in (int,float) or not isfinite(start) or not isfinite(target):
            raise ValueError('Неконечное время траектории')
        raw_frames=[];times=[];settings=None;parent=None;initial=None;origin=None;previous_halted=False
        for index,entry in enumerate(document['frames']):
            if stop_requested is not None and stop_requested():raise CancelledError()
            name=f'frame-{index:06d}.json'
            if (type(entry) is not dict or set(entry)!={'file','time_seconds','sha256'} or entry['file']!=name
                    or type(entry['time_seconds']) not in (int,float) or not isfinite(entry['time_seconds'])):
                raise ValueError('Неверный кадр траектории')
            path=(self.directory/name).resolve()
            if not path.is_relative_to(self.directory) or path.stat().st_size>MAX_BYTES:
                raise ValueError('Недопустимый файл кадра')
            raw=path.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=entry['sha256']:raise ValueError('SHA кадра не совпал')
            state,snapshot=_decode(raw)
            state_document=to_document(state)
            validate_target(state,target,document['packet_steps'])
            initial_contact=(state.halted and state.events and state.events[-1].time==state.time
                             and index==len(document['frames'])-1 and not previous_halted)
            if (state.time!=entry['time_seconds'] or state.time<start
                    or (times and (state.time<times[-1] or (state.time==times[-1] and not initial_contact)))):
                raise ValueError('Неверная последовательность времён')
            if not index:
                if state.time!=start:raise ValueError('Начальная эпоха не совпала')
                settings=state_document['settings'];parent=snapshot;initial=state_document['initial'];origin=state_document['origin']
            elif (state_document['settings']!=settings or snapshot!=parent or state_document['initial']!=initial
                  or state_document['origin']!=origin):
                raise ValueError('Настройки, начальные данные или родитель изменились между кадрами')
            raw_frames.append(raw);times.append(state.time);previous_halted=state.halted
            if progress is not None:progress(index+1,len(document['frames']))
        if stop_requested is not None and stop_requested():raise CancelledError()
        if (document['status']=='complete' and times[-1]!=target
                or document['status']=='halted' and not state.halted):
            raise ValueError('Статус не соответствует конечному кадру')
        self._document=json.dumps(document,allow_nan=False)
        self._raw_frames=tuple(raw_frames)
        self.times=tuple(times)

    @property
    def metadata(self):
        return json.loads(self._document)

    def frame(self,index):
        return _decode(self._raw_frames[index])
