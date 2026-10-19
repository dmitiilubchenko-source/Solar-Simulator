"""Shared edit/add fields. Only this input layer knows display units and origin."""
import tkinter as tk
from tkinter import messagebox, ttk

from .experiment import copy_bodies
from .input_units import LENGTH_UNITS, MASS_UNITS, SPEED_UNITS, from_si, to_si
from .simulation import Body
from .vector3 import Vector3


class BodyFields:
    def __init__(self, dialog, bodies, *, has_radius):
        self.dialog = dialog
        self.has_radius = has_radius
        self.bodies = tuple(copy_bodies(bodies))
        self.references = (None,)+self.bodies
        self.keys = ('name', 'mass')+(('radius',) if has_radius else ())+('x', 'y', 'z', 'vx', 'vy', 'vz')
        self.variables = {key: tk.StringVar() for key in self.keys}
        self.labels = {}
        for row, key in enumerate(self.keys, start=1):
            label = ttk.Label(dialog)
            label.grid(row=row, column=0, sticky='w', padx=10, pady=3)
            self.labels[key] = label
            ttk.Entry(dialog, textvariable=self.variables[key], width=30).grid(row=row, column=1, padx=10)
        controls = ttk.Frame(dialog)
        controls.grid(row=11, column=0, columnspan=2, sticky='ew', padx=10, pady=6)
        self.selectors = []
        for row, (label, values) in enumerate((('Масса', tuple(MASS_UNITS)), ('Длины', tuple(LENGTH_UNITS)),
                                              ('Скорости', tuple(SPEED_UNITS)),
                                              ('Опора', ('Инерциальная',)+tuple('Тело: '+b.name for b in self.bodies)))):
            ttk.Label(controls, text=label).grid(row=row, column=0, sticky='w')
            combo = ttk.Combobox(controls, values=values, state='readonly', width=28)
            combo.current(0)
            combo.grid(row=row, column=1, sticky='ew', pady=2)
            combo.bind('<<ComboboxSelected>>', self._change)
            self.selectors.append(combo)
        self.mass_unit, self.length_unit, self.speed_unit, self.reference = self.selectors
        ttk.Label(dialog, text=f'Учебные шкалы: M⊕={MASS_UNITS["M⊕ (учеб.)"]:.7g} кг; '
                  f'M☉={MASS_UNITS["M☉ (учеб.)"]:.7g} кг.\n'
                  'Опора — состояние выбранного тела при открытии редактора.\n'
                  'Прибавляются положение и скорость; оси не вращаются.', wraplength=560).grid(
                      row=12, column=0, columnspan=2, padx=10, pady=6)
        self.context = self._context()
        self.si = {}
        self.shown = {}

    def _context(self):
        return (self.mass_unit.get(), self.length_unit.get(), self.speed_unit.get(), self.reference.current())

    def _conversion(self, key, context):
        mass, length, speed, index = context
        if not 0 <= index < len(self.references):
            raise ValueError('Выберите опорное тело')
        reference = self.references[index]
        if key == 'mass':
            return 'mass', mass, 0.
        if key == 'radius':
            return 'length', length, 0.
        velocity = key.startswith('v')
        offset = (getattr(reference.velocity if velocity else reference.position, key[-1])
                  if reference is not None else 0.)
        return ('speed', speed, offset) if velocity else ('length', length, offset)

    def _capture(self):
        values = {}
        for key, variable in self.variables.items():
            if key == 'name':
                continue
            text = variable.get().strip()
            if text == self.shown.get(key):
                values[key] = self.si[key]  # Preserve unchanged SI despite display rounding.
            elif not text:
                values[key] = None
            else:
                quantity, unit, offset = self._conversion(key, self.context)
                values[key] = to_si(text, quantity, unit, offset=offset)
        return values

    def _render(self, values, context):
        shown = {}
        for key, value in values.items():
            quantity, unit, offset = self._conversion(key, context)
            shown[key] = '' if value is None else f'{from_si(value, quantity, unit, offset=offset):.17g}'
        # Compute the entire display before committing any field/context.
        self.si = values
        self.shown = shown
        self.context = context
        for key, text in shown.items():
            self.variables[key].set(text)
        for key, label in self.labels.items():
            title = {'name': 'Имя', 'mass': 'Масса', 'radius': 'Радиус'}.get(key, key)
            label.configure(text=title if key == 'name' else title+', '+self._conversion(key, context)[1])

    def populate(self, body, *, blank_vectors=False):
        values = dict(mass=body.mass, **({'radius': body.radius} if self.has_radius else {}))
        for prefix, vector in (('', body.position), ('v', body.velocity)):
            values.update({prefix+axis: None if blank_vectors else getattr(vector, axis) for axis in 'xyz'})
        self._render(values, self.context)
        self.variables['name'].set(body.name)

    def set_mass(self, mass):
        text = f'{from_si(mass, "mass", self.context[0]):.17g}'
        self.si['mass'] = mass
        self.shown['mass'] = text
        self.variables['mass'].set(text)

    def _change(self, event=None):
        try:
            self._render(self._capture(), self._context())
        except (ValueError, OverflowError) as error:
            for selector, value in zip(self.selectors[:3], self.context[:3]):
                selector.set(value)
            self.reference.current(self.context[3])
            messagebox.showerror('Единицы не изменены', str(error), parent=self.dialog)

    def read(self, *, spin=None):
        values = self._capture()
        if any(value is None for value in values.values()):
            raise ValueError('Заполните все численные поля тела')
        return Body(self.variables['name'].get(), values['mass'],
                    Vector3(*(values[axis] for axis in 'xyz')),
                    Vector3(*(values['v'+axis] for axis in 'xyz')),
                    values.get('radius', 0.), spin if spin is not None else Vector3(0., 0., 0.))
