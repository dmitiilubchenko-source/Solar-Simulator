# Однородная континуальная сфера: проверка86–90

[Договор и primary sources](continuum-spin-contract.md) фиксирует SI,
arealradius, gravitationalmass/asymptotictime и linearΩ definition.
Модель constantε incompressible fluid — математический acausal benchmark.
Лунные параметры, runtime/H57/strictreceipts не изменялись.

## Зафиксированный протокол

M=3kg,R=2m,G=0.4m³/(kg s²), Ω=0.001s^-1 дляSIchargecheck.
c=sqrt(GM/(RC)) меняется, а M/R фиксированы. C=.008/.002/.0005/.02/.1/.25.
1025uniform **радиальных** узлов s0..1, не temporaltrajectory.
Rawproduction f(0)=1,fprime(0)=0, exactregularlimit без epsilon.
DOP853rtol1e-11; независимый pressure-sourceRiccati z(0)=0,
RK452e-10/2e-12 иDOP8532e-13. Wrong-no-pressure DOP8531e-11.
TOVinward s1..0 atC=.25, p(1)=0, RK452e-10/2e-12.
Всеatolrtol/50/maxradialstep1/512. Policies заданы доjobs и не ослаблялись.
Matter-current integral Simpson на1025/513nodes проверяет другой способ I.

39newtests passed1.26s. Fresh89:21max/4min/5bool=30criteria passed,
32ODEjobs/32NPZ,6.183s. Frozen242files=238Python+2usedpolicies+
2primary artifacts; executedcopies иarrays SHA/rawinitial/grid verified.
[Отчёт первого аудита](continuum-spin-validation.json) сохранён.
ReportSHA a6034d5c9c1cc1d7d4e4072b05c326134c72b547db42410ef1e9007f34603243.
Граничный пример M/R не подбирался по результатам; PN coefficients взяты
из primaryChan(3.11) и собственного заранее записанного ODE expansion.

## Результаты и чувствительность

| Величина | Максимальное sampled отличие |
|---|---:|
| Metric j'/j vs independent stress-source /C | 2.665e-15 |
| Static pressure derivative vs TOV /C | 1.332e-15 |
| Static surface metric/pressure | 0 |
| Exterior fΩ/value/derivative matching | 1.110e-16 /0 |
| Rawproduction z vs independent radialprofile | 2.775e-14 |
| Production a vs fine Riccati a | 1.166e-15 |
| Riccati levels /fine-tighter a difference | 8.327e-16 /1.166e-15 |
| Independent TOV pressure vs static formula | 2.776e-16 |
| TOV levels pressure difference | 0 |
| Matter-current integral vs boundary a | 2.252e-12 |
| Integral1025/513nodes difference | 3.378e-11 |

a=I/(MR²) безразмерно. Почти одинаковые ODE references при двухrtol
не дают истинную точность1e-15: maxstep доминирует, TOVlevels здесь совпали
побайтно. Независимая quadrature чувствительна сильнее. Ни sampledgrid,
ни conservation/staticchecks, ни agreement не rigorous trueerrorbound.

| C | a(C), first audit89 |
|---:|---:|
| .008 | .40276898444398757 |
| .002 | .40068733391419437 |
| .0005 | .40017152959225794 |
| .02 | .4070231768219248 |
| .1 | .43896616573020947 |
| .25 | .5246917252742197 |

FirstPN a=.4+12C/35 residuals уменьшаются при doublingc с ratios
16.131663/16.032619; заранее16±.3. Quadratic a добавляет212C²/525;
c^-6 residual ratios64.571015/64.141513, заранее64±1.
Richardson firstslope .34284825763 против12/35, отличие8.885e-6.
AtC=.0005 secondcoefficient residual2.738e-4 — finiteC truncation,
а не fit/newcoefficient. Newtonlimit approached; exacta(.0005)≠.4.

Четыре deliberately wrong controls дали заметное отличие:
omittedpressure a2.276e-2, constantNewtonI1.247e-1,
omitted Ω matching5.805e-1, ignoredframedragprofile5.252e-1.
Wrong-no-pressure сохраняет Newtonlimit, но slope.285875 вместо2/7
с finiteC deviation1.607e-4; правильный slope12/35 другой.

## Отказы и открытые ограничения

87:16passed/1failed — j(surface)0.9999999999999999 из округления
(3A-u)/2 приu=A. Алгебраически равнозначное A+(A-u)/2 восстановило
exactsurfaceA без projection/epsilon/измененияcriteria; исходники и отказ
сохранены .tools/rotation86-89/test87-failure. Повтор17passed0.13s.
Publisher webfollowups InternalError; оригинал HartlePDF downloaded/SHA
и visualrender проверены локально. pdftotext не был установлен;
использован доступный pdftoppm. PrimaryReina/Chan доступны наarxiv.

После scientificjobs выявлен offline-import failure: auditmodule читает
ignored localprimaryPDF при импорте, поэтому чистая копия без.tools не
импортируется. Отказ сохранён .tools/rotation86-89/offline-import-failure.json.
Он не меняет приведённые scientificnumbers, но требует отдельного исправления
sourceguard перед завершением сквозной проверки. Старый report не перезаписываем.

90 исправляет lifecycle: code/policy guard приimport, primarycache guard
только внутри fullscientificaudit, обязательно доjobs и между ними.
Cleanoffline sourcecopy теперь импортируется; попытка audit без primarycache
явно отклоняется до создания work/report. Regression проверен в childinterpreter.
Fresh90 [актуальный отчёт](continuum-spin-validation-r2.json): те же30criteria,
32jobs/32NPZ/242copies,6.189s. Physics/inputs/originalpolicy/criteria unchanged.
SHA48608c80632afc53891bf9ad34e71de66b1fbbd0594b9cb7ae8106bda0da5e7e.
Все scientificmetrics/order и32decodedNPZ совпали с89 побайтно;
старыйJSON и executed89sources сохранены. Localrefinement receipt в.tools.
40newtests passed1.67s. Первый full89check1123Python167.84s/17Rust/fmt
passed, но offlinefailure выявлен отдельно и сохранён; finalfull90check
выполняется после исправления, результат будет записан по завершении.

Finalfull90check завершён:1124Python passed167.58s,17Rust passed,
fmtобоихcrates и1158file/line links.40newtestcases входят в1124;
1084 относится к85. Проверки выполнены послеsourceguardfix, а не только
перед ним. Preservationreceipt локально .tools/rotation86-89/verification.json.
Runtime/data/oldreports/strictreceipts сохранены; публикация/portable вне задачи.
Finalpreservation passed:475из479baselinefiles unchanged, изменены4private
docs;139oldJSON/68runtimeRustfiles и все362oldstatusentries сохранены.
242sourcecopies/report,32NPZ/report иprimarySHA повторно проверены;
policy/metrics/order/decodedarrays90=89 побайтно. Обаотказа сохранены.
Handoff79строк, прежнийhandoff/archiveprefix сохранены побайтно.

Нет конечных Ω²shape/mass/energy terms; нельзя использовать .5IΩ² как
сертифицированный полный GR rotationalmassenergy этого тела. Second-order
surface-mass correction дляconstantε(Reina22) остаётся будущим обязательством.
Нет harmonic→ADM/SSC/tetrad/inertia tensor или physicalMooninitial mapping.
ρe не conservedρ*/baryonicrestρ; внутренние stress/EOS/Pi Луны не заданы.
Приливы,121.84″ discrepancy и экспериментальное Kuiper528/SB441 остаются открытыми.
