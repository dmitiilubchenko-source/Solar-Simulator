"""Independent rational order limits and integrity of coefficient diagnostics."""
from decimal import localcontext
from fractions import Fraction as F
import hashlib
import json
from math import factorial

import pytest

from scripts.audit_dop853_coefficients import (
    COUNTS, ROOT, density, describe, literal_tables, order, residuals, run, trees_through,
)


def rk4():
    return ((F(0), F(0), F(0), F(0)), (F(1, 2), F(0), F(0), F(0)),
            (F(0), F(1, 2), F(0), F(0)), (F(0), F(0), F(1), F(0))), (
            F(1, 6), F(1, 3), F(1, 3), F(1, 6))


def test_tree_counts_density_and_independent_classical_methods():
    groups = trees_through(8)
    assert tuple(map(len, groups.values())) == COUNTS
    for n, trees in groups.items():
        assert len(set(trees)) == len(trees)
        assert all(order(t) == n and tuple(sorted(t)) == t for t in trees)
        chain = ()
        for _ in range(n-1):
            chain = (chain,)
        assert density(chain) == factorial(n)
        assert density(((),)*(n-1)) == n
    for a, b, expected_order in (
        (((F(0),),), (F(1),), 1),
        (((F(0), F(0)), (F(1, 2), F(0))), (F(0), F(1)), 2),
        (*rk4(), 4),
    ):
        result = residuals(a, b)
        assert all(v == 0 for t, v in result.items() if order(t) <= expected_order)
        assert any(v != 0 for t, v in result.items() if order(t) == expected_order+1)


def test_all_eight_low_order_conditions_against_explicit_formulas():
    # Deliberately arbitrary explicit rational table, not an order-four table.
    a = ((F(0),)*3, (F(2, 5), F(0), F(0)), (F(-1, 7), F(4, 3), F(0)))
    b = (F(2, 3), F(-3, 2), F(5, 7))
    c = tuple(map(sum, a))
    mv = lambda v: tuple(sum(x*y for x, y in zip(row, v)) for row in a)
    dot = lambda v: sum(x*y for x, y in zip(b, v))
    ac = mv(c)
    leaf = ()
    pair = (leaf,)
    expected = {
        leaf: sum(b)-1,
        pair: dot(c)-F(1, 2),
        (leaf, leaf): dot(tuple(x*x for x in c))-F(1, 3),
        (pair,): dot(ac)-F(1, 6),
        (leaf, leaf, leaf): dot(tuple(x**3 for x in c))-F(1, 4),
        (leaf, pair): dot(tuple(x*y for x, y in zip(c, ac)))-F(1, 8),
        ((leaf, leaf),): dot(mv(tuple(x*x for x in c)))-F(1, 12),
        ((pair,),): dot(mv(ac))-F(1, 24),
    }
    assert residuals(a, b, 4) == expected
    # Chain recurrence independently has only the first three nonzero powers
    # for a strictly lower triangular three-stage matrix.
    result = describe(a, b, c)
    chain = leaf
    for n, displayed in enumerate(result['linear_chain_residuals'], 1):
        assert displayed == next(row['decimal'] for row in result['residuals']
                                 if row['tree'] == repr(chain))
        if n > 3:
            assert residuals(a, b)[chain] == -F(1, factorial(n))
        chain = (chain,)


def test_literal_extraction_retains_digits_without_executing_source():
    source = 'C = np.array([0.0]*12)\nA[1,0] = 0.123456789012345678901234567890\n'
    # An explicit literal list is required; arbitrary source is never executed.
    source = source.replace('[0.0]*12', '['+','.join(['0.0']*12)+']')
    source += 'raise RuntimeError("must never execute")\n'
    with localcontext() as context:
        context.prec = 7
        a, b, c = literal_tables(source)
    assert a[1][0] == F('0.123456789012345678901234567890')
    assert a[1][0] != F(float('0.123456789012345678901234567890'))
    assert b == c == (F(0),)*12
    with pytest.raises(ValueError, match='duplicate'):
        literal_tables(source+'A[1,0] = 0.1\n')
    with pytest.raises(ValueError, match='Nonexplicit'):
        literal_tables(source+'A[1,1] = 0.1\n')
    with pytest.raises(ValueError):
        literal_tables(source+'A[2,0] = execute()\n')


def test_pinned_source_failure_and_prior_result_never_overwritten(tmp_path):
    old = tmp_path/'kept.json'
    old.write_bytes(b'keep')
    with pytest.raises(FileExistsError):
        run(tmp_path/'not-needed.py', old)
    assert old.read_bytes() == b'keep'
    # SHA failure is checked before creating a result in the required local root.
    source = tmp_path/'bad.py'
    source.write_bytes(b'bad source')
    destination = ROOT/'.tools/coefficient-test-sha-rejection/result.json'
    assert not destination.exists()
    with pytest.raises(ValueError, match='SHA'):
        run(source, destination)
    assert not destination.exists()
    with pytest.raises(ValueError, match='fresh .tools'):
        run(source, tmp_path/'elsewhere.json')


def test_implicit_table_is_rejected():
    with pytest.raises(ValueError, match='explicit'):
        residuals(((F(1),),), (F(1),))
    with pytest.raises(ValueError, match='dimensions'):
        residuals((), (F(1),))


def test_published_exact_residuals_reproduce_from_public_rationals():
    receipt = json.loads((ROOT/'docs/dop853-coefficients-validation.json').read_text())
    assert receipt['complete'] and receipt['abc_binary64_match']
    assert not receipt['production_eligible'] and not receipt['runtime_modified']
    assert receipt['cause_of_orbital_failures'] == 'NOT_ESTABLISHED'
    assert receipt['audit_source_sha256'] == hashlib.sha256(
        (ROOT/'scripts/audit_dop853_coefficients.py').read_bytes()).hexdigest()
    table = receipt['decimal_literals']
    a = tuple(tuple(map(F, row)) for row in table['a'])
    b, c = tuple(map(F, table['b'])), tuple(map(F, table['c']))
    assert describe(a, b, c) == receipt['literal_rationals']
    rounded = lambda xs: tuple(F(float(v)) for v in xs)
    assert describe(tuple(map(rounded, a)), rounded(b), rounded(c)) == receipt['exact_binary64']
