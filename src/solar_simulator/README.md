# Ключевые файлы Python-пакета

Начните с experiment.py: здесь связываются состояние, настройки и расчёт.
Подробный путь одного шага — в [разборе](../../docs/runtime-walkthrough.md).

| Файл | Ответственность |
|---|---|
| [experiment.py](experiment.py) | Settings/Experiment, создание, проверка сочетаний и advance |
| [simulation.py](simulation.py), [vector3.py](vector3.py) | Тела, векторы, ньютоновская модель и фиксированный шаг |
| [accuracy.py](accuracy.py) | Адаптивное интегрирование DOP853 через SciPy |
| [continuous.py](continuous.py) | Ограниченный непрерывный сеанс DOP853; это отдельный режим с собственными gates |
| [native_forces.py](native_forces.py), [rust_backend.py](rust_backend.py) | Адаптеры рабочих Rust-вычислений |
| [storage.py](storage.py), [branch_io.py](branch_io.py) | Проверка/запись checkpoint и полного опыта с parent |
| [time_control.py](time_control.py) | Продвижение к целевому времени с заданными границами пакетов |
| [ephemerides.py](ephemerides.py), [perturbers.py](perturbers.py) | Начальные астрономические данные и добавления к ним |
| [commands.py](commands.py), [cli.py](cli.py) | Команды песочницы и прежние команды диагностики |
| [app.py](app.py), [orbit_view.py](orbit_view.py) | Окно, управление рабочим потоком и представление результатов |
| [trajectory_loader.py](trajectory_loader.py), [comparison_loader.py](comparison_loader.py) | Фоновая проверка записей, подготовка просмотра/сравнения и отмена; рабочий поток не владеет Tk-объектами |

Численные величины runtime — SI; преобразования ввода и координат должны
быть явными. Физические функции работают без окна. Вид/проекция не должны
менять модель или допуски. Backend rust не означает, что адаптивный
интегратор целиком перенесён в Rust.

Запуск из корня проекта:

```powershell
.venv/Scripts/python.exe -X utf8 -B -m solar_simulator --help
.venv/Scripts/python.exe -X utf8 -B -m scripts.sandbox_checks
```

[Выбор проверок](../../docs/verification/README.md) связывает задачу с нужным
прогоном. Для настоящей полной приёмки требуется собранный native; для
документарной правки не нужен новый годовой расчёт.

Файлы Python здесь оставлены на прежних путях и не продублированы в новых
папках: старые научные отчёты закрепляют их source SHA. Этот README даёт
точку входа в ключевые файлы; физический перенос требует отдельной оценки
импортов, зависимостей и исторической воспроизводимости.
