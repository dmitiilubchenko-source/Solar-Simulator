# Годовая квалификация385: successor375 для кандидата0.3.3

31 октября2026. Этот документ фиксируется до научного запуска.
Разрешение владельца: отдельный successor с исходной наукой375, новой
source/native/environment привязкой и отдельным статусом compatibility.
Кандидат неизменен: `fe0f456f2c7ba3a077eac21fc8413937d6e84fac`.
Исторический375, CURRENT_RECEIPT_SHA, 376/380/384 и все прежние FAIL сохраняются.

## Модель и критерии

Точное научное содержимое [protocol375](../scripts/current-runtime-375-protocol.json)
копируется без изменений; меняются только разрешённые383 provenance fields
runtime_commit/candidate_native/candidate_environment. Отдельный freeze385
связывает этот JSON, полную среду, source/data и новые observing/assessment tools.
Проверка выполняется в существующей собственной кандидатной venv, не Research.

10 тел DE441 (планетные барицентры, разрешённые Earth/Moon без двойной EMB),
SSB/EclipticJ2000, JD2461321.5TDB, SI,31557600s,125epochs/9holdout.
EIH1PN point masses + fixed Sun/Earth J2 с реакцией; mixed PN–figure,
приливы, астероиды и высшие PN члены отсутствуют. [Первичная основа и
соглашения375](current-runtime-375-protocol.md) и [рабочие силы](native-eih.md).
Используются исходные SHA-проверенные40ответов JPL; без запроса новых эпох.

SciPy production PerBodyDOP853, Earth–Moon relative variables, dt3600s,
Strict rtol3e-14, atol.001m/1e-9m/s,20/10intervals per packet.
Python/Rust strict20/strict10/standard20(1e-13), оба strict holdout20.
Standard остаётся диагностическим; старый FAIL не аннулируется новым результатом.
Прежние6sandbox cases ×2backends также выполняются существующим375 driver.

Численные gates375: <10m/<1e-4m/s для каждого тела; Earth–Moon<.1m/<1e-5m/s;
reference sensitivity<1m/тело и<.1m относительной пары; model energy residual<1e-10;
tolerance/packet sensitivity<10m/тело/<.1m Earth–Moon. Все прочие criteria375,
включая sandbox, сохранены в исходном JSON дословно.
JPL residual отдельно:<10km/тело/<1km Earth–Moon на125epochs. Это не solver error.

Независимый reference — прежний scalar Rust EIH/body-axis J2, другая EMB-карта,
AU/year/interleaved RK45, уровни rtol1e-13/max_step1800s и3e-14/900s,
atol1e-17. Свежая компиляция oracle в exclusive output, без старого reference cache.
Рабочий DOP853 остаётся без max_step; d32 не применяется.

## Инструментирование и независимый replay

[Обёртка](../scripts/qualify_annual385.py) запускает неизменный375 driver
из candidate/scripts. Новые инструменты имеют свой Git commit/SHA, не
переносятся в кандидатную ветку. До/после каждого job проверяются реальные
candidate HEAD/чистота, все frozen sources, native/dependencies/thread settings,
G, протокол и inputs. np.load старых scientific arrays при acquisition запрещён;
старые cache bytes разрешены только для исходной SHA-проверки375.
Каждый завершённый пакет журналируется; при STOP остаются packet data и
завершённые per-job arrays/receipts. Внутренние accepted/rejected steps неизвестны.

[Новый assessor](../scripts/assess_annual385.py) переиспользует numerical,
sensitivity, packet-grid, JPL parsing и gates375. Все saved r/v и JPL метрики
повторно вычисляются scalar math.dist, инварианты — отдельными scalar fsum
Noether E/P/L + fixedJ2 potential. Сверка scalar/runtime E имеет заранее
заданный технический предел1e-13|E0| (не новый science accuracy threshold).
E измеряется в J, P в kg·m/s, L в kg·m²/s. Fixed-axis J2 не сохраняет orbital L;
1PN P и E имеют ошибки усеченияO(c^-4), mixed PN–figure terms не включены.
Совпадение backend не является независимой физической теорией. Арифметический
audit разделяет исходные уравнения, константы, binary64 и saved reference;
это не внешняя рецензия и не строгая граница глобальной ошибки.

Exact same-packet checkpoint restart проверяется реальным375 driver и saved
middle/resumed arrays. Source-bound новые научные gates не переопределяют
старый CURRENT_RECEIPT_SHA. Текущий произвольный runtime не аттестуется replay.

## Compatibility и stop rules

Оригинальная375 среда имела unset numerical thread variables. Новый запуск
явно фиксирует OMP/OPENBLAS/MKL_NUM_THREADS=1, прочие переменные записываются
как реально установлены. Старую среду не выдавать за восстановленную.
Accepted032 не запускается в подставленном окружении. Compatibility — отдельный
UNRESOLVED, byte-exact gate не выполнен; произвольного численного допуска нет.
Исключение accepted032 jobs из новой матрицы относится только к этой явно
разрешённой отдельной проверке совместимости; scientific375 criteria не меняются.

CPU allocation до запуска: runtime600s, fresh reference350s, assessment100s,
reserve150s; hard total1200CPU/1800wall/2GiBprivate tree/512MiBnew artifacts.
Ранние пределы aggregate1100CPU/1700wall/1.75GiBcombined private/448MiB.
Обоснование:375наблюдал current21–69s и annual+holdout reference~135s wall,
но overlap не доказывает CPU; резерв учитывает журналирование/надзор/другой ABI.
Запуски последовательные. Существующий50msmonitor384 используется побайтно;
parent CPU/RAM учитываются отдельно. Sampling допускает short-process/spike
пропуски и небольшой overshoot; это не OS hard quota. При STOP бюджет не
поднимается и не сбрасывается. Публикуются все частичные результаты/причины.

Перед запуском: arithmetic/fault tests, actual-native probe, negative source/
native/environment/protocol SHA checks, проверка exclusive output и полноты.
После — independent saved-data assessment, повторная SHA-проверка, resource
summary, compact evidence и reviewed non-Git archive с cloud SHA readback.
Полная Q2/check_project/portable/main/tag/release/LATEST запрещены. После385 стоп.
