"""Read-only physical snapshots; existing evaluator and background lifecycle."""
from concurrent.futures import CancelledError
from functools import partial
import json
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

import numpy as np

from .rotation import angular_velocity,rotation_matrix
from .trajectory_loader import TrajectoryLoader

ROTATION_SCOPE=('Newton Q2: разложение второго порядка, M–Q; без Q2–Q2, высших '
    'мультиполей, приливов, диссипации и релятивистских взаимодействий.')
AXES_DESCRIPTION=('Главные оси I1/I2/I3: красная/зелёная/синяя. Длина — ограничивающий '
    'радиус, не форма тела; в проекции ось может сократиться до точки.')


def prepare_inspection(document,stop_requested,progress):
    if stop_requested():raise CancelledError()
    from .storage import from_document
    from .inspection import report
    state=from_document(document)
    progress('Диагностика снимка',0,1)
    existing=report(state)  # No new evaluator, integration or accuracy estimate.
    rotations=[dict(body=r.body,quaternion=list(r.quaternion),angular_momentum=list(r.angular_momentum),
        angular_velocity=angular_velocity(r.figure,r.quaternion,r.angular_momentum).tolist(),
        body_to_inertial=rotation_matrix(r.quaternion).tolist(),principal_moments=list(r.figure.moments)) for r in state.rotations]
    if stop_requested():raise CancelledError()
    progress('Диагностика снимка',1,1)
    return dict(time_seconds=state.time,rotations=rotations,numerical_reliability=existing['numerical_reliability'])


def projected_axes(experiment,names,reference,axes):
    """Three unit-principal directions scaled by Rbound, not ellipsoid axes."""
    positions={b.name:np.array([b.position.x,b.position.y,b.position.z]) for b in experiment.bodies}
    origin=positions[reference] if reference is not None else np.zeros(3)
    segments=[]
    for r in experiment.rotations:
        if r.body not in names:continue
        p=positions[r.body]-origin;R=rotation_matrix(r.quaternion)
        segments.extend(np.array([p,p+r.figure.bounding_radius*R[:,j]])[:,axes] for j in range(3))
    return segments


def rotation_text(payload):
    if not payload['rotations']:
        return ('Динамических вращающихся фигур нет.\n'
                'Пассивный Body.spin не задаёт ориентацию или rigid-body вращение.')
    vector=lambda values:'['+', '.join(format(v,'.17g') for v in values)+']'
    lines=[ROTATION_SCOPE,'','q=(w,x,y,z): body → инерциальный базис, безразмерный.',
        'S и ω ниже в инерциальном базисе. q/S показаны как сохранены;',
        'матрица R и ω вычислены существующими функциями; сохранение не нормируется.','']
    for r in payload['rotations']:
        lines.extend([r['body'],'q = '+vector(r['quaternion']),
            'S [кг·м²/с] = '+vector(r['angular_momentum']),
            'ω [рад/с] = '+vector(r['angular_velocity']),
            'I1,I2,I3 [кг·м²] = '+vector(r['principal_moments']),'R body → inertial:'])
        lines.extend(vector(row) for row in r['body_to_inertial']);lines.append('')
    return '\n'.join(lines)


class InspectionLoader(TrajectoryLoader):
    """Reuse cancellation/error/Tk ownership; inspect a detached codec snapshot."""
    def __init__(self,window,document):
        self._start(window,partial(prepare_inspection,document),
            'Solar — вращение и надёжность','Отчёт не построен')
        self.status.set('Подготовка снимка; расчёт орбиты не запускается…')

    def _show(self,payload):
        self.payload=payload
        self.window.geometry('960x680');self.window.minsize(600,400)
        ttk.Label(self.window,text=f"Снимок t = {payload['time_seconds']:.17g} с. "
            'Только чтение; значения не обновляются при продолжении опыта.',wraplength=900).pack(fill='x',padx=10,pady=8)
        self.viewer=ttk.Notebook(self.window);self.viewer.pack(fill='both',expand=True,padx=8)
        self.texts=[]
        reliability=payload['numerical_reliability']
        summary=('Модель: '+reliability['model']['description']+'\n'
            'Энергия и моменты — диагностические величины, а не глобальная ошибка.\n'
            'Точность этого снимка не установлена; настройки не доказывают историю пакетов.\n\n')
        for title,text in [('Вращение (SI)',rotation_text(payload)),
                ('Численная надёжность',summary+json.dumps(reliability,ensure_ascii=False,indent=2))]:
            field=ScrolledText(self.viewer,wrap='word',font='TkFixedFont')
            field.insert('1.0',text);field.configure(state='disabled')
            self.viewer.add(field,text=title);self.texts.append(field)
        ttk.Button(self.window,text='Закрыть',command=self.close).pack(pady=8)
