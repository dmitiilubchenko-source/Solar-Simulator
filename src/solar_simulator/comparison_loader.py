"""Cancellable comparison preparation; the worker never owns Tk objects."""
from concurrent.futures import CancelledError
from functools import partial

from .comparison import Comparison
from .trajectory import Trajectory
from .trajectory_loader import TrajectoryLoader


def prepare_comparison(parent_directory,child_directory,stop_requested,progress,*,event_side):
    parent=Trajectory(parent_directory,stop_requested=stop_requested,
                      progress=lambda done,total:progress('Чтение родителя',done,total))
    child=Trajectory(child_directory,stop_requested=stop_requested,
                     progress=lambda done,total:progress('Чтение ветки',done,total))
    comparison=Comparison(parent,child,event_side=event_side,
                          stop_requested=stop_requested,progress=progress)
    samples=[]
    for index in range(len(comparison.pairs)):
        if stop_requested():raise CancelledError()
        samples.append(comparison.sample(index))
        progress('Подготовка разностей',index+1,len(comparison.pairs))
    if stop_requested():raise CancelledError()
    return comparison,samples


class ComparisonLoader(TrajectoryLoader):
    def __init__(self,window,parent_directory,child_directory,*,event_side):
        self._start(window,partial(prepare_comparison,parent_directory,child_directory,event_side=event_side),
                    'Solar — открытие сравнения','Сравнение не открыто')

    def _show(self,result):
        from .comparison_view import ComparisonViewer
        comparison,samples=result
        self.viewer=ComparisonViewer(self.window,comparison,samples=samples)
