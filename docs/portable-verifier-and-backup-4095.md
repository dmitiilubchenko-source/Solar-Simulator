# 409.5 — current040-verifier и проверка portable-архива

2026-11-16. **Current-source preflight и целостность нового ZIP — PASS.
Подготовка к отдельно разрешённой полной410 — GO. Сама410 не выполнялась; выпуск — NO-GO.**

[Машинный отчёт](portable-verifier-and-backup-4095.json),
[инструменты и компактные результаты](../scripts/qualification4095/README.md).

## Что изменено

Runtime237f736/tree5cf43fd9 и native407V/wheel сохранены побитно. В новой ветке
`codex/packaging-040-verifier-4095` от02ca1cf добавлены два verification-скрипта
и явный opt-in в check_portable.py. Исторический режим по умолчанию не меняется.
Старый ZIP409, исходники, manifests/reports/SHA и численные критерии сохранены.

Current manifest связывает все5573runtime-файла: Python, зависимости, actual
численные модули, ABI, native, interpreter, metadata, IC/settings, reference,
эпохи и SI/SSB/EclipticJ2000/TDB. Проверка читает именно packaged files и
отклоняет внешний Python. Новый verifier находится вне старого historical bundle.
Различающиеся historical/current source SHA показаны явно; старый strict guard
по-прежнему отказывает до интегрирования. Saved replay выполнен прежним кодом.

Default `Physics Verification.cmd` делает только current preflight, без scientific
PASS. Будущий `--run --output NEW_OUTSIDE_DIRECTORY` выполняет фактическое
advance_towards с прежней пакетизацией20, пишет states.jsonl/NPZ и failure/result
даже при FAIL; cached trajectory не является входом solver. В409.5 этот годовой
путь не запускался, кроме преднамеренного отказа по неверному pin до propagation.

Прежние критерии:125эпох,10тел,1год;10км/тело и1км Moon−Earth; stored comparison
0.1м/1e-5м/с, исходные energy diagnostics. Не заявляем новый физический PASS.

## Новый отдельный ZIP

`SolarSimulator-0.4.0-20261116-4095.zip`,114633711байт,6005members.
SHA256 `33114f5ac2234e01e1e248fae757187a50a81020e2b225ee6b746e28e1073e33`.
По независимому побайтному сравнению изменён только старый Physics Verification.cmd,
добавлены четыре current verification-файла. Все runtime-файлы и исторический
verification bundle совпадают с409. ВсеCRC/SHA проверены; обаZIP остаются локально.

## Безопасность и проверки

Закрытый asset contract проверяет полный набор путей, размер/SHA/CRC, типы,
происхождение и private/secret-контроль. Исполняемые файлы допустимы только
из authenticated qualified runtime. Любое изменение байтов отзывает исключение.
147publicCA подтверждены как X509 без private key; стандартный Lib/venv допускается
по точным qualifiedstdlib paths/SHA, а не по каталогу. Публичные font/doc false hits,
gzip datasets, один NumPy fixturepickle и dateutil aliases имеют отдельные узкие
типовые проверки. Pickle не загружается, tar не извлекается в файловую систему.
Никаких общих исключений для runtime, PEM, venv или opaque binary не добавлено.

19отрицательных verifier-проверок,15security-controls,5integration-controls PASS.
Проверены source/force/torque/integrator, IC/settings/reference/epochs/frame,
native033/подмена.pyd/ABI/metadata, внешний Python и невозможность cache-option.
Security fixtures отдельно проверяют ключи, credentials, чужие файлы/бинарники,
повреждённые CA/wheel/resources, symlink/traversal/nested archives, dev-env/SQLite,
private context и secret в публичном каталоге. Исходные ZIP не изменялись.

Первый input checker ошибся в ZIP-root; исправлен только checker. Первые два
security review были чрезмерно строгими к qualified dateutil aliases и NumPy
fixturepickle; отказы и исходники сохранены. Уточнения ограничены exact bytes,
без доверия всему runtime. Независимый auditor сверил реальные ZIP bytes,
historical refusal и raw negative logs; короткий packaged Tk/native smoke PASS.

## Ресурсы, наука и решение

Полная стоимость подготовки — [resource ledger](../scripts/qualification4095/resources.json):
учтены CPU supervisor/детей и все отказы, плюс conservative allowances. Sampled
memory не OSquota. Ни один cap не увеличивался. Backup имеет отдельный budget.

Не выполнялись fresh-year/continuous/full410/3083/399/402. Первоначальный
resource preflight был UNRESOLVED. Последующий read-only аудит первичных
измерений дал основание для инженерного прогноза: [метод/числа/ограничения](../scripts/qualification4095/resource-forecast410.json).
Strict385:15.2282205с/499пакетов; его IC/settings/origin/units точно совпадают с новым
bundle. Continuous-year:1.4635815с; settings/origin совпадают. Для354тел проверены
все начальные координаты/скорости против первого сохранённого кадра, а
settings совпадают после штатного dataclass-asdict представления. Diagnostic
settings не являются checkpoint: проба поместить их в документ была правильно
отклонена storage; никакие данные/схемы ради сравнения не исправлялись.

Взято худшее измерение каталожных controller/IO-вариантов8.885131с, включая
более дорогой restart. Численные затраты умножены на4 — явный инженерный запас,
не измеренное замедление040 и не статистическая граница. С прочимиGUI/IO/bindings
worker budget округлён до250CPU. Измеренный максимумCPUнадзора/wall0.7674
округлён до0.8;450wall дают360CPU надзора, ещё40CPU резерв: **650CPU/450wall**.
ПрогнозRAM1.5GiB выше actualsource408peak1.005GB; disk1GiB покрываетZIP/одну
распаковку/workflows/raw/logs. Это нижеearly720/960/1.8GiB/1.8GiB. Предпосылки:
не менее2доступныхlogicalCPU, тот жеПК и сопоставимая нагрузка, threadvars=1,
свежий ограниченный output-root без чужого кеша. Actualcost может выйти за прогноз;
guard обязан остановиться, сохранивpartial, без повышенияcaps илиskip проверок.

[Новый immutableплан410v3](../scripts/qualification4095/acceptance410-plan-v3.json)
фиксирует exactZIP/source/native/verifier/acceptance-tool/monitor SHA и
обязательные fresh/continuous/GUI/recovery/compatibility проверки. Старыйplan409
не изменён. Внутренние неисполненные metadata-черновикиv2 сохранены отдельно;
после добавления exact-byte recoveryrecipe создан новый finalv3, без исполнения.
Полная410 требует **отдельного разрешения владельца**. Прогноз основан на прежних
замерах сопоставимых задач, а не на новом годовом PASS040.

Historical39928/28; D1numerical11/11, effects10/11, distance_AB0.244795м вместо10м
FAIL,3old380+4short402FAIL и fullD1NO-GO остаются. Нет универсальной ошибки или
аттестации arbitrary Q2/реальных тел. Current binding — не scientific certification.

Cloud backup новогоZIP **VERIFIED**: независимое скачивание10объектов,
сборка7частей из новых облачных байтов, полный SHA/размер114633711B и все6005CRC/SHA
совпали. Evidence409.5 и Git-рецепт также скачаны/сверены; owner-only/parent/account
проверены. [Cloud receipt](../scripts/qualification4095/cloud-verification.json),
[исходные readback/resource receipts](../scripts/qualification4095/cloud-readback-receipts.json).
Evidence409 не загружается повторно. Main/tag/LATEST/принятая032 не меняются.

Итог подготовки:225.078125chargedCPU/176.022966activewall, включая20CPU40wall
консервативного хвоста. Новый backup отдельно:58.281250chargedCPU/
192.025008activewall; все hard/early caps соблюдены. Source/raw arrays,
исторические FAIL, все ZIP и реальные error/partial receipts сохранены.

**GO TO SEPARATELY AUTHORIZED FULL PORTABLE ACCEPTANCE410 — exact new ZIP,
preflight verified, not scientific or release approval.** Source/security/cloud
блокеры409 закрыты; ресурсный прогноз обоснован указанными измерениями и
допущениями. Ни full410, ни новая научная квалификация, ни выпуск не заявлены. STOP.

Two-Q2 остаётся экспериментальной Newton total-degree-two M–Q моделью без
Q2–Q2, высших мультиполей, приливов, диссипации и совместных EIH/Q2-членов.
