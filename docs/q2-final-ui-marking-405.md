# Окончательная научная маркировка Q2 — этап 405

2026-11-09. **Технический GO финального source-кандидата к дальнейшей проверке
качества. Полная D1 application acceptance и релиз 0.3.3 — NO-GO.**
[Машинный отчёт](q2-final-ui-marking-405.json), [инструменты](../scripts/qualification405/README.md),
[замороженный план](../scripts/qualification405/plan.json).

## Кандидат и единственное изменение

Ветка `codex/candidate-0.3.3-final-marking-405`, commit `8fe01304e502f55e879addb0a4b6f3e062832e37`,
точный родитель `0985860f1776594a565f5754275fd110a00e29f2`, tree `f65701c8576e53882771e9f1b6633c92866f46f3`.
Предыдущий кандидат 404 не изменён. Единственный production diff — одна строка
в существующем литерале `TWO_Q2_EXPERIMENTAL_WARNING` в `inspection.py`:

- Было: «Проверка GUI lifecycle: сообщения Tcl ещё не разрешены.»
- Стало: «Закрытие GUI: ограниченная проверка404 — 18/18 PASS, без оставшихся Tcl callback errors в квалифицированной среде. Это не гарантия для других версий Tk/Matplotlib и не готовность релиза.»

Все остальные фразы предупреждения дословно прежние. Полный diff есть в JSON.
[Строгий guard 403](../scripts/q2_text_delta403.py) проверил AST и байты вне
единственного литерала. Git blob inventory совпадает кроме inspection.py;
SHA-256 всех остальных **1227 файлов** совпали.
Для sparse-checkout пропущенные файлы проверены через точные Git blobs;
фактические файлы обоих checkout также проверены, весь src/rust присутствует.
Физика, integrators/error control/R-reuse, GUI fix404/callback ownership,
worker/recovery/save/load, Rust/native/ABI, IC/G/settings не изменены.
Новых imports, вычислительных вызовов и side effects нет.

Новый actual fingerprint: `f31aa35a6f4b1e504c1ce34b620a7ca7fe7e5ecf3ca5b4d5d8f2a86d0fe52091`.
Родитель 404: `81f9b67806a0b258a4a4b5ec0f8d535f56e23c0ab4bf81125f3375fa090de805`.
Штатный `recipe.runtime_fingerprint('rust')` вызван в новом source checkout;
сохранены его реальные order-preserving LF JSON bytes. Это source fingerprint,
не wheel/portable fingerprint; сортировка JSON даёт иной SHA представления.
Профили отличаются только `inspection.py`; остальные поля структуры равны.
Actual import: `C:\Users\Admin\Desktop\Solar-candidate-033-final-marking-405\src\solar_simulator\__init__.py`; prefix `C:\Users\Admin\Desktop\Solar-candidate-033-384\.venv`.
Python3.14.2t/NumPy2.5.1/SciPy1.18.1/Matplotlib3.11.0, Tcl/Tk8.6.15;
native0.3.3 SHA `651e3466d67b94601c56eaf1bd622f178748c8439ade7e6725fd52682e13e091`. Окружение не обновлялось.

## Реально выполненные проверки

**13 portable tests PASS, 0 skip**: существующие шесть403 и семь405.
Negative controls отклоняют изменения physics, app callback, storage, Rust/native,
реальных байтов dummy native, imports и структуры. Они не подменяют проверку
реального native SHA и полного кандидата, выполненную отдельно.

| Состояние | Q2 | Предупреждение | current_trajectory_certified | Глобальная ошибка |
|---|---:|---|---|---|
| zero | 0 | нет | False | неизвестна |
| one | 1 | нет | False | неизвестна |
| two | 2 | есть | False | неизвестна |
| arbitrary_loaded_two | 2 | есть | False | неизвестна |

Четыре состояния прошли через одно реальное окно Laboratory. Model info и обе
вкладки инспектора используют один текст; loaded custom checkpoint переименован
и геометрически изменён и **не получает** допуска402. q/S/settings и документы
до/после инспекции равны; checkpoint SHA неизменен. Старые numerical diagnostics
не изменились. При показе предупреждения force/invariant helpers запрещены;
полная штатная диагностика сохраняет прежние вычисления инвариантов/потенциала.
Integration/RHS entrypoints заблокированы; **новых орбит и evolution calls — 0**.

Один итоговый single-root smoke использует штатную очередь Tk для инспектора,
закрывает Laboratory и продолжает обработку Tcl после destroy: **0 background
errors, пустая очередь**, правильные владельцы afterID. Это не повтор18cases404.
[Независимый аудитор](../scripts/qualification405/audit.py) отдельно пересчитал
AST с нейтрализацией ровно одной константы, проверил actual SHA, профиль,
raw callbacks, четыре сохранённых снимка и исторические completion/SHA404.
Входные evidence при аудите не изменились. Собственные проверки не являются
внешней научной рецензией и не дают универсальной гарантии GUI/физики.

## Сохранённые отказы стенда

1. Первый fail-closed аудитор ошибочно требовал полный checkout и остановился
   на отсутствующем CI-файле до GUI/импортов кандидата. Исправлен только способ
   проверки blob/working-tree provenance; исходный v1 сохранён с проверенным SHA.
2. Следующая попытка дошла до close, но harness вызывал private
   `InspectionLoader._poll()` вручную при ожидающем таймере. Это очищало `_timer`
   без отмены того callback. Отдельный короткий контроль сохранил afterID/command
   и **одну ожидаемую ошибку Tcl** после такого misuse. Production не менялся.
   Финальный стенд ждёт штатного scheduled poll через Tk events и проходит.
   Первый отказ не сохранил массив callback snapshots; их точные ID и число ошибок
   неизвестны и не реконструированы. Лог, стоимость, исходники v2 и готовый профиль
   сохранены. Четыре требуемых UI-состояния повторены для полного evidence;
   завершённые13tests и18cases404 не повторялись. Новые case receipts публикуются
   отдельно сразу после завершения каждой проверки.

Неподдерживаемый direct private poll не объявлен нормальным пользовательским API.
Наличие контрольной ошибки нельзя смешивать с нулём ошибок финального штатного smoke.
Был также read-only Git/editor отказ: PowerShell разобрал некавыченный HEAD^{tree};
правильный quoted вызов подтвердил tree, source не изменился.

## Область применимости evidence 399–404

| Этап | Что подтверждает | Чего не подтверждает |
|---|---|---|
| [399](q2-scientific-qualification-399.md) | R-reuse source equivalence на fixed58 jobs | Не снимает три FAIL380, не общий допуск |
| [401](q2-interface-qualification-401.md) | Source-bound интерфейс a99 в прежнем scope | Не автоматический допуск нового fingerprint |
| [402](q2-application-acceptance-402.md) | Точное синтетическое A/B, 0–200с; numerical11/11 | Effects10/11: distance_AB0.244795м вместо10м FAIL |
| [403](q2-ui-lifecycle-403.md) | Причина dangling callbacks на e9; reproducer10errors | Не исправление production |
| [404](q2-gui-lifecycle-fix-404.md) | 18/18 GUI cases,10→0 MRE, worker/recovery в qualified env | Не гарантия иных Tk/Matplotlib и не выпуск |

Новый405 текст не квалифицирует заново научную траекторию и не принимает старые
source-bound receipts под новым SHA. Полный Git/AST diff обосновывает delta-only
техническую проверку: вычисления и GUI lifecycle404 побитно прежние, изменён текст.

Предупреждение сохраняет: experimental Newton total-degree2 M–Q; без Q2–Q2,
высших мультиполей, приливов, диссипации и совместных EIH/Q2. A+D1 утверждён только
как цель точного синтетического демо A/B 0–200с. Numerical11/11 PASS не устраняет
FAIL эффекта расстояния. **Полная D1 application acceptance — NO-GO**; три FAIL380
и четыре коротких FAIL402 остаются. Глобальная точность произвольного опыта
не установлена. Loaded two-Q2 не получает допуска402; обычный Start не ограничен
200с. **Release0.3.3 — NO-GO.** Критерии Δ/B/U/N и IC не менялись.

## Ресурсы и резервирование

Суммарно **36.078125 charged CPU-с / 35.916041
active wall-с**, sampled private worker peak **456048640 байт**,
данные **1807881 байт** на итоговом замере. Все failed attempts,
launcher/supervisor и финальный аудит включены. Initial2CPU/5wall — allowance,
не измерение; 50ms sampling и0.25tail не строгие непрерывные bounds. Git/editor/cloud
CPU не измерены и исключены. Caps60CPU/150wall/1GiB/32MiB и early48/120/900MiB/28MiB
не повышались. Backup — отдельный измеряемый operational workflow.

Архив404 и обязательный erratum **заново скачаны**: size/SHA/parent совпали,
все82 member CRC/SHA проверены в памяти. Correct parent e9 независимо подтверждён
Git. Старый ошибочный manifest и архив не перезаписаны. Erratum SHA
`6aff3ca203101bc86e8713f0d1817da9bb853fa208b37b95a9b664fd297a8107`.
Новый backup405: **CLOUD_VERIFIED_SHA256**, оба объекта независимо скачаны заново:

- ZIP **680123 байта**, SHA-256
  `cb19c42eecf4f5fc2e669973028e118672e8686d557601e0ff1ce83cabf54d88`.
- Git recovery recipe для82db424: **582 байта**, SHA-256
  `7af3d1f5d107c2cdac0d761702d3a637bcae8af9adeb9ed01b7e589bcb7dff50`.

Размер, SHA и parent совпали.53raw/служебных файла, manifest и restore instructions
проверены CRC/memberSHA. Поля candidate/base явно заданы и сверены с Git до/после
создания ZIP; общей замены номера этапа нет. Архивы399–404 повторно не загружались.
Private context/SQLite/secrets/окружения/кеши исключены; чистый Git восстановим по
точным опубликованным commits. Исходники/архивы не удалялись и не перезаписывались.

Отдельный operational ledger: **8.953125 CPU-с / 21.518445 active wall-с**,
включая один отказ lock и повтор. После возврата команды со still-running session
следующий verifier был ошибочно запущен раньше завершения первого. Защита backup.py
отклонила активный lock без записи manifest. После завершения первого выполнен
новый fetch и отдельный retry; оба исходных receipt сохранены, lock не удалялся.
Непересекающиеся вычислительные этапы не затронуты; сумма operational wall
консервативно включает небольшое перекрытие. Connector CPU не измерен;
окно API/transfer/orchestration 76.066 с не является
измерением скорости сети или CPU. Operational caps20CPU/180wall, early16/140 не повышались.


| Verdict | Решение |
|---|---|
| SCIENTIFIC_UI_TEXT | PASS, ограниченная проверенная формулировка |
| TEXT_ONLY_SOURCE_DELTA | PASS одного литерала |
| GUI_LIFECYCLE_EVIDENCE | Исторический404 PASS + один штатный smoke405 PASS |
| NUMERICAL_SOURCE_IDENTITY | PASS, без новой научной квалификации |
| APPLICATION_D1 | NO-GO, прежний FAIL distance effect |
| RELEASE_READINESS | NO-GO |

Технический GO — только к следующей проверке качества source-кандидата. Следующий
практический шаг: отдельно разрешённая source/native/portable приёмка с явной
экспериментальной областью Q2 и сохранённым D1 NO-GO; здесь она не запускалась.
Main, tags, LATEST и принятая portable0.3.2 не менялись. После отчёта STOP.
Рекомендуемая модель следующей ограниченной инженерной задачи: GPT-6.1 Sol High.
