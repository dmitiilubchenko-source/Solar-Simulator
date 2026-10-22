# IAS15: сила C/Rust для десяти тел, протокол359

23 октября2026, до реализации и расчётов. Новый вопрос: сохраняет ли IAS15
численные критерии175 при замене только C/basic силы полным callback Rust?
Это не повтор прежнего C-IAS15 против Rust/SciPy-DOP853 бенчмарка.
Основание: [171–175](newton-year-protocol.md),
[357](ias15-native-newton-validation.md), [358](ias15-native-session-validation.md).

## Данные, модель, критерии

Те же Sun/Mercury/Venus/Earth/Moon/Mars/Jupiter/Saturn/Uranus/Neptune,
IC `solar-sandbox-strict-checkpoint.json` и year_times из
`continuous-integration-reference.npz`, с исходными SHA171. SI, SSB,
Ecliptic J2000, JD2461321.5 TDB, происхождение DE441; время модели в секундах.
Массы гигантов относятся к исходным барицентрам; новых тел/спутников нет.
Только Newton point masses, без PN/J2/spin/softening/COMshift/relative_pair.
Те же G и начальные binary64 массы/p/v, без подгонки или ручной правки IC.

Сначала pilot30суток на прежней61эпохе, затем полный31557600с/125эпох.
Пакеты по старому `newton_year.packet_end`:20×3600с с укорочением на выходах,
полный год499границ. Это другая сетка, чем у двухтельного сеанса358.
REBOUND5.2.2 IAS15, epsilon1e-9/1e-11, PRS23/min_dt0/softening0,
initialdt18с, exact_finish_time1. Один тёплый controller на траекторию.
Native: gravitynone, полный NewtonCallback357, velocity-dependent0,
light_speedNone/relative_pairNone; настоящий compiled solar_native, no fallback.
Basic: встроенная C-сила. Настройки/masses проверять до/после каждого пакета,
ошибки callback/NaN/shape/interrupt перекидывать до возврата результата.
Сеанс/checkpoint358 с ограничением N=2 не менять и не выдавать за N-body.

Критерии175: для каждого тела r<10м,v<1e-4м/с; Moon−Earth r<0.1м,v<1e-5м/с;
полные ньютоновские E/L/P drift<1e-10. Отсчёт инвариантов от исходных IC;
не энергия изолированной пары. Публиковать все тела, оба epsilon и всеFAIL.
Не заявлять точность относительно JPL для этой неполной Newton-модели.

## Квалификация существующего эталона

Не переносить широкий source-PASS175:8файлов уже отличаются. Проверить SHA
обоих raw JSON/NPZ из public receipt175, source-модули actual RK45/metrics,
версии NumPy/SciPy/Python, G/AU/LEVELS, битовые IC/grid/masses и origin.
Сравнения четырёх уровней RK45 и initial roundtrip пересчитать из кеша.
Граница принятия эталона прежняя: тела1м/1e-6мс, пара0.01м/1e-7мс;
roundtrip тела0.002м/1e-8мс, пара0.0001м. Никакой ручной замены первой строки.
Повторить reference_2 (rtol3e-14/max450с/AU-year) для pilot и года текущим
кодом; требовать побитного совпадения с кешем. При несовпадении сохранить
отказ и не сертифицировать кандидатов этим эталоном. Оценка чувствительности
не является строгой глобальной границей ошибки. Первичные источники и
описание независимой RK45/EMB реализации остаются из протокола171.

## Проверки и результаты

До полного опыта: наклонное аналитическое равностороннее трёхтельное решение
для обоих modes/epsilon, независимый Decimal100 градиент потенциала для
исходных10тел (<5e-13 относительно нормы ускорения каждого тела), реакция/
перестановка/rotation, native исключения/NaN/shape/interrupt, doublegravity,
точный fractional endpoint и запрет перезаписи старого output.
C-контроль outputs/steps/calls/границы обязан повторить175; дополнительно
сверить с прежним `newton_year.ias_trajectory` на текущих IC.

Прогрев+3чередующихся полных повтора каждого варианта; basic без counter
в таймере и отдельный counted прогон, native всегда считает callback.
Повторы/инструментирование не меняют arrays/steps. Таймер включает setup,
integration/FFI и снятие125outputs/всех packetstates; oracle/metrics/hash/файлы
исключены. Это цена двух реализаций силы/обвязки, не чистого интегратора.

Новый output/source snapshot, partial receipt при отказе; точные source/input/
library/native/sdist SHA до/после, Cargo canonicalLF+raw before/after как357.
Сохранить raw reference175 и его неизменные receipts. Для публичного offline
replay использовать точные оригинальные NPZ175, новые arrays/receipt/метрики,
проверить другой root без C/native/.tools/сети и отказ при повреждении данных.
PASS359 относится к численному Newton/N-body coupling на этих эпохах.
Лицензия/поставка IAS15, собственный Rust-интегратор, cold recovery, JPL,
общая версия/portable/main — отдельные решения и проверки.
