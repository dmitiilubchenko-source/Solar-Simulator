"""Exact, autonomous RK order-condition diagnostics; never changes a solver.

Theory: Butcher & Podhaisky, arXiv:2112.01608v1, equations (6)-(8).
Table literals: pinned SciPy 1.18.1; its BSD notice is in
rust/solar_adaptive/LICENSE-SCIPY.txt. No downloaded code is executed.
"""
import argparse
import ast
from decimal import Decimal, localcontext
from fractions import Fraction as F
from functools import cache
import hashlib
from importlib.metadata import distribution
import json
from math import factorial, prod
from pathlib import Path
import re
import struct
import subprocess
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA = 'e283219a0f1e5f2cc37924ab961d9d24932f69a6d69fe68ee384b7c31f08839a'
PROTOCOL = 'docs/dop853-coefficients-protocol.md'
COUNTS = (1, 1, 2, 4, 9, 20, 48, 115)


def literal_tables(text):
    """Extract decimal A[0:12], A[12] (=B), C[0:12], without float casts."""
    a = [[F(0) for _ in range(12)] for _ in range(13)]
    c = None
    seen = set()
    for node in ast.parse(text).body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id == 'C':
            if c is not None or not isinstance(node.value, ast.Call):
                raise ValueError('Unexpected C declaration')
            c = [number(text, v) for v in node.value.args[0].elts[:12]]
        if (isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name)
                and target.value.id == 'A'):
            indices = ast.literal_eval(target.slice)
            if not isinstance(indices, tuple) or len(indices) != 2:
                raise ValueError('Unexpected A index')
            i, j = indices
            if not (type(i) is int and type(j) is int and 0 <= i < 16 and 0 <= j < 16):
                raise ValueError('Unexpected A dimensions')
            if i > 12:
                continue  # Dense-output stages do not enter the accepted update.
            if j >= 12 or j >= i or (i, j) in seen:
                raise ValueError('Nonexplicit or duplicate A entry')
            a[i][j] = number(text, node.value)
            seen.add((i, j))
    if c is None or len(c) != 12 or not seen:
        raise ValueError('Missing twelve-stage table')
    return tuple(map(tuple, a[:12])), tuple(a[12]), tuple(c)


def number(text, node):
    token = ast.get_source_segment(text, node)
    if token is None or not re.fullmatch(r'-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?', token):
        raise ValueError('Expected a finite decimal literal')
    return F(token)


@cache
def order(tree):
    return 1 + sum(map(order, tree))


@cache
def density(tree):
    return order(tree) * prod(map(density, tree))


def trees_through(max_order):
    """Unordered rooted trees as canonical sorted tuples of child trees."""
    if type(max_order) is not int or not 1 <= max_order <= 8:
        raise ValueError('Bounded orders 1 through 8 only')
    groups = {1: [()]}
    for n in range(2, max_order + 1):
        candidates = sorted(t for group in groups.values() for t in group)
        def forests(remaining, start, chosen):
            if remaining == 0:
                yield chosen
            for i in range(start, len(candidates)):
                child = candidates[i]
                size = order(child)
                if size <= remaining:
                    yield from forests(remaining-size, i, chosen+(child,))
        groups[n] = list(forests(n-1, 0, ()))
    return groups


def residuals(a, b, max_order=8):
    """Phi_i(leaf)=1; Phi_i([t...])=product(A Phi(t...))_i."""
    stages = len(b)
    if not stages or len(a) != stages or any(len(row) != stages for row in a):
        raise ValueError('Table dimensions differ')
    if any(a[i][j] for i in range(stages) for j in range(i, stages)):
        raise ValueError('Expected explicit tableau')
    @cache
    def weights(tree):
        factors = [tuple(sum((a[i][j]*weights(child)[j] for j in range(stages)), F(0))
                         for i in range(stages)) for child in tree]
        return tuple(prod(factor[i] for factor in factors) for i in range(stages))
    return {tree: sum((b[i]*weights(tree)[i] for i in range(stages)), F(0))-F(1, density(tree))
            for group in trees_through(max_order).values() for tree in group}


def scientific(value):
    with localcontext() as context:
        context.prec = 50
        return str(Decimal(value.numerator)/Decimal(value.denominator))


def describe(a, b, c):
    rows = residuals(a, b)
    groups = {}
    for n in range(1, 9):
        selected = [(tree, value) for tree, value in rows.items() if order(tree) == n]
        worst, value = max(selected, key=lambda item: abs(item[1]))
        groups[str(n)] = dict(count=len(selected), nonzero=sum(v != 0 for _, v in selected),
            maximum_absolute_residual=scientific(abs(value)), worst_tree=repr(worst))
    # A separate scalar linear recurrence: b^T A^(k-1) 1 = 1/k!.
    vector = (F(1),)*len(b)
    chains = []
    for n in range(1, 9):
        value = sum((x*y for x, y in zip(b, vector)), F(0))-F(1, factorial(n))
        chains.append(scientific(value))
        vector = tuple(sum((x*y for x, y in zip(row, vector)), F(0)) for row in a)
    return dict(by_order=groups, row_sum_minus_c=[scientific(sum(row)-v) for row, v in zip(a, c)],
        b_sum_minus_one=scientific(sum(b)-1), linear_chain_residuals=chains,
        residuals=[dict(tree=repr(t), order=order(t), density=density(t), exact=str(v),
                        decimal=scientific(v)) for t, v in rows.items()])


def run(source, output):
    """Require an exact pinned source and a new local result path."""
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists():
        raise FileExistsError('Preserve previous coefficient audit')
    if not output.is_relative_to((ROOT/'.tools').resolve()):
        raise ValueError('Use a fresh .tools output')
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA:
        raise ValueError('Pinned SciPy source SHA differs')
    start = perf_counter()
    a, b, c = literal_tables(raw.decode('utf-8'))
    rational = [x for row in a for x in row]+list(b)+list(c)
    rust_path = ROOT/'rust/solar_adaptive/src/coefficients.rs'
    rust_raw = rust_path.read_bytes()
    rust_bits = re.findall(rb'from_bits\(0x([0-9a-f]{16})\)', rust_raw)
    if len(rust_bits) != 194:
        raise ValueError('Rust table length changed')
    rounded = [F(float(v)) for v in rational]
    expected = b''.join(struct.pack('>d', float(v)) for v in rational)
    actual = b''.join(bytes.fromhex(v.decode()) for v in rust_bits[:168])
    if actual != expected:
        raise ValueError('Rust A/B/C are not the rounded pinned literals')
    report = dict(protocol=PROTOCOL, complete=False, runtime_modified=False,
        production_eligible=False, cause_of_orbital_failures='NOT_ESTABLISHED',
        scipy_source_sha256=SOURCE_SHA, rust_source_sha256=hashlib.sha256(rust_raw).hexdigest(),
        audit_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        protocol_sha256=hashlib.sha256((ROOT/PROTOCOL).read_bytes()).hexdigest(),
        baseline_commit=subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        abc_binary64_match=True, coefficient_count=168, e3_e5_audited=False,
        arithmetic='Exact fractions; decimal strings are display only',
        decimal_literals=dict(a=[[str(x) for x in row] for row in a],
                              b=list(map(str, b)), c=list(map(str, c))))
    report['literal_rationals'] = describe(a, b, c)
    ab = tuple(tuple(rounded[i:i+12]) for i in range(0, 144, 12))
    report['exact_binary64'] = describe(ab, tuple(rounded[144:156]), tuple(rounded[156:]))
    if tuple(v['count'] for v in report['exact_binary64']['by_order'].values()) != COUNTS:
        raise ArithmeticError('Rooted-tree enumeration differs')
    report.update(complete=True, seconds=perf_counter()-start)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=distribution('scipy').locate_file(
        'scipy/integrate/_ivp/dop853_coefficients.py'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = run(args.source, args.output)
    print(json.dumps({key: report[key] for key in ('complete', 'abc_binary64_match', 'seconds')}, indent=2))


if __name__ == '__main__':
    main()
