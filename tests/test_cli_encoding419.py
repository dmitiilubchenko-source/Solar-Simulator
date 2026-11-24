"""Expected CLI errors remain readable when Windows stderr is redirected."""
from pathlib import Path
import subprocess
import sys


def test_redirected_ascii_stderr_is_utf8_for_expected_error(tmp_path):
    root = Path(__file__).resolve().parents[1]
    raw = root / 'src/solar_simulator/data/two-q2-demo380.json'
    code = "import sys; sys.stderr.reconfigure(encoding='ascii',errors='backslashreplace'); from solar_simulator.commands import main; main(['inspect',sys.argv[1]])"
    p = subprocess.run([sys.executable, '-B', '-c', code, str(raw)], capture_output=True, cwd=tmp_path)
    assert p.returncode == 2
    assert 'не более одного' in p.stderr.decode('utf-8')
    assert b'Traceback' not in p.stderr
