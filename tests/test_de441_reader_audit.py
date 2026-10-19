"""Independent recurrence and complete scientific qualification controls."""
from decimal import Decimal, localcontext
import json

import numpy as np
import pytest

from scripts import de441_decimal as high
from scripts import assess_de441_reader as module


def test_decimal_cubic_and_second_derivative_are_analytic_in_seconds():
    with localcontext() as ctx:
        ctx.prec = 70
        p, v, a = high.recurrence([1., 2., 3., 4.], Decimal('0.25'), Decimal(400))
        assert p == Decimal('-3.875')
        assert v == Decimal('-0.02')
        assert a == Decimal('0.0009')


def good_report():
    return dict(jpl=dict(bodies={name:dict(strict_passed=True) for name in module.de.NAMES},
        moon_relative=dict(strict_passed=True)),
        decimal=dict(checks_passed=True, rows=[dict(index=i) for i in module.INDICES]),
        boundaries=dict(checks_passed=True, boundary_pairs=2749),
        finite_differences=dict(checks_passed=True, rows=[{}]*9),
        negative_controls=dict(checks_passed=True))


@pytest.mark.parametrize('missing', ['body', 'decimal', 'boundary', 'difference'])
def test_partial_scientific_evidence_cannot_qualify_even_if_flags_say_passed(missing):
    report = good_report()
    assert module.qualification(report)
    if missing == 'body': report['jpl']['bodies'].pop('Earth')
    elif missing == 'decimal': report['decimal']['rows'].pop()
    elif missing == 'boundary': report['boundaries']['boundary_pairs'] -= 1
    else: report['finite_differences']['rows'].pop()
    assert not module.qualification(report)


def test_timing_budget_success_cannot_replace_failed_strict_ephemeris_match():
    report = good_report()
    report['jpl']['moon_relative'].update(strict_passed=False, timing_budget_passed=True)
    assert not module.qualification(report)


@pytest.mark.parametrize('key', ['decimal', 'boundaries', 'finite_differences', 'negative_controls'])
def test_other_successes_do_not_hide_failed_independent_checks(key):
    report = good_report()
    report[key]['checks_passed'] = False
    assert not module.qualification(report)


def test_failed_audit_cannot_be_overwritten_before_input_reads(tmp_path, monkeypatch):
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    output = tmp_path/'.tools/kept.json'
    output.parent.mkdir()
    output.write_bytes(b'previous failure')
    with pytest.raises(ValueError, match='fresh'):
        module.run(output)
    assert output.read_bytes() == b'previous failure'
