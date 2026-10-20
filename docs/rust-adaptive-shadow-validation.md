# Высокая точность при прежних шагах не устранила4FAIL

20 октября2026,338. На всех9условиях335 выполнен теневой пересчёт с50 и80
десятичными цифрами. Критерий0.1м/1e-6мс сохраняется: прошли5/9 как для
preparedIC, так и при отдельном сравнении с исходным actual-IC эталоном.
**Это сохранённый отрицательный результат гипотезы, а не исправление Rust.**
[Протокол](rust-adaptive-shadow-protocol.md), [полные показатели/SHA](rust-adaptive-shadow-validation.json),
[Decimal50/80, оба oracle100 и времена](rust-adaptive-shadow-samples.npz).

Модель: Newton2point/SI/наклонные3D-оси/t0=0/два периода,6×82/3×60 эпох.
Только относительные6переменных, без PN/фигур/COM/P. Высокоточный RK использует
принятые h337 и те же A/B как exact(binary64). Контроллер не запускается,
rtol не меняется, rejected proposals не продвигают состояние.

Начальное preparedIC берётся из записанных внутренних переменных и побитно
равно float64-разности двух тел. Оно отличается от точной разности float64
компонент physicalIC. Сила r'=v,v'=−mu r/|r|³, mu=exactG×sum(exactmass).
RHS не округляет промежуточные аргументы/результаты до float64. Проверен
точными радиусами/масштабом/перестановкой и старым Decimal RHS161 при70 цифрах.
Таблица RK проверена свободным движением и аналитическим осциллятором.

Время — exact сумма принятых h, проверенная через Fraction. Максимальное
отличие от исходной эпохи5.825743e-11с записано, шаги не корректировались.
PreparedIC oracle70/100 вызывается на этой сумме; actual-IC oracle70/100 —
на прежних временах335. Его float64-экспорт точно совпал с исходным NPZ.
Во всех случаях неопределённость обоих oracle ниже1e-6м/1e-12мс, t0 exact.

| Условие | Rust335 max r, м | Shadow80 vs prepared, м | Shadow80 vs actual, м | Диагностический prepared gate |
|---|---:|---:|---:|---|
| holdout_circular | 0.00313941684 | 0.00344549727 | 0.00326230116 | PASS |
| holdout_moderate | 0.0257091984 | 0.0297844037 | 0.0297407691 | PASS |
| holdout_original | 4.41136742 | 3.80255916 | 3.84183275 | FAIL |
| holdout_permuted | 3.63821078 | 3.8070552 | 3.8463288 | FAIL |
| holdout_apocentre | 0.104507247 | 0.185006727 | 0.18511704 | FAIL |
| holdout_eccentric_phase | 0.0559542685 | 0.0561111295 | 0.0567350842 | PASS |
| original_0.0 | 0.00730790102 | 0.00362607555 | 0.00344277026 | PASS |
| original_0.5 | 0.0314748887 | 0.0299683772 | 0.0299248172 | PASS |
| original_0.95 | 4.04361594 | 3.80239834 | 3.84167194 | FAIL |

Для82:e=.95 повышение точности даёт3.841833м вместо Rust4.411367м,
но апоцентр ухудшился до0.185117м вместо0.104507м. Все отказы сохранены.
Максимальная разность shadow50/80 ≈3.448e-34м/4.397e-39мс: в самом этом
опыте нехватка десятичных разрядов уже не объясняет метровую ошибку.
Ни эти цифры, ни сходство траекторий не являются истинной астрономической
точностью: остаются дискретизация, binary64-таблица и ограничения модели.

Relative E/L drift вычислен относительно preparedIC, оба <1e-10 во всех9.
Малый drift снова не гарантирует орбитальный критерий. Полная инерциальная
энергия/P не проверяются; здесь только относительная диагностическая модель.
Повышены вместе RK/RHS арифметика; их отдельный причинный вклад не установлен.

65relatedPython/0skip/10new прошли за4.66с. Полный научный запуск192.227с;
ненулевой CLI-код означает полный диагностический FAIL, не crash. Строки
Decimal сохранены без преобразования в float64, NPZ1018506байт. Код, входные
JSON/NPZ и все trace проверены по SHA до/после; raw receipt и dirty-снимок
локальны в `.tools/shadow338/audit`. Новых зависимостей/сети/Rust-build/ZIP нет.

```powershell
.venv/Scripts/python.exe -X utf8 -B -m scripts.assess_kepler_shadow --output .tools/shadow-replay/result.json
```

Нужны локальные trace337 с правильными SHA. На новом checkout сначала
[воспроизвести337](rust-adaptive-trace-validation.md), затем передать его новый
receipt через `--trace-receipt NEW_RECEIPT`. Выход новый; повреждённый кеш
или изменённые научные исходники отклоняются. Ни один старый SHA не заменён.

Следующая связанная [проверка339](rust-adaptive-refinement-validation.md)
делит каждый h на2/4 по отдельно заданному протоколу; oracle-кеш переиспользуется.
Рабочий Rust остаётся5PASS/4FAIL. Product0.3.0/portable/main прежние;
выпуск и runtime-замена этим опытом не квалифицированы.

- [Decimal RHS](C:/Users/Admin/Desktop/Solar-simulator/scripts/kepler_shadow.py:10),
  [фиксированный RK](C:/Users/Admin/Desktop/Solar-simulator/scripts/kepler_shadow.py:21),
  [точное время](C:/Users/Admin/Desktop/Solar-simulator/scripts/kepler_shadow.py:80).
- [Все9случаев](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_kepler_shadow.py:30),
  [RHS-контроли](C:/Users/Admin/Desktop/Solar-simulator/tests/test_kepler_shadow.py:23),
  [повреждённая сетка](C:/Users/Admin/Desktop/Solar-simulator/tests/test_kepler_shadow.py:72).
