# Stress и metric charge в сферическом вращении96–98

Продолжение [mass/chart/observer92–95](continuum-conventions-contract.md).
Та же constant-energy-density sphere, SI, gravitationalM/arealR,
asymptotic time, static background и linearΩ Hartle profile h=barω/Ω.
Домен C=GM/(Rc²)1e-12…0.3; нет singular/negative-pressure extension.

[Mazur/Mottola2015, HTML(40–44), PDF(3.14–3.18)](https://arxiv.org/html/1501.03806)
проверен по первичному тексту: для static isotropic pressure формула
mass flux содержит lapse и stress trace. Используем только regular
положительно-давленческий background, не остальные гипотезы статьи.
[Hartle1967,(46–49)](https://articles.adsabs.harvard.edu/pdf/1967ApJ...150.1005H)
и [Chan2015,(3.11)](https://arxiv.org/pdf/1411.7141) уже проверены в86–90;
их pinned artifacts повторно сверяются при audit. Дополнительное
разделение членов ниже — собственный алгебраический вывод.

## Комаровская масса

Metric: ds²=−N²c²dt²+dr²/u²+r²dΩ², u²=1−2Cs²,
N=(3A−u)/2,A=√(1−2C),pRatio=p/(ρe c²).
MKomar(s)=c²r²u(dN/dr)/G=M s²u N'(s)/C.
Для perfect fluid dMKomar/ds=3Ms² N(1+3pRatio)/u.
Energy-only и pressure-trace contributions соответственно
3Ms²N/u и9Ms²N pRatio/u. Сумма проверяется против независимого
lapse gradient и integrated flux, а не только против другого matter integral.
Именно для постоянной ε: N(1+3pRatio)=u, поэтому MKomar(s)=Ms³.
Это особенность данного solution; общий interiorKomar mass не равен
Misner–Sharp m(r). Proper-energy mass из95 по-прежнему отличается отM.
Здесь не задаётся локальная ковариантная density gravitationalfieldenergy.

## Разложение интеграла инерции

a=I/(MR²)=2∫s⁴ h(1+pRatio)/(uN) ds. Для диагностики строим
ordered telescoping decomposition интегранда:

| Член | Точный integrand | LinearC integrated coefficient |
|---|---|---:|
| Newton baseline | 2s⁴ | 0 |
| Pressure | 2s⁴ pRatio | 2/35 |
| Proper spatial volume | 2s⁴(1+pRatio)(1/u−1) | 2/7 |
| Lapse | 2s⁴(1+pRatio)/u (1/N−1) | 16/35 |
| Frame/profile | 2s⁴(1+pRatio)/(uN)(h−1) | −16/35 |

Сумма равна полному integrand. Это выбранный порядок bookkeeping;
переупорядочение перераспределяет mixedC² terms. Члены не выдаются за
отдельные инвариантные gravitationalfieldspin или физические tensors.
SmallC differences 1/u−1 и1/N−1 вычисляются через rationalized expressions.
Reference отдельно интегрирует Riccati z=s f'/f иlogf; полный профиль
нормируется boundary z. Из формулы volume-current считается прямой I.

## Ошибки, которые компенсируют друг друга

При одновременном неправильном удалении lapse и h остаётся
awrong=2∫s⁴(1+pRatio)/u ds. Он имеет тот же Newtonlimit2/5
и тот же firstPN coefficient12/35: lapse/profile first-order integrals
в этом benchmark взаимно уничтожаются. Значит одна slope проверка
этой пары ошибок не обнаружит.
Но awrong=2/5+12C/35+(151/315)C²+O(C³), тогда как правильный
a имеет (212/525)C². Разность awrong−a=(17/225)C²+O(C³).
Вывод коэффициентов сделан до freshjobs; никакого fit по аудитным данным.
Проверяются отдельные члены, radialprofile, independent metric massflux,
second coefficient и negative controls, а не только согласие полногоI.

Ничего из этого не добавляет finiteΩ² energy/shape/mass correction,
PN elastic tensor, multipoles, ADM/harmonic/SSC map, full orbit+spin
conservative Hamiltonian или физическое lunar initial state/tides.
Чтобы квалифицировать будущие E/J, нужен полный согласованный порядок
extendedbody model; spherical bookkeeping само по себе его не задаёт.
