# Проверки и точность

## Какую команду выбрать

Команды запускаются из корня проекта в настроенной среде.

| Задача | Команда |
|---|---|
| Быстрый Python CI-набор | `.venv/Scripts/python.exe -X utf8 -B scripts/check_suites.py python` |
| Короткая приёмка песочницы с Python/Rust | `.venv/Scripts/python.exe -X utf8 -B -m scripts.sandbox_checks` |
| Полная приёмка исходников с настоящим native | `.venv/Scripts/python.exe -X utf8 -B scripts/check_project.py --require-native` |

Что входит в короткую приёмку, её данные и ограничения — в
[локальном README](../../scripts/sandbox_checks/README.md).
Полная source-проверка не заменяет испытание настоящего portable ZIP.
Исследовательский adaptive-набор запускается отдельно при изменениях
относящегося численного кода, а не как обязательный этап любой правки.

Точный список CI: `scripts/check_suites.py <suite> --list`. Python-набор
также проверяет подготовку portable-документов и восстановление публичных
входов. Его общий pytest setup пока требует архив исследовательских входов
даже для простых тестов. [Зависимости и ограничения](../development/maintenance-032.md)
разобраны отдельно; проверка документов не означает приёмку настоящего ZIP.

## На что опирается рабочая версия

Версия 0.3.2 опубликована в main с тегом v0.3.2 после source/native и отдельной
ZIP-приёмки: [результаты и SHA](../release-032-validation.md).
Последующие изменения dev не входят в этот принятый ZIP.

- [Приёмка 0.3.1](../release-031-validation.md): исходники/native, совместимость,
  настоящая portable и новый годовой Strict расчёт из поставки.
- [Плотное сравнение с JPL](../dense-jpl-validation.md): 10 тел / 1 год на заданной
  сетке эпох. Это квалификация конкретных входов и модели.
- [Строгий профиль и границы](../qualification-extension-validation.md):
  отдельные успешные проверки и сохранённый исходный numerical FAIL.
- [Автономный проверочный bundle](../verification-bundle-validation.md):
  различие сохранённого evidence replay и нового интегрирования.

## Как читать результаты

Тесты реализации, аналитическое решение, инварианты, сходимость и остаток
относительно эфемериды отвечают на разные вопросы. Количество PASS или
малый rtol сами по себе не задают точность всех произвольных систем.
Нужно смотреть модель, начальные условия, эпохи, ошибки, критерии и ограничения.

[IAS15 full-state](../ias15-full-suite-validation.md) и
[перезапуск в новом процессе](../ias15-process-validation.md) — ограниченные
завершённые исследования. Они не заменили рабочий SciPy runtime.
[Rust adaptive prototype](../rust-adaptive-prototype-validation.md) сохраняет
непройденные численные критерии. Старые cold/Standard/continuous/PN/rotation/
Kuiper ограничения не отменяются новыми организационными изменениями.

[Границы исторической проверки после 374](../development/historical-checkpoints.md):
архивный replay не квалифицирует сегодняшний runtime; обязательные отказы
годовых receipts сохраняются до отдельного доказательства.

[Текущая квалификация375](../current-runtime-375-validation.md) содержит свежие
Strict/holdout/sandbox расчёты и отдельное сравнение с0.3.2. Historical replay
и current qualification по-прежнему различаются.

[Прицельная проверка рабочего DOP853376](../runtime-reliability-376.md):
обычные пакеты Python/Rust, e=.5/.95/.99 и два начала; аналитический
Decimal-эталон, независимый Fraction observer, точный file/process restart.
Все36 коротких cases сохранены; high-e ошибки не скрыты малым дрейфом энергии.
Наблюдения IAS15 не считаются дефектами рабочего DOP853.

[Пользовательский inspect --reliability](../inspect-reliability.md) объясняет
модель, применимые инварианты, настройки и неизвестные границы пакетов.
Он не выдаёт дрейф энергии за глобальную ошибку и не аттестует произвольный опыт.
[Main/tag/GitHub Release: проверенный статус](../release-status-20261028.md).

В том же руководстве: `check-recipe DIRECTORY --reliability` показывает историю
из manifest/recipe/frames; целостность, текущая совместимость, replay и точность
разделены. Ни одна орбита для этого отчёта не пересчитывается.

[Опыт379: dynamic max_step](../runtime-step-379-validation.md):4 фиксированных
high99 условия376, uncapped exact controls, независимые аналитика/метрики,
смешанный результат и NO-GO. Это отдельная численная диагностика, не новый
профиль точности или изменение пользовательского runtime.

[Две вращающиеся фигуры380](../two-q2-380.md): модель M-Q без Q2-Q2,
независимые производные потенциала и scaled matrix/body-Pi RK45, synthetic
2/3body, старые0/1byte-exact. Сохранены3FAIL пакетной сходимости и отдельный
непрерывный контроль. Новые SHA не наследуют current375 annual qualification.

[Практическая демонстрация381](../two-q2-laboratory.md): GUI lifecycle0/1/2фигуры,
точные380IC, SI/omega solve, проекции, неизменность состояния при просмотре и
отмене, bounded200s demo. Это функциональная проверка, не новая аттестация физики.

[Целостность и CI382](../integrity-ci-382.md): документальный revert проверен
tree/actual blobs/SHA; portable evidence paths и CI integrity отделены от
строгого scientific gate. [План0.3.3](../qualification-033-plan.md) пока не исполнен.

[Подготовка383](../qualification-033-preflight.md): staged0.3.3/native, новые
sealed output существующих375/376/380; bounded preflight не является новой
scientific qualification. Основной запуск пока NO-GO по указанным блокерам.
