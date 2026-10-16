"""Public research inputs replace the old dependency on a private work cache."""
import pytest

from scripts.prepare_test_inputs import restore


@pytest.fixture(scope="session",autouse=True)
def public_research_inputs():
    restore()
