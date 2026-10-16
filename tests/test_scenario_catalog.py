import tkinter as tk
import pytest

from solar_simulator.scenario_catalog import CATALOG, KEY_BY_TITLE, ScenarioVariable
from solar_simulator.experiment import PRESETS


def test_catalog_has_unique_display_names_for_every_canonical_preset():
    assert tuple(CATALOG) == PRESETS
    assert len(KEY_BY_TITLE) == len(PRESETS)
    assert all(title and description for title, description in CATALOG.values())
    assert "не прошло" in CATALOG["solar-system-kuiper-ring"][1]


def test_scenario_variable_preserves_keys_and_decodes_actual_Tk_selection():
    interpreter = tk.Tcl()
    variable = ScenarioVariable(interpreter)
    for key in PRESETS:
        variable.set(key)
        assert variable.get() == key
        assert interpreter.getvar(variable._name) == CATALOG[key][0]
        interpreter.setvar(variable._name, CATALOG[key][0])
        assert variable.get() == key
    with pytest.raises(ValueError, match="Неизвестный"):
        variable.set("unknown")
