"""Plot actual annual residuals and geometry sensitivity of the own ring model."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    report=json.loads(Path('docs/kuiper-ring-validation.json').read_text(encoding='utf-8'))
    with np.load('.tools/ring-production.npz',allow_pickle=False) as archive:
        times=archive['times'].copy()
        arrays={name:archive[name].copy() for name in archive.files if name!='times'}
    reference=json.loads(Path('docs/solar-system-reference.json').read_text(encoding='utf-8'))
    dt=(np.array(reference['epochs_jd_tdb'])-report['epoch_jd_tdb'])*86400
    index=np.array([np.flatnonzero(times==t)[0] for t in dt])
    figure,axes=plt.subplots(2,2,figsize=(13,8),constrained_layout=True)
    labels={'no_ring':'384: без кольца','ring_36_0':'420: 36 точек, фаза 0','ring_144_0':'528: 144 точки, фаза 0'}
    for ax,name,row in ((axes[0,0],'Neptune',9),(axes[0,1],'Earth-Moon',None)):
        expected=np.array([s['position'] for s in next(b for b in reference['bodies'] if b['name']==name)['states']])
        for variant,label in labels.items():
            q=arrays[variant]
            if row is None:
                from solar_simulator.kuiper_ring import solar_system_ring
                bodies,_=solar_system_ring();fraction=bodies[4].mass/(bodies[3].mass+bodies[4].mass)
                position=q[index,3,:3]+fraction*(q[index,4,:3]-q[index,3,:3])
            else:position=q[index,row,:3]
            ax.plot(dt/86400,np.linalg.norm(position-expected,axis=1),marker='.',label=label)
        ax.set_title(('Нептун' if row else 'Барицентр Земли–Луны')+': остаток JPL')
        ax.set_ylabel('Расстояние, м');ax.legend(fontsize=8)
    ax=axes[1,0]
    for row,name in ((0,'Sun'),(3,'Earth'),(5,'Mars'),(9,'Neptune')):
        ax.plot(times/86400,np.linalg.norm(arrays['ring_36_0'][:,row,:3]-arrays['no_ring'][:,row,:3],axis=1),label=name)
    ax.set_title('Изменение модели при добавлении кольца');ax.set_ylabel('Расстояние, м');ax.legend(fontsize=8)
    ax=axes[1,1]
    for name,label in (('ring_72_0','36 → 72'),('ring_144_0','36 → 144'),('ring_36_1','Две фазы, 36')):
        ax.plot(times/86400,np.linalg.norm(arrays['ring_36_0'][:,9,:3]-arrays[name][:,9,:3],axis=1),label=label)
    ax.set_title('Нептун: чувствительность к геометрии');ax.set_ylabel('Расстояние, м');ax.legend(fontsize=8)
    for ax in axes.flat:
        ax.grid(alpha=.25);ax.set_xlabel('Сутки от начальной эпохи');ax.set_ylim(bottom=0)
    figure.suptitle('Остаточная масса Койпера: собственная автономная аппроксимация',fontsize=15)
    figure.savefig('docs/kuiper-ring-comparison.png',dpi=160)
    plt.close(figure)
    print('docs/kuiper-ring-comparison.png')


if __name__=='__main__':main()
