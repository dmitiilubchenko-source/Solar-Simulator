# Масса, радиус и наблюдатель в сферическом эталоне

Этапы92–95 продолжают [линейное вращение86–90](continuum-spin-contract.md).
Это изолированный исследовательский стенд, не новая физическая модель Луны.
Модель: постоянная плотность энергии ε, статическая Schwarzschild sphere и
Hartle spin только первого порядка по Ω. SI; s=r/R, C=GM/(Rc²),
u=√(1−2Cs²), A=√(1−2C), N=(3A−u)/2; t нормировано на бесконечности.
Домен1e-12≤C≤0.3 сохраняется. Несжимаемый EOS остаётся непричинным.

## Первичные определения и собственный вывод

[Hartle1967, оригинал p1022,(109–113)](https://articles.adsabs.harvard.edu/pdf/1967ApJ...150.1005H)
проверен визуально: число барионов есть интеграл сохраняющегося тока,
а разбиение energy/rest density требует отдельного термодинамического входа.
[Urbano/Veermäe2018,(34–36)](https://arxiv.org/html/1810.07137)
проверен по оригинальному HTML: quasi-isotropic metric, отличие areal и
isotropic radii, внешнее r=ρ(1+GM/(2ρc²))².
[Beltracchi/Posada2024,(9–11),(31–33)](https://arxiv.org/html/2403.08250v2)
проверен по оригинальному HTML: shift ω, четырёхскорость, exterior J/Ω.
Рассмотренные здесь interior transform, Jacobian и коэффициенты ниже —
наш вывод из этих метрик; они не приписываются готовой формуле статьи.
HTML/PDF SHA и точный перечень прочитанного сохранены локально в
`.tools/rotation92-95/source-review.json`. Consensus search/fetch доступен.

## Три различных массы

Гравитационная M определяется внешним полем; dm/dr=4πr²ε/c²,
то есть m(s)=M s³. Собственный пространственный объём на t=const:
dV=4πR³s² ds/u. Поэтому интеграл плотности энергии по этому объёму
Mproper(s)=M s³ F(2Cs²), где F(z)=₂F₁(1/2,3/2;5/2;z).
Его surface ratio q=Mproper/M=1+3C/5+9C²/14+5C³/6+O(C⁴).
Это не барионная масса. (Mproper−M)c² имеет leading3GM²/(5R),
но без rest-density/EOS не выдаётся за полную физическую binding energy.

Барионная rest density ρb(s) задаётся явно, отдельно от ε/c²:
dMb/ds=4πR³s²ρb/u. В статическом пределе W=1, а
ρ*=√γ Wρb; в areal Cartesian chart √γ=1/u.
Для линейного Ω corrections W−1 и shape находятся в пропущенном Ω².
Никакой автоматической догадки ρb=ε/c² или Π=0 нет.
В audit положительные профили ρb/ρe=0.7 и0.4(1+0.5s²) —
синтетические tracer inputs для проверки интеграла тока, не новый EOS.
Они не сертифицируют термодинамическую согласованность fluid matter.

## Isotropic chart с внешней нормировкой

Пусть x=ρ/R. Из равенства radial/angular spatial metric coefficients:
d ln x/ds=1/(s u). Внешняя асимптотическая нормировка даёт
xsurface=(1−C+A)/2=(1+A)²/4, а regular interior solution:
x(s)=k s/(1+u), k=(1+A)³/4.
x'(s)=k/[u(1+u)], включая точное regular x'(0)=k/2.
Обратная карта s=2kx/(k²+2Cx²), 0≤x≤xsurface.
Spatial metric в Cartesian isotropic coordinates: γij=ψ⁴δij,
ψ²=s/x=(1+u)/k, включая центр ψ²=2/k.
Следовательно √γ=(s/x)³, ρ*iso=ρb(s/x)³ и
(s/x)³ x² x'=s²/u. Последнее проверяет инвариантность массы тока
и собственного объёма в обеих системах координат.
Isotropic coordinates здесь не названы harmonic или ADM; соответствующий
глобальный map/centre/SSC для предыдущего Hamiltonian пока отсутствует.

## Частота и наблюдатель

Ω=dφ/dt постоянно, barω=Ω−ω; профиль h=barω/Ω из Hartle radial ODE.
Для статического наблюдателя dτ=Ndt+O(Ω²), angular rate Ωstatic=Ω/N.
Для ZAMO dφobserver/dt=ω и relative rate ΩZAMO=barω/N=Ωh/N.
Обе формулы линейны по Ω и точны по C для данного spherical background.
Скорость экваториального вещества относительно ZAMO v=RsΩh/N.
Rate helper принимает существующий slow-rotation domain Ω²R³/(GM)≤1e-2.
Случай Ω=0 обрабатывается без деления на Ω; sign Ω сохраняется.
Это не TDB/TCB conversion и не PA attitude transport.

J — exterior conserved angular momentum и I=J/Ω — distant response.
Число J/Ωstatic=IN и J/ΩZAMO=IN/h зависит от места наблюдателя;
это лишь apparent response при выбранных часах, не новая инерция тела.
Нельзя вывести finiteΩ² energy=IΩ²/2 без соответствующего второго порядка.
Ни один helper не меняет canonical_initial/local_rotation_transfer.

## Независимые аналитические пределы и отрицательные контроли

Из опубликованного a=I/(MR²)=2/5+12C/35+O(C²) и преобразований выше:

| Нормировка того же J | Constant | Linear C coefficient |
|---|---:|---:|
| a, gravitational M / areal R / distant Ω | 2/5 | 12/35 |
| a/q, proper-energy M / areal R / distant Ω | 2/5 | 18/175 |
| a/xsurface², gravitational M / isotropic surface radius / distant Ω | 2/5 | 8/7 |
| aA, gravitational M / areal R / surface static rate | 2/5 | −2/35 |
| aA/(1−2Ca), gravitational M / areal R / surface ZAMO rate | 2/5 | 46/175 |

Это смена определения измеряемого числа, а не исправление Einstein/Hartle
физики. Проверки slope/Richardson и c^-4 remainder фиксируются до jobs.
Reference: proper-volume quadrature двух уровней, interior log-coordinate
ODE, isotropic-coordinate baryon quadrature через inverse map, и
metric/tetrad определения local rates. Квадратурные/ODE sensitivity
публикуются отдельно; совпадение программ не является error bound.
Wrong controls: Euclidean volume, areal radius под именем isotropic,
ρ* как scalar, отсутствие lapse, отсутствие shift, прежний12/35 после
смены нормировки. Все должны быть обнаружены, без ослабления критериев.

## Что остаётся открытым

Baryonic EOS/internal energy, PN continuum spin/tensor/multipoles,
stress/field contributions, harmonic→ADM centre/SSC, полный conservative
Hamiltonian E/J, lunar initial mapping и tides остаются будущими задачами.
Численная проверка сферического benchmark не даёт физической lunar accuracy.
