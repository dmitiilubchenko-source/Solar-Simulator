"""Compare sampled JPL residuals and explicitly separate the model increment."""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from solar_simulator.perturbers import solar_system_kuiper
from scripts.assess_pluto import reference
from scripts.assess_relative_coordinates import REFERENCE_SHA256
from scripts.assess_solar_j2 import PLANET_REFERENCE_SHA256


def main():
    report=json.loads(Path('docs/kuiper-validation.json').read_text(encoding='utf-8'))
    if not report['checks_passed']:
        raise ValueError('Annual KBO checks have not passed')
    pair=reference('docs/solar-system-moon-reference.json',REFERENCE_SHA256)
    planets=reference('docs/solar-system-reference.json',PLANET_REFERENCE_SHA256)
    bodies,origin=solar_system_kuiper()
    names=[b.name for b in bodies];e,m=names.index('Earth'),names.index('Moon')
    fraction=bodies[m].mass/(bodies[e].mass+bodies[m].mass)
    expected_center=np.array([s['position'] for s in next(b for b in pair['bodies'] if b['name']=='Earth-Moon')['states']])
    expected_neptune=np.array([s['position'] for s in next(b for b in planets['bodies'] if b['name']=='Neptune')['states']])
    with np.load('.tools/kuiper-production.npz',allow_pickle=False) as source:
        times=source['times'];days=times/86400
        pindices=[int(np.flatnonzero(times==(jd-origin.epoch_jd_tdb)*86400)[0]) for jd in planets['epochs_jd_tdb']]
        fig,axes=plt.subplots(1,3,figsize=(14,4.6))
        for key,label,color in (('parent_354','354 тела','#356da8'),('kuiper_384','384 тела: +30 KBO','#cc782c')):
            value=source[key]
            center=value[:,e,:3]+fraction*(value[:,m,:3]-value[:,e,:3])
            axes[0].plot(days,np.linalg.norm(center-expected_center,axis=1),'.-',label=label,color=color)
            axes[1].plot(days[pindices],np.linalg.norm(value[pindices,names.index('Neptune'),:3]-expected_neptune,axis=1),'.-',label=label,color=color)
        change=source['kuiper_384'][:,:354,:3]-source['parent_354'][:,:,:3]
        for name in ('Sun','Earth','Mars','Neptune'):
            axes[2].plot(days,np.linalg.norm(change[:,names.index(name)],axis=1),'.-',label=name)
        for axis,title in zip(axes,('Барицентр Земли–Луны: остаток JPL','Нептун: остаток JPL','Изменение модели при добавлении KBO')):
            axis.set_title(title,fontsize=10)
            axis.set_xlabel('Сутки от начальной эпохи')
            axis.set_ylabel('Расстояние, м');axis.grid(alpha=.25);axis.legend(fontsize=8)
            axis.set_ylim(bottom=0)
        fig.suptitle('30 отдельных объектов пояса Койпера: годовой контроль',fontsize=13)
        fig.text(.5,.017,'SSB/Ecliptic J2000. Одинаковые прежние 354 начальных состояния; нет подбора параметров по будущим орбитам.',ha='center',fontsize=9)
        fig.tight_layout(rect=(0,.055,1,.94))
        output=Path('docs/kuiper-comparison.png');fig.savefig(output,dpi=160);plt.close(fig)
        print(output,hashlib.sha256(output.read_bytes()).hexdigest())


if __name__=='__main__':
    main()
