#409.5 — current040-verifier и проверка portable-архива

2026-11-16. **Current-source preflight и целостность нового ZIP — PASS.
Полная410 и выпуск — NO-GO: ресурсный preflight годовых проверок не подтверждён.**

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

Не выполнялись fresh-year/continuous/full410/3083/399/402. Прогноз настоящих
годовых затрат exact040 не подтверждён замерами409: короткий smoke не даёт
обоснованной экстраполяции. Поэтому RESOURCE PREFLIGHT UNRESOLVED; новый immutable
план410 не создан, прежний заблокированный план409 сохранён. Для запуска нужна
отдельная авторизация и обоснованный общий бюджет, включая надзор/IO/continuous.

Historical39928/28; D1numerical11/11, effects10/11, distance_AB0.244795м вместо10м
FAIL,3old380+4short402FAIL и fullD1NO-GO остаются. Нет универсальной ошибки или
аттестации arbitrary Q2/реальных тел. Current binding — не scientific certification.

Cloud backup новогоZIP пока PENDING отдельного bounded upload/readback.
Evidence409 не загружается повторно. Main/tag/LATEST/принятая032 не меняются.
