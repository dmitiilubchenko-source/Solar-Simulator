# solar_core: собственное Rust-ядро

Рабочий crate 0.3.1. Здесь живёт вычислительная часть без Python и GUI;
границу Python обслуживает соседний [solar_native](../solar_native/README.md).

| Файл | Что читать |
|---|---|
| [src/lib.rs](src/lib.rs) | Body/Vector3, validate, парные Newton accelerations, evolve с Velocity Verlet, diagnostics |
| [src/main.rs](src/main.rs) | Standalone JSON stdin/stdout для сравнения с Python |
| [src/relativity.rs](src/relativity.rs) | Рабочие Newton/EIH силы и относительная пара |
| [src/contacts.rs](src/contacts.rs), [src/impacts.rs](src/impacts.rs), [src/collisions.rs](src/collisions.rs) | Поиск/обработка контактов и ограниченные столкновительные сценарии |
| [Cargo.toml](Cargo.toml) | Версия и зависимости crate |

Body содержит mass, position/velocity и spin. Единицы — SI, векторы 3D;
наличие spin не означает полной вращательной модели для всех режимов.
Нулевые расстояния и неконечные состояния отклоняются; несовместимость
физических режимов дополнительно проверяется на уровне Python Experiment.

Из корня проекта:

```powershell
cargo test --manifest-path rust/solar_core/Cargo.toml
cargo fmt --manifest-path rust/solar_core/Cargo.toml --check
```

Standalone main читает JSON с bodies/dt/steps, возвращает bodies/diagnostics;
при ошибке пишет stderr и завершает процесс с ненулевым кодом.
Он вызывает фиксированный Verlet, не является самостоятельным DOP853.

Поведение на границе языков проверяют [Python/native тесты](../../tests/test_native.py).
Модельные и численные результаты — в [разделе проверок](../../docs/verification/README.md).
История: git log -- rust/solar_core. Нового номера версии эта документация не задаёт.
