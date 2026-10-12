"""Measured optical residuals, with chronological fit/forecast separation."""
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,default=Path('docs/orbit-observations-validation.json'))
    parser.add_argument('--dataset',type=Path,default=Path('src/solar_simulator/data/orbit-observations-13270.json'))
    parser.add_argument('--output',type=Path,default=Path('docs/orbit-observations-residuals.png'))
    args = parser.parse_args(argv)
    report = json.loads(args.report.read_text(encoding='utf-8'))
    document = json.loads(args.dataset.read_text(encoding='utf-8'))
    records = {r['id']:r for r in document['observations']}
    fig,axes = plt.subplots(2,1,figsize=(10,6.4),sharex=True,layout='constrained')
    for axis,component,label in zip(axes,('east_arcsec','north_arcsec'),('Восток: RA × cos(Dec)','Север: Dec')):
        for split,color,name in (('training','#166ea6','Подбор: январь–март'),('holdout','#cf641d','Прогноз: апрель–май')):
            rows = report[split]['residuals']
            t = [datetime.fromisoformat(records[r['id']]['utc'].replace('Z','+00:00')) for r in rows]
            y = [r[component] for r in rows]
            sigma_key = 'sigma_ra_arcsec' if component=='east_arcsec' else 'sigma_dec_arcsec'
            errors = [records[r['id']][sigma_key] for r in rows]
            axis.errorbar(t,y,yerr=errors,fmt='o',ms=4,alpha=.72,color=color,
                          ecolor=color,elinewidth=.6,capsize=1,label=name)
        axis.axvline(datetime(2020,4,1),color='#767676',ls='--',lw=1)
        axis.axhline(0,color='#8b8b8b',lw=.6)
        axis.grid(alpha=.18)
        axis.set_ylabel(label+'\nугловые секунды')
    axes[0].legend(loc='upper left',frameon=False,ncol=2)
    axes[0].set_title('Астероид 13270: орбита по реальным наблюдениям MPC / ATLAS T08',fontsize=13)
    axes[1].xaxis.set_major_locator(dates.MonthLocator())
    axes[1].xaxis.set_major_formatter(dates.DateFormatter('%Y-%m'))
    axes[1].set_xlabel('Дата наблюдения UTC; поздние измерения не участвовали в подборе')
    fig.suptitle(f"Подбор: RMS {report['training']['rms_arcsec']:.3f}″ · отдельный прогноз: RMS {report['holdout']['rms_arcsec']:.3f}″\n"
                 'Планетный фон задан DE441; полоски — заявленная погрешность измерений 1σ',fontsize=10)
    fig.savefig(args.output,dpi=180)
    plt.close(fig)
    print(args.output)


if __name__=='__main__':
    main()
