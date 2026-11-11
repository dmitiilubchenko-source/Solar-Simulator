#409 — cloud408 закрыт; portable0.4.0 собрана, допуск410 заблокирован verifier

2026-11-11. **Сборка/smoke/целостность — GO. Полная410 не выполнена и пока
не допущена: штатный fresh-year verifier отвергает source040 по историческим SHA.**
Выпуск/main/tag/LATEST — NO-GO, принятая032не менялась.
[Машинный отчёт](portable-build-409.json), [инструменты](../scripts/qualification409/README.md),
[frozen inputs/план410](../scripts/qualification409/acceptance410-plan.json),
[все6001ZIPmembers с SHA/CRC](../scripts/qualification409/zip-members.json).

## Cloud closure408

Повторных upload408 не было. Свежие connectorreferences дали независимые HTTPS
скачивания всех3частей,600Bmanifest и582BGitrecoveryrecipe. У каждой части
свой immutable completion/resource receipt. Архив собран **только из этих новых
облачных байтов**, размер44203479B, SHA256f9e56e3ddc3d93b0d29916dd0a7c095e9ea8c8af975f1370a222af31f2bfbadd.
Все1110ZIPmembers CRC/SHA и2982logicalfiles/1109uniquepayloads проверены.
Globalbackupmanifest получил CLOUD_VERIFIED_CHUNKS_SHA256; parent/account/owner-only
проверены заново. Оригинальный408архив/отчёты и прежний CPUUNRESOLVED не менялись.

Первый16MiBreadback занял около202s — согласуется с недостаточностью прежнего100s
timeout при наблюдавшейся сети, но не доказывает одинаковые условия двух запусков.
Новый надзор учитывал child+supervisorCPU. Измеренный30CPU расход первойчасти
потребовал заранее sealedA2 только для остатка:200ms вместо50ms, прочая логика385
побитно прежняя.5synthetic faults(wall/CPU/RAM/disk/interrupt) сохраняют receipts.
Sampling не OSquota;150msдополнительной stoplatency явно учитывается.
Новые409A charged64.375CPU/552.782964activewall с
консервативными allowances, внутри120/1800 иearly96/1440. Старый408budget не обнулялся.

## Точная сборка

Runtime exact237f736/tree5cf43fd9…; sourceenvironmentfpf84294862fac710dedd03bdf854b537e541aa5c955f90938832e9b72840d2083.
Новая отдельная branch `codex/packaging-0.4.0-reuse-wheel-409`, commit `02ca1cf1b0e327481713bfa7d9b0fa328991c0ef`.
Изменён **только scripts/build_portable.py**, ни один runtime/Rust/test/IC/schema/threshold.
Qualified407Venv не переустанавливалась. Native wheel SHA5c2db314218484f5cb8b436de4479d5ecb069b56a5bd621eaa6e5cd5c70a5adb;
.pyd SHAa2b7e07573720a269efc712ee4fb74dcc747d24a4967d72d4c3d812158b3399b reused, компиляция native запрещена wrapper.
Defaultbuilder остаётся прежним; opt-inreuse проверяет version/ABI/wheelSHA/pydSHA,
добавляет offline/noisolationPythonwheel, outputroot и SHA-boundархивныйexportroot.
BUILD-INFO содержит sourcecommit/tree/toolingSHA/nativeSHA/archivalexportrole.

Исходный обязательный JPLexport действительно отказал: исторический strictreport
ожидает другиеexperiment.py/application_profiles.py. FAIL сохранён. Для **экспорта
сохранённых траекторий** создана отдельная read-onlyfixture с точными старыми
байтами изnumeric-before373/laboratory-before381; archive/memberSHA прежние.
Exporter/его sourceguards и отчёты не менялись. Старыеsrc там только данные,
не liveimports; текущие040modules импортируются изqualifiedsource, advance
запрещён в preflight. Это historicalreplay, а не новый годовой scientificPASS040.

ИтоговыйZIP `SolarSimulator-0.4.0-20261111-224857-409.zip`, 112698889B,
SHA256 `74247a863bd1c445ecfa736e1a0df60db43ad541cb34d7df5de909410781f3bd`.6001members, всеCRC/SHA и paths/symlinks/privatefiles
проверены независимо. Исходный builderZIP сохранён отдельно; финальныйZIP
дополняет только generatedCURRENT-STATUS контекстом408/409/непройденной410.
Оригинальные source docs не переписывались, scientificFAIL не скрывались.

## Проверки и наблюдавшиеся отказы

Buildersmokes: реальный packagedPython/Tk/nativephysics иGUI start/close PASS.
Независимые -I probes подтвердили metadata040, actualpackagedorigins/Tcl,
точныйnativeSHA, доступностьtwo_q2_demoresource. Настоящий injection постороннего
пакета отказал поorigincheck. Не запускались fullcheck_portable/relocated/year/continuous.
Полнаяruntimeclosure5573files сверена сqualifiedCPython,
точными distributions и2wheelcontents; 46licensefiles.
Нетpytest/maturin/setuptools/pip вsitepackages. Publicdocs402/404/license доступны.
ПубличныеverificationZIP иERFAsource-licensecopy являются явными approvedassets,
не случайнымиresearch/privateфайлами.

Negativecontrols: missing/wrongversion/wrongABI/wheelSHA/pydSHA/ambiguouswheels,
unexpectedcompiler/archivalmanifest-or-sourcecorruption/outsideimport; legacydefault
command сохранён без actualcompile. Три аудитных FAIL сохранены: неверныйdemoAPI
в первом smoke и два пропущенных approvedassets в allowlist. Исправлены только
аудитные скрипты, пакет и scientificcriteria не подгонялись; ZIP не пересобирался
ради smokePASS. Initial/finalZIP distinct, оба остаются локально.

## Реальный блокер410

Существующий `verification/recompute_jpl.py` при новом040runtime останавливается
на `Runtime scientific source changed: src/solar_simulator/experiment.py` **до
интегрирования**. Этот отрицательный preflight сохранён. Старыйstrictreport не
переименован и егоSHA не заменены. Перед410нужен отдельный reviewedcurrent-source
binding verifier/protocol, сохраняющий oldstrictmode, IC/settings/criteria и
проверяющий exact040source/native/environment. Нельзя просто убрать проверку,
заменить expectedSHA или подменить mandatoryfresh-year/continuous сохранённымиNPZ.

Plan410фиксирует этотZIP/source/tooling/native и все mandatoryпроверки, но status
BLOCKED_NOT_AUTHORIZED. Caps900CPU1200wall/2GiB2GiB,early720/960/1.8GiB1.8GiB;
прогноз годовых затрат UNRESOLVED: короткийsmoke не даёт такой экстраполяции.
Годовой иcontinuous расчёты здесь не выполнялись, допускне заявлен.

## Наука, ресурсы и дальнейший шаг

Historical39928/28;40211/11numeric,10/11effects,distance0.244795m vs10mFAIL;
3old380+4short402FAIL/fullD1NO-GO сохранены. TwoQ2Newton M-Qdegree-two экспериментален:
нетQ2-Q2/высшихмультиполей/приливов/диссипации/EIH-Q2/universalerrorbound.
Source408и409buildsmoke не сертифицируют реальные тела/произвольные системы.

На момент отчётаBcharged131.890625CPU/85.703552wall;
CPU supervisor/неудачных попыток включён. Hard300/600/2GiB1GiB,
early240/480/1.8GiB900MiB неизменны, exact385monitor. Finalization дополняется
в том же budget, новыйbackup отдельно. Backup409 пока CLOUD_UNVERIFIED.

Дальше — завершениеbackup409 и отдельно разрешённая подготовка year-source
verifier410. Текущий результат не GO TO EXECUTABLE410 и не releaseapproval. STOP.

Финальный учёт409B: 153.968750CPU / 127.314597activewall
включая отдельный консервативный хвост20CPU/40wall; все ранние границы соблюдены.
Подробности и ограничения измерения — [final closure](../scripts/qualification409/final-closure.json).

Контроль финализации из обычного shell сначала отказал по fingerprint окружения:
в shell не были заданы квалифицированные численные thread-переменные.
Повтор в том же bounded409B guard с исходным env-контрактом прошёл. Исходники,
native и ожидаемый fingerprint не менялись; этот отказ относится к запуску
проверяющего скрипта, а не к packaged runtime. Его затраты входят в хвост20CPU/40wall.
