"""Tk/Matplotlib лаборатория. Физика в рабочем потоке, Tk только в главном."""
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from .cli import report
from .experiment import PRESETS, Settings, advance, create_experiment, preset, reset
from .simulation import Body, total_energy
from .storage import load, save
from .vector3 import Vector3


class Laboratory:
    def __init__(self, root, experiment=None):
        self.root = root
        self.root.title("Solar Simulator — лаборатория ньютоновской гравитации")
        self.root.geometry("1180x820")
        self.experiment = experiment or preset("sun-earth")
        self.pool = ThreadPoolExecutor(max_workers=1,thread_name_prefix="solar-physics")
        self.future = None
        self.running = False
        self.closed = False
        self.frames = deque(maxlen=1500)
        self.energies = deque(maxlen=1500)
        self.actions = []
        self.scenario = tk.StringVar(value="sun-earth")
        self.backend = tk.StringVar(value=self.experiment.settings.backend)
        self.dt = tk.StringVar(value=f"{self.experiment.settings.dt:.17g}")
        self.mode = tk.StringVar(value=self.experiment.settings.contact_mode)
        self.restitution = tk.StringVar(value=str(self.experiment.settings.restitution))
        self.batch = tk.StringVar(value="20")
        self.eccentricity = tk.StringVar(value="0")
        self.reference = tk.StringVar(value="Инерциальная")
        self.plane = tk.StringVar(value="XY")
        self.status = tk.StringVar()
        self.details = tk.StringVar()
        self._build()
        self._set_experiment(self.experiment)
        self.root.protocol("WM_DELETE_WINDOW",self.close)
        self.root.after(40,self._poll)

    def _button(self,parent,text,command):
        widget = ttk.Button(parent,text=text,command=lambda:self._guard(command))
        widget.pack(side="left",padx=3,pady=4)
        self.actions.append(widget)
        return widget

    def _entry(self,parent,label,variable,width=12):
        ttk.Label(parent,text=label).pack(side="left",padx=(8,2))
        widget=ttk.Entry(parent,textvariable=variable,width=width)
        widget.pack(side="left")
        self.actions.append(widget)
        return widget

    def _combo(self,parent,label,variable,values,width=14,callback=None,lock=True):
        ttk.Label(parent,text=label).pack(side="left",padx=(8,2))
        widget=ttk.Combobox(parent,textvariable=variable,values=values,state="readonly",width=width)
        widget.pack(side="left")
        if callback:
            widget.bind("<<ComboboxSelected>>",lambda _:callback())
        if lock:
            self.actions.append(widget)
        return widget

    def _build(self):
        top=ttk.Frame(self.root); top.pack(fill="x",padx=8)
        self._combo(top,"Сценарий",self.scenario,PRESETS,width=19)
        self._entry(top,"Эксцентриситет Земли",self.eccentricity,7)
        self._button(top,"Новый сценарий",self._new)
        self._button(top,"Открыть JSON",self._load)
        self._button(top,"Сохранить JSON",self._save)
        self._button(top,"Сбросить",self._reset)
        controls=ttk.Frame(self.root); controls.pack(fill="x",padx=8)
        self._combo(controls,"Ядро",self.backend,("python","rust"),width=8)
        self._entry(controls,"dt, с",self.dt,15)
        self._combo(controls,"Контакт",self.mode,("stop","bounce","merge"),width=8)
        self._entry(controls,"Упругость",self.restitution,6)
        self._button(controls,"Применить параметры",self._settings)
        playback=ttk.Frame(self.root); playback.pack(fill="x",padx=8)
        self.start_button=self._button(playback,"Запуск",self._start)
        self.pause_button=ttk.Button(playback,text="Пауза",command=self._pause)
        self.pause_button.pack(side="left",padx=3)
        self.step_button=self._button(playback,"Один шаг",lambda:self._submit(1))
        self._entry(playback,"Шагов за кадр (скорость)",self.batch,7)
        self.reference_widget=self._combo(playback,"Относительно",self.reference,("Инерциальная",),
            callback=self._draw,lock=False,width=16)
        self._combo(playback,"Проекция",self.plane,("XY","XZ","YZ"),width=5,callback=self._draw,lock=False)
        self._button(playback,"Изменить тело…",self._edit)
        ttk.Label(self.root,text="Все физические величины в SI. Размер маркеров условный. Начальные орбиты учебные, без эфемерид.",
                  anchor="w").pack(fill="x",padx=12,pady=(4,0))
        self.figure=Figure(figsize=(10,6),dpi=100)
        self.orbit=self.figure.add_subplot(211)
        self.energy=self.figure.add_subplot(212)
        self.figure.subplots_adjust(left=.09,right=.96,hspace=.45,bottom=.09,top=.95)
        self.canvas=FigureCanvasTkAgg(self.figure,master=self.root)
        self.canvas.get_tk_widget().pack(fill="both",expand=True)
        toolbar=NavigationToolbar2Tk(self.canvas,self.root,pack_toolbar=False)
        toolbar.pack(fill="x")
        ttk.Label(self.root,textvariable=self.status,anchor="w").pack(fill="x",padx=12,pady=2)
        ttk.Label(self.root,textvariable=self.details,anchor="w",wraplength=1140).pack(fill="x",padx=12,pady=(0,8))

    def _guard(self,action):
        if self.future is not None or self.running:
            return
        try:
            action()
        except (ValueError,RuntimeError,OSError,OverflowError,ImportError) as error:
            messagebox.showerror("Расчёт не выполнен",str(error),parent=self.root)

    def _lock(self):
        busy=self.future is not None or self.running
        for widget in self.actions:
            if busy:
                widget.configure(state="disabled")
            else:
                widget.configure(state="readonly" if isinstance(widget,ttk.Combobox) else "normal")

    def _settings(self):
        settings=Settings(float(self.dt.get()),self.backend.get(),self.mode.get(),float(self.restitution.get()))
        if self.experiment.halted and settings.contact_mode in ("bounce","merge"):
            # Только явный выбор модели разрешает продолжить остановленный контакт.
            self.experiment=replace(self.experiment,settings=settings,halted=False)
        else:
            self.experiment=replace(self.experiment,settings=settings)
        self._draw()

    def _new(self):
        self._set_experiment(preset(self.scenario.get(),backend=self.backend.get(),
                                    eccentricity=float(self.eccentricity.get())))

    def _reset(self):
        self._set_experiment(reset(self.experiment))

    def _load(self):
        path=filedialog.askopenfilename(parent=self.root,filetypes=[("Solar JSON","*.json")])
        if path:
            self._set_experiment(load(path))

    def _save(self):
        path=filedialog.asksaveasfilename(parent=self.root,defaultextension=".json",
                                        filetypes=[("Solar JSON","*.json")])
        if path:
            save(self.experiment,path)

    def _set_experiment(self,experiment):
        self.experiment=experiment
        self.running=False
        self.frames.clear(); self.energies.clear()
        self.backend.set(experiment.settings.backend)
        self.dt.set(f"{experiment.settings.dt:.17g}")
        self.mode.set(experiment.settings.contact_mode)
        self.restitution.set(str(experiment.settings.restitution))
        self.reference.set("Инерциальная")
        self.reference_widget.configure(values=("Инерциальная",)+tuple("Тело: "+b.name for b in experiment.bodies))
        self._record()
        self._draw()
        self._lock()

    def _record(self):
        self.frames.append({b.name:(b.position.x,b.position.y,b.position.z) for b in self.experiment.bodies})
        residual=total_energy(self.experiment.bodies)+self.experiment.dissipated_energy+self.experiment.model_energy_offset-total_energy(self.experiment.initial)
        self.energies.append((self.experiment.time,residual))
        self.reference_widget.configure(values=("Инерциальная",)+tuple("Тело: "+b.name for b in self.experiment.bodies))
        if self.reference.get() not in self.reference_widget.cget("values"):
            self.reference.set("Инерциальная")

    def _start(self):
        self._settings()
        if self.experiment.halted:
            raise ValueError("Расчёт остановлен при контакте. Сбросьте сценарий или явно выберите bounce/merge.")
        self._batch_size()  # Ошибка ввода выявляется до запуска.
        self.running=True
        self._lock()

    def _pause(self):
        self.running=False
        self._lock()
        self._draw()

    def _batch_size(self):
        value=int(self.batch.get())
        if not 1<=value<=2000:
            raise ValueError("Шагов за кадр: от 1 до 2000")
        return value

    def _submit(self,steps):
        if self.future is None:
            if not self.running:
                self._settings()
            self.future=self.pool.submit(advance,self.experiment,steps)
            self._lock()

    def _poll(self):
        if self.closed:
            return
        if self.future is not None and self.future.done():
            future=self.future
            self.future=None
            try:
                self.experiment=future.result()
                self._record()
                if self.experiment.halted:
                    self.running=False
                self._draw()
            except Exception as error:
                self.running=False
                messagebox.showerror("Расчёт остановлен",str(error),parent=self.root)
            self._lock()
        if self.running and self.future is None:
            self._submit(self._batch_size())
        self.root.after(40,self._poll)

    def _draw(self):
        axes={"XY":(0,1),"XZ":(0,2),"YZ":(1,2)}
        x,y=axes[self.plane.get()]
        names=[b.name for b in self.experiment.bodies]
        references=["Тело: "+name for name in names]
        reference=references.index(self.reference.get()) if self.reference.get() in references else None
        reference_name=names[reference] if reference is not None else None
        self.orbit.clear(); self.energy.clear()
        for i,name in enumerate(names):
            points=[(f[name][x]-(f[reference_name][x] if reference_name is not None else 0),
                     f[name][y]-(f[reference_name][y] if reference_name is not None else 0)) for f in self.frames
                     if name in f and (reference_name is None or reference_name in f)]
            line,=self.orbit.plot([p[0] for p in points],[p[1] for p in points],linewidth=1,label=name)
            self.orbit.plot(*points[-1],marker="o",markersize=6,color=line.get_color())
        self.orbit.set_xlabel(f"{'XYZ'[x]}, м"); self.orbit.set_ylabel(f"{'XYZ'[y]}, м")
        self.orbit.set_aspect("equal",adjustable="datalim")
        self.orbit.grid(alpha=.25); self.orbit.legend(loc="upper right",fontsize=8)
        self.energy.plot([p[0] for p in self.energies],[p[1] for p in self.energies],color="#b35c1e")
        self.energy.set_xlabel("Время, с"); self.energy.set_ylabel("Остаток баланса, Дж")
        self.energy.grid(alpha=.25)
        values=report(self.experiment)
        state="контакт: остановка" if self.experiment.halted else ("работает" if self.running else "пауза")
        self.status.set(f"t = {values['time_seconds']:.9g} с | dt = {self.experiment.settings.dt:.6g} с | "
                        f"{state} | {len(names)} тел | событий: {values['events']} | "
                        f"потери: {values['dissipated_energy_joules']:.6g} Дж")
        fmt=lambda vector:', '.join(f"{v:.4g}" for v in vector)
        self.details.set(f"Импульс (кг·м/с): [{fmt(values['momentum'])}]   "
                         f"Угловой момент (кг·м²/с): [{fmt(values['angular_momentum'])}]   "
                         f"Центр масс (м): [{fmt(values['center_of_mass'])}]. Графики по снимкам; до 1500 кадров.")
        self.canvas.draw_idle()

    def _edit(self):
        dialog=tk.Toplevel(self.root)
        dialog.title("Новое начальное состояние — время и история будут сброшены")
        dialog.transient(self.root); dialog.grab_set()
        selected=tk.StringVar(value=self.experiment.bodies[0].name)
        combo=ttk.Combobox(dialog,textvariable=selected,values=[b.name for b in self.experiment.bodies],state="readonly")
        combo.grid(row=0,column=0,columnspan=2,padx=10,pady=8)
        fields=("Имя","Масса, кг","Радиус, м","x, м","y, м","z, м","vx, м/с","vy, м/с","vz, м/с")
        variables=[tk.StringVar() for _ in fields]
        for row,(field,variable) in enumerate(zip(fields,variables),start=1):
            ttk.Label(dialog,text=field).grid(row=row,column=0,sticky="w",padx=10,pady=3)
            ttk.Entry(dialog,textvariable=variable,width=30).grid(row=row,column=1,padx=10)
        def populate(_=None):
            b=next(b for b in self.experiment.bodies if b.name==selected.get())
            values=(b.name,b.mass,b.radius,b.position.x,b.position.y,b.position.z,b.velocity.x,b.velocity.y,b.velocity.z)
            for variable,value in zip(variables,values):
                variable.set(value if isinstance(value,str) else f"{value:.17g}")
        def apply():
            try:
                values=[v.get() for v in variables]
                mass,radius,x,y,z,vx,vy,vz=map(float,values[1:])
                bodies=list(self.experiment.bodies)
                index=next(i for i,b in enumerate(bodies) if b.name==selected.get())
                body=Body(values[0],mass,Vector3(x,y,z),Vector3(vx,vy,vz),radius,bodies[index].spin)
                bodies[index]=body
                self._set_experiment(create_experiment(bodies,self.experiment.settings))
                dialog.destroy()
            except (ValueError,OverflowError) as error:
                messagebox.showerror("Неверное тело",str(error),parent=dialog)
        combo.bind("<<ComboboxSelected>>",populate)
        populate()
        ttk.Button(dialog,text="Применить как новый эксперимент",command=apply).grid(row=10,column=0,columnspan=2,pady=12)

    def close(self):
        self.closed=True
        self.running=False
        self.pool.shutdown(wait=False,cancel_futures=True)
        self.root.destroy()


def launch(experiment=None):
    root=tk.Tk()
    Laboratory(root,experiment)
    root.mainloop()
