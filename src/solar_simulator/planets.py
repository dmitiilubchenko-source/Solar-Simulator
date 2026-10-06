from math import isfinite


def _validate_mass(mass: float) -> None:
    if not isfinite(mass) or mass <= 0:
        raise ValueError("Масса должна быть положительным конечным числом")


def create_catalog():
    """Создать независимый каталог; массы в килограммах."""
    return {
        "Земля": {"id": 1, "mass": 5.972e24},
        "Марс": {"id": 2, "mass": 6.39e23},
        "Венера": {"id": 3, "mass": 4.867e24},
        "Юпитер": {"id": 4, "mass": 1.898e27},
        "Сатурн": {"id": 5, "mass": 5.683e26},
        "Уран": {"id": 6, "mass": 8.681e25},
        "Нептун": {"id": 7, "mass": 1.024e26}
    }

def add_planet(name: str, planet_id: int, mass: float, *, catalog: dict) -> None:
    _validate_mass(mass)
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Имя не должно быть пустым")
    if type(planet_id) is not int or planet_id <= 0:
        raise ValueError("ID должен быть положительным целым числом")
    if name in catalog:
        raise ValueError(f"Планета с именем '{name}' уже существует.")
    if planet_id in [planet["id"] for planet in catalog.values()]:
        raise ValueError(f"Планета с ID '{planet_id}' уже существует.")

    planet = {"id": planet_id, "mass": mass}
    catalog[name] = planet


def find_planet_by_id(planet_id: int, *, catalog: dict):
    for name, planet in catalog.items():
        if planet["id"] == planet_id:
            return name, planet.copy()
    raise ValueError(f"Планета с ID '{planet_id}' не найдена.")

def change_planet_mass(name: str, new_mass: float, *, catalog: dict) -> None:
    _validate_mass(new_mass)
    if name not in catalog:
        raise ValueError(f"Планета с именем '{name}' не найдена.")
    catalog[name]["mass"] = new_mass

def remove_planet(name: str, *, catalog: dict) -> None:
    if name not in catalog:
        raise ValueError(f"Планета с именем '{name}' не найдена.")
    del catalog[name]

def planets_heavier_than(mass: float, *, catalog: dict) -> list[str]:
    if not isfinite(mass) or mass < 0:
        raise ValueError("Порог массы должен быть конечным и неотрицательным")
    list_of_planets = []
    for name, planet in catalog.items():
        if planet["mass"] > mass:
            list_of_planets.append(name)
    return list_of_planets

def mass_difference(register, planet_name1, planet_name2) -> float:
    if planet_name1 not in register or planet_name2 not in register:
        raise ValueError("Планета не найдена в параметре register.")
    return abs(register[planet_name1]["mass"] - register[planet_name2]["mass"])
