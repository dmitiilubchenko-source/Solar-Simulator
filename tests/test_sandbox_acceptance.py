"""Source receipts must reject tampering; historical failures remain visible."""
import json
from pathlib import Path
import shutil

import pytest

from scripts.accept_sandbox import ROOT, check_receipts, workflows
from scripts.sandbox_checks.accept_sandbox import CURRENT_RECEIPT,audit_receipt_inputs


@pytest.fixture
def historical_checkout(tmp_path):
    """Exact375 source/data bytes; this fixture does NOT qualify the host."""
    import hashlib
    from zipfile import ZipFile
    from scripts.release_history import (ROTATION_ARCHIVE,ROTATION_ARCHIVE_SHA,ROTATION_FILES,
        LABORATORY_ARCHIVE,LABORATORY_ARCHIVE_SHA,LABORATORY_FILES)
    current = json.loads((ROOT/CURRENT_RECEIPT).read_bytes())
    paths = {CURRENT_RECEIPT,current['protocol'],current['array_archive'],
             *current['source_sha256'],*current['input_sha256']}
    for name in paths:
        destination = tmp_path/name
        destination.parent.mkdir(parents=True,exist_ok=True)
        expected=current['source_sha256'].get(name)
        if expected is not None and hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected:
            for archive_name,digest,names in ((LABORATORY_ARCHIVE,LABORATORY_ARCHIVE_SHA,LABORATORY_FILES),
                    (ROTATION_ARCHIVE,ROTATION_ARCHIVE_SHA,ROTATION_FILES)):
                if name not in names:continue
                raw=(ROOT/archive_name).read_bytes();assert hashlib.sha256(raw).hexdigest()==digest
                with ZipFile(ROOT/archive_name) as archive:old=archive.read(name)
                if hashlib.sha256(old).hexdigest()==expected:
                    destination.write_bytes(old);break
            else:raise AssertionError('Exact qualified375 source unavailable:'+name)
        else:shutil.copy2(ROOT/name,destination)
    return tmp_path


def test_dense_failure_retained_and_frozen375_inputs_verified(historical_checkout):
    failed = json.loads((ROOT/"docs/qualification-grid-validation.json").read_bytes())
    strict = json.loads((ROOT/"docs/strict-profile-validation.json").read_bytes())
    assert len(failed["epochs_jd_tdb"]) == strict["samples"] == 125
    assert failed["results"]["rust"]["relative_numerical_error"]["position_metres"] > .1
    assert not failed["checks_passed"] and strict["checks_passed"]
    assert strict["settings"]["rtol"] == 3e-14
    assert all(row["relative_numerical_error"]["position_metres"] < .1 for row in strict["results"].values())
    assert len(strict["holdout_times_seconds"]) == 9
    assert all(row["checks_passed"] for row in strict["holdout"].values())
    assert not strict["jpl_new_epochs_checked"] and not failed["jpl_coverage"]["new_epochs_checked"]
    integrity=audit_receipt_inputs(historical_checkout)
    assert integrity['source_inputs_intact']
    assert integrity['current_environment_checked'] is False
    assert integrity['current_qualification_passed'] is False
    with pytest.raises(ValueError,match='Scientific receipt source/input changed'):
        check_receipts()  # Changed current files cannot borrow historical qualification.


@pytest.mark.parametrize("target", ["src/solar_simulator/oblateness.py", "docs/solar-system-moon-reference.json"])
def test_source_or_pinned_reference_change_rejected_before_acceptance(historical_checkout, target):
    import re
    assert audit_receipt_inputs(historical_checkout)['source_inputs_intact']
    with (historical_checkout/target).open("ab") as stream:stream.write(b"\n")
    with pytest.raises(ValueError, match="changed: "+re.escape(target)):
        check_receipts(historical_checkout)


def test_strict_checkpoint_target_branch_export_and_continuation():
    result = workflows()
    assert result["checkpoint_continue_exact"] and result["initial_unchanged"]
    assert result["csv_rows"] == result["branch_addition_bodies"] == 11
