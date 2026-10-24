# solar_adaptive: исследовательский solver

Этот crate имеет package name solar_adaptive_research, версию 0.3.0 и
publish=false. Он не заменяет рабочий SciPy DOP853 и не входит в desktop runtime.

| Файл | Роль |
|---|---|
| [src/solver.rs](src/solver.rs) | Прототип адаптивного интегрирования |
| [src/coefficients.rs](src/coefficients.rs) | Численная таблица метода |
| [src/newton.rs](src/newton.rs) | Исследовательская правая часть |
| [src/trace.rs](src/trace.rs) | Изолированный диагностический trace |
| [tests/contract.rs](tests/contract.rs), [tests/trace.rs](tests/trace.rs) | Контракт и диагностика |

Прежде чем запускать новый опыт, прочтите [контракт](../../docs/rust-adaptive-contract.md),
[исходный результат](../../docs/rust-adaptive-prototype-validation.md) и
[диагностику](../../docs/rust-adaptive-diagnosis.md). Старый абсолютный
численный критерий не пройден: успешны 5 из 9 задач, четыре отказа сохранены.
PASS cargo test проверяет
свой контракт и не означает достаточной точности всех орбит.

Из корня проекта, только для относящейся исследовательской задачи:

```powershell
cargo test --manifest-path rust/solar_adaptive/Cargo.toml
cargo test --manifest-path rust/solar_adaptive/Cargo.toml --features diagnostic-trace
```

Это не обязательный шаг любой правки GUI или документации. История:
git log -- rust/solar_adaptive. Общее назначение проверок —
[в отдельном разделе](../../docs/verification/README.md).
