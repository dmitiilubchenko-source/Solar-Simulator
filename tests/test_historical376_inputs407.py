"""Missing/foreign input bundles must fail, never skip or use the current binary."""
from pathlib import Path
import pytest
from historical376_fixture407 import checkout
ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('kind',['missing','corrupt'])
def test_no_substitution_for_missing_or_changed_historical_dependencies(tmp_path,monkeypatch,kind):
    bundle=tmp_path/'forensic.zip'
    if kind=='corrupt':bundle.write_bytes(b'not historical376 inputs')
    monkeypatch.setenv('SOLAR_HISTORICAL376_BUNDLE',str(bundle))
    with pytest.raises(ValueError,match='Missing exact|Changed offline'):checkout(ROOT,tmp_path/'old376')
