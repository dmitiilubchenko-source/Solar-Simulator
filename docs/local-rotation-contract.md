# Локальное вращение и канонический перенос: договор модели 72–74

Новый стенд проверяет консервативную математику отдельно от лунных данных.
Он не квалифицирует перенос DE441, PN-инерцию Луны или её физическую точность.
Прежний H57 и runtime не меняются.

## Первичные определения и границы

[Klioner, Soffel, Xu, Wu, публикация Journées2001 / arXiv2003](https://arxiv.org/pdf/astro-ph/0303377),
§§2–4, (1)–(12): локальные PN-spin, Tisserand-инерция и вращающиеся
массовые мультиполи имеют отдельные определения. Формальная модель
вращающихся мультиполей не определяет физическую жёсткость вещества.
Ведущий Newton-предел STF-квадруполя связан с инерцией общей плотностью;
эта связь сама по себе не вычисляет PN-поправки к обоим определениям.

[Klioner, Gerlach, Soffel2010](https://arxiv.org/pdf/1001.0915),
§2, (2.1)–(2.4), §7, (7.3)–(7.9), §8, (8.1): локальное время,
совместимость параметров и дополнительный инерциальный момент нужно
задавать вместе. Производная CΩ в (8.1) запрещает заменять перенос
произвольным добавлением прецессии к уже заданной скорости.

[Gerlach, Klioner, Soffel, препринт2012](https://arxiv.org/pdf/1202.5870),
§§3–5, (4)–(12): два представления движения согласуются при переносе
также внешних координат, входящих в момент. Здесь воспроизводится этот
принцип на замкнутой синтетической паре, а не земная величина прецессии.

[DJS2008, PRD77,064032](https://arxiv.org/html/0711.1048v2),
(6)–(10), (13), §III, §VI: covariant-spatial spin → metric square root →
Euclidean spin является отдельной операцией; canonical centre/SSC
согласуется с ней. Корень не SO(3)-поворот ориентации. Его знание
не превращает протяжённое тело с независимыми PN-моментами в ADM-pointspin.

Consensus search/fetch доступны для rigid-multipole и consistent-precession
статей. Формулы сверены по arXiv выше. RAA Wang2016 PDF вернула InternalError;
её конкретные формулы не используются. PDF-SHA не заявляется.

## Отдельная консервативная модель

Параметры SI: m1,m2,G>0, Cbody — постоянная симметричная положительно
определённая матрица kg m², Mbody — постоянная STF-матрица kg m².
Модель позволяет несовпадающие главные оси этих матриц. Их независимость
явно феноменологическая: это не утверждение наличия реализуемой плотности.
Минимальное расстояние задаёт область вне тела; количественная точность
усечения мультиполей этим ограничением не доказывается.

r=xpoint−xfigure, p=μ dr/dT, μ=m1 m2/(m1+m2); свободное движение центра
масс отделено, J ниже — полный момент пары относительно её центра масс.
S — пространственный
канонический угловой момент ротора. R(q) активно переносит body→local,
q=(w,x,y,z). Сырые q в решателе не проецируются; только вычисление R
использует нормированный представитель. Все моменты выражены в том же
локальном евклидовом базисе и одном заданном координатном времени T.

```text
C = R Cbody R^T, M = R Mbody R^T, n = r/|r|
h = p²/(2μ) − G m1 m2/|r| + S·C^-1 S/2
    − 3 G m2 (n·M n)/(2 |r|³)
W = C^-1 S
F = −G m1 m2 n/|r|² + 3 G m2 [M n − 2.5(n·M n)n]/|r|⁴
τ = −3 G m2 n×(M n)/|r|³
r_T = p/μ, p_T = F, S_T = τ, R_T = hat(W) R
J = r×p + S; h_T=0, J_T=r×F+τ=0
```

Последние уравнения выведены из указанного конечного h. Trot даёт
ориентационную производную, которая сокращает W×S в пространственном
уравнении S; исключать её при независимой проверке нельзя. Уравнения
не содержат диссипацию, заданную орбиту или поправку, поддерживающую её.
При Mbody=tr(Cbody)/3 identity−Cbody это прежний Newton-MacCullagh.
В H57 specificQ=(3I−tr(I)identity)/m, поэтому M=−m specificQ/3;
название Q без нормировки и знака недостаточно для переноса.

## Что ещё не определено для Луны

| Договор | Необходимое свидетельство |
| --- | --- |
| C и M | одинаковые PN-определения, solid/whole/mantle/core, постоянные/переменные части, неопределённости |
| время | локальная шкала и dT/dt вдоль выбранного центра; dimensional radius/GM/I compatibility |
| оси | local Tisserand/PA, triad/tetrad, источник B и его производных |
| spin | локальный volume-spin или covariant spin, метрика, SSC, каноническая переменная и её Poisson brackets |
| центры | полный выбранный PN-multipole harmonic→canonical перенос, не только LO pointspin shift |
| динамика | согласованные PN tidal/orbital/reaction terms и инварианты, порядок усечения |

Rdot pinned-профиля уже globalTDB. Joint inversion58 уже включает SO.
Ни часы, ни движение осей, ни SO к ним повторно не добавляются этим стендом.
Mean-solid I ≠ undistorted-mantle PA ≠ wholegravity. Physicalmapping=false.

Следующий73 реализует только заданный SO(3)/clock canonical перенос
этой замкнутой модели. Tetrad/SSC/metric-provider Луны остаются отдельной
физической задачей; uniform F³ не заменяет её.

## Канонический перенос 73

Задаются B(t)∈SO(3), Bdot, Wb=vee(Bdot B^T), Wbdot,
T(t), r=dT/dt>0, rdot=d²T/dt². Это заданное преобразование евклидовых
координат нашей модели, а не вычисленный BCRS→local Lorentz/SSC перенос.
Поворачиваются все канонические векторы и ориентация:

```text
rg=B rl, pg=B pl, Sg=B Sl, Rg=B Rl(T(t))
K(t,zg)=r h(zg)+Wb·Jg, Jg=rg×pg+Sg
rgdot=r pg/μ + Wb×rg
pgdot=r Fg + Wb×pg
Sgdot=r τg + Wb×Sg
Wg=r Cg^-1 Sg + Wb
∂K/∂t=rdot h+Wbdot·Jg
```

Знак **плюс** относится к активной карте local→target, указанной выше.
Он выведен здесь из canonical action и проверяется независимыми Kgrad
и productrule, а не заимствуется по названию «rotating frame». Обратная
карта использует B^T и соответствующий генератор с обратным знаком.
Во временно преобразованной форме действия дополнительный член
равен −Wb·Jg; поэтому Hamiltonian получает +Wb·Jg.

Смена базиса при фиксированном времени каноническая; reparametrization
времени требует K=r h. Массам, C/M, S и SI-единицам множители F не
назначаются: совместимое масштабирование физических величин64 отличается
от этой операции. Одно B не является метрической тетрадой.

Из наблюдаемых vg/Wg восстанавливаются
p=μ(vg−Wb×rg)/r и S=Cg(Wg−Wb)/r. Назначения p=μvg и S=CgWg
вообще не дают эти переменные. Это модельная инверсия, не расширение58
для произвольных исходных локальных PN-инерций.

h и B^T Jg сохраняются; K и Jg при движущемся базисе обычно изменяются.
Баланс K−K0=∫∂tKdt — работа временного преобразования координат,
а не приливная диссипация. В целевом S действует Wb×S; при описании
через механический Cg Wg появляются другие connection-terms. Поэтому
KGS2010(8.1) нельзя механически прибавить к canonical Sdot этого стенда.

Rawq умножается на явно заданный unitqB (Hamilton product); знак qB
определяет lift, не выбирается по очередной матрице и не сбрасывает spin.
Initialq unit требуется отдельно; RK-stage q не нормируется в хранении.

[Научный аудит74](local-rotation-validation.md) связывает результат с
проверенными строками и показывает чувствительность независимого эталона.

## Реализация и локальная проверка

- [SI-параметры C/M](C:/Users/Admin/Desktop/Solar-simulator/scripts/local_multipole.py:40),
  [поле, сила и момент](C:/Users/Admin/Desktop/Solar-simulator/scripts/local_multipole.py:70),
  [h](C:/Users/Admin/Desktop/Solar-simulator/scripts/local_multipole.py:99),
  [поток](C:/Users/Admin/Desktop/Solar-simulator/scripts/local_multipole.py:107),
  [инварианты](C:/Users/Admin/Desktop/Solar-simulator/scripts/local_multipole.py:115).
- [Явная граница часов и базиса](C:/Users/Admin/Desktop/Solar-simulator/scripts/local_rotation_transfer.py:22),
  [каноническая карта и rawq lift](C:/Users/Admin/Desktop/Solar-simulator/scripts/local_rotation_transfer.py:66),
  [K](C:/Users/Admin/Desktop/Solar-simulator/scripts/local_rotation_transfer.py:89),
  [полный target RHS](C:/Users/Admin/Desktop/Solar-simulator/scripts/local_rotation_transfer.py:98),
  [инверсия vg/Wg](C:/Users/Admin/Desktop/Solar-simulator/scripts/local_rotation_transfer.py:111),
  [явная мощность](C:/Users/Admin/Desktop/Solar-simulator/scripts/local_rotation_transfer.py:126),
  [обратные инварианты](C:/Users/Admin/Desktop/Solar-simulator/scripts/local_rotation_transfer.py:136).
- [Независимый scalarH](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_local_multipole.py:14),
  [complex-step производные](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_local_multipole.py:25),
  [rawmatrix/bodyEuler oracle](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_local_multipole.py:36).
- [Производные h, реакции и общий J](C:/Users/Admin/Desktop/Solar-simulator/tests/test_local_multipole.py:22),
  [старый Newton-MacCullagh предел](C:/Users/Admin/Desktop/Solar-simulator/tests/test_local_multipole.py:37),
  [производные K и произведения](C:/Users/Admin/Desktop/Solar-simulator/tests/test_local_rotation_transfer.py:18),
  [инверсия и неверный spin](C:/Users/Admin/Desktop/Solar-simulator/tests/test_local_rotation_transfer.py:45),
  [connection totalJ и работа](C:/Users/Admin/Desktop/Solar-simulator/tests/test_local_rotation_transfer.py:60),
  [metric-root rejection](C:/Users/Admin/Desktop/Solar-simulator/tests/test_local_rotation_transfer.py:81).

72: 16новых тестов, вместе с10 прежними rotation —26passed1.72s.
73: 11новых, вместе с относящимися72/time/initial —60passed4.71s.
74 добавил явные отказы переполнения составных H/RHS/power и неверных
clockacceleration, прежде чем запускать аудит. Всего44новых теста
72–74 прошли1.83s. Научный аудит прошёл31max/5min/5boolchecks,
полный check_project —977Python242.45s и17Rust; fmt обоих crates успешны.
Статические пороги и конфигурация находятся в
[local-rotation-policy.json](../scripts/local-rotation-policy.json).

Тестовый источник/протокол/снимок дерева сохранены локально в
`.tools/rotation72-74`; личные документы не публикуются. Ошибка
вспомогательного чтения tests/conftest.py выявлена при восстановлении:
файла в проекте нет, pytest-настройки прочитаны из pyproject.toml.
Это не отказ вычисления и не проблема доступа.
