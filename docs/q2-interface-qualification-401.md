# Завершение source-bound квалификации интерфейса Q2 — 401

2026-11-08. Проверки точного интерфейсного кандидата завершены. GO только к
отдельному решению владельца о допустимой области и следующей application acceptance.
Application A/D1 не разрешена и не выполнена; выпуск0.3.3 — NO-GO.
Полный машинный результат: [JSON](q2-interface-qualification-401.json).

## Идентичность и область проверки

- Dev до работы: `5541b1b5c4a2fdf2d05c7d03d760887d0294d6c4`.
- Оптимизированный родитель: `f723a2162b4e115378959e244f428529be2d4516`.
- Интерфейсный кандидат: `a99f73a4adce95be9d264d8c403e0e6768a54cd7`, отдельная ветка
  `codex/candidate-0.3.3-q2-interface-400`; исходники кандидатов не изменены.
- Python3.14.2t / NumPy2.5.1 / SciPy1.18.1 / solar-native0.3.3.
  Изолированные src-каталоги395/400; зависимости и интерпретатор — среда384.
  `activate()` проверяет actual import origins и dependency prefix, не metadata wheel.
- Native `.cp314t-win_amd64.pyd` SHA256
  `651e3466d67b94601c56eaf1bd622f178748c8439ade7e6725fd52682e13e091`.
- Actual source fingerprint LF: parent `d1a2e827e6edcf43ceedacbfc3f62ad72b624c2f0f03332326aa0cf6185695c7`;
  candidate `1a5b054241a628dc6d4ade30a978726166d001dbb0f25ad9a971cd7fc9f21122`. Это не portable/wheel-квалификация.
  Старый raw395profile SHA `b667c5083fe1dba7df6d3de72960f3a3a769052e60fd06a6e6c4cd2eaeb8f23d` сохранён.

Профили получены заново штатным `recipe.runtime_fingerprint`, а не переименованием
профиля родителя. Canonical JSON сортирует ключи; SHA его файла отличается от
SHA исходного order-preserving LF-вывода. Структуры проверены на равенство,
свежие байты штатного вывода сохранены отдельно. Исторические байты/SHA неизменны.

## Presentation delta и callers

Фактический [AST/byte audit400](../scripts/q2_presentation_delta400.py) выполнен:
ровно24добавленные строки в app.py, inspection.py, inspection_view.py.
Полная Git blob inventory, SHA256 разрешённых файлов и AST остальных узлов
проверены. Удаление строго разрешённых presentation nodes оставляет прежний AST.
Численные модули, Rust/native, force/torque/Hamiltonian, R-reuse, IC, настройки,
solver/error control, storage/schema, GUI calculation/recovery callbacks идентичны.

Прочитаны callers: model_info меняет только отображаемую StringVar без physics
write trace; inspection добавляет общий текст в limitations, сохраняя qualification
false/global error unknown; rotation_text получает префикс от pure count helper.
Подготовка q/S/omega и dispatch остаются прежними. Никаких новых Start-ограничений.

## Recovery400 и ровно десять новых запусков

Старый400 остаётся PARTIAL_RESOURCE_STOP, его96.3125CPU не возвращены в новый бюджет.
Архив54278B SHA256
`bcccf57600fa12057599c816cd7d8bd064015f4ae74af055b62c70d1e76b921f`
аутентифицирован с CRC, manifest/member SHA, архивным кодом и provenance.
Проверены raw arrays, IC/settings/backend/epochs, checkpoint второго кадра,
source/tool bindings и локальные оригиналы. Архивный код не исполнялся.
Это документальная цепочка происхождения, не удалённая execution attestation.

Два завершённых point baseline400 использованы read-only через
[адаптер](../scripts/q2_interface_recovery401.py:41). Старый helper не объявлен
resume-capable. Новый исполнитель создал только4baseline one/two и6candidate
point/one/two, каждый с отдельными started/complete receipts, SHA и IC bindings.

SI; прежние фабрики sun-earth / lunar_rotation / two_q2_demo; epochs0/2/4s,
dt2s. Никаких новых accuracy thresholds. Каждый case:0→2→4s плюс отдельное
продолжение сохранённого кадра2→4s тем же пакетом. Наблюдаемые counters включают
этот restart. Point/one rtol1e-13, two1e-11; все остальные настройки в raw IC.

| Case/backend | Parent | Candidate | p/v/q/S | Solver calls parent/candidate | Native parent/candidate | nfev parent/candidate |
|---|---|---|---|---|---|---|
| point / python | 400 authenticated | 401 new | exact | 3 / 3 | 0 / 0 | unknown / 123 |
| point / rust | 400 authenticated | 401 new | exact | 3 / 3 | 123 / 123 | unknown / 123 |
| one / python | 401 new | 401 new | exact | 3 / 3 | 0 / 0 | 132 / 132 |
| one / rust | 401 new | 401 new | exact | 3 / 3 | 132 / 132 | 132 / 132 |
| two / python | 401 new | 401 new | exact | 3 / 3 | 0 / 0 | 132 / 132 |
| two / rust | 401 new | 401 new | exact | 3 / 3 | 132 / 132 | 132 / 132 |

Все6пар: точные binary64 p/v/q/S (включая порядок/shape), полные payload,
checkpoint, same-packet restart, исходные настройки и numerical diagnostics.
Inspection не меняет состояние или checkpoint. Независимый offline-аудит строит
NumPy `<f8` arrays из raw документов и сравнивает байты; не читает только готовый PASS.

Важное ограничение: исторические point RHS/nfev не записаны и остаются null.
Три solver invocations доказаны статически архивным helper и неизменным point-DOP
call path; это не измеренные старые counters. Native0/123 сохранены в400.
Для четырёх новых вращательных пар все измеренные solver/RHS/nfev/native counters
совпали. Внутренние accepted/rejected шаги и controller state не реконструировались.

## Проверки, ошибки и сохранность науки

- Только исправленный renamed-body/relative_pair тест на exacta99:1PASS/0skip.
- Новые synthetic adapter fault controls:13PASS/0skip, включая foreign IC,
  неполные epochs/checkpoint, bool/NaN, nativecounter, unsafe/ambiguous paths,
  сохранение отрицательного нуля. [Тесты](../tests/test_q2_recovery401.py:18).
- Новые scientific cases:10complete, старые аутентифицированные:2;6exact pairs.
- Первые два recovery attempts завершились KeyError из-за Windows separators
  в исторических metadata refs. Исправлена только нормализация логических ссылок,
  без изменения старых файлов/данных/SHA; оба отказа и стоимость сохранены.
- Первый отчётный audit ошибочно хешировал sorted JSON как исходный LF-профиль.
  Он остановился до записи отчёта; свежий вывод подтвердил ожидаемые fingerprints.
  Отказ и стоимость сохранены. Ни один научный расчёт не повторялся.
- Старые74PASS400 не повторены; fixed58/28exact399,380 и benchmark394 не запускались.
  SHA отчёта399, замороженного плана и reference380 сверены с исходным Git.
  Три уникальных strict-convergence FAIL380 (6source comparisons399) остаются FAIL.

Сопоставление подтверждает source-bound применимость имеющегося399 только в его
фиксированной области. Это не новый receipt399, глобальная ошибка произвольной
орбиты, реальная точность Земли–Луны или оправдание трёх FAIL. Физика — прежняя
Newton total-degree2 M-Q, без Q-Q, высших мультиполей, приливов, диссипации, EIH-Q2.

## Ресурсы и сохранение

Полный отдельный401 computational ledger: **53.687500 chargedCPU s /
44.458232 activewall s**; все отказы включены.
WorkerCPU 36.765625s;
parent supervision плюс tail allowances 16.921875s.
Worker private sampled peak 161550336B;
stage files на момент сводки 3012458B.
Исходные160CPU/300wall/1GiB/64MiB и early128/240/900MiB/52MiB не повышены.
50ms sampled tree/memory и0.25CPU/wall allowance на phase не являются строгим
непрерывным upper bound. Combined parent+worker memory контролировалась отдельно.
Редактирование/Git/cloud не выдаются за измеренный scientific CPU; backup учитывается отдельно.

Incremental backup: **CLOUD_UNVERIFIED**. Оригиналы raw/checkpoint/profiles/logs
сохранены; manifests содержат source/cloud locations, размеры, SHA, Git bindings.
Проверка облака — отдельное скачивание, размер/SHA/parent, а не наличие очереди.
Точный backup record находится в JSON; приватный контекст в архив не включается.

## Раздельные решения

| Проверка | Решение |
|---|---|
| PRESENTATION DELTA | PASS, exact3files/AST/bytes |
| SHORT SOURCE EQUIVALENCE | PASS,6exact contrasts; historical RHS/nfev unknown |
| SCIENTIFIC EVIDENCE APPLICABILITY | Только доказанная source identity и фиксированная область399; прежние FAIL сохраняются |
| APPLICATION A/D1 | NOT APPROVED / NOT EXECUTED |
| RELEASE READINESS | NO-GO |

Следующий полезный шаг: отдельное решение владельца по experimental scope A/B,
затем отдельно разрешённая application acceptance D1 при выборе A. Никаких новых
научных матриц для повторения уже подтверждённого; main/tag/LATEST/portable032
сохранены. Текущий этап после отчёта останавливается. Модель для следующего
небольшого инженерного этапа: GPT-6.1Sol High.
