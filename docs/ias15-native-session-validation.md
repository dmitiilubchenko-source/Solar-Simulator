# Сеанс IAS15 с силой Rust: результат 358

23 октября2026. [Предварительный протокол](ias15-native-session-protocol.md),
[полный receipt](ias15-native-session-validation.json),
[побитно совпавшие массивы357](ias15-native-newton-samples.npz).

**36/36 PASS:** basic18/18, native18/18 на прежних девяти задачах и обоих
значениях epsilon. Все outputs, packet clocks/states, physical JSON/SHA,
steps_done и callback counters совпали с357. Его basic уже bitexact356/353warm.
Новая обвязка сохранила численное поведение и критерии; точность не улучшалась.

## Изменение архитектуры

[IAS15Session](../scripts/ias15_session.py#L27) сохраняет единый lifecycle:
копии входов/выходов, совместный committed tuple, точные границы пакетов,
latch ошибки, no-op/invalid limits/close. Создание controller, интегрирование
и проверка модели выделены в три внутренних метода. Поведение по умолчанию —
прежний basic, без нового публичного параметра или общего plugin-интерфейса.

[IAS15NativeSession](../scripts/ias15_native_session.py#L9) переиспользует
lifecycle и подключает полный NewtonCallback357: gravity=none,
velocity-dependent=0, light_speed=None, relative_pair=None. Единственный
controller живёт между пакетами; checkpoints не пересоздают интегратор.
Native callback всегда считается. Проверки модели до/после integrate и
callback.check выполняются до commit. После отказа current/counters прежние,
next запрещён; сеанс удаляет собственные ссылки на controller/callback.
Очистка callback также покрывает JSON/finite/model отказ после integrate.

## Независимые проверки отказов

Перед полным опытом55тестов PASS14.27с/0skip:28новых native,21basic и6исторических
replay-проверок. Управляемый fake меняет private state до отказа:
OSError/KeyboardInterrupt, time1ULP, NaN, mass/G/gravity/velocityflag/counter,
ошибка physical JSON. Проверены old snapshot/counters, attempts отдельно,
единственный controller, запрет resume, close после failure.

В настоящем C-интеграторе после успешного пакета callback намеренно выдаёт
exception/NaN/shape/KeyboardInterrupt. Все четыре отказа перекинуты наружу,
без проигнорированного ctypes-исключения; текущий снимок остался прежним.
Отдельно: alias входов/выходов/statistics, invalid limits/no-op/fractional finish,
doublegravity до integrate, missing-native без fallback, запрет перезаписи
старых audit output. Наклонный аналитический круг проходит обаepsilon:
позиция<0.1м, скорость<1e-6м/с. Fake не является эталоном физики.

## Полная численная проверка

Девять прежних actualIC/SI/inertial задач, два периода, эпохи82/60 и packet_dt,
epsilon1e-9/1e-11, REBOUND5.2.2/PRS23/min_dt0/softening0/dt0=packet_dt/200,
exact_finish_time=1. Без PN/J2/COMshift/подмены relative_pair.
Сравнение с независимым Decimal f/g oracle338 и исходными E/L/P;
старые пределы0.1м/1e-6мс/E-L-P1e-10 неизменны.

| epsilon | basic max r, м | native max r, м | basic max v, м/с | native max v, м/с |
|---|---:|---:|---:|---:|
| 1e-09 | 0.0487800633268 | 0.0174321112477 | 6.22092766956e-07 | 2.22305796281e-07 |
| 1e-11 | 0.0246113501464 | 0.0276909600003 | 3.13173945618e-07 | 3.53150994901e-07 |

Все36сеансов closed/finished true, failed false, simulations=1.
4488пакетов,4524physicalcheckpoints,180массивов. Независимо вычисленный
rawNPZ полностью совпал по байтам с357:1679357bytes,
SHA256 `c6cdb55296285c3298e21a09da86125e16588d7b8229005557aafd4efeaafd42`.
Публичный receipt повторно использует этот архив без дополнительной копии.
Raw/source snapshot нового расчёта сохранены `.tools/native-session358/first/`.

## История и воспроизводимость

Перед правкой сохранены точные байты356:
[исторический модуль](../scripts/validation/ias15_session_356.py),
SHA `1058c0f065edc4dfef26df9f153c4c2dbb071342f7cdd122e9e1c76d15fe17c2`.
[Replay356](../scripts/replay_ias15_session.py#L21) использует явно эту копию
с исходным SHA, остальные bindings проверяет как прежде. Старые JSON/NPZ,
критерии и результаты356/357 не переписаны. Исторический PASS сам по себе
не проверяет изменённый live-код; именно для этого выполнен новый опыт358.
Новый replay358 проверяет текущие источники отдельно от исторического файла.

Source/input/library/native/sdist SHA до/после совпали. Cargo metadata —
прежняя политика357: LF canonical и raw SHA до/после; алгоритмы/данные exactbytes.
Offline358 сначала проверяет357/356, затем заново сверяет метрики/lifecycle/
счётчики новой записи и тождество архива. Вычислительные библиотеки не вызываются.
Offline-проверка не воспроизводит таймеры и не пересобирает binary.

## Вычислительная стоимость

Прогрев+3измеряемых повтора; отдельный counted basic. Все повторные массивы
и счётчики побитны. Таймер включает setup/close/next/current/copies/JSON/FFI,
исключает oracle/hash/файлы. Basic в таймере без callback-счётчика, native
всегда с ним; отношение времён не является чистым сравнением интеграторов.

| epsilon | Сумма9 медиан basic, с | Сумма9 медиан native, с |
|---|---:|---:|
| 1e-09 | 0.789451000 | 3.186931600 |
| 1e-11 | 0.804111900 | 3.546534400 |

Полный опыт 43.432096400с, warnings=[]. Старые таймеры356/357
выполнялись в другое время/с другой обвязкой и инструментированием;
по разнице этих времён ускорение не заявляется. Оптимизация не выполнялась.

## Область результата

Это research-сеанс только двух точечных тел, в одном потоке, без disk resume.
Его снимок не сохраняет внутренние buffers IAS15; coldFAIL353/355 остаются.
Собственный Rust-интегратор3355/9 также не переаттестован. N-body/год/JPL
требуют отдельного протокола, согласованных моделей и данных.
Runtime/src/rust/data/pyproject/версия0.3.0/main/tags/принятый ZIP прежние.
Лицензия/поставка IAS15 в продукте не выбраны; новых сил или графики нет.

[Полный стенд](../scripts/assess_ias15_native_session.py#L51),
[offline replay358](../scripts/replay_ias15_native_session.py#L18),
[отказы после мутации](../tests/test_ias15_native_session.py#L61),
[реальные ошибки callback](../tests/test_ias15_native_session.py#L86).
Номера строк сверены. Команда offline:

```powershell
.venv/Scripts/python.exe -X utf8 -B -m scripts.replay_ias15_native_session
```

## Итог регрессий

После полного опыта8offline/root/corruption тестов PASS39.31с/0skip.
Финальные связанные наборы:127adaptive Python PASS106.27с и111IAS15/API Python
PASS5.56с, оба0skip;238различных связанных тестов. Rust/adaptive12default,
15diagnostic-trace и fmt PASS. Inventory1071,1393file/line links и diff check PASS.
Старые353/355/356/357receipts сохранены побайтно, их архивы/SHA проверены;
356source проверяется по точной исторической копии, новая реализация — по358.
Это не полныйproduction/GUI/portable прогон. Логи и итоговый guard:
`.tools/native-session358/{related-adaptive.log,related-ias15.log,final_guard.py}`.
Неуспешных проверок в358 не было; прежние научныеFAIL остаются в истории.
