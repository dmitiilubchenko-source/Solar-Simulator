# Группы проверок и CI

Полная приёмка исходников по-прежнему: `python -X utf8 -B scripts/check_project.py --require-native`.
Она запускает весь pytest, production Rust/fmt и ссылки; любой skip запрещён.
Это не приёмка нового portable: реальный ZIP проверяется отдельно.

`scripts/check_suites.py` содержит явные ограниченные CI-подмножества,
не разбиение всего набора без остатка. --list показывает точные пути/исключения.

- python: математика/Newton, checkpoint, диагностика и инфраструктура; два
  Rust-параметра storage явно deselected, native здесь не требуется.
- desktop: GUI/recovery/trajectory/artists/units и native contract; doctor
  требует реальный PyO3/standalone/Tk, pytest native_audit запрещает skip,
  затем production Rust/fmt.
- adaptive: контракты/целостность сохранённых исследовательских данных,
  isolated Rust default+diagnostic-trace tests/fmt. Это не новый орбитальный
  аудит335–339 и не квалификация экспериментального backend.

Примеры: `python -B scripts/check_suites.py python`, аналогично desktop/adaptive.
Дорогие расчёты запускаются отдельно по их протоколам.

[Workflow](../.github/workflows/checks.yml): push dev и PR вdev/main запускают
Python Linux3.14 и desktop Windows3.14t. Python-пакеты ограничены существующим
constraints; это CI-проверка других установок/компилятора, не обещание
битового совпадения или научной точности всех платформ. Rust в Windows job
использует stable toolchain hosted runner; прежний локальный GNU-профиль
не выдаётся за проверенный на hosted MSVC. Actions закреплены по commit SHA.
Права contents:read, credentials checkout не сохраняются; личный репозиторий
CI не читает, релизы/main не публикует. Research job — только явный
workflow_dispatch с research=true; GitHub может требовать наличие workflow
на default branch для ручного запуска, перенос вmain согласовывается отдельно.
До этого исследовательскую группу можно выполнить локально.

Workflow/source checks не заменяют полный локальный --require-native,
научные протоколы и реальную проверку ZIP на новом пути.

Python-группа также проверяет исторический JPL440/source snapshots безсети
и распространения траектории; это защита происхождения прежних результатов.

Публичная проверка ссылок исключает теже личные документы PRIVATE_DOCS,
что inventory: её результат одинаков при наличии/отсутствии private context.
