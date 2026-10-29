# Сохранность после случайного задания и CI382

29октября2026. Проверка A выполнена до правок CI и подготовки
[плана0.3.3](qualification-033-plan.md). Только Solar-Simulator, без статьи,
новых IAS15, физических моделей или дорогой квалификации.

## Последствия ошибочного задания

Local dev был9d00a5c5b9507ab246e6a565d46a3dea6cf777bc; после fetch origin/dev
4dc6320038fe300032d9390cbcb9d9e31f7ddefc, maincf653c9 неизменён.
Один Solar worktree, staged/unstaged/untracked не было, локальных unpublished
commits нет. После аудита и разрешения пользователя — только fast-forward.
Reset/clean/stash/history rewrite не выполнялись.

|Commit|Изменения|
|---|---|
|243845845a7c888dd7ed93c3492580fc3423bf72|README link +55строчный docs/solar-research-status-20261029.md|
|4dc6320038fe300032d9390cbcb9d9e31f7ddefc|Точное удаление этих56строк/документа|

Оба остались в истории. Tree9d00a5c и4dc6320:
`664ee5fa573537b051a25480222b6b30faf54b5d`. Actual1217tracked файлов
дополнительно сверены git hash-object с blob IDs исходного tree с учётом Git
filters, mismatches0. Значит tracked physics/models/integrators/thresholds/
data/evidence/receipt/SHA/config/metadata не изменились.

Это **не** доказательство для всех ignored/external files. Отдельно учтены
193642файла в .tools/.venv/build/dist/Rust targets/egg-info по size/mtime:
после15:35MSK изменений нет, полного старого SHA inventory для них нет.
14known source/data/native SHA381 совпали; версии381/Python3.14.2t, NumPy2.5.1,
SciPy1.18.1, Matplotlib3.11.0/pip check прошли; source snapshot381 соответствует
binding. Private context10files verify PASS. Отдельный Documents/ChatGPT/SOLAR —
unborn Git с9старыми untracked review/notes entries, не Solar worktree, не менялся.
Другие устройства и произвольные внешние файлы не проверены.

Remote tags совпали с локальными. Принятый portable0.3.2 SHA
`7c578220ec77e792aa9589f32a30352e88277d0d096bff0ad3ca5aae9c014c49`
совпал; LATEST не менялся. Demo data SHA
`3f6fa9b5883db9e14653c43ddc7359e4cf795744e42d3345baf9ea018772428b`.
375–381 evidence сохранены;8cases/24snapshots byte-exact; независимый offline380
replay сохранил3FAIL;59коротких проверок PASS.

## Фактический CI и причины

[Run40875987286](https://github.com/dmitiilubchenko-source/Solar-Simulator/actions/runs/40875987286):
4dc6320, Linux3FAIL/655PASS/1штатный native skip/4deselect;
Windows8FAIL/156PASS. Ранее9d00a5c также имел CI failure; tree после revert тот же.

|Группа|Причина|Тесты|
|---|---|---|
|Linux2FAIL|Windows input_SHA256 paths379 читаются POSIX как буквальное имя с backslash|runtime_step379_evidence: replay и negative metric|
|Linux1FAIL|continuation original_plan380 записан с backslash|two_q2_evidence: compact replay|
|Windows3FAIL|source/data tests ошибочно ожидают полный qualified gate на чужом runner|sandbox_acceptance: profile и2tamper|
|Windows5FAIL|те же ошибочные positive preconditions|current_runtime_qualification:4corruption +native|

CI Linux Python3.14.9, Windows3.14.10t; receipt375 связан с3.14.2t и конкретными
Python/shared-library/native bytes. Другой runner старым отчётом не квалифицируется.
Native build и остальные156desktoptests прошли; сами8отказов не доказательство
runtime regression. Недостающая научная квалификация новой среды остаётся.

## Исправление и самопроверка

Отдельный commitbc75156cb01ea2818a6df78fc55582d27f676dc3:

- evidence_path в существующем release_history нормализует только внутренний
  относительный путь при чтении, запрещает escape/drive/UNC/..; используется379/380.
  Ни historical JSON, ни его SHA не меняются.
- audit_receipt_inputs выполняет все прежние hash/source/data/gates/retained-FAIL
  проверки и явно возвращает current_environment_checked=false,
  current_qualification_passed=false. Это не fallback и не scientific gate.
- check_receipts требует те же входы **и реальный полный**
  runtime_fingerprint('rust'). Нет permissive flag, fake fingerprint, нового
  skip/xfail или изменения научных порогов.
- Тесты проверяют source-only integrity, реальные changed thread settings,
  actual environment equality/inequality, missing native и corruption.
  Fingerprint не подставляется для положительного прохождения.

Оригинальные3LinuxFAIL сохранены из GitHub; локально реальное OMP_NUM_THREADS=2
воспроизвело все8старых FAIL. После исправления14affected tests проходят и
в чужой среде, требуя отказа gate.11path/scope checks первоначально красные;
после32связанных PASS. Независимый AST-audit сохранил все5исходных условий отказа
gate. Это структурная проверка плюс выполнение, не новая верификация физики.

Старые verification sources — ci-before382.zip, SHA
`a2b6a165f1c333a903fd7be4c5a3d2da2e8bf92b95ca9de7f24e1e065f89d078`,
только historical evidence. Physics src/rust/native/schemas/старые data и
evidence/пороги не менялись. Локально source CI670PASS/4штатных deselect/14.09s,
desktop166PASS/0skip/172.91s, Rust19PASS/обаfmt; full release acceptance не запускалась.

Результат удалённого CI сообщается отдельно по SHA/run: локальный PASS не
удалённый успех. Логи/SHA — локально и в отдельном private cloud archive;
upload/queue не доказывает backup без readback. [Машинный аудит](integrity-ci-382.json).

Для CI-fix commitbc75156 настоящий
[run40929366178](https://github.com/dmitiilubchenko-source/Solar-Simulator/actions/runs/40929366178)
завершился success: Python и desktop-native jobs успешны. Adaptive research
не запрашивался. Это source CI, не scientific gate; новые годовые результаты
или квалификация CI-runner этим не создавались.

## Решение

**А. Повредило ли случайное задание Solar?** В tracked state повреждений нет:
область commits и одинаковые trees/1217blobs это доказывают.
**Б. Полностью ли устранены последствия?** Active tracked эффект отменён;
commits остаются намеренно. Полного прошлого fingerprint всех ignored/external
files нет, абсолютного доказательства за этой границей нет. В protected
inputs/native/portable отклонений нет.
**В. Можно ли продолжать?** Да, от проверенной базы и с исправленным CI
контрактом. Это не GO на0.3.3release или автоматический годовой прогон.

