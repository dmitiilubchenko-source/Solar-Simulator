"""Verification commands protect existing reports before loading or calculating."""
from pathlib import Path
import subprocess
import sys


def test_fresh_verification_preserves_existing_output_before_opening_missing_bundle(tmp_path):
    root=Path(__file__).resolve().parents[1]
    output=tmp_path/"previous report.json";output.write_bytes(b"sentinel")
    result=subprocess.run([sys.executable,"-X","utf8","-B","-I",str(root/"scripts/recompute_jpl.py"),
        str(tmp_path/"absent bundle"),"--output",str(output)],capture_output=True,text=True,encoding="utf-8",timeout=30)
    assert result.returncode != 0 and "Preserve previous result" in result.stderr
    assert output.read_bytes() == b"sentinel"


def test_fresh_verification_never_writes_inside_verified_payload(tmp_path):
    root=Path(__file__).resolve().parents[1]
    folder=tmp_path/"verified bundle";folder.mkdir()
    result=subprocess.run([sys.executable,"-X","utf8","-B","-I",str(root/"scripts/recompute_jpl.py"),
        str(folder),"--output",str(folder/"result.json")],capture_output=True,text=True,encoding="utf-8",timeout=30)
    assert result.returncode != 0 and "outside sealed bundle" in result.stderr
    assert not (folder/"result.json").exists()
