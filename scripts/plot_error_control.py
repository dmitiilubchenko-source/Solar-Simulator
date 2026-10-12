"""Plot sampled independent agreement, separate from physical JPL residuals."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from solar_simulator.perturbers import solar_system_asteroids_catalog
from scripts.assess_relative_coordinates import relative_states


def main():
    report = json.loads(Path('docs/error-control-validation.json').read_text(encoding='utf-8'))
    initial, _ = solar_system_asteroids_catalog()
    with np.load('.tools/error-control-states.npz', allow_pickle=False) as archive:
        time = archive['times']/86400
        reference = archive['reference']
        variants = {key:archive[key] for key in ('global_rms', 'global_rms_strict', 'per_body_stricter')}
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.3), constrained_layout=True)
    labels = {'global_rms':'Global RMS: x 10 µm', 'global_rms_strict':'Global RMS: x 1 µm',
              'per_body_stricter':'Per body: x 0.1 µm'}
    colors = {'global_rms':'#b55327', 'global_rms_strict':'#7b6597', 'per_body_stricter':'#167a88'}
    for key, value in variants.items():
        all_errors = np.max(np.linalg.norm(value[:,:,:3]-reference[:,:,:3], axis=2), axis=1)
        relative = np.linalg.norm((relative_states(value, initial)-relative_states(reference, initial))[:,:3], axis=1)
        for ax, errors in zip(axes, (all_errors, relative)):
            ax.plot(time[1:], np.maximum(errors[1:], 1e-7)*1000, label=labels[key], color=colors[key], lw=1.6)
    for ax, title, metric in zip(axes, ('Worst of all 354 bodies', 'Moon relative to Earth'),
                                  ('all_bodies', 'moon_relative_to_earth')):
        uncertainty = report['independent_reference_convergence'][metric]['maximum_position_metres']*1000
        ax.axhline(uncertainty, color='#59636c', lw=1., ls='--', label='RK45 level difference (maximum)')
        ax.set(title=title, xlabel='Elapsed time (days)', ylabel='Difference from independent RK45 (mm)', yscale='log')
        ax.grid(True, which='both', alpha=.2)
        ax.legend(fontsize=8, loc='upper left')
    figure.suptitle('Same forces and starts; 45 annual samples. Differences are not global error bounds.', fontsize=11)
    output = Path('docs/error-control-comparison.png')
    figure.savefig(output, dpi=160)
    plt.close(figure)
    print(output)


if __name__ == '__main__':
    main()
