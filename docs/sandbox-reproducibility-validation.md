# Связанный блок125–134: воспроизводимость и управление

14октября2026. Десятьэтапов без добавления физических эффектов:

|Этап|Результат|
|---|---|
|125|Чистая копия и новаяvenv выявили6fail/15errors/4skip вместо скрытой зависимости откеша|
|126|Публичный bundle7закреплённых входов, SHA всех38исходных provenance проверены|
|127|Ссылки разрешаются в перенесённойкопии, выходизROOT/чужиеanchor отвергаются|
|128|18версий зависимостей, freshPython/native/Rustbuild, явныйGNUbinutils|
|129|CLIrun-until иготовыйsolar-sandbox с прежнимиSettings|
|130|Извлечениеparent/child ипродолжениеbundlechild|
|131|GUIвозвращаетparent после сохраненияcurrent; cancel/error сохраняютопыт|
|132|GUIудаляеттело черезветку, сохраняетparent ине отключаетфизическиеguards|
|133|CSVорбитальныйсрез сSI/Settings/frame/time/источником иатомарнойзаписью|
|134|Чистаякопия/общаярегрессия/годовойCLI/portable/сохранность|

[Воспроизводимая установка](reproducibility.md), [команды иGUI](sandbox-controls.md),
[предварительные критерии](reproducibility-protocol.md).
[Числа, версии и SHA](sandbox-reproducibility-validation.json) сохранены отдельно.

## Подтверждённые проверки

Диагностическаякопия содержала573текущих публичныхфайла, новуюvenvCPython3.14t,
точные18версий изpipindex; исходнаяvenv/личныедокументы/privatecache не копировались.
До:6failed,1303passed,4skipped,15errors158.82с; sourceboundinputs отсутствовали,
Ruststandalone не былсобран. Отказ499publicdocslinks настаром Desktopanchor
сохранён. После входов иfreshRustrelease1334passed160.89с, безskip.
ЧистыеPythonwheel/17Rustcoretests/nativePyO3compiled изисходниковкопии.

Отдельная финальнаякопия591publicфайла использовала ранее созданнуюизолированную
venv иfreshnative128 (Rustисточники прежние), установила новыйpurewheel из134.
Начальныйnumericcache отсутствовал; семьвходов восстановились изpublicbundle.
Все1359тестов прошли181.79с безskip. Это копия нынешнихtracked+untracked,
не проверка опубликованногоcommit илидругого компьютера. 499публичныхссылок
проверены вROOTкопии. Rawsource/newwheel противисходников проверены отдельно.

Оригинальный full впервые1359passed171.49с с8предупреждениями: Windows
subprocess вtesthelper читал UTF8русскийstderr какcp1252. Добавлены явныйencoding
и UTF8режим дочернегоpytest. Повтор18CLIcases сthreadwarnings какerrors прошёл
11.37с. Финальнаяобщаяпроверка записана ниже после её завершения.

Финальный повтор: **1359Python за171.54с безwarnings иskip**,17Rust,
fmt обоихcrates прошли. Новыйблок добавил31тестовыйслучай поверх1328.
Ни один прежний физический критерий/тест не был удалён или ослаблен.

НовыйCLI изчистойкопии довёл исходныйRustпрофиль20×3600с до31557600с,
Settingsсохранились. Конечнаяэпоха: Moon671.919м, Moonrelative642.853м,
Mercury207.718м, Earth146.186м, Mars571.341м; остальные<274м. Все10км/1км
цели на этом endpoint прошли. Время8.168с включаетsubprocess/чтение/конечный
отчёт, безGUI; это не speedupbenchmark и не максимумза весьгод.
Предыдущие124показатели45/13эпох остаются [отдельными](sandbox-demo-validation.md).

## Отказы и пределы

- Publictestbundle610190байт содержит только7нужныхисследовательскихфайлов.
  Старыеtest66/вход/SHA/criteria не менялись. Corruptedexisting не заменяется;
  новыеguardsпроверяют отказдозаписи. Дляfreshresearchаудитов могут понадобиться
  другиестарые primarycache; проверенныйfulltestsuite не обещает их наличие.
- Nativebuild bundleddlltoolCreateProcessfailed; явный--gnu-bin сas/dlltool
  прошёл. Guardсначалаошибочнотребовалgcc иотклонил корректныйbinutilsbootstrap,
  исправлен по фактическому составуинструментов. PATH меняется толькоchild.
- СтарыеresearchJSON остаются историческимиаудитами, их широкиеprovenance
  включают прежниеbuild/entrypoint/checkscripts. Этиtoolingфайлы изменились;
  старыеSHA не переписаны. Пятьактуальныхsandbox/time физическихsourceSHA
  по-прежнему совпали. Силы/интеграторы/Rust/runtimeданные прежние.
- GUIpointeditor не поддерживаетdynamic/prescribedQ2, lastbody/figure/pair
  removal отклоняется. Толькоimmediateparent, бездеревапредков/rewind.
- CSVсодержитorbitalslice; JSON нужен для продолженияspin/q/events/history.
  НовыеCLIоперации требуют отдельныйoutput, исходныйcheckpointсохраняется.
- EclipticJ2000 исправлен втексте двухдокументов: расчёт/ref ужеиспользовал
  правильныйframe. Нет новойJPLмодели, подгонки илисертификации изменённыхсистем.

## Свежая переносимая сборка

[ZIP105717720байт](C:/Users/Admin/Desktop/Solar-simulator/dist/SolarSimulator-0.2.0-20261014-211002.zip),
[SHA256](C:/Users/Admin/Desktop/Solar-simulator/dist/SolarSimulator-0.2.0-20261014-211002.zip.sha256):
`e88d84034a3f00a512ea86e3bd6e47d3490c12a847c9789467bcfeccc0394b61`.
Запуск Solar Sandbox.cmd. CRC/SHA,338relativeMarkdownlinks, runtime/src/data
побитноидентичны, privateдокументы/.tools отсутствуют. ZIP124 сохранён, SHAпроверен.
Relocation вновыйпутьспробелами, Python-I/собственныйTcl/packages/Windows-onlyPATH:
все старыеnative/science/rotation/orbitfit checks прошли. НастоящийGUI:
Moon7200→10800/contact0.1/footer; solar10000.25 target/pause/save/resume;
add11bodyparentexact, returnparent ссохранениемchild, removeSun/freeEarth.
CSVвызван черезизолированныйsubprocess новогоCLI ипрочитан csv.DictReader.

Другойкомпьютер отдельно не проверялся. Версия0.2.0 сновойметкойсборки;
подписанныйустановщик/3D/приливы/магнитосферы/Rustfullport не добавлялись.
НикакихGitHub/commit/push/удалений. Логи иточныеbytebaseline остаются локально.

[КонтроллерCLI](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/commands.py:13),
[чтениеветки](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/branch_io.py:8),
[CSV](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/state_export.py:13),
[parentGUI](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/app.py:599),
[removeGUI](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/app.py:662),
[publicinputs](C:/Users/Admin/Desktop/Solar-simulator/scripts/prepare_test_inputs.py:18),
[переносимые ссылки](C:/Users/Admin/Desktop/Solar-simulator/scripts/check_project.py:24).
