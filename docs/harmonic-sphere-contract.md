# Глобальная harmonic sphere: квалификация источников99

Продолжение [конвенций92–95](continuum-conventions-contract.md) и
[stress/current96–98](continuum-stress-contract.md). Этап99 проверяет
уравнения, gauge choice и независимые аналитические пределы. Полная
численная карта interior/exterior пока не реализована; runtime не изменён.

## Источники и выбор координат

[Klioner/Soffel2014,(1),(97–117)](https://arxiv.org/html/1403.0024)
прочитан по первичному тексту. Его smooth harmonic chart выбирает
regular origin, asymptotic scale и непрерывность radial map/derivative.
[Gergely, comment,(1–5) и заключение](https://arxiv.org/html/0712.3749)
отдельно проверен: physical Darmois junction не требует непрерывности
производной новой radial coordinate. Это дополнительное условие smooth
chart, а не универсальная физическая необходимость или единственность.
Данные источников/SHA закреплены `.tools/rotation99/source-review.json`.

В предлагаемом стенде explicitly выбираем smooth asymptotically normalized
harmonic Cartesian chart с X^i=R H(s)n^i, s=r_areal/R; t unchanged.
R остаётся areal surface radius, M — gravitational exterior mass,
C=GM/(Rc²), N/u — прежний exact static sphere. Эта карта не становится
ADM canonical map, SSC centre relation или физической Lunar PA map.

## Уравнение и regular centre

Из harmonic condition следует (s²Nu H')'−2(N/u)H=0.
При H=sF: F''+(4/s+a)F'+bF=0, где
a=Cs/(uN)−2Cs/u², b=C/(uN)−6C/u².
Regular raw solution F(0)=1,F'(0)=0; exact limit
F''(0)=C[6−1/N(0)]F(0)/5. Затем rawsolution масштабируется
boundary matching; никакого epsilon, скрытой radial projection или clipping.

Для независимого эталона можно интегрировать Riccati+logF:
w=F'/(sF), ℓ=logF, w(0)=C[6−1/N(0)]/5,ℓ(0)=0,
w'=[6C/u²−C/(uN)−5w]/s−s w(w+a/s), ℓ'=s w.
Regular derivative w'(0)=0. Требуется отдельная проверка поведения численной
системы у origin и контроля roundoff в difference term; она ещё не выполнена.

## Exterior residual gauge и стыковка

Vacuum operator: [s(s−2C)H']'−2H=0. Помимо Hgrow=s−C существует
decaying solution D; предлагаем нормировку
D=−3[(s−C)ln(1−2C/s)+2C]/(2C³).
Прямое вычисление разности при малом C не использовать: оно неустойчиво.
Наш независимый equivalent integral:
D=3∫_0^1 t²/[(s−C)²−C²t²]dt, s≥1.
Его stable series D=s^-2∑_{j≥0}6(j+1)(2C/s)^j/[(j+2)(j+3)].
Будущая production series должна иметь явно обоснованный tail bound.

Hext=s−C+B D(s). Asymptotic scale фиксирует growing mode, но не
decaying B. В выбранном smoothchart на s=1 решить систему
αF1−BD1=1−C, α(F1+F'1)−BD'1=1.
Контролировать conditioning, положительный radial Jacobian и не выдавать
неразличимые на float64 compactness corrections за physical precision.
Для математического стенда предложен C≥1e-4…0.3; физическая лунная
compactness находится вне этой будущей численной qualification.

## Независимые опубликованные пределы

Согласованные полиномы из primary(113–115), в нашем обозначении:
Hint=s[1+(−3/2+s²/2)C+(1/4−9s²/10+15s⁴/28)C²]+O(C³),
Hext=s−C−4C²/(35s²)+O(C³), Hsurface=1−C−4C²/35+O(C³).
Isotropic surface из95 равен1−C−C²/4+O(C³): charts отличаются уже вC².
Коэффициент I/(M Rchart²) firstPN8/7 поэтому совпадает в обоих charts;
само это совпадение не сертифицирует coordinate map.
Из Chan inertia series и radius expansions собственный вывод:
harmonic second coefficient50/21, отличие harmonic−isotropic=−19C²/175.
Эти значения не подбирались по будущим numerical trajectories.

## Что проверено в99 и что следует проверить в100

Exact Fraction-polynomial operator для interior/exterior доC² равен нулю;
surface value иderivative jumps также exactlyzero. Localproof
`.tools/rotation99/check_polynomials.py`/`polynomial-check.json`.
Independent positive Gauss64 integral и128-term series exteriorbasis
agree1.78e-15 scaled; vacuumoperator residual2.67e-15 scaled, fixed1e-11.
Эти6checks passed. First receiptserialization failed NumPy bool flags;
originalscript/failure сохранены `serialization-failure`, explicitbuiltinbool
исправлен без изменения формул/criteria. No full matched IVP run in99.

Следующий100: реализовать isolated research map, независимый Riccati
reference и frozen predeclared audit; проверить radial metric/current
Jacobian, exterior/centre/surface, published c^-6remainders и wronggauge
controls. Не навязывать H=s−C всему interior или ошибочно занулять
residualgauge при выбранном smoothchart. После globalchart всё ещё нужны
PN tensor/stress/spin/multipoles, conservative Hamiltonian E/J и ADM/SSC
mapping, прежде чем менять physicalMoon initial rotation или включать tides.

## Текущее уточнение100–104

Численная selectedsmooth harmonicmap реализована и проверена в benchmark
1e-4≤C≤0.3. Production rawF/Fprime иstable128-term exteriorbasis сexplicit
tailbounds,2x2matching иmetric/currentJacobian. Independentreference теперь
используетδ=w−w0/logF иrationalizedregularsource; исходныйнеуспешныйaudit
иcauseanalysis сохранены. Это exactchangeofvariables, не новая физика.
[Результаты, отказы и проверенные строки](harmonic-sphere-validation.md).
