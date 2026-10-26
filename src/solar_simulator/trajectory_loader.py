"""Prepare verified playback off the Tk thread; cancellation never alters a recording."""
from concurrent.futures import CancelledError,ThreadPoolExecutor
from functools import partial
from queue import Empty,Full,Queue
from threading import Event
import tkinter as tk
from tkinter import messagebox,ttk

from .trajectory import Trajectory


def _report(messages,phase,done,total):
    try:messages.put_nowait((phase,done,total))
    except Full:pass


def prepare_trajectory(directory,stop_requested,progress):
    track=Trajectory(directory,stop_requested=stop_requested,
                     progress=lambda done,total:progress('Проверка файлов',done,total))
    frames=[]
    for index in range(len(track.times)):
        if stop_requested():raise CancelledError()
        state,_=track.frame(index)
        frames.append({b.name:(b.position.x,b.position.y,b.position.z) for b in state.bodies})
        progress('Подготовка просмотра',index+1,len(track.times))
    if stop_requested():raise CancelledError()
    return track,frames


class TrajectoryLoader:
    def __init__(self,window,directory):
        self._start(window,partial(prepare_trajectory,directory),
                    'Solar — открытие траектории','Траектория не открыта')

    def _start(self,window,prepare,title,error_title):
        """Shared lifecycle for the two read-only recording loaders."""
        self.window=window;self.viewer=None;self.closed=False;self._timer=None
        self.error_title=error_title
        self.stop=Event();self.messages=Queue(maxsize=1)
        self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='solar-trajectory-reader')
        window.title(title)
        self.status=tk.StringVar(master=window,value='Проверка записи…')
        ttk.Label(window,textvariable=self.status,wraplength=540).pack(padx=16,pady=12)
        self.progress=ttk.Progressbar(window,length=440,maximum=1)
        self.progress.pack(padx=16,pady=8)
        ttk.Button(window,text='Отмена',command=self.close).pack(pady=12)
        window.protocol('WM_DELETE_WINDOW',self.close)
        window.bind('<Destroy>',self._destroyed,add='+')
        # The worker owns only an Event/Queue, never a bound Tk controller.
        self.future=self.pool.submit(prepare,self.stop.is_set,partial(_report,self.messages))
        self._timer=window.after(40,self._poll)

    def _poll(self):
        if self.closed:return
        self._timer=None
        try:
            phase,done,total=self.messages.get_nowait()
            self.status.set(f'{phase}: {done}/{total}')
            self.progress.configure(maximum=total,value=done)
        except Empty:pass
        if not self.future.done():
            self._timer=self.window.after(40,self._poll);return
        try:result=self.future.result()
        except CancelledError:self.close();return
        except Exception as error:
            detail=str(error);error.__traceback__=None
            try:messagebox.showerror(self.error_title,detail,parent=self.window)
            finally:self.close()
            return
        self._release()
        for widget in self.window.winfo_children():widget.destroy()
        try:self._show(result)
        except Exception as error:
            try:messagebox.showerror(self.error_title,str(error),parent=self.window)
            finally:self.window.destroy()

    def _show(self,result):
        track,frames=result
        from .trajectory_view import TrajectoryViewer
        self.viewer=TrajectoryViewer(self.window,track,frames=frames)

    def _release(self):
        if self.closed:return
        self.closed=True;self.stop.set()
        if self._timer is not None:
            self.window.after_cancel(self._timer);self._timer=None
        self.pool.shutdown(wait=False,cancel_futures=True)

    def _destroyed(self,event):
        if event.widget is self.window:self._release()

    def close(self):
        self._release()
        if self.window.winfo_exists():self.window.destroy()
