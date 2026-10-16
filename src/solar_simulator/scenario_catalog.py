"""Display names only: canonical experiment/CLI/storage keys stay unchanged."""
import tkinter as tk


CATALOG = {
    "sun-earth": ("Солнце и Земля", "Учебная двухтельная орбита. Эксцентриситет задаёт форму исходной орбиты Земли."),
    "earth-moon": ("Земля и Луна — учебный опыт", "Учебная двухтельная система без эфемерид и динамического вращения."),
    "binary-star": ("Двойная звезда", "Две звезды обращаются вокруг общего центра масс; учебные начальные условия."),
    "sun-earth-moon": ("Солнце, Земля и Луна — учебный опыт", "Учебная трёхтельная система. Для начальных данных JPL выберите вариант с планетами."),
    "spheres": ("Столкновения двух сфер", "Учебные сферы с контактными радиусами: Verlet и отскоки; доступны остановка и слияние."),
    "solar-system": ("Планетные системы — 9 тел", "Начальные данные JPL DE441: барицентры планетных систем; Земля и Луна объединены."),
    "solar-system-moon": ("Планеты с отдельной Луной — 10 тел", "Начальные данные JPL DE441: Земля и Луна отдельно. Кнопка вращения Луны создаёт отдельный готовый профиль."),
    "solar-system-pluto": ("Планеты и Плутон — 11 тел", "К системе с отдельной Луной добавлен барицентр системы Плутона."),
    "solar-system-asteroids": ("Планеты и 3 астероида — 14 тел", "Система с Луной и Плутоном дополнена Церерой, Палладой и Вестой."),
    "solar-system-asteroids-full": ("Планеты и 16 астероидов — 27 тел", "Набор крупных астероидов SB441. Для больших расчётов можно явно выбрать Rust."),
    "solar-system-asteroids-catalog": ("Планеты и 343 астероида — 354 тела", "Полный набор343астероидов DE441: все тела взаимодействуют, расчёт тяжелее малых опытов."),
    "solar-system-kuiper": ("Астероиды и объекты Койпера — 384 тела", "К набору343астероидов добавлены30отдельных объектов Койпера; все тела взаимодействуют."),
    "solar-system-kuiper-ring": ("Кольцо Койпера — эксперимент, 420 тел", "Экспериментальное кольцо420не прошло геометрический критерий. Вариант528из JSON прошёл свои проверки, но остатки KBO выросли."),
}
KEY_BY_TITLE = {values[0]: key for key, values in CATALOG.items()}


class ScenarioVariable(tk.StringVar):
    """Tk displays a Russian title; application callers read/set canonical keys."""
    def __init__(self, master=None, value="sun-earth"):
        super().__init__(master, value=CATALOG[value][0])

    def get(self):
        title = super().get()
        if title not in KEY_BY_TITLE:
            raise ValueError("Неизвестный сценарий: "+title)
        return KEY_BY_TITLE[title]

    def set(self, value):
        if value not in CATALOG:
            raise ValueError("Неизвестный сценарий: "+str(value))
        super().set(CATALOG[value][0])
