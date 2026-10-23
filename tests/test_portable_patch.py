"""Exercise the same real-process probe used for the extracted 0.3.1 runtime."""
import json
import os
from pathlib import Path
import subprocess
import sys


def test_patch_probe_in_real_isolated_process(tmp_path):
    env = os.environ.copy()
    env['LOCALAPPDATA'] = str(tmp_path/'user data')
    env['MPLCONFIGDIR'] = str(tmp_path/'matplotlib')
    script = Path(__file__).resolve().parents[1]/'scripts/portable_patch_workflows.py'
    process = subprocess.run([sys.executable, '-X', 'utf8', '-B', '-I', str(script)],
                             cwd=tmp_path, env=env, capture_output=True, text=True,
                             encoding='utf-8', timeout=120)
    assert process.returncode == 0, process.stdout+process.stderr
    result = json.loads(process.stdout)
    assert result['isolated'] == 1
    assert result['preserved_transitions'] == result['rejected_write_failures'] == 6
    assert result['physical_accuracy_claim'] is False
    assert all(result[k] for k in ('reader_off_Tk_thread', 'Tk_heartbeat',
        'cancellation_preserves_recording', 'analytic_free_motion_frames',
        'playback_no_solver', 'persistent_artists'))
