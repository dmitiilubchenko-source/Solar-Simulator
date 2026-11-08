"""Portable negative controls for the strict403 text whitelist."""
import pytest
from scripts.q2_text_delta403 import compare
BASE=b"TWO_Q2_EXPERIMENTAL_WARNING=('old')\n\ndef f():return 7\n"
def test_only_literal_change_allowed():
 assert compare(BASE,BASE.replace(b"'old'",b"'new'"))['all_other_AST_and_bytes_exact']
@pytest.mark.parametrize('bad',[BASE.replace(b'return 7',b'return 8'),BASE.replace(b"('old')",b"str('new')"),BASE+b'# extra\n',BASE.replace(b"('old')",b"('new',)"),BASE+b"TWO_Q2_EXPERIMENTAL_WARNING='duplicate'\n"])
def test_unapproved_structural_or_byte_delta_rejected(bad):
 with pytest.raises(ValueError):compare(BASE,bad)
