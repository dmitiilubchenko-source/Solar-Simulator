# Короткая карта проекта

Актуально на 25 октября 2026. Принятый выпуск — 0.3.2, разработка в dev.
Начало документации — [четыре раздела](README.md); ниже ключевые части кода.

| Часть | Точка входа | Ответственность |
|---|---|---|
| Python-пакет | [Локальный README](../src/solar_simulator/README.md) | Настройки/состояние, расчёт, сохранения и интерфейс; в README перечислены ключевые файлы |
| Rust core | [Локальный README](../rust/solar_core/README.md) | Newton/EIH силы, Verlet, диагностика и контакты |
| Python/Rust мост | [Локальный README](../rust/solar_native/README.md) | PyO3 API и массивы на границе языков |
| Экспериментальный solver | [Локальный README](../rust/solar_adaptive/README.md) | Исследовательский Rust adaptive, отдельно от продукта |
| Короткая приёмка | [Локальный README](../scripts/sandbox_checks/README.md) | Научные receipts, аналитика и пользовательский цикл |
| Проверки | [Команды и области](verification/README.md) | Быстрый CI, полная source/native приёмка, ограниченные научные результаты |
| Работа с программой | [Руководства](user/README.md) | Редактор, ветки, запись, сравнение и recovery |
| Фоновое чтение | [Загрузчик траекторий](../src/solar_simulator/trajectory_loader.py), [загрузчик сравнения](../src/solar_simulator/comparison_loader.py) | Общий жизненный цикл окна загрузки; чтение и подготовка вне Tk, отмена между кадрами |
| Разработка | [Первое чтение](development/README.md) | Установка, путь одного шага, компоненты и выпуски |
| Числовой ввод | [Контракт](development/numeric-validation.md), [_numbers.py](../src/solar_simulator/_numbers.py) | Типы физических параметров и ранняя валидация; формулы и кодеки прежние |

## Правила размещения

Код продукта находится в src и rust; scripts содержит рабочие инструменты
и отдельные исследовательские стенды. tests проверяет реализацию и контракты.
Реестр публичных файлов — [project-inventory.json](project-inventory.json).

Для связанной группы допускается локальный README. Папка на каждый маленький
файл и отдельные CHANGELOG не обязательны. Изменение импорта/команды/ограничения
должно отражаться в README группы и затронутых проверках.

Личные инструкции, журнал, план и handoff передаются только через разрешённый
приватный контекст; они не входят в публичный код или portable. .tools,
recovery, пользовательские записи и build/dist — разные виды данных;
их не удаляют как одну общую кучу.

Численные исходники и JSON/NPZ с source SHA сохраняют канонические пути.
Для их переноса сначала требуется оценка воспроизводимости; нельзя заменять
старые SHA текущими ради PASS. Короткая карта не квалифицирует новую физику.

Прежняя подробная карта и завершённые ревью сохранены в [архиве](archive/README.md).

[Исторические доказательства и checkpoint](development/historical-checkpoints.md):
минимальный resolver, обязательные зависимости и отдельные границы допуска.

[Квалификация текущего ядра375](current-runtime-375-validation.md): фиксированный
протокол, реальные Python/Rust jobs, независимый reference и source-bound gate.

[Рабочий DOP853 и надёжность376](runtime-reliability-376.md): путь вычисления,
границы применимости Research,36 коротких Newton cases, high-e ошибки и точное
file/process продолжение. Численная диагностика не заменяет JPL qualification.

[Понятный отчёт о надёжности](inspect-reliability.md): opt-in расширение
`inspect` в commands.py и presentation helper inspection.py. Старый cli.report,
физические diagnostics, recipe, storage и интеграторы сохраняют прежние байты.

`check-recipe DIRECTORY --reliability` в том же helper показывает проверенный
пакетный префикс записи, endpoints fingerprints и отдельно текущую совместимость;
точность траектории и фактический replay из этих сведений не следуют.

[Ограниченный max_step379](runtime-step-379-validation.md): один d32 для
обычного high-e DOP853; peri-start лучше, apo-start position хуже. NO-GO
для production, никакого изменения сил/интегратора/пользовательских настроек.

[Две динамические Q2-фигуры380](two-q2-380.md): существующий RotationDOP853,
усечённый M-Q Hamiltonian без Q2-Q2, два q/S, schema10 save/resume, независимые
градиенты/матричный RK45. Старые0/1 сохраняются. Три packet convergence FAIL
сохранены; непрерывный контроль сходится. Current375 gate новому коду отказывает.

[Laboratory381](two-q2-laboratory.md): package resource точных synthetic380 IC,
готовый профиль, оси на существующих2Dпроекциях, read-only q/S/ω и доступ к
inspection.report через существующий async-loader lifecycle. Физика/CLI/schema
не менялись; PRESETS остаются базовыми сценариями, demo — отдельная кнопка.

[Аудит382](integrity-ci-382.md) и [план квалификации0.3.3](qualification-033-plan.md):
сохранность после документального отката, CI portability/source integrity,
отдельный строгий source/environment-bound gate и ещё не выполненный release plan.

[Подготовка кандидата383](qualification-033-preflight.md): отдельный staging export,
явный metadata overlay, новые sealed планы и output существующих drivers.
Технический preflight не является научной квалификацией или выпуском.

[Newton384](newton-384-validation.md): отдельный Git-кандидат033, свежие36jobs,
независимый raw-state audit, scope375/380 и сохранённые ограничения выпуска.

Годовой successor375 кандидата033: [протокол385](annual-385-protocol.md),
[scripts/qualify_annual385.py](../scripts/qualify_annual385.py),
[scripts/assess_annual385.py](../scripts/assess_annual385.py); без изменения runtime.
