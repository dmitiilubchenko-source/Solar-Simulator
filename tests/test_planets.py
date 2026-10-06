import pytest
from solar_simulator.motion import update_velocity, update_position
from solar_simulator.planets import find_planet_by_id, planets_heavier_than, add_planet, mass_difference, create_catalog, change_planet_mass, remove_planet

@pytest.fixture
def catalog():
    return create_catalog()

def test_find_planet_by_id(catalog) -> None:

    assert find_planet_by_id(1, catalog=catalog) == ('Земля', {'id': 1, 'mass': 5.972e+24})

def test_planets_heavier_than(catalog) ->  None:

    assert planets_heavier_than(1e26, catalog=catalog) ==  ["Юпитер","Сатурн","Нептун"]
    assert planets_heavier_than(1e100, catalog=catalog) ==  []


def test_add_planet_duplicate_by_id(catalog) -> None:

    with pytest.raises(ValueError) as error:
        add_planet("АВАВА", 1, 1e100, catalog=catalog)
    assert str(error.value) == "Планета с ID '1' уже существует."


def test_mass_difference() -> None:
    planets = {
        "Earth": {"mass": 100},
        "Mars": {"mass": 20},
    }

    planets2 = {
        "Earth": {"mass": 12},
        "Mars": {"mass": 3},
    }

    assert mass_difference(planets, "Earth", "Mars") == 80
    assert mass_difference(planets2, "Earth", "Mars") == 9

def test_update_velocity() -> None:
   assert update_velocity(3.0, 2.0, 0.5) == pytest.approx(4.0)
   assert update_velocity(3.0,  0.0, 5.0) == pytest.approx(3.0)
   assert update_velocity(3.0, -2.0, 2.0) == pytest.approx(-1.0)

def test_update_position() -> None:
    assert  update_position(10.0, 3.0, -2.0, 2.0) == pytest.approx(12.0)
    assert update_position(10.0, 3.0, 0.0, 2.0) == pytest.approx(16.0)
@pytest.mark.parametrize("mass", [0, -1, float("nan"), float("inf")])
def test_invalid_mass_does_not_change_catalog(catalog, mass):
    with pytest.raises(ValueError):
        add_planet("Тест", 8, mass, catalog=catalog)
    with pytest.raises(ValueError):
        change_planet_mass("Земля", mass, catalog=catalog)
    assert "Тест" not in catalog
    assert catalog["Земля"]["mass"] == 5.972e24


def test_catalogs_are_independent(catalog):
    other = create_catalog()
    change_planet_mass("Земля", 1, catalog=catalog)
    remove_planet("Марс", catalog=catalog)
    assert other["Земля"]["mass"] == 5.972e24
    assert "Марс" in other


def test_add_and_find(catalog):
    add_planet("Тест", 8, 10, catalog=catalog)
    name, planet = find_planet_by_id(8, catalog=catalog)
    assert name == "Тест"
    assert planet == {"id": 8, "mass": 10}
    planet["mass"] = 0
    assert catalog[name]["mass"] == 10
