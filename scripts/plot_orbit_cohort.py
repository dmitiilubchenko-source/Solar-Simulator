"""Compare long-season prediction residuals with explicit error-model assumptions."""
import argparse
from datetime import datetime
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.dates as dates
import matplotlib.pyplot as plt
import numpy as np


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,default=Path('docs/orbit-cohort-validation.json'))
    parser.add_argument('--output',type=Path,default=Path('docs/orbit-cohort-residuals.png'))
    args=parser.parse_args(argv)
    report=json.loads(args.report.read_text(encoding='utf-8'))
    cases=[c for c in report['cases'] if c['status']=='evaluated']
    fig,axes=plt.subplots(len(cases),1,figsize=(10,3.2*len(cases)),layout='constrained',squeeze=False)
    for axis,case in zip(axes[:,0],cases):
        dataset=json.loads(Path(f"src/solar_simulator/data/orbit-cohort-{case['designation']}.json").read_bytes())
        records={r['id']:r for r in dataset['observations']}
        for name,color,label in [('independent','#166ea6','Независимые снимки'),('station_night','#cf641d','Общая ошибка ночи 0,15″')]:
            model=case['models'][name]
            rows=model['holdout']['residuals']
            # Show every held-out measurement, preserving unfavorable cases.
            t=[datetime.fromisoformat(records[r['id']]['utc'].replace('Z','+00:00')) for r in rows]
            axis.scatter(t,[r['radial_arcsec'] for r in rows],s=13,alpha=.55,color=color,
                         label=f"{label}: RMS {model['holdout']['rms_arcsec']:.3f}″")
        axis.set_title(f"Астероид {case['designation']} · пауза до проверочного сезона {case['selection']['gap_days']:.0f} суток",fontsize=12)
        axis.set_ylabel('Угловое отклонение, ″')
        axis.set_ylim(bottom=0)
        axis.grid(alpha=.2)
        axis.legend(loc='upper left',fontsize=9,frameon=False)
        axis.xaxis.set_major_locator(dates.MonthLocator(interval=1))
        axis.xaxis.set_major_formatter(dates.DateFormatter('%Y-%m'))
    axes[-1,0].set_xlabel('Проверочные наблюдения UTC · весь сезон исключён из подбора')
    fig.suptitle('Настоящие измерения MPC: длинный прогноз для двух объектов\n'
                 'Планеты и обсерватории заданы DE441; масштаб по вертикали отдельный для каждого объекта',fontsize=11)
    fig.savefig(args.output,dpi=180)
    plt.close(fig)
    print(args.output)


if __name__=='__main__':
    main()
