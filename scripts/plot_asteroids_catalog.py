"""Scientific plot of sampled model/JPL residuals with the unchanged parent."""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from solar_simulator.perturbers import solar_system_asteroids_full,solar_system_asteroids_catalog
if __package__:
    from .assess_pluto import reference
    from .assess_relative_coordinates import REFERENCE_SHA256
    from .assess_solar_j2 import PLANET_REFERENCE_SHA256
else:
    from assess_pluto import reference
    from assess_relative_coordinates import REFERENCE_SHA256
    from assess_solar_j2 import PLANET_REFERENCE_SHA256


def main():
    pair=reference('docs/solar-system-moon-reference.json',REFERENCE_SHA256)
    planets=reference('docs/solar-system-reference.json',PLANET_REFERENCE_SHA256)
    initial,origin=solar_system_asteroids_catalog()
    names=[b.name for b in initial]
    e,m=names.index('Earth'),names.index('Moon')
    fraction=initial[m].mass/(initial[e].mass+initial[m].mass)
    expected=np.array([s['position'] for s in next(b for b in pair['bodies'] if b['name']=='Earth-Moon')['states']])
    mars=next(b for b in planets['bodies'] if b['name']=='Mars')
    expected_mars=np.array([s['position'] for s in mars['states']])
    with np.load('.tools/asteroids-catalog-production.npz',allow_pickle=False) as source:
        times=source['times']
        assert source['sixteen_asteroids'].shape==(45,27,6) and source['all_343_tighter'].shape==(45,354,6)
        day=times/86400
        planet_indices=[int(np.flatnonzero(times==(jd-origin.epoch_jd_tdb)*86400)[0]) for jd in planets['epochs_jd_tdb']]
        figure,axes=plt.subplots(1,2,figsize=(11,4.3))
        for key,label,color in [('sixteen_asteroids','16 астероидов','#be5540'),
                ('all_343_tighter','Все 343 астероида, строгие допуски','#267ca3')]:
            value=source[key]
            center=value[:,e,:3]+fraction*(value[:,m,:3]-value[:,e,:3])
            residual=np.linalg.norm(center-expected,axis=1)
            axes[0].plot(day[1:],residual[1:],'.-',label=label,color=color,linewidth=1.7,markersize=4)
            residual=np.linalg.norm(value[planet_indices,names.index('Mars'),:3]-expected_mars,axis=1)
            axes[1].plot(day[planet_indices][1:],residual[1:],'.-',label=label,color=color,linewidth=1.7,markersize=5)
        for axis,title in zip(axes,['Барицентр Земли–Луны относительно SSB','Марс относительно SSB']):
            axis.set_title(title,fontsize=11)
            axis.set_xlabel('Сутки от начальной эпохи')
            axis.set_ylabel('Расхождение с JPL DE441, м')
            axis.set_yscale('log')
            axis.grid(which='both',alpha=.2)
        axes[0].legend(fontsize=8)
        figure.suptitle('Вклад полного каталога астероидов в годовую модель',fontsize=13)
        figure.text(.5,.015,'Одинаковые исходные 27 тел и физика. Показаны контрольные снимки; остаток включает отличия модели.',ha='center',fontsize=8)
        figure.tight_layout(rect=(0,.045,1,.94))
        output=Path('docs/asteroids-catalog-comparison.png')
        figure.savefig(output,dpi=160)
        plt.close(figure)
        print(output,hashlib.sha256(output.read_bytes()).hexdigest())


if __name__=='__main__': main()
