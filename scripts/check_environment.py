"""Read-only environment preflight; it never installs packages or downloads data."""
import argparse
import hashlib
import importlib
from importlib import metadata
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import sysconfig

ROOT=Path(__file__).resolve().parents[1]


def inspect_environment(*,root=ROOT,require_native=False,gui=False,validated=False):
    checks=[]
    def check(name,required,probe):
        try:detail=probe();ok=True
        except Exception as error:detail=f'{type(error).__name__}: {error}';ok=False
        checks.append(dict(name=name,required=required,ok=ok,detail=detail))
    versions={}
    for name in ('numpy','scipy','matplotlib','pytest'):
        def probe(name=name):
            module=importlib.import_module(name)
            versions[name]=metadata.version(name)
            return versions[name]
        check(name,True,probe)
    def tkinter():
        tk=importlib.import_module('tkinter')
        if gui:
            window=tk.Tk()
            try:window.withdraw();return f'Tk {window.tk.call("info","patchlevel")}; display available'
            finally:window.destroy()
        return f'Tk {tk.TkVersion}; display not tested (use --gui)'
    check('tk',gui,tkinter)
    cargo=shutil.which('cargo') or str(Path.home()/'.cargo/bin'/('cargo.exe' if sys.platform=='win32' else 'cargo'))
    check('cargo',require_native,lambda:subprocess.check_output([cargo,'--version'],text=True,encoding='utf-8',timeout=10).strip())
    def native():
        if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
        from scripts.native_audit import require_native as verify
        return verify()
    check('solar_native',require_native,native)
    executable=Path(root)/'rust/solar_core/target/release'/('solar_core.exe' if sys.platform=='win32' else 'solar_core')
    def standalone():
        if not executable.is_file():raise FileNotFoundError('Build standalone Rust: cargo build --release --manifest-path rust/solar_core/Cargo.toml')
        return str(executable)
    check('rust_standalone',require_native,standalone)
    def public_inputs():
        manifest=json.loads((Path(root)/'tests/data/research63-inputs.json').read_text(encoding='utf-8'))
        data=(Path(root)/'tests/data/research63-inputs.zip').read_bytes()
        if hashlib.sha256(data).hexdigest()!=manifest['bundle_sha256']:raise ValueError('Public test bundle SHA256 mismatch')
        if not any((Path(root)/'src/solar_simulator/data').glob('*.json')):raise FileNotFoundError('Runtime JSON data absent')
        return 'Public test bundle SHA256 verified; runtime JSON present (not a scientific audit)'
    check('public_inputs',True,public_inputs)
    def context():
        missing=[p for p in ('AGENTS.md','docs/session-handoff.md') if not (Path(root)/p).is_file()]
        if missing:raise FileNotFoundError('Restore private context if needed: '+', '.join(missing))
        return 'Local instructions and handoff available; private caches are not checked'
    check('personal_context',False,context)
    def validated_profile():
        if sys.platform!='win32' or sys.version_info[:2]!=(3,14) or not sysconfig.get_config_var('Py_GIL_DISABLED'):
            raise ValueError('Recorded profile requires Windows CPython3.14t; this environment needs separate qualification')
        for line in (Path(root)/'requirements/validated-windows-cp314t.txt').read_text().splitlines():
            name,version=line.split('==')
            if metadata.version(name)!=version:raise ValueError(f'{name}: expected {version}, got {metadata.version(name)}')
        return 'Recorded platform/ABI/package versions match; not a physics or portable acceptance'
    check('validated_profile',validated,validated_profile)
    return dict(python=sys.version,executable=sys.executable,platform=platform.platform(),
                free_threaded=bool(sysconfig.get_config_var('Py_GIL_DISABLED')),checks=checks,
                passed=all(row['ok'] or not row['required'] for row in checks))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-native',action='store_true')
    parser.add_argument('--gui',action='store_true',help='Require a real Tk display')
    parser.add_argument('--validated',action='store_true',help='Require the recorded Windows3.14t constraints profile')
    parser.add_argument('--json',action='store_true')
    args=parser.parse_args(argv)
    result=inspect_environment(require_native=args.require_native,gui=args.gui,validated=args.validated)
    if args.json:print(json.dumps(result,ensure_ascii=False,indent=2))
    else:
        print(result['python'])
        for row in result['checks']:
            status='PASS' if row['ok'] else 'FAIL' if row['required'] else 'OPTIONAL'
            print(f'{status}: {row["name"]}: {row["detail"]}')
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
