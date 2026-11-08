# Q2-400: предварительный кандидат с достоверным предупреждением

2026-11-08. **PARTIAL_RESOURCE_STOP. Реализация предупреждения подготовлена; presentation-only квалификация не завершена. Release0.3.3 NO-GO; A/D1 не утверждены.**

## Кандидат и интерфейс

Отдельная ветка `codex/candidate-0.3.3-q2-interface-400`, commit `a99f73a4adce95be9d264d8c403e0e6768a54cd7`, parent — точный `f723a2162b4e115378959e244f428529be2d4516`. Ветка отправлена отдельно, удалённый SHA проверен. Оригинальные f723a216/fe0f456 сохранены. В dev runtime не переносился. Это предварительный исходный кандидат, не принятый выпуск.

Проверенные точки кода именно этого кандидата: [единый текст](https://github.com/dmitiilubchenko-source/Solar-Simulator/blob/a99f73a4adce95be9d264d8c403e0e6768a54cd7/src/solar_simulator/inspection.py#L12), [выбор маркировки](https://github.com/dmitiilubchenko-source/Solar-Simulator/blob/a99f73a4adce95be9d264d8c403e0e6768a54cd7/src/solar_simulator/inspection.py#L23), [model_info](https://github.com/dmitiilubchenko-source/Solar-Simulator/blob/a99f73a4adce95be9d264d8c403e0e6768a54cd7/src/solar_simulator/app.py#L393), [inspection view](https://github.com/dmitiilubchenko-source/Solar-Simulator/blob/a99f73a4adce95be9d264d8c403e0e6768a54cd7/src/solar_simulator/inspection_view.py#L56). Эти ссылки не относятся к прежнему runtime ветки dev.

Diff: только24 добавленные строки в app.py, inspection.py, inspection_view.py. Один текст и pure count-helper в inspection; существующие model_info и rotation_text его используют. Выбор демо и загрузка уже проходят через `_update_profile_info`, поэтому callbacks запуска/загрузки не менялись. Legacy cli.report, физические настройки, IC, solver/native, форматы сохранений и source bytes R-reuse прежние. Mixed line endings app.py сохранены, лишняя нормализация исключена.

Предупреждение сообщает экспериментальный Newton total-degree-two M–Q, отсутствие Q2–Q2/высших мультиполей, приливов, диссипации и совместных EIH/Q2 эффектов; перечисляет три FAIL380, отсутствие универсальной границы ошибки, незавершённую квалификацию конкретного короткого демо и отсутствие гарантии точности реальных тел. Отдельно указано: обычный «Старт» не ограничен200с, цель относится к «Рассчитать до t». Текст не утверждает A/D1 или release waiver.

В GUI текст виден при выборе и загрузке двух фигур, в model_info, обеих inspection-вкладках и в numerical_reliability.model.limitations. Ноль/одна Q2 и EIH+fixed J2 не получают two-Q2 маркировку. Поля current_trajectory_certified/global errors сохраняют False/None; имя,200с и receipt не дают PASS.

## Фактические проверки

До правки:1 ожидаемый FAIL — отсутствующий общий warning API. После правки: **74 PASS /1 FAIL /0 skip** из75 целевых pytest cases. Проверялись реальные Tk widgets,0/1/2фигуры, demo/load/save, Start против target, q/S/settings, отсутствие записи при отмене, invalid data, inspection, остановка/recovery и короткое продолжение Python/Rust. Это целевой subset, не application acceptance A. Полная таблица и исходный traceback находятся в [машинном отчёте](q2-experimental-interface-400.json).

Единственный FAIL оказался ошибкой нового тестового ввода: тело переименовано, а relative_pair осталось A/B. Существующая проверка правильно отказала. Исправлена только фикстура; **перепроверка исправленного случая ещё не выполнена**. Production validation не ослаблялась.

Шесть portable synthetic negative controls прошли: штатные presentation-вставки допустимы, изменения force G, tolerance, native source, callback и новый файл отвергаются. Это тесты механизма [`q2_presentation_delta400.py`](../scripts/q2_presentation_delta400.py), не доказательство actual delta кандидата. Старый whitelist391 не используется и historical receipts не менялись.

## Что не завершено

Последний combined worker был остановлен до загрузки нового кандидата: сохранены только два baseline point случая Python/Rust на эпохах0/2/4с, с exact checkpoint resume. Нет `base-complete.json`/`candidate-complete.json` и нет ни одной завершённой пары источников. Остальные четыре baseline и шесть candidate случаев не квалифицированы; их незавершённое выполнение нельзя реконструировать по предположениям. Partial-файлы сохранены; не подменять их completed.

**Новый actual source/environment fingerprint не вычислен. Формальный реальный AST-аудит не достигнут.** В отчёте эти поля явно отсутствуют/NOT_COMPUTED, старый fingerprint f723a216 не выдан за новый. Предварительный побайтовый просмотр остальных materialized Python package files не нашёл отличий, а Git diff ограничен тремя presentation-файлами; этого недостаточно, чтобы объявить всю source-bound delta qualification завершённой.

74 успешных теста не повторялись. Выполненные scientific39958 trajectories, old380 и benchmark394 не запускались. Preserved SHA399/380 и sealed399plan приведены в JSON. Результат399 — exact source equivalence в fixed58, а не универсальная физическая точность: три strict FAIL остаются.

## Ресурсный STOP и качество

До финального шага начислено89.062500CPU; остаток до early95 —5.937500CPU. Оценка финального combined шага4.8CPU оказалась недостаточной: фактически7.250000CPU с supervision/tail. Всего **96.312500CPU /76.214704active wall с**. Early-stop reason=`stage-CPU`, exit15. Жёсткий cap120CPU/240wall не превышен; ранний порог95 достигнут, лимиты не повышались.

1CPU/1wall в сумме — явный allowance за первый неаттестованный startup-отказ wrapper, а не измеренный CPU. Ещё по0.25CPU/wall начислено на завершение каждого из трёх guarded attempts. После STOP новых вычислительных проверок нет; оформление, Git и обязательное резервирование учитываются отдельно.

В большом targeted прогоне worker потребил59.078125CPU, supervisor25.687500CPU; в финальной попытке worker3.453125CPU, supervisor3.125000CPU. Служебная стоимость существенна и учтена, а не списана со счёта. Это наблюдение для будущего планирования, не разрешение ослабить надзор. Максимальный sampled worker private tree402907136B, последний disk1229976B; combined memory guard и исходные1GiB/64MiB caps сохранены.50мс sampling/final CPU/allowance не являются строгими непрерывными границами.

Первый wrapper ошибочно создал каталог, который monitor создаёт exclusively; worker не стартовал. Причина исправлена только в новом служебном wrapper, отказ и allowance сохранены. Дальше исходный fail-тест действительно дошёл до ImportError. Предварительный empty-index нового --no-checkout worktree материализован из HEAD до правок; исходные worktrees не затронуты.

Candidate-only UI-тесты лежат явно в [scripts/qualification400](../scripts/qualification400/README.md), отдельно от обычного dev CI: dev UI остаётся прежним. Это не skip/xfail. Новый helper коротких сравнений сохранён как executed artifact в raw; у него нет квалифицированного resume-контракта. Автоматически повторять его на существующем output нельзя: нужна отдельная recovery/continuation постановка с повторной проверкой provenance и сохранением уже выполненных работ.

## Следующие действия A/B

**Текущее решение: NO-GO для завершённой presentation-only квалификации и выпуска; исходный кандидат сохранён предварительно.**

A: сначала отдельный малый этап завершает fingerprint/AST, исправленный name-тест и оставшиеся сравнения, без повтора74PASS и двух completed baseline случаев. Только владелец утверждает экспериментальный scope и исключения release gate. Application acceptance D1 затем требует отдельного разрешения; подготовка интерфейса его не заменяет.

B: если две Q2 исключаются из выпуска, потребуется явная проверка create/load/advance, сохранение пользовательских исходников и регрессии0/1. Скрытия кнопки недостаточно. Такой dispatch/validation diff выходит за presentation-only область и требует своего impact analysis.

Main/version tags/LATEST/portable0.3.2, физика, native и прежние scientific criteria не изменялись. После отчёта STOP. Рекомендуемая модель следующего узкого завершения — GPT-6.1 Sol High.

## Сохранение

Резервирование нового partial raw, receipts и manifests выполняется отдельно через Project-Archives/Solar-Simulator. Статус облака до фактического readback — PENDING/CLOUD_UNVERIFIED; итоговые SHA/ID/стоимость будут добавлены после проверки. Чистые Git source files, окружения, кэши, личные документы и SQLite в архив не входят.


### Подтверждённый итог резервирования

Архив **Solar-Simulator-stage400-partial-20261108.zip**, 54278B, SHA256 `bcccf57600fa12057599c816cd7d8bd064015f4ae74af055b62c70d1e76b921f`, [облачная копия](https://drive.google.com/file/d/1PEZybFv7L3VomjctdmNIwXD5pf8ZmRi_/view) — **CLOUD_VERIFIED_SHA256**. Подключённый аккаунт/родитель и owner-only доступ проверены. Независимый raw download через Drive-коннектор дал тот же размер и SHA256 (стандартный Node crypto); локальный архив при этой проверке не читался. Научные вычисления не выполнялись.

Локальные guarded backup операции: 10.390625CPU/9.078037active wall с. Сам `prepare` **не завершён**: его операционный early10CPU достигнут; hard12 не превышен. Полный prepare не повторялся. Завершение очереди сделано отдельно metadata-only после облачного proof: 0.156250CPU; за исходный отказ регистрации начислено0.25CPU allowance. Всего локально 10.796875CPU с этим allowance. CPU коннектора/Node не измерен локальным guard; это отдельная операция сохранности, не новый бюджет тестов.

После принудительной остановки prepare остался lock PID26804. Его принадлежность stopped process receipt и отсутствие активного процесса подтверждены; lock сохранён отдельным файлом, чужая активная блокировка не снималась. В metadata регистрации сначала возник TypeError из-за повторного keyword status; запись manifest не началась, lock освободился в finally. Ошибка исправлена только в новом служебном helper, затем зарегистрирован ровно один текущий Solar-Simulator archive row под штатным lock. Прочие проекты/конфигурация не менялись.

Содержимое ZIP и исходные partial receipts сохранены. Будущие cloud proof/metadata закрытия не вложены рекурсивно в созданный ранее ZIP: они входят в этот Git JSON и центральный backup manifest. Статус local prepare не подменён PASS.
