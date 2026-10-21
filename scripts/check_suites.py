"""Explicit CI subsets. Full acceptance remains check_project.py --require-native."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
SUITES={
    'python':[
        'tests/test_vector3.py','tests/test_simulation.py','tests/test_storage.py',
        'tests/test_environment_check.py','tests/test_gui_process_encoding.py','tests/test_project_links.py',
        '--deselect=tests/test_storage.py::test_checkpoint_resume_matches_uninterrupted[sun-earth-rust]',
        '--deselect=tests/test_storage.py::test_checkpoint_resume_matches_uninterrupted[spheres-rust]'],
    'desktop':[
        'tests/test_app_workflows.py','tests/test_experiment_transition_gui.py',
        'tests/test_controlled_stop.py','tests/test_recovery_journey.py',
        'tests/test_trajectory.py','tests/test_trajectory_gui.py','tests/test_trajectory_loading.py',
        'tests/test_plot_artists.py','tests/test_body_units_gui.py','tests/test_required_native.py'],
    'adaptive':[
        'tests/test_rust_adaptive_audit.py','tests/test_rust_adaptive_diagnosis.py',
        'tests/test_kepler_shadow.py','tests/test_shadow_refinement.py','tests/test_rust_trace.py']}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('suite',choices=SUITES)
    parser.add_argument('--list',action='store_true',help='Show exact selected tests without executing them')
    args=parser.parse_args(argv)
    if args.list:print(json.dumps(SUITES[args.suite],indent=2));return
    python=[sys.executable,'-X','utf8','-B']
    cargo=shutil.which('cargo') or str(Path.home()/'.cargo/bin'/('cargo.exe' if sys.platform=='win32' else 'cargo'))
    def run(command):subprocess.run(command,cwd=ROOT,check=True)
    run(python+['scripts/project_inventory.py'])
    plugins=[]
    if args.suite=='desktop':
        run(python+['scripts/check_environment.py','--require-native','--gui'])
        plugins=['-p','scripts.native_audit']
    run(python+['-m','pytest','-q','-p','no:cacheprovider',*plugins,*SUITES[args.suite]])
    if args.suite=='desktop':
        for crate in ('solar_core','solar_native'):
            run([cargo,'fmt','--manifest-path',f'rust/{crate}/Cargo.toml','--check'])
        run([cargo,'test','--manifest-path','rust/solar_core/Cargo.toml'])
    if args.suite=='adaptive':
        manifest='rust/solar_adaptive/Cargo.toml'
        run([cargo,'fmt','--manifest-path',manifest,'--check'])
        run([cargo,'test','--manifest-path',manifest])
        run([cargo,'test','--manifest-path',manifest,'--features','diagnostic-trace'])


if __name__=='__main__':main()
