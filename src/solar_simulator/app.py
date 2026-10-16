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
from .simulation import Body
from .storage import load, save
from .vector3 import Vector3
from .scenario_catalog import CATALOG, ScenarioVariable
from .control_row import ControlRow
from .time_control import advance_towards, validate_target


class Laboratory:
    def __init__(self, root, experiment=None):
        self.root = root
        self.root.title("Solar Simulator — гравитационная лаборатория")
        self.root.geometry("1180x820")
        self.root.minsize(860,640)
        self.experiment = experiment or preset("sun-earth")
        if experiment is None:
            self.experiment = replace(self.experiment, settings=replace(self.experiment.settings, integrator="dop853"))
        self.pool = ThreadPoolExecutor(max_workers=1,thread_name_prefix="solar-physics")
        self.future = None
        self.running = False
        self.target_time = None
        self.parent_snapshot = None
        self.closed = False
        self.frames = deque(maxlen=1500)
        self.energies = deque(maxlen=1500)
        self.actions = []
        self.scenario = ScenarioVariable(value="sun-earth")
        self.scenario_info = tk.StringVar(value=CATALOG["sun-earth"][1])
        self.scenario.trace_add("write",lambda *_:self.scenario_info.set(CATALOG[self.scenario.get()][1]))
        self.backend = tk.StringVar(value=self.experiment.settings.backend)
        self.integrator = tk.StringVar(value=self.experiment.settings.integrator)
        self.physics = tk.StringVar(value=self.experiment.settings.physics)
        self.figures = tk.StringVar(value="saved" if self.experiment.settings.figures else "none")
        self.relative_pair = tk.StringVar(value="saved" if self.experiment.settings.relative_pair else "none")
        self.rtol = tk.StringVar(value=str(self.experiment.settings.rtol))
        self.position_atol = tk.StringVar(value=str(self.experiment.settings.position_atol))
        self.velocity_atol = tk.StringVar(value=str(self.experiment.settings.velocity_atol))
        self.error_control = tk.StringVar(value=self.experiment.settings.error_control)
        self.dt = tk.StringVar(value=f"{self.experiment.settings.dt:.17g}")
        self.mode = tk.StringVar(value=self.experiment.settings.contact_mode)
        self.restitution = tk.StringVar(value=str(self.experiment.settings.restitution))
        self.batch = tk.StringVar(value="20")
        self.target = tk.StringVar(value="31557600")
        self.eccentricity = tk.StringVar(value="0")
        self.reference = tk.StringVar(value="Инерциальная")
        self.view = tk.StringVar(value="Все тела")
        self.plane = tk.StringVar(value="XY")
        self.status = tk.StringVar()
        self.details = tk.StringVar()
        self.model_info = tk.StringVar()
        self._build()
        self._set_experiment(self.experiment)
        self.root.protocol("WM_DELETE_WINDOW",self.close)
        self.root.after(40,self._poll)

    def _button(self,parent,text,command):
        widget = ttk.Button(parent,text=text,command=lambda:self._guard(command))
        parent.add(widget)
        self.actions.append(widget)
        return widget

    def _entry(self,parent,label,variable,width=12):
        group=ttk.Frame(parent); parent.add(group)
        ttk.Label(group,text=label).pack(side="left",padx=(3,2))
        widget=ttk.Entry(group,textvariable=variable,width=width)
        widget.pack(side="left")
        self.actions.append(widget)
        return widget

    def _combo(self,parent,label,variable,values,width=14,callback=None,lock=True):
        group=ttk.Frame(parent); parent.add(group)
        ttk.Label(group,text=label).pack(side="left",padx=(3,2))
        widget=ttk.Combobox(group,textvariable=variable,values=values,state="readonly",width=width)
        widget.pack(side="left")
        if callback:
            widget.bind("<<ComboboxSelected>>",lambda _:callback())
        if lock:
            self.actions.append(widget)
        return widget

    def _build(self):
        top=ControlRow(self.root); top.pack(fill="x",padx=8)
        self.scenario_widget=self._combo(top,"Новый опыт",self.scenario,tuple(CATALOG[key][0] for key in PRESETS),width=39,
                                        callback=lambda:self._guard(self._select_scenario))
        self._entry(top,"Эксцентриситет Земли",self.eccentricity,7)
        self._button(top,"Новый сценарий",self._new)
        self._button(top,"Открыть JSON",self._load)
        self._button(top,"Сохранить JSON",self._save)
        self._button(top,"Сбросить",self._reset)
        self.scenario_info_widget=ttk.Label(self.root,textvariable=self.scenario_info,anchor="w",wraplength=1140)
        self.scenario_info_widget.pack(fill="x",padx=12,pady=3)
        quick=ControlRow(self.root); quick.pack(fill="x",padx=8)
        self._button(quick,"Луна: свободное вращение",self._open_lunar_rotation)
        self._button(quick,"Солнечная система: EIH + J2",self._open_solar_sandbox)
        self.settings_button=self._button(quick,"Настройки расчёта",self._toggle_settings)
        self.view_widget=self._combo(quick,"Показать",self.view,("Все тела",),width=16,
                                     callback=self._draw,lock=False)
        self.settings_frame=ttk.Frame(self.root)
        self.settings_visible=False
        controls=ControlRow(self.settings_frame); controls.pack(fill="x",padx=8)
        self._combo(controls,"Ядро",self.backend,("python","rust"),width=8)
        self._entry(controls,"dt, с",self.dt,15)
        self._combo(controls,"Контакт",self.mode,("stop","bounce","merge"),width=8)
        self._entry(controls,"Упругость",self.restitution,6)
        self._button(controls,"Применить параметры",self._settings)
        precision=ControlRow(self.settings_frame); precision.pack(fill="x",padx=8)
        self._combo(precision,"Интегратор",self.integrator,("verlet","dop853"),width=9)
        self._entry(precision,"Отн. допуск",self.rtol,10)
        self._entry(precision,"Допуск x, м",self.position_atol,10)
        self._entry(precision,"Допуск v, м/с",self.velocity_atol,10)
        error_controls=ControlRow(self.settings_frame); error_controls.pack(fill="x",padx=8)
        self._combo(error_controls,"Контроль ошибки",self.error_control,("per-body","global-rms"),width=12)
        error_controls.add(ttk.Label(error_controls,text="DOP853: локальные допуски; per-body проверяет каждую орбиту"))
        physics=ControlRow(self.settings_frame); physics.pack(fill="x",padx=8)
        self._combo(physics,"Физика",self.physics,("newtonian","eih-1pn"),width=14)
        self._combo(physics,"Фигура",self.figures,("none","earth-j2","earth-q2","earth-moon-q2","solar-j2","sun-earth-moon-q2","saved"),width=18)
        self._combo(physics,"Точность пары",self.relative_pair,("none","earth-moon","saved"),width=12)
        physics.add(ttk.Label(physics,text="Заданные q2: до 365.25 суток; DOP853"))
        playback=ControlRow(self.root); playback.pack(fill="x",padx=8)
        self.playback_frame=playback
        self.start_button=self._button(playback,"Запуск",self._start)
        self.pause_button=ttk.Button(playback,text="Пауза",command=self._pause)
        playback.add(self.pause_button)
        self.step_button=self._button(playback,"Один шаг",lambda:self._submit(1))
        self._entry(playback,"Шагов за кадр (скорость)",self.batch,7)
        self.reference_widget=self._combo(playback,"Относительно",self.reference,("Инерциальная",),
            callback=self._draw,lock=False,width=16)
        self._combo(playback,"Проекция",self.plane,("XY","XZ","YZ"),width=5,callback=self._draw,lock=False)
        self._button(playback,"Изменить тело…",self._edit)
        self._button(playback,"Добавить тело…",self._add_body)
        self._button(playback,"Удалить тело…",self._remove_body)
        destination=ControlRow(self.root); destination.pack(fill="x",padx=8)
        self._entry(destination,"До t, с от начала",self.target,17)
        self.target_button=self._button(destination,"Рассчитать до t",self._start_target)
        destination.add(ttk.Label(destination,text="Вперёд; пауза ждёт пакет"))
        self.parent_button=self._button(destination,"Вернуть родителя…",self._restore_parent)
        self.model_info_widget=ttk.Label(self.root,textvariable=self.model_info,anchor="w",wraplength=1140)
        self.model_info_widget.pack(fill="x",padx=12,pady=(4,0))
        self.figure=Figure(figsize=(10,6),dpi=100)
        self.orbit=self.figure.add_subplot(211)
        self.energy=self.figure.add_subplot(212)
        self.figure.subplots_adjust(left=.09,right=.96,hspace=.45,bottom=.09,top=.95)
        self.canvas=FigureCanvasTkAgg(self.figure,master=self.root)
        # Reserve the footer before the expandable canvas consumes the cavity.
        footer=ttk.Frame(self.root); footer.pack(side="bottom",fill="x")
        toolbar=NavigationToolbar2Tk(self.canvas,footer,pack_toolbar=False)
        toolbar.pack(fill="x")
        self.status_widget=ttk.Label(footer,textvariable=self.status,anchor="w",wraplength=1140)
        self.status_widget.pack(fill="x",padx=12,pady=2)
        self.details_widget=ttk.Label(footer,textvariable=self.details,anchor="w",wraplength=1140)
        self.details_widget.pack(fill="x",padx=12,pady=(0,8))
        self.canvas.get_tk_widget().pack(fill="both",expand=True)
        self.canvas.get_tk_widget().bind("<Configure>",self._fit_graph,add="+")
        self.root.bind("<Configure>",self._resize_text,add="+")

    def _fit_graph(self,event):
        height=max(100,event.height)
        # Reserve pixel space for tick labels, axis labels and the lower title.
        usable=max(80,height-73)
        self.figure.subplots_adjust(top=1-28/height,bottom=min(.3,45/height),
                                    hspace=130/max(30,usable-65))
        self.canvas.draw_idle()

    def _toggle_settings(self):
        self.settings_visible=not self.settings_visible
        if self.settings_visible:
            self.settings_frame.pack(fill="x",before=self.playback_frame)
        else:
            self.settings_frame.pack_forget()
        self.settings_button.configure(text="Скрыть настройки" if self.settings_visible else "Настройки расчёта")

    def _resize_text(self,event):
        if event.widget is self.root:
            for widget in (self.scenario_info_widget,self.model_info_widget,self.status_widget,self.details_widget):
                widget.configure(wraplength=max(100,event.width-24))

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
        self.pause_button.configure(state="normal" if busy else "disabled")
        self.parent_button.configure(state="disabled" if busy or self.parent_snapshot is None else "normal")

    def _settings(self):
        settings=Settings(float(self.dt.get()),self.backend.get(),self.mode.get(),float(self.restitution.get()),
            self.integrator.get(),float(self.rtol.get()),float(self.position_atol.get()),float(self.velocity_atol.get()),
            self.physics.get(),self._selected_figures(self.experiment),self._selected_pair(self.experiment),self.error_control.get())
        changed_physics = (settings.physics != self.experiment.settings.physics
                           or settings.figures != self.experiment.settings.figures)
        if changed_physics and self.experiment.time > 0:
            raise ValueError("Смена физики требует нового сценария или сброса времени")
        if settings.physics == "eih-1pn":
            from .relativity import validate_bodies
            validate_bodies(self.experiment.bodies)
        if settings.integrator == "dop853" and any(b.radius > 0 for b in self.experiment.bodies):
            raise ValueError("DOP853 поддерживает только точечные тела без контактов")
        from .oblateness import validate_figures, validate_orientation_origin
        validate_figures(self.experiment.bodies, settings.figures, self.experiment.time)
        validate_orientation_origin(settings.figures, self.experiment.origin)
        from .coordinates import prepare_pair
        prepare_pair(self.experiment.bodies,settings.relative_pair)
        if self.experiment.rotations or self.experiment.initial_rotations:
            from .nbody_rotation import validate_experiment
            validate_experiment(replace(self.experiment, settings=settings))
        if self.experiment.halted and settings.contact_mode in ("bounce","merge"):
            # Только явный выбор модели разрешает продолжить остановленный контакт.
            self.experiment=replace(self.experiment,settings=settings,halted=False)
        else:
            self.experiment=replace(self.experiment,settings=settings)
        if changed_physics:
            self.energies.clear()
            values=self._record()
        else:
            values=None
        self._draw(values)

    def _selected_figures(self, experiment, *, new=False):
        if self.figures.get()=="none":
            return ()
        if self.figures.get()=="earth-j2":
            from .oblateness import earth_j2
            return earth_j2(experiment.bodies, experiment.origin)
        if self.figures.get() in ("earth-q2", "earth-moon-q2"):
            from .oblateness import earth_moon_quadrupoles
            return earth_moon_quadrupoles(experiment.bodies, experiment.origin, moon=self.figures.get()=="earth-moon-q2")
        if self.figures.get()=="solar-j2":
            from .oblateness import solar_j2
            return solar_j2(experiment.bodies,experiment.origin)
        if self.figures.get()=="sun-earth-moon-q2":
            from .oblateness import sun_earth_moon_quadrupoles
            return sun_earth_moon_quadrupoles(experiment.bodies,experiment.origin)
        if self.figures.get()=="saved" and not new:
            return experiment.settings.figures
        raise ValueError("Для нового сценария выберите none или профиль фигуры; saved сохраняет параметры открытого JSON")

    def _selected_pair(self, experiment, *, new=False):
        option = self.relative_pair.get()
        if option == "none":
            return None
        if option == "earth-moon":
            return ("Earth","Moon")
        if option == "saved" and not new:
            return experiment.settings.relative_pair
        raise ValueError("Для нового сценария выберите none или earth-moon; saved сохраняет пару из JSON")

    def _new(self):
        experiment = preset(self.scenario.get(),backend=self.backend.get(),
                            eccentricity=float(self.eccentricity.get()))
        settings = replace(experiment.settings, integrator=self.integrator.get(),
                           rtol=float(self.rtol.get()), position_atol=float(self.position_atol.get()),
                           velocity_atol=float(self.velocity_atol.get()),physics=self.physics.get(),
                           figures=self._selected_figures(experiment,new=True),relative_pair=self._selected_pair(experiment,new=True),
                           error_control=self.error_control.get())
        self._set_experiment(create_experiment(experiment.bodies, settings,origin=experiment.origin))

    def _select_scenario(self):
        from .application_profiles import scenario
        prepared=scenario(self.scenario.get(),backend=self.backend.get(),
                          eccentricity=float(self.eccentricity.get()))
        self._sync_settings(prepared.settings)

    def _open_lunar_rotation(self):
        from .application_profiles import lunar_rotation
        prepared=lunar_rotation(backend=self.backend.get())
        self._set_experiment(prepared)
        self.scenario.set("solar-system-moon")

    def _reset(self):
        self._set_experiment(reset(self.experiment),parent_snapshot=self.parent_snapshot)

    def _load(self):
        path=filedialog.askopenfilename(parent=self.root,filetypes=[("Solar JSON","*.json")])
        if path:
            from .branch_io import open_experiment
            experiment,snapshot=open_experiment(path)
            self._set_experiment(experiment,parent_snapshot=snapshot)

    def _save(self):
        path=filedialog.asksaveasfilename(parent=self.root,defaultextension=".json",
                                        filetypes=[("Solar JSON","*.json")])
        if path:
            save(self.experiment,path)

    def _set_experiment(self,experiment,*,parent_snapshot=None):
        self.experiment=experiment
        self.parent_snapshot=parent_snapshot
        if experiment.origin:
            self.model_info.set(("Основа JPL + собственная геометрия кольца; " if any(b.name.startswith("Kuiper-Ring-") for b in experiment.initial) else "JPL ")
                + f"{experiment.origin.ephemeris}; начальная эпоха JD {experiment.origin.epoch_jd_tdb:.9f} TDB. "
                + ("Земля и Луна отдельно; остальные планетные системы точечные; SI."
                 if {"Earth", "Moon"}.issubset({b.name for b in experiment.initial})
                 else "Барицентры планетных систем; SI; размер маркеров условный.")
                + (" Добавлены Церера, Паллада и Веста." if any(b.name=="Ceres" for b in experiment.initial) else "")
                + (" Всего 16 крупных астероидов SB441." if len(experiment.initial)==27 and any(b.name=="Interamnia" for b in experiment.initial) else "")
                + (" Полный набор 343 астероидов DE441; 354 взаимодействующих тела." if len(experiment.initial)==354 else "")
                + (" 343 астероида и 30 отдельных объектов Койпера; 384 взаимодействующих тела." if len(experiment.initial)==384 else "")
                + (" Остаточное кольцо Койпера: собственная автономная аппроксимация, все точки взаимодействуют; начальные фазы DE441 не восстановлены." if any(b.name.startswith("Kuiper-Ring-") for b in experiment.initial) else "")
                + (" Добавлен барицентр системы Плутона." if any(b.name=="Pluto-System" for b in experiment.initial) else ""))
        else:
            self.model_info.set("Все величины в SI. Размер маркеров условный. Учебные начальные условия, без эфемерид.")
        self.running=False
        self.target_time=None
        self.frames.clear(); self.energies.clear()
        self._sync_settings(experiment.settings)
        self.reference.set("Инерциальная")
        self.view.set("Все тела")
        if experiment.rotations and {"Earth","Moon"}.issubset({b.name for b in experiment.bodies}):
            self.view.set("Земля и Луна")
            self.reference.set("Тело: Earth")
        self.reference_widget.configure(values=("Инерциальная",)+tuple("Тело: "+b.name for b in experiment.bodies))
        values=self._record()
        self._draw(values)
        self._lock()

    def _sync_settings(self,settings):
        self.backend.set(settings.backend)
        self.integrator.set(settings.integrator)
        self.physics.set(settings.physics)
        self.figures.set("saved" if settings.figures else "none")
        self.relative_pair.set("saved" if settings.relative_pair else "none")
        self.rtol.set(str(settings.rtol))
        self.position_atol.set(str(settings.position_atol))
        self.velocity_atol.set(str(settings.velocity_atol))
        self.error_control.set(settings.error_control)
        self.dt.set(f"{settings.dt:.17g}")
        self.mode.set(settings.contact_mode)
        self.restitution.set(str(settings.restitution))

    def _record(self):
        self.frames.append({b.name:(b.position.x,b.position.y,b.position.z) for b in self.experiment.bodies})
        values=report(self.experiment)
        residual=values["energy_budget_residual_joules"]
        self.energies.append((self.experiment.time,residual))
        self.reference_widget.configure(values=("Инерциальная",)+tuple("Тело: "+b.name for b in self.experiment.bodies))
        if self.reference.get() not in self.reference_widget.cget("values"):
            self.reference.set("Инерциальная")
        names={b.name for b in self.experiment.bodies}
        views=("Все тела","Земля и Луна") if {"Earth","Moon"}.issubset(names) else ("Все тела",)
        self.view_widget.configure(values=views)
        if self.view.get() not in views:
            self.view.set("Все тела")
        return values

    def _start(self):
        self._batch_size()  # Reject input before applying any pending settings.
        self._settings()
        if self.experiment.halted:
            raise ValueError("Расчёт остановлен при контакте. Сбросьте сценарий или явно выберите bounce/merge.")
        self.target_time=None
        self.running=True
        self._lock()
        self._update_status()

    def _start_target(self):
        target=float(self.target.get())
        validate_target(self.experiment,target,self._batch_size())
        self._settings()
        if self.experiment.halted:
            raise ValueError("Расчёт остановлен при контакте. Сбросьте сценарий или явно выберите bounce/merge.")
        self.target_time=target
        self.running=self.experiment.time < target
        self._lock()
        self._update_status()

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
            if self.running and self.target_time is not None:
                self.future=self.pool.submit(advance_towards,self.experiment,self.target_time,steps)
            else:
                self.target_time=None
                self.future=self.pool.submit(advance,self.experiment,steps)
            self._lock()
            self._update_status()

    def _poll(self):
        if self.closed:
            return
        try:
            if self.future is not None and self.future.done():
                future=self.future
                self.future=None
                self.experiment=future.result()
                values=self._record()
                if self.experiment.halted or (self.target_time is not None and self.experiment.time >= self.target_time):
                    self.running=False
                self._draw(values)
            if self.running and self.future is None:
                self._submit(self._batch_size())
        except Exception as error:
            self.running=False
            self._update_status()
            messagebox.showerror("Расчёт остановлен",str(error),parent=self.root)
        finally:
            # Input/submission errors must not terminate the Tk polling loop.
            if not self.closed:
                self._lock()
                self.root.after(40,self._poll)

    def _update_status(self,values=None):
        if values is None:
            values=dict(time_seconds=self.experiment.time,physics=self.experiment.settings.physics,
                        events=len(self.experiment.events),dissipated_energy_joules=self.experiment.dissipated_energy)
        if self.experiment.halted:
            state="контакт: остановка"
        elif self.future is not None:
            state="расчёт пакета" if self.running else "завершает пакет (пауза)"
        else:
            state="работает" if self.running else "пауза"
        if self.target_time is not None:
            state += f"; цель {self.target_time:.9g} с"
        self.status.set(f"t = {values['time_seconds']:.9g} с | dt = {self.experiment.settings.dt:.6g} с | "
                        f"{state} | {values['physics']}{' + Q2' if self.experiment.settings.figures else ''}{' + вращение' if self.experiment.rotations else ''} | {len(self.experiment.bodies)} тел | событий: {values['events']} | "
                        f"потери: {values['dissipated_energy_joules']:.6g} Дж")

    def _draw(self,values=None):
        axes={"XY":(0,1),"XZ":(0,2),"YZ":(1,2)}
        x,y=axes[self.plane.get()]
        names=[b.name for b in self.experiment.bodies]
        references=["Тело: "+name for name in names]
        reference=references.index(self.reference.get()) if self.reference.get() in references else None
        reference_name=names[reference] if reference is not None else None
        if self.view.get()=="Земля и Луна":
            names=[name for name in names if name in ("Earth","Moon")]
        from .plot_artists import PlotArtists
        if not hasattr(self,"_plot_artists"):
            self._plot_artists=PlotArtists(self.orbit,self.energy)
        self._plot_artists.update(self.frames,names,reference_name,(x,y),self.energies)
        self.orbit.set_xlabel(f"{'XYZ'[x]}, м"); self.orbit.set_ylabel(f"{'XYZ'[y]}, м")
        self.orbit.set_aspect("equal",adjustable="datalim")
        self.orbit.grid(alpha=.25)
        self.orbit.set_title(f"{self.view.get()} — {self.reference.get()}",fontsize=9)
        pn = self.experiment.settings.physics == "eih-1pn"
        self.energy.set_xlabel("Время, с")
        self.energy.set_ylabel("Остаток EIH 1PN, Дж" if pn else "Остаток баланса, Дж")
        if pn:
            self.energy.set_title("Остаток включает усечение модели 1PN/J2, не только интегрирование" if self.experiment.settings.figures
                                  else "Остаток включает погрешность усечения 1PN, не только интегрирования",fontsize=9)
        elif self.experiment.rotations:
            self.energy.set_title("Ньютоновская орбита + жёсткое вращение; без приливов и EIH",fontsize=9)
        else:
            self.energy.set_title("")
        self.energy.grid(alpha=.25)
        values=report(self.experiment) if values is None else values
        self._update_status(values)
        fmt=lambda vector:', '.join(f"{v:.4g}" for v in vector)
        self.details.set(f"Импульс {'EIH 1PN ' if pn else ''}(кг·м/с): [{fmt(values['momentum'])}]   "
                         f"{'Полный L: орбита + вращение' if self.experiment.rotations else 'Угловой момент'} (кг·м²/с): [{fmt(values['angular_momentum'])}]   "
                         f"Центр масс (м): [{fmt(values['center_of_mass'])}]. "
                         + self._figure_description(values)
                         + ("Вращение включено; баланс учитывает энергию и угловой момент вращения. " if self.experiment.rotations else "")
                         + "Графики по снимкам; до 1500 кадров.")
        self.canvas.draw_idle()

    def _figure_description(self,values):
        from .oblateness import prescribed
        if prescribed(self.experiment.settings.figures):
            return f"Q2: ориентация задана извне; её работа {values['orientation_work_joules']:.4g} Дж учтена в балансе. "
        if self.experiment.settings.figures:
            return "J2: оси фиксированы; орбитальный момент обменивается с ними, вращение не рассчитывается. "
        return ""

    def _edit(self):
        self._check_body_editor()
        dialog=tk.Toplevel(self.root)
        dialog.title("Новый опыт — исходный вариант будет сохранён в файле ветки")
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
                self._check_body_editor()
                values=[v.get() for v in variables]
                mass,radius,x,y,z,vx,vy,vz=map(float,values[1:])
                old=next(b for b in self.experiment.bodies if b.name==selected.get())
                body=Body(values[0],mass,Vector3(x,y,z),Vector3(vx,vy,vz),radius,old.spin)
                # Fixed figures retain their explicit parameters; renaming a
                # source requires updating the figure and is rejected here.
                from .sandbox import branch_experiment
                branch=branch_experiment(self.experiment,replacements=((old.name,body),))
                self._commit_body_branch(branch,dialog)
            except (ValueError,OverflowError,OSError) as error:
                messagebox.showerror("Неверное тело",str(error),parent=dialog)
        combo.bind("<<ComboboxSelected>>",populate)
        populate()
        ttk.Button(dialog,text="Применить как новый эксперимент",command=apply).grid(row=10,column=0,columnspan=2,pady=12)

    def _check_body_editor(self):
        if self.future is not None or self.running:
            raise ValueError("Редактирование требует паузы и завершения пакета")
        from .oblateness import prescribed
        if self.experiment.rotations or self.experiment.initial_rotations:
            raise ValueError("Редактор тел не поддерживает динамическую инерцию/q/S; создай отдельный новый сценарий")
        if prescribed(self.experiment.settings.figures):
            raise ValueError("Редактирование начальных данных требует сброса и выбора фигуры none: профиль DE441 привязан к исходной эпохе")

    def _commit_body_branch(self,branch,dialog):
        from .sandbox import save_branch
        path=filedialog.asksaveasfilename(parent=dialog,title="Сохранить исходный и новый опыт",
            defaultextension=".json",filetypes=[("Ветка Solar JSON","*.json")])
        if not path:
            return
        save_branch(branch,path)
        self._set_experiment(branch.child,parent_snapshot=branch.parent_snapshot)
        dialog.destroy()

    def _restore_parent(self):
        from .branch_io import parent_experiment
        restored=parent_experiment(self.parent_snapshot)
        path=filedialog.asksaveasfilename(parent=self.root,defaultextension=".json",
            title="Сохранить текущий опыт перед возвратом к родителю",filetypes=[("Solar JSON","*.json")])
        if not path:return
        save(self.experiment,path)
        self._set_experiment(restored)

    def _open_solar_sandbox(self):
        from .application_profiles import solar_sandbox
        result=solar_sandbox(backend=self.backend.get())
        self.view.set("Все тела")
        self.reference.set("Инерциальная")
        self._set_experiment(result)
        self.scenario.set("solar-system-moon")

    def _add_body(self):
        self._check_body_editor()
        from .simulation import SUN_MASS, EARTH_MASS
        dialog=tk.Toplevel(self.root)
        dialog.title("Добавить точечное тело — новый опыт с сохранением родителя")
        dialog.transient(self.root);dialog.grab_set()
        templates={"Учебная планета: масса Земли":("Планета",EARTH_MASS),
                   "Учебная звезда: масса Солнца":("Звезда",SUN_MASS)}
        selected=tk.StringVar(value=next(iter(templates)))
        combo=ttk.Combobox(dialog,textvariable=selected,values=tuple(templates),state="readonly",width=38)
        combo.grid(row=0,column=0,columnspan=2,padx=10,pady=8)
        fields=("Имя","Масса, кг","x, м","y, м","z, м","vx, м/с","vy, м/с","vz, м/с")
        variables=[tk.StringVar() for _ in fields]
        for row,(field,variable) in enumerate(zip(fields,variables),start=1):
            ttk.Label(dialog,text=field).grid(row=row,column=0,sticky="w",padx=10,pady=3)
            ttk.Entry(dialog,textvariable=variable,width=30).grid(row=row,column=1,padx=10)
        def populate(_=None):
            label,mass=templates[selected.get()]
            names={b.name for b in self.experiment.bodies}
            index=1
            while f"{label} {index}" in names:index+=1
            variables[0].set(f"{label} {index}")
            variables[1].set(f"{mass:.17g}")
        def apply():
            try:
                self._check_body_editor()
                values=[v.get() for v in variables]
                mass,x,y,z,vx,vy,vz=map(float,values[1:])
                body=Body(values[0],mass,Vector3(x,y,z),Vector3(vx,vy,vz))
                from .sandbox import branch_experiment
                branch=branch_experiment(self.experiment,additions=(body,))
                self._commit_body_branch(branch,dialog)
            except (ValueError,OverflowError,OSError) as error:
                messagebox.showerror("Неверное тело",str(error),parent=dialog)
        combo.bind("<<ComboboxSelected>>",populate)
        populate()
        ttk.Label(dialog,text="Векторы вводятся явно в текущей инерциальной системе (SI).\n"
            "Тело точечное (радиус 0); шаблон массы не задаёт готовую орбиту.",
            wraplength=420).grid(row=9,column=0,columnspan=2,padx=10,pady=8)
        ttk.Button(dialog,text="Сохранить и добавить как новый опыт",command=apply).grid(row=10,column=0,columnspan=2,pady=12)

    def _remove_body(self):
        self._check_body_editor()
        from .sandbox import branch_experiment
        dialog=tk.Toplevel(self.root);dialog.title("Удалить тело — сохранить родителя")
        dialog.transient(self.root);dialog.grab_set()
        names=tuple(b.name for b in self.experiment.bodies)
        selected=tk.StringVar(value=names[0])
        ttk.Label(dialog,text="Удаление создаёт новый опыт. Фигуры и пары не отключаются автоматически.",
                  wraplength=430).pack(padx=12,pady=10)
        ttk.Combobox(dialog,textvariable=selected,values=names,state="readonly",width=32).pack(padx=12,pady=6)
        def apply():
            try:
                self._check_body_editor()
                branch=branch_experiment(self.experiment,removals=(selected.get(),))
                self._commit_body_branch(branch,dialog)
            except (ValueError,OverflowError,OSError) as error:
                messagebox.showerror("Удаление не выполнено",str(error),parent=dialog)
        ttk.Button(dialog,text="Сохранить и удалить как новый опыт",command=apply).pack(padx=12,pady=12)

    def close(self):
        self.closed=True
        self.running=False
        self.pool.shutdown(wait=False,cancel_futures=True)
        self.root.destroy()


def launch(experiment=None):
    root=tk.Tk()
    Laboratory(root,experiment)
    root.mainloop()
