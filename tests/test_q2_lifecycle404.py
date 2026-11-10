"""Portable negative controls for unchanged callback/import/byte scope."""
import pytest
from scripts.q2_lifecycle_delta404 import protected_rest
OLD=b'class Laboratory:\n    def _poll(self):return 1\n\n    def _finish_stop(self):return 2\n'
def test_lifecycle_change_does_not_grant_changes_to_other_methods():
 protected_rest(OLD,OLD.replace(b'_poll(self):return 1',b'_poll(self):return 3'),'Laboratory',{'_poll'})
@pytest.mark.parametrize('new',[OLD.replace(b'_finish_stop(self):return 2',b'_finish_stop(self):return 4'),b'import os\n'+OLD,OLD+b'# outside\n'])
def test_protected_dispatch_import_or_bytes_are_rejected(new):
 with pytest.raises(ValueError):protected_rest(OLD,new,'Laboratory',{'_poll'})
