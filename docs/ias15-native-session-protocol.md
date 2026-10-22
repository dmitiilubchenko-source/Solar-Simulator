# Тёплый IAS15-сеанс с полной силой Rust: протокол 358

23 октября 2026, до реализации и результатов. Основание:
[356 lifecycle](ias15-session-validation.md),
[357 force coupling](ias15-native-newton-validation.md).
Новых формул нет: прежние Newton2point/SI/инерциальные3D/model-time t0=0,
источники и ограничения IAS15 из [обзора](integrator-candidate-review.md).
Не регистрировать метод в runtime, не выбирать лицензию/способ поставки.

## Минимальная правка и история

В существующем research IAS15Session выделить создание controller,
интегрирование пакета и проверку модели в три внутренние операции.
Поведение по умолчанию basic сохраняется. Явный IAS15NativeSession повторно
использует владение копиями, атомарный committed tuple, границы, latch/close.
Полная native сила и проверка callback берутся из357: gravity=none,
velocity-dependent=0, light_speed=None, relative_pair=None; без COMshift/PN/J2.
Настройки проверять до и после интегрирования, callback.check до commit.
Никаких общих registry/traits/plugin-интерфейсов для гипотетической физики.

До правки сохранить точные байты IAS15Session356 в
scripts/validation/ias15_session_356.py, проверить по исходному SHA receipt356.
Replay356 использует явно этот исторический файл с прежним SHA, остальные
bindings проверяет как прежде. Старые JSON/NPZ/протоколы не менять. Исторический
PASS не квалифицирует новую реализацию; новый сеанс проходит отдельный опыт.

## Контракт и проверки до полного опыта

Один controller до close/ошибки, независимые входные/выходные массивы;
current/next/statistics не дают права менять внутреннее состояние.
Только весь успешно проверенный пакет обновляет совместно snapshot/counters.
Callback exception/NaN/shape/KeyboardInterrupt, изменённые time/mass/G/state,
ошибка physical JSON и обратный счётчик после внутренней мутации должны
сохранить последний снимок и committed counters, установить failed, освободить
принадлежащий сеансу controller/callback и запретить повтор next.
Attempted callbacks остаются отдельно, включая неуспешный пакет.
Неверный until/no-op не вызывает C и не отравляет сеанс; close идемпотентен,
current после close доступен. Нет восстановления controller из JSON.
Отсутствующий настоящий native отвергается; Python fallback запрещён.

Сначала тесты неизменного basic lifecycle356 и native отказов/alias/границ,
реальный наклонный аналитический круг при обоих epsilon, тест сохранения
исторического source356 и отказ при его порче. Новые live-source повреждения
должен обнаруживать replay358, не историческая проверка356.

## Полная проверка

Все9 прежних actual-IC задач, эпохи82/60, два периода, packet_dt,
epsilon1e-9/1e-11, REBOUND5.2.2/PRS23/min_dt0/softening0/dt0=packet_dt/200,
exact_finish_time=1. Новый basic сеанс должен побитно повторить356,
native —357native: outputs, все packet clocks/states/JSON/SHA, steps_done,
force_evaluations. На сеанс simulations=1, closed/finished true, failed false.
Прежние actual-IC Decimal338 критерии r<0.1м, v<1e-6м/с, E/L/P<1e-10;
неопределённость oracle <1e-6м/<1e-12м/с. Не обнулять инварианты.

Прогрев+3повтора, отдельно counted basic; native всегда считает callback.
Все массивы/счётчики битовые между повторами. Таймер включает setup/close,
next/current/copies/JSON/FFI; oracle/hash/файлы исключены. Разные обвязки и
инструментирование не выдавать за ускорение интегратора. Отдельный новый output,
partial receipt при отказе, source snapshot; точные algorithm/input/library/
native/sdist SHA до/после; Cargo metadata по явной LF-политике357 и rawSHA.
После — public arrays/receipt/offline replay в другом root, без native/C/raw/сети,
corruption guards. Старые coldFAIL353/355 и Rust3355/9 сохраняются.
Это не N-body/JPL квалификация, не новый выпуск или пользовательский recovery.

Если все180массивов и NPZ-байты полностью совпадут с357, новый публичный
receipt ссылается на существующий архив357 с тем же SHA вместо второй копии.
Независимо вычисленный новый raw NPZ и source snapshot всё равно сохраняются.
