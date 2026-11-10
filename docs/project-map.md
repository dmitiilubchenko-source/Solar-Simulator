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

[Квалификация R-reuse399](q2-scientific-qualification-399.md) и
[машинные результаты](q2-scientific-qualification-399.json): 58 фиксированных
jobs, exact source equivalence и независимый offline-аудит. Три прежних
strict convergence FAIL сохранены; результат не является разрешением релиза.

[Интерфейсный кандидат400](q2-experimental-interface-400.md): отдельная
ветка с общим предупреждением о двух Q2. Проверка остановлена по CPU;
новый fingerprint и реальный AST-допуск не завершены. Dev runtime прежний.

[Завершение source-bound проверки401](q2-interface-qualification-401.md):
реальный AST/fingerprint, два аутентифицированных старых point-результата и
десять недостающих запусков; шесть точных сравнений. Инструменты и границы —
[qualification401](../scripts/qualification401/README.md). Исторический400
остаётся PARTIAL; application A/D1 и выпуск ещё не разрешены.

[Прикладная квалификация402](q2-application-acceptance-402.md): владелец утвердил
A+D1 только для точного200sдемо.22jobID завершены; численные D1 gates прошли,
но10mэффект скалярного расстояния не достигнут. Полный учебный D1 остаётся NO-GO,
исторические/новые convergence FAIL сохранены. [Инструменты](../scripts/qualification402/README.md)
не меняют runtime; выпуск/portable не разрешены.

[Маркировка и lifecycle403](q2-ui-lifecycle-403.md): отдельный кандидат с одним
изменённым текстовым литералом; причины Tcl pending-after исследованы без орбит.
[Локальные инструменты](../scripts/qualification403/README.md) сохраняют исходные
FAIL402/380 и отделяют дефект teardown от исправления тестового harness.

[Исправление lifecycle404](q2-gui-lifecycle-fix-404.md): отдельный GUI-кандидат
с отменой owned poll/layout/TkAgg callbacks, без изменения физики или текста403.
[Проверки и ограничения private API](../scripts/qualification404/README.md)
отделяют технический teardown-допуск от прежних научных и учебных FAIL;
это не универсальный допуск GUI или релиза.

[Финальная маркировка405](q2-final-ui-marking-405.md): один литерал после fix404,
сохранённые scientific FAIL, новый source fingerprint и один штатный GUI smoke.
[Проверки текста и provenance](../scripts/qualification405/README.md) переиспользуют
guards403/404 и учитывают sparse checkout и контракт scheduled inspector poll.

[Полная source/native/GUI приёмка406](q2-release-source-acceptance-406.md):
exact405 candidate,3045узлов без исключений,2972PASS/63FAIL/10ERROR.
[Исполнители и sealed plan](../scripts/qualification406/README.md) отделяют
реальные GUI-ограничения, исторические fixtures и ошибки размещения стенда.
Rust/native и bounded recovery прошли, общая source/portable/release приёмка NO-GO.

[Устранение блокеров407](q2-release-blockers-407.md): отдельный кандидат от405,
layout/poll ownership, exact historical fixtures и публичные402/404документы.
[Инструменты и план408](../scripts/qualification407/README.md) сохраняют73исходных
отказа и phased PASS; полный3073прогон ещё не выполнен, scientific/release NO-GO.

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

Результат385: [годовая EIH+J2 квалификация](annual-385-validation.md);
Strict PASS, Standard Rust diagnostic FAIL, compatibility отдельно UNRESOLVED.

Две Q2: [область/политика386](two-q2-scope-386.md),
[отдельный прикладной draft](two-q2-application-protocol.md); waiver/B_app требуют владельца.

Совместимость032/033: [контракт387](compatibility-387-plan.md),
[частичный результат387](compatibility-387-validation.md),
[read-only verifier/observer](../scripts/check_compatibility387.py).
Acquisition остановлен по памяти до IC; A/B/C ещё не квалифицированы.

[Startup-memory388](startup-memory-388-validation.md): privatecommit проверен
прямым Win32 API, controlled BLAS profiles, originalSTOP сохранён;
[план продолжения387](compatibility-387-continuation-388-plan.md) без выполнения орбит.

[Реальное сравнение389](compatibility-389-validation.md):8shortcases exact,
legacy/recovery/GUI checks; fullgate остаётся PARTIAL до oldtwo-Q2 negativecheck.
[План389](compatibility-389-plan.md) и [harness/observer](../scripts/check_compatibility389.py).

[Контроль390](compatibility-390-validation.md) завершил oldtwo-Q2negative безорбит;
[assessment387–390](compatibility-387-390-assessment.md) закрывает только restricted
compatibility A/B/C, не release033/scientificaccuracy gate.

[Состав релиза391](release-scope-391.md): конкретное предложение A/B,
учебные бюджеты D1/D2, маркировка и порядок оставшейся приёмки.
Решение владельца ещё требуется; runtime и замороженный кандидат не менялись.

[Расследование Q2-392](q2-numerical-investigation-392.md): независимые сохранённые
метрики, ограниченные standard cold/continuous traces и профиль RHS.
Причинный вклад reset/roundoff не разделён; три FAIL380 остаются FAIL.
Offline CLI: scripts/q2_saved_metrics392.py, без интегрирования/текущей аттестации.

[Локальные Q2-контрасты393](q2-causal-investigation-393.md): source-bound fixed
COM frame, pure encode/decode, независимый Decimal observer и15старыхпакетов.
Frame CONTRIBUTES, restart/truncation-v-roundoff UNRESOLVED, production не менялся.
Tools: scripts/q2_fixed_frame393.py и scripts/q2_frame_observer393.py; не runtime.

[Изолированный R-reuse394](q2-performance-prototype-394.md): локальный branch
от frozen033, exact short r/v/q/S/RHS/persistence, five-series timing.
GO TO REVIEW, не внедрение/новая qualification; helper и exact patch вне runtime.

[Review/кандидат395](q2-optimization-review-395.md): отдельный source f723a21,
индивидуальная проверка raw timing/error precedence и0/1/2Q2+actualTk.
[Следующая scientific qualification](q2-optimized-qualification-protocol-395.md)
только спланирована; ни optimized runtime в dev, ни новый scientificPASS не объявлены.

[Preflight396](q2-optimized-qualification-396.md): источники проверены, K=1
reference380 блокирует запуск58jobs. Новый provenance/output helper вне runtime;
0/58, старые3FAIL сохранены, исправление reference требует отдельного этапа.

[Reference repair397](q2-reference-repair-397.md): отдельный K1/K2 output unpacker,
старый380/RHS неизменны, recovery archive audit/short analytic controls.
Proposed398 binding plan сохраняет58jobs, которые здесь не запускались.

[Preflight398](q2-qualification-preflight-398.md): draft fixed58 executor,
body-ID observer и continuous-t0 recording fix; partial Python probes/faults.
NO-GO399: Rustcohorts/controller/budget admission не завершены, sealedGOplan нет.

[Preflight398B](q2-qualification-preflight-398b.md): missingRust prefixes завершены,
resource-history guard проверен и усилен; независимый merge/budget по4cohorts
пока только проект. NO-GO399, production physics/candidates не изменены.

[Групповой допуск398C](q2-final-admission-398c.md): собственные budgets/receipts
четырёхгрупп, guardedresume и отдельная full58offline assessment. TechnicalGO,
[sealedplan399](../scripts/q2-qualification399-plan.json); выполнение отдельно
разрешает владелец. Это validationtooling, не новый физический runtime.
