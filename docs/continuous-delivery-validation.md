# Проверенная поставка экспериментального расчёта

15 октября2026. Архив`SolarSimulator-0.2.0-20261015-020815.zip`,107107450байт,
SHA`4c5b4eaf23b7e4f0a68fb59decbb1532fa3c58615093ea27392622cda2104612`.
[Полная приёмка](continuous-delivery-validation.json),
[научные результаты и непройденный общий критерий](continuous-integration-validation.md).

Fullcheck:1428Python178.24с/17Rust/fmtboth/1457source-line links прошли.
РеальныйZIP распакован в новый путь с пробелами, изолированныйPython-I с
Windows-onlyPATH: native/Tcl/Tk/все прежние GUIworkflow/legacyJPLreplay+
freshstrictгод прошли. CRC/386relativeMarkdownlinks/67runtimepy+jsonbytes,
publicNPZ/validationJSON byteexact, privatefilesexcluded. СтарыйZIP149SHAпрежний.

ЭкспериментальныйCLI354/720000с/packet20:11снимков/3894CSVстроки,
530RHS; все позиции и скорости совпали точно с опубликованными массивами.
Continuousstrictгод125эпох/499пакетов/10682RHS также воспроизведён точно;
relativeindependentRK45error0.040073м. Это isolatedreproduction, не новый
контролируемый speedbenchmark; выигрыш62.12% — из отдельного pairedстенда153.

Запуск`Continuous Catalog Experimental.cmd`; результаты в новой локальной
папке`%LOCALAPPDATA%/SolarSimulator/experiments`, путь печатается вконсоли.
`final.json` можно открыть вобычномокне, дальше работаетпрежнийGUIметод.
Общий Kepler0.1мgateвсёещёFAILED; experimental=true, generalrelease=false,
ни автоматическойсменыGUI, ни гарантиигодовой354точности/FPS/другогоПК.

## Уточнение причины Kepler отказа

[Измеренная фазовая диагностика](continuous-phase-diagnosis.json): в худшей
точкеe.95/2оборота δr4.390841м почтиполностьюкасательная(-4.390841м),
радиальнаячасть0.000095м. Сдвигвремениδt=δr_tangent/|v|≈−23.6054мкс;
скоростьсогласуетсяс aδt до2.595e-9м/с при полномδv5.599e-5м/с.
Следовательно, ошибка преимущественнофазовая, анерадиальнаядеформация.

ДляKepler n=√(μ/a³), ε=−μ/(2a); малыеизмененияorbitalenergy меняют
meanmotion и накапливаютсявфазу. Decimal70расчётεпо фактическимfloatснимкам
и60-точечныйинтегралδn/n далиэквивалентныйсдвиг−23.6473мкс.
Оценкаinitialfrequencybias≈−2.4195мкс: представленныеfloatначальныевекторы
такжеотличаютсяотидеальнойноминальнойаналитики. Это приближённоеобъяснение,
сэффективнымμизroundednativeGm, нестрогаядекомпозицияинеисправление.
Порогне менялся; старыеотказысохранены. Дляследующейпроверкинужен точный
matched-initialanalyticoracle, затем независимаячувствительностьшага/точности.
Рекомендация: GPT-6.1SolHigh, посколькузадачаначисленнуюточность.
