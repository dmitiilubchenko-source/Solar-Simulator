"""Read-only desktop playback of saved packet endpoints."""
from time import monotonic
import tkinter as tk
from tkinter import filedialog,messagebox,ttk
from pathlib import Path

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg,NavigationToolbar2Tk
from matplotlib.figure import Figure

from .plot_artists import PlotArtists
from .playback import Playback


class TrajectoryViewer:
    def __init__(self,window,trajectory,*,frames=None):
        self.window=window;self.player=Playback(trajectory)
        self.window.title('Solar — просмотр записанной траектории')
        self.window.geometry('1000x750')
        self.frames=frames
        if self.frames is None:
            self.frames=[]
            for index in range(len(trajectory.times)):
                state,_=trajectory.frame(index)
                self.frames.append({b.name:(b.position.x,b.position.y,b.position.z) for b in state.bodies})
        controls=ttk.Frame(window);controls.pack(fill='x',padx=8,pady=6)
        ttk.Button(controls,text='Просмотр',command=self._play).pack(side='left')
        ttk.Button(controls,text='Пауза',command=self.player.pause).pack(side='left')
        ttk.Button(controls,text='Снимок JSON…',command=self._export_frame).pack(side='left')
        ttk.Button(controls,text='Рецепт…',command=self._recipe).pack(side='left')
        self.rate=tk.StringVar(value='10')
        ttk.Label(controls,text='Снимков/с').pack(side='left',padx=(10,3))
        ttk.Entry(controls,textvariable=self.rate,width=8).pack(side='left')
        ttk.Label(controls,text='Проекция').pack(side='left',padx=(10,3))
        self.plane=tk.StringVar(value='XY')
        plane=ttk.Combobox(controls,textvariable=self.plane,values=('XY','XZ','YZ'),state='readonly',width=5)
        plane.pack(side='left');plane.bind('<<ComboboxSelected>>',lambda event:self._draw())
        self.reference=ttk.Combobox(controls,state='readonly',width=25)
        self.reference.pack(side='left',padx=8);self.reference.bind('<<ComboboxSelected>>',lambda event:self._draw())
        self.references=(None,)
        self.position=tk.DoubleVar(value=0.)
        self.slider=ttk.Scale(window,from_=0,to=len(trajectory.times)-1,variable=self.position,command=self._seek)
        self.slider.pack(fill='x',padx=10)
        self.status=tk.StringVar()
        ttk.Label(window,textvariable=self.status,wraplength=950).pack(fill='x',padx=10,pady=4)
        ttk.Label(window,text='Только сохранённые снимки. Нет расчёта и интерполяции между ними.').pack()
        self.figure=Figure(figsize=(9,5),dpi=100);self.axis=self.figure.add_subplot(111)
        self._plot_artists=PlotArtists(self.axis)
        self.canvas=FigureCanvasTkAgg(self.figure,master=window)
        self.canvas.get_tk_widget().pack(fill='both',expand=True)
        NavigationToolbar2Tk(self.canvas,window)
        self.closed=False;self._last=monotonic();self._timer=None
        window.protocol('WM_DELETE_WINDOW',self.close)
        self._draw();self._timer=window.after(40,self._tick)

    def _draw(self):
        index=self.player.index;names=tuple(self.frames[index])
        selected=self.references[self.reference.current()] if self.reference.current()>=0 else None
        self.references=(None,)+names
        self.reference.configure(values=('Инерциальная',)+names)
        self.reference.current(self.references.index(selected) if selected in self.references else 0)
        reference=self.references[self.reference.current()]
        axes={'XY':(0,1),'XZ':(0,2),'YZ':(1,2)}[self.plane.get()]
        self._plot_artists.update(self.frames[:index+1],names,reference,axes,())
        self.axis.set_xlabel(self.plane.get()[0]+', м');self.axis.set_ylabel(self.plane.get()[1]+', м')
        self.axis.set_aspect('equal',adjustable='datalim')
        self.position.set(index)
        track=self.player.trajectory
        self.status.set(f'Снимок {index+1}/{len(track.times)} | t={track.times[index]:.17g} с | '
                        f'запись: {track.metadata["status"]} | {track.directory}')
        self.canvas.draw_idle()

    def _play(self):
        try:
            self.player.tick(0.,float(self.rate.get()))
            if self.player.index==len(self.frames)-1:self.player.seek(0)
            self.player.play();self._last=monotonic();self._draw()
        except (ValueError,OverflowError) as error:messagebox.showerror('Просмотр',str(error),parent=self.window)

    def _seek(self,value):
        self.player.seek(int(round(float(value))));self._last=monotonic();self._draw()

    def _recipe(self):
        try:
            from .recipe import audit_recipe
            result=audit_recipe(self.player.trajectory)
            text=('Код и окружение совпадают с рецептом записи.' if result['compatible'] else
                  'Несовпадение: '+', '.join(result['differences']))
            messagebox.showinfo('Рецепт опыта',text+'\nЭто проверка происхождения, не физической точности.',parent=self.window)
        except (ValueError,OSError,RuntimeError,OverflowError,ImportError) as error:
            messagebox.showerror('Рецепт недоступен',str(error),parent=self.window)

    def _export_frame(self):
        path=filedialog.asksaveasfilename(parent=self.window,defaultextension='.json',filetypes=[('Solar JSON','*.json')])
        if not path:return
        try:
            if Path(path).resolve().is_relative_to(self.player.trajectory.directory):
                raise ValueError('Сохраняйте копию вне каталога исходной траектории')
            from .branch_io import save_experiment
            state,parent=self.player.state
            save_experiment(state,path,parent_snapshot=parent)
        except (ValueError,OSError,RuntimeError,OverflowError) as error:
            messagebox.showerror('Снимок не сохранён',str(error),parent=self.window)

    def _tick(self):
        if self.closed:return
        now=monotonic()
        try:
            before=self.player.index
            self.player.tick(now-self._last,float(self.rate.get()))
            if self.player.index!=before:self._draw()
        except (ValueError,OverflowError) as error:
            self.player.pause();self.rate.set('10')
            messagebox.showerror('Просмотр',str(error),parent=self.window)
        self._last=now;self._timer=self.window.after(40,self._tick)

    def close(self):
        if self.closed:return
        self.closed=True
        if self._timer is not None:self.window.after_cancel(self._timer)
        self.window.destroy()


def launch(directory):
    from .trajectory_loader import TrajectoryLoader
    root=tk.Tk();TrajectoryLoader(root,directory);root.mainloop()
