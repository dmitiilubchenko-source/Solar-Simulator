"""Check the numerical AST and save the exact wrapper diff from frozen 409.5."""
import ast
import difflib
import hashlib
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
BASE = "d04dc9aa5ca3d95659fc996ea560f042016ce67e"
OLD = "e332fca075e4dd686c3011a0f644c19e2af2210025badffb8117f516d74687a7"
PATH = "scripts/check_portable.py"


def text(node):
    return ast.unparse(node)


def func(tree, name):
    return next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)


def verify():
    before = subprocess.check_output(["git","-C",str(ROOT),"show",f"{BASE}:{PATH}"])
    after = (ROOT/PATH).read_bytes()
    assert hashlib.sha256(before).hexdigest() == OLD
    old = ast.parse(before)
    new = ast.parse(after)
    ob, nb = func(old,"main"), func(new,"main")
    target = next(i for i,n in enumerate(ob.body) if text(n) == "result['continuous'] = check_continuous(folder, environment)")
    delta = len(nb.body)-len(ob.body)
    assert delta == 2
    assert text(nb.body[target]) == "evidence = None"
    assert text(nb.body[target+1]).startswith("if args.current040_manifest_sha256 is not None:")
    assert text(nb.body[target+2]) == "result['continuous'] = check_continuous(folder, environment, evidence=evidence)"
    nb.body[target:target+3] = [ob.body[target]]

    prev, now = func(old,"check_continuous"), func(new,"check_continuous")
    assert now.args.kwonlyargs[0].arg == "evidence" and len(now.args.kwonlyargs) == 1
    now.args = prev.args
    # The only changes to the nested program are the three evidence conditionals
    # and replacing two reads of the snapshot with the same snapshot captured once.
    old_probe = ast.parse(prev.body[1].value.value)
    new_probe = ast.parse(now.body[1].value.value)
    capture_nodes = [node for node in new_probe.body if isinstance(node,ast.If)]
    assert len(capture_nodes) == 3
    assert text(capture_nodes[0].test) == "len(sys.argv) > 1"
    assert all(text(n.test) == "evidence_api" for n in capture_nodes[1:])
    assert text(capture_nodes[2].body[0]).startswith(
        "evidence_api['write_year'](sys.argv[2], root, provenance, inputs_before, actual, actual_epochs_seconds,")
    new_probe.body = [n for n in new_probe.body if n not in capture_nodes]
    loop = next(n for n in new_probe.body if isinstance(n,ast.For))
    assert len(loop.body) == 4 and text(loop.body[1]) == "current = session.current"
    assert text(loop.body[2]) == "values.append(matrix(current))"
    assert text(loop.body[3].test) == "evidence_api"
    assert text(loop.body[3].body[0]) == "actual_epochs_seconds.append(float(current.time))"
    loop.body[1:] = ast.parse("values.append(matrix(session.current))").body
    assert ast.dump(old_probe) == ast.dump(new_probe), "Continuous numerical AST changed"
    now.body[1] = prev.body[1]
    command = now.body[2].value.args[0]
    assert text(command.elts[-1]) == "*(evidence or ())"
    command.elts.pop()
    assert ast.dump(old) == ast.dump(new), "Wrapper AST changed outside the evidence path"

    # Independently check the exact bytes of every unrelated function and the
    # unchanged portions of the modified functions, from their original lines.
    a, b = before.splitlines(keepends=True), after.splitlines(keepends=True)
    raw_old, raw_new = ast.parse(before), ast.parse(after)
    for item in raw_old.body:
        if isinstance(item, ast.FunctionDef) and item.name not in ("main","check_continuous"):
            other = func(raw_new,item.name)
            assert a[item.lineno-1:item.end_lineno] == b[other.lineno-1:other.end_lineno]
    sections = dict(old_sha256=OLD, new_sha256=hashlib.sha256(after).hexdigest(),
        exact_unchanged_functions=[n.name for n in raw_old.body if isinstance(n,ast.FunctionDef)
                                  and n.name not in ("main","check_continuous")],
        continuous_numerical_AST_equal=True, non_evidence_wrapper_AST_equal=True,
        modifications=["external evidence binding and isolated argv", "snapshot time/order capture",
                       "existing actual array/provenance publication"])
    diff = b"".join(difflib.diff_bytes(difflib.unified_diff,a,b,fromfile=b"frozen409.5/check_portable.py",
                                        tofile=b"410E/check_portable.py",n=0))
    return sections, diff
