# Изменённый десятикомпонентный Solar: пилот198

15 октября2026, после193–197, до новых измерений. Повторно используется
существующий independent_reference из assess_relative_coordinates.py:
RK45, AU/year, interleaved EMB+Moon−Earth, отдельный scalarRustEIH и
independent_figure_vector. Новый закон силы или mapping не вводится.

Три ветки исходного pinned strictcheckpoint: Sun.mass×1.25;
Earth.position+(1e6,−2e6,3e6)м; Moon.velocity+(100,−50,25)м/с.
Одна правка на опыт, t_child=0, origin=None, parentсохраняется.
Инерциальные оси/скорости остаются исходными SSB/EclipticJ2000;
физические величины SI. Абсолютная эпоха исходного родителя2461321.5TDB
не превращает изменённый старт в новый JPL-набор. Радиусы/J2/оси прежние.
GM внешних гигантов остаётся системным, новых спутников или масс нет.

259200с (3суток),25 равномерных эпох, packet20. Унаследованные Settings:
DOP853/rtol3e-14/xatol1e-3м/vatol1e-9м/с/per-body/relativeEarthMoon,
dt3600с. Кандидаты: legacyPython/Rust и continuousRust. Проверить точные
IC/epochs/общие границы, повторы, legacycheckpointcontinuation и parentSHA.

Независимый reference: (rtol,maxstepseconds)=(1e-13,1800),(3e-14,900),
(3e-14,450),atol1e-17. Перед применением pin исходники, исходный strictJSON,
фактически загруженный scalaroracleDLL и native.pyd/SciPy. Scalaroracle
snapshotсверить с полной matrixEIH:physicalC fullacceleration<3e-14;
приC/10 отдельная PNпоправка<3e-9 относительноPN. Последнее — усиленный
проверочный предел, не скорость света интегрируемого опыта. Реальные
траектории используют C=299792458м/с. Weak-field guard сохраняется.

Pass-throughfigurecallback считает RHS по трём перезапускам t=0, возвращая
неизменённый независимый векторный J2. Проверить ровно три уровня и рост
RHS900→450. Нельзя принимать неактивный cap за измеренное уточнение.
Referenceinitialroundtrip<.002м/1e-8м/с по всем, relativeMoon<.0001м.
Последняя чувствительность<1м/1e-6м/с по всем и<.01м/1e-7м/с для пары.
Это прежняя область квалификации reference, не строгая граница.

Кандидаты:каждое тело<10м/1e-4м/с,relativeMoon<.1м/1e-5м/с.
Не ослаблять пороги после результата. Все неуспехи сохранить. Ни одного
JPLзапроса/подгонки/сверки counterfactualсреальной эфемеридой. 21источник
Noether здесь не интегрируется: rawE/P/J не используются как conservationgate.
Балансы модельных систем193–197 не приписываются этому пилоту.

Referencecost отдельно; один repeat/прогрев и3чередующихся fulltimings
кандидатов, включаяsetup/25снимков, безreference/диагностики/report/hash.
Сохранить actualIC/masses/times/NPZ,3referencelevels/RHS/source/DLLbinarySHA,
точные повторы и ограничения. Это три старта/трое суток/25эпох, не годовая
сертификация editedSolar, не гарантия всех сближений или новых параметров.
