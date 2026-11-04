# Две Q2: проект отдельного прикладного протокола

4 ноября2026, этап386. **DRAFT_OWNER_REQUIRED. Не разрешение вычислений,
не утверждённый release waiver, численный B_app пока не назначен.**
Этот протокол оценивает полезность ограниченного учебного опыта. Он не
переименовывает [scientific380 FAIL](two-q2-380.md) и не заменяет его критерии.

## Предлагаемая область

Первый прикладной scope — существующее синтетическое GUI-демо A/B до200s,
оба point-force backend. Выбор200s взят из уже существующего интерфейса381,
не из нового поиска удачных IC/ошибок. Это **предложение более узкого release
scope**, которое требует владельца; оно не исправляет старый4000s gate.
Двух-/трёхтельные4000s результаты380 остаются отдельным историческим контекстом.
Трёхтельный случай и произвольные отредактированные системы этим draft не
получают нового прикладного допуска. Для расширения сначала отдельная спецификация.

IC строго из `/cases/0/initial` файла `scripts/two-q2-380-plan.json`,
SHA256 `26eaaf67878e34bd292682b90e07b0df5e3ad9b096f8ee9d0f5a0cf6e9b94d68`.
Runtime resource `src/solar_simulator/data/two-q2-demo380.json`:
SHA256 `3f6fa9b5883db9e14653c43ddc7359e4cf795744e42d3345baf9ea018772428b`.
Документы равны полностью, включая обе q/S/I и начальные настройки.
Перечислять округлённые IC вместо этих binary64 inputs запрещено.

SI, произвольный инерциальный базис/elapsed t=0, не JPL/UTC/TDB.
M_A=1e15kg, M_B=2e14kg, bounding radii1000/900m, начальная separation12000m;
все I/q/S/COM/drift сохраняются дословно. Hamiltonian — Newton monopoles +
total-degree2 M–Q каждой фигуры, без Q–Q/высших моментов/EIH/приливов/контактов.
Требуется d_AB>1900m, для внешней точки d>R_bound фигуры. Касание запрещено.
Условие проверяется на IC и в RHS. Оно не является оценкой точности усечения
около поверхности. Body.radius/passive spin=0,2уникальных RotationState,
масса инерции равна массе тела; FixedJ2/PrescribedQuadrupole не смешиваются.

## Замораживаемый numerical recipe

Рекомендуемый baseline — **actual GUI**, а не похожий уровень380:
dt50s, rtol1e-11, position_atol1e-7m, velocity_atol1e-11m/s,
q_atol1e-13, S_atol_i=|S_i(0)|1e-13, relative A/B, per-body RotationDOP853.
Output epochs0,50,100,150,200s;4cold packets по1шагу. Цель GUI200s
не ограничивает обычный Start программно: после200s опыт уже вне этой области.

До будущего запуска закрепить оба backend и все четыре уровня:
baselineGUI плюс **все3прежних** levels coarse/standard/fine из380 без правок.
В380 standard atol равны1e-8m/1e-12m/s, поэтому он отличается от baselineGUI.
q/S coefficients брать из plan380 spin_factor100/1/.03, не из результата опыта.
Не выбирать только лучший backend/уровень. Одинаковые времена/IC во всех jobs.

Для sensitivity — два заранее заданных recipes:4cold packets и одно
непрерывное integrate на200s с той же5точечной выдачей существующего
nbody_rotation.integrate. Итого16коротких runtime jobs, не новый solver.
Непрерывный контроль не заменяет пользовательский cold recipe.
Дополнительно baselineGUI каждого backend повторить в той же frozen среде;
same-packet файл в100s, продолжение двумя исходными50s пакетами.
Повтор должен сохранять точные physical states/q/S/settings; сравнение
с принятой032 является отдельным compatibility этапом.

## Наблюдаемые и независимость

На одинаковых эпохах, без phase/rotation/translation fitting, сохранять:

| Наблюдаемая | Ошибка и единицы |
|---|---|
| r каждого тела и rho_AB | max Euclidean difference,m; общий COM drift не скрывает относительную пару |
| v каждого тела и v_AB | max Euclidean difference,m/s |
| Ориентация каждой фигуры | raw R difference Frobenius; отдельно physical angle,rad, если reference R достаточно ортогонален |
| S каждой фигуры | max inertial vector difference,kg·m²/s; каждый spin отдельно |
| H/P/L | Полные orbital+spin quantities и исходные нормировки380, не только orbital L |
| q | Исходные raw значения и drift нормы, без исправления сохранённого состояния |

Reference переиспользует `scripts/two_q2_reference380.py`: другой набор
переменных (scaled Cartesian/R/body-Pi), RK45, scalar-I force/torque,
исходные rtol3e-11/3e-13, dimensionless atol=rtol*.01, max_step50s.
Два **свежих** reference на той же5точечной сетке, не production force callback.
Полные исходники/compiler/dependencies/native/IC/epochs/commands/outputs SHA
и actual source/env проверки до/после обязательны. Общие G/IC/Hamiltonian,
binary64/SciPy ограничивают независимость; это не внешняя рецензия.

Ортогональность reference R проверять до angular interpretation. Для точных
SO(3): ||R1−R2||F=2sqrt(2)sin(theta/2). При non-orthogonal reference сохранять
raw defect, а не получать фиктивную точную theta через acos около1. Если
используется polar projection только в observer, заранее описать её и включить
projection defect в uncertainty; raw reference и q/S не переписывать.
Знак q и −q физически эквивалентен; сравнение raw q нужно для persistence,
но не как единственная мера ошибки ориентации.

## B_app: предложение и обязательное решение владельца

Нужно задать **вектор бюджета**, а не общий RMS и не energy drift:
B_r[m], B_rAB[m], B_v[m/s], B_vAB[m/s], B_theta[rad], B_SA/B[kg·m²/s].
Предлагаемое прикладное правило: каждый B_j<=Delta_j/10, где Delta_j —
заранее объявленный минимальный физический эффект, который учебный опыт
должен надёжно различать. Доля1/10 — предлагаемое инженерное распределение
бюджета разрешения, не физическая константа или вывод из380ошибок.

Это обосновывает размерности и назначение бюджета: численная неопределённость
должна быть существенно меньше демонстрируемого изменения r/v/оси/S.
Печатные17значащих цифр, zoom и неизвестное число пикселей такого требования
не задают. Ни минимальные Delta_j, ни требуемая точность измерения владельцем
не определены. Поэтому **B_app_numeric=null; подстановка любого численного
порога сейчас была бы произвольной.** Старые1e-7/1e-8 здесь не становятся B_app.
Нужно согласовать измеримый учебный эффект/разрешение отдельно для каждого
observable и обеих фигур, затем численно зафиксировать бюджет до новых данных.

После утверждения B_j предлагается заранее выделить U_ref,j<=B_j/10 и
сохранить отдельно repeat/precision sensitivity N_j. Пример правила будущей
engineering acceptance: e_j+U_ref,j+N_j<B_j при неизменных EPL/q gates380
и exact restart. Эти доли/правило также требуют согласования. Уровневая
разность reference и N_j — эмпирические indicators, не доказанные верхние
границы; их сумма не даёт строгого global error theorem. Шум не вычитается.
Если reference/noise неразличимы относительно B_j, статус UNRESOLVED.
Same-environment repeat проверяет воспроизводимость, но не измеряет абсолютный
roundoff; precision contrast надо обосновать отдельно, не менять backend ядра
молча. Старые packet convergence380 FAIL остаются FAIL при любом новом исходе.

Численная точность относительно этого Hamiltonian не ограничивает ошибку
модели реальных тел: I/R_bound не определяют все высшие multipoles/деформацию.
Для реальной системы нужен иной физический бюджет/данные, здесь его нет.

## Stop/GO и необходимые ресурсы

Отрицательные checks: касание/пересечение spheres, точка внутри R_bound,
неверные q/mass/I, дубли spin, более2фигур, EIH/fixed/prescribed mixing,
контактные radii/passive spin; отказ без изменения исходного опыта.
При выходе из domain на RHS сохранять last completed packet/recovery и причину,
не продолжать с fallback/искусственным смягчением. Функциональные negative
пробы могут пересекать границу специально; это не допущенные physical cases.

До исполнения утвердить policyA, узкий scope200s, все numeric B_j/Delta_j,
reference/noise правило, code/env freeze и бюджет. Предварительный потолок
будущего smoke qualification60CPU/120wall/1GiB/32MiB, ранние50/100/900MiB/28MiB;
оценка5–20CPU s предварительна (не линейная экстраполяция4000s).
При недостаточном preflight — NO-GO без поднятия лимита. Все FAIL/partial
сохранять отдельно, никакого перебора параметров после результатов.
В386 этот эксперимент **не запускался**. Пока numeric B_app и waiver не
утверждены, **NO-GO новой прикладной квалификации и release допуска**.
