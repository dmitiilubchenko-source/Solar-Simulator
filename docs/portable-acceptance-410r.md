# 410R — остановка до portable acceptance

19 ноября 2026. **PORTABLE ACCEPTANCE NO-GO/PARTIAL.** Полный worker ни разу
не запускался. Блокер обнаружен при проверке обязательных выходных данных.
[Машинный отчёт](portable-acceptance-410r.json).

Закреплённый `check_portable.py` имеет SHA256
`e332fca075e4dd686c3011a0f644c19e2af2210025badffb8117f516d74687a7`.
В `check_continuous` каталог пишет `continuous-catalog-check/snapshots.csv`.
Затем годовой solver накапливает состояния в `values` и создаёт из них
`actual`. Единственная экспортируемая информация об этом годе —
максимальные ошибки `year_reproduction`, `relative_independent` и
`year_statistics`. Wrapper читает только JSON из stdout дочернего
процесса. Реальные годовые состояния не сохраняются.
[Построение массива](<C:/Users/Admin/Desktop/Solar-packaging-040-4095/scripts/check_portable.py:567>) ·
[Экспорт сводки](<C:/Users/Admin/Desktop/Solar-packaging-040-4095/scripts/check_portable.py:572>).

Независимый статический аудит сверил SHA и разобрал AST внешнего wrapper
и вложенного скрипта. Он также подтвердил SHA эталонного NPZ внутри ZIP.
Этот NPZ содержит эталоны размера 125 × 10 × 6 для года и 11 × 354 × 6 для
каталога. Для повторного вычисления ошибок нужны новые actual states, а
максимумы из stdout не позволяют их восстановить. Отдельное сохранение
результатов current040 fresh-year не устраняет проблему: это другой
путь интегрирования. По preflight STOP попытка остановлена до любых
GUI или научных запусков. [Аудит](../scripts/qualification410r/independent-audit.json).

Проверены точный ZIP409.5, 114 633 711 байт и CRC, размер и SHA всех 6005
элементов по asset contract. Совпали SHA wrapper, manifest, native,
wheel, обоих verifier и трёх файлов supervisor 410.3. Закреплённые
runtime/packaging worktree чистые. Fingerprint установленного
квалифицированного окружения совпал. Это проверка привязок до запуска
portable. На Windows build 26200 доступно 16 логических CPU, около
3,95 ГБ RAM и 284 ГБ диска. Среди читаемых команд не найдено
параллельной qualification. Проверка Job в рамках 410R помечена
NOT_RUN после обнаружения блокера. [Привязки](../scripts/qualification410r/input-preflight.json) ·
[Хост](../scripts/qualification410r/host.json).

Supervisor completion, standalone imports, GUI, recovery, backward
compatibility, historical replay, current040 fresh-year, continuous-year
и каталог — **NOT_RUN**. Новых численных ошибок или орбитальных пакетов
нет. D1 и release readiness остаются NO-GO. Исторические scientific FAIL
и уровни доказательности сохранены.

В 410R затрачено 3,546875 CPU-секунды и 5,15 секунды wall на два
измеренных preflight-скрипта. Отдельно отведены 12 CPU и 60 wall на
подготовку и закрытие. Backup имеет отдельный бюджет. Исторический 410
с backup остаётся 53,4375 CPU / 114,919286 wall. Расходы tooling
410.1–410.3 и консервативные начисления перечислены отдельно.
[Новый план](../scripts/qualification410r/execution-plan.json) ·
[Журнал ресурсов](../scripts/qualification410r/resource-ledger.json).

Минимальное исправление evidence-контракта — сохранить в том же
цикле `check_continuous` время и actual states, затем привязать их
к SHA эталона, IC и источника. Независимый auditor сможет пересчитать
year и Moon–Earth ошибки из сохранённых данных. Это потребует новой
явной привязки SHA wrapper. Физика, native, ZIP, выбор сценариев и
пороги в 410R сохранены.

Архив свидетельств в Project-Archives получил **CLOUD_VERIFIED_SHA256**.
После независимого скачивания подтверждены размер 26 277 байт, SHA256
`d560d1019dc603a86935854ee3d52fc913f85799a640d3342d69bfac17c84e76`,
CRC всех 15 элементов и SHA файлов из manifest. В архиве только материалы
preflight 410R и рецепт восстановления. Расход backup с allowances составил
8,1875 CPU и 19,57 wall при отдельном лимите 20/100.
[Квитанция backup](../scripts/qualification410r/backup-receipts.json).
