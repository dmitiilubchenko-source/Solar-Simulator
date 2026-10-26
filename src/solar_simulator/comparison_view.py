"""Read-only overlay and residuals at verified common saved epochs."""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

class ComparisonViewer:
    def __init__(self, window, comparison, *, samples=None):
        self.window = window
        self.comparison = comparison
        self.index = 0
        self.samples = []
        window.title('Solar — исходный и изменённый опыт')
        window.geometry('1100x850')
        controls = ttk.Frame(window)
        controls.pack(fill='x', padx=8, pady=6)
        ttk.Label(controls, text='Тело').pack(side='left')
        names = comparison.body_names
        self.body = ttk.Combobox(controls, values=names, state='readonly', width=22)
        self.body.pack(side='left', padx=6)
        if names:
            self.body.current(0)
        self.body.bind('<<ComboboxSelected>>', lambda event: self._draw())
        ttk.Label(controls, text='Система').pack(side='left')
        self.references = (None,)+names
        self.reference = ttk.Combobox(controls, values=('Инерциальная',)+names, state='readonly', width=22)
        self.reference.current(0)
        self.reference.pack(side='left', padx=6)
        self.reference.bind('<<ComboboxSelected>>', lambda event: self._reload())
        self.plane = ttk.Combobox(controls, values=('XY', 'XZ', 'YZ'), state='readonly', width=5)
        self.plane.current(0)
        self.plane.pack(side='left', padx=6)
        self.plane.bind('<<ComboboxSelected>>', lambda event: self._draw())
        ttk.Button(controls, text='Отчёт JSON…', command=self._export).pack(side='left')
        self.position = tk.DoubleVar(value=0.)
        self.slider = ttk.Scale(window, from_=0, to=len(comparison.pairs)-1,
                                variable=self.position, command=self._seek)
        self.slider.pack(fill='x', padx=10)
        self.status = tk.StringVar()
        ttk.Label(window, textvariable=self.status, wraplength=1050).pack(fill='x', padx=10)
        self.figure = Figure(figsize=(10, 6), dpi=100, layout='constrained')
        grid = self.figure.add_gridspec(2, 2, height_ratios=(1.2, 1.))
        self.orbit = self.figure.add_subplot(grid[0, :])
        self.distance = self.figure.add_subplot(grid[1, 0])
        self.velocity = self.figure.add_subplot(grid[1, 1])
        self.canvas = FigureCanvasTkAgg(self.figure, master=window)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
        NavigationToolbar2Tk(self.canvas, window)
        self.closed = False
        window.protocol('WM_DELETE_WINDOW', self.close)
        if samples is None:self._reload()
        else:
            self.samples=samples
            self._draw()

    def _reload(self):
        reference = self.references[self.reference.current()]
        try:
            self.samples = [self.comparison.sample(i, reference=reference)
                            for i in range(len(self.comparison.pairs))]
            self._draw()
        except (ValueError, OverflowError) as error:
            self.samples = []
            for axis in (self.orbit, self.distance, self.velocity):
                axis.clear()
            self.status.set('Сравнение недоступно: '+str(error))
            self.canvas.draw_idle()

    def _draw(self):
        if not self.samples:
            return
        name = self.body.get()
        row = self.samples[self.index]
        axes = {'XY': (0, 1), 'XZ': (0, 2), 'YZ': (1, 2)}[self.plane.get()]
        for axis in (self.orbit, self.distance, self.velocity):
            axis.clear()
        nan = float('nan')
        for prefix, label, style in (('parent', 'Исходный', '-'), ('child', 'Изменённый', '--')):
            points = [sample['bodies'].get(name, {}).get(prefix+'_position_m', (nan, nan, nan))
                      for sample in self.samples[:self.index+1]]
            self.orbit.plot([p[axes[0]] for p in points], [p[axes[1]] for p in points], style, label=label)
            self.orbit.scatter([points[-1][axes[0]]], [points[-1][axes[1]]], s=25)
        self.orbit.set_xlabel(self.plane.get()[0]+', м')
        self.orbit.set_ylabel(self.plane.get()[1]+', м')
        self.orbit.set_aspect('equal', adjustable='datalim')
        self.orbit.set_title(name if name else 'Нет общих имён тел')
        self.orbit.legend(loc='upper right')
        for axis, key, label in ((self.distance, 'distance_m', '|Δr|, м'),
                                 (self.velocity, 'distance_m_per_s', '|Δv|, м/с')):
            values = [sample['bodies'].get(name, {}).get(key, nan) for sample in self.samples]
            axis.plot(self.comparison.times, values)
            axis.axvline(self.comparison.times[self.index], color='gray', linestyle=':')
            axis.set_xlabel('Секунд после ветвления')
            axis.set_ylabel(label)
        values = row['bodies'].get(name)
        difference = (f'|Δr|={values["distance_m"]:.9g} м; |Δv|={values["distance_m_per_s"]:.9g} м/с'
                      if values else 'Нет общего тела или опоры: численное сравнение отсутствует')
        origin = self.comparison.origin
        basis = (f'{origin.frame}; {origin.center}; JD₀={origin.epoch_jd_tdb:.17g} TDB + t_parent/86400'
                 if origin else 'Общий базис родителя; календарная эпоха не задана')
        reference = self.references[self.reference.current()]
        metadata = self.comparison
        used_parent = {i for i, _ in metadata.pairs}
        used_child = {j for _, j in metadata.pairs}
        self.status.set(
            f'{self.index+1}/{len(self.samples)} общих эпох | t_parent={row["parent_time_seconds"]:.17g} с; '
            f't_child={row["child_time_seconds"]:.17g} с; якорь={metadata.anchor_time:.17g} с | '
            f'сторона: {metadata.event_side}; опора: {reference if reference is not None else "инерциальная"}\n'
            f'{difference}. Δ = изменённый − исходный. {basis}\n'
            f'Только у родителя: {row["parent_only"]}; только у ветки: {row["child_only"]}. '
            f'Несопоставленных кадров: {len(metadata.parent.times)-len(used_parent)} / '
            f'{len(metadata.child.times)-len(used_child)}. Без интерполяции и расчёта.')
        self.position.set(self.index)
        self.canvas.draw_idle()

    def _seek(self, value):
        self.index = min(max(0, int(round(float(value)))), len(self.comparison.pairs)-1)
        self._draw()

    def _export(self):
        path = filedialog.asksaveasfilename(parent=self.window, defaultextension='.json',
                                           filetypes=[('Solar comparison JSON', '*.json')])
        if not path:
            return
        try:
            self.comparison.save_report(path, reference=self.references[self.reference.current()])
        except (ValueError, OSError, RuntimeError, OverflowError) as error:
            messagebox.showerror('Отчёт не сохранён', str(error), parent=self.window)

    def close(self):
        if not self.closed:
            self.closed = True
            self.window.destroy()


def launch(parent_directory, child_directory, *, event_side):
    from .comparison_loader import ComparisonLoader
    root = tk.Tk()
    ComparisonLoader(root,parent_directory,child_directory,event_side=event_side)
    root.mainloop()
