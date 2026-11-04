# Compatibility390 — отдельный узкий план до выполнения

5 ноября2026. Исходныйdevfcca776, accepted032cf653c9, frozen033fe0f456.
Не повторять8cases/16restarts/384/385/380/388/полнуюportable acceptance.
Raw389two-q2.json доступен,4382bytes,
SHAa56269a82892b6dc740b309e77db2a085dca7ad3ed563e40e1964e3e66461055.
Baseline — existing389accepted/one-q2-dop853-python/frame-1.json,3221bytes,
SHAbdb3ec1147785014646a8656bc38a5762c85d0ad5fb6c3f9d127b2a70f18c1dc.
Оба sourceSHA сверены с tracked389rawmanifest; новых IC/сценариев нет.

Новый .tools/qualification390, независимый390binding. Max30CPU/90activewall/
512MiBsampledprivate/16MiB,early25CPU/75wall/450MiB/14MiB. ПриSTOPнепродолжать/
неувеличивать лимиты. ControllerCPU/children и concurrentprivate учитываются;
external50ms+self10ms/450MiB. SamplingнеOSquota. Git/docs/network/backup отдельно.

Ресурсная оценка по388–389: low-thread startup/self до149MiB,389вместе сGUI
self226.22MiB+supervisor36.15MiB<450MiB. Actualold startup3898.30CPU+1.81supervision
включал2fingerprints/imports. Candidate390 толькоfilevalidation+1FP, безGUI и
двух повторных frozenverifyFP. Проекцияобщего20–24CPU/до60wall,не гарантия.
Избегаем повторной5979memberраспаковки/CRC: originalZIP SHA вновь проверяется,
runtime/package/dependency/native hashes actualFP сверяются с сохранёнными389.
Дополнительноcritical installedpackage/Python/native files сверяются с389ZIPmanifest.

Порядок: легковесные input/archive/source SHA и binding → unit guards →
candidate033load/to_document двухфигурного файла безintegration → actual032
storage.load и GUI._guard(_load). Preflightprofile доNumpy OMP/OPENBLAS/MKL1,
остальные3unset. -I/-B/externalpycacheprefix; LOCALAPPDATA/MPLCONFIGDIR isolated390.

Fileaudit: схема10,originNone,2distinct initial/current rotations,обаq/S,
finite lengths,noexternalURL/path. Candidateactualfrom_document подтвердитполную
строгуюсхему/physicalconstructorcontracts и roundtrip/bits безизмененияfile.
Actualprefix/metadata/native pathSHA/Python/ABI/FP проверяются собственнымruntime.
Known environment389 SHA old4d8838…f335,new056c455…795a — сравнениеactualdict,
не подделка fingerprint. Candidategit/sourcefreeze/native проверяются отдельноSHA.

GUIbaseline — существующийone-Q2savedstate. Nativeold0cbc, package изoriginaldist;
ожидается ValueError «Схема 10 требует одну динамическую фигуру». Нуженреальный
вызовstorage и штатногоGUIhandler,недостаточнопрочитатьисключениепокоду.
Мокируютсятолькоfile selectors/messagebox modal delivery. Специальныеsentinels
запрещаютintegration calls,неподменяя результат load. Послеотказа проверитьidentity,
settings,parent,fullcanonicaldocument иbits initial/currentq/S,отсутствиеновых
recovery во времяотказа. Затемконтрольныйsave/recovery долженоставитьстаруюодну
фигуруполностьювалидной. Unexpectedacceptance→FAIL/reproducer,nofallback/noPASS.

Независимыйread-onlypostflight: input/baselineSHA unchanged,rawbefore/after,
q/Sbits,errorroute,FPbeforeafter,outputsSHA. Reuseactual3898case/16restartrecords
толькодляsummaryA/B/C;невыдаватьстарыйSTOPзавершённымзаднимчислом.
Исходный389TypeError иCPUSTOPсохраняются. ОбщийrestrictedcompatibilityGO лишьпосле
успеха390negative;это неscientificaccuracy/универсальнаяnativeэквивалентность/
release waiver386/full033acceptance. После390STOP.
