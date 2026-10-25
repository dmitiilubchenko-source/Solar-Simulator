# solar_native: Python ↔ Rust

Рабочий PyO3-модуль кандидата 0.3.2. Передаёт владеющие массивы через границу языков
и вызывает [solar_core](../solar_core/README.md). Это не отдельная физическая модель.

Основной файл — [src/lib.rs](src/lib.rs). Экспорты:

- evolve: фиксированный шаг для массивов masses/positions/velocities;
- point_acceleration: рабочие Newton/EIH силы, опциональная relative_pair;
- diagnostics: энергия, импульсы и центр масс;
- run_until_contact, resolve_contact, simulate_collisions: контактные сценарии.

Входные массивы имеют согласованную длину, координаты/скорости — векторы 3D,
единицы SI. Ошибки Rust отображаются в Python ValueError. Крупные вычисления
выполняются через py.detach; наличие модуля не заменяет проверку физики/FFI.

Python-адаптеры: [rust_backend.py](../../src/solar_simulator/rust_backend.py) и
[native_forces.py](../../src/solar_simulator/native_forces.py).
При DOP853 на Rust могут вычисляться силы, а интегрирование остаётся SciPy.

Из корня проекта в его Python-среде:

```powershell
.venv/Scripts/python.exe -X utf8 -B scripts/build_native.py
.venv/Scripts/python.exe -X utf8 -B -m pytest -q -p scripts.native_audit tests/test_native.py tests/test_native_forces.py
```

[Cargo.toml](Cargo.toml) описывает crate, [pyproject.toml](pyproject.toml) —
wheel/maturin. Основная [инструкция установки](../../docs/reproducibility.md)
фиксирует окружение; не обновляйте численные зависимости ради перестановки файлов.
История: git log -- rust/solar_native. Полная приёмка — [здесь](../../docs/verification/README.md).
