"""Stage a versioned candidate without changing the developer installation.

No orbit integration, native build or release publication is performed here.
The export plus six metadata overlays is explicitly distinct from a clean Git
checkout. Dependencies are shared read-only and recorded, not newly installed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile
import venv

ROOT = Path(__file__).resolve().parents[1]
METADATA = ('pyproject.toml', 'rust/solar_core/Cargo.toml',
    'rust/solar_native/Cargo.toml', 'rust/solar_native/pyproject.toml',
    'rust/solar_core/Cargo.lock', 'rust/solar_native/Cargo.lock')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    with Path(path).open('x', encoding='utf8', newline='\n') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def version_overlay(root, version='0.3.3'):
    """Only package versions; never global replacement in scientific evidence."""
    if version != '0.3.3':
        raise ValueError('This preparatory stage is specifically for0.3.3')
    changes = {}
    for name in METADATA:
        path = root/name
        before = sha(path)
        text = path.read_text(encoding='utf8')
        if name.endswith('.lock'):
            text, count = re.subn(r'(name = "solar_(?:core|native)"\nversion = )"0\.3\.[23]"',
                lambda m:m[1]+'"'+version+'"', text)
            expected = 2 if '/solar_native/' in name else 1
        else:
            text, count = re.subn(r'(?m)^version = "0\.3\.[23]"$', 'version = "'+version+'"', text)
            expected = 1
        if count != expected:
            raise ValueError('Unexpected source metadata: '+name)
        path.write_text(text, encoding='utf8', newline='\n')
        changes[name] = dict(before=before, after=sha(path))
    from scripts.build_portable import candidate_versions
    if candidate_versions(root)[0] != version:
        raise ValueError('Candidate metadata disagree')
    return changes


def stage(output, commit, dependency_site):
    output, dependency_site = Path(output).resolve(), Path(dependency_site).resolve()
    # Require an exact commit, never the implicit current working tree.
    actual = subprocess.check_output(['git','rev-parse',commit+'^{commit}'], cwd=ROOT, text=True).strip()
    if actual != commit:
        raise ValueError('Full exact commit required')
    if not (dependency_site/'scipy').is_dir() or not (dependency_site/'numpy').is_dir():
        raise ValueError('Missing pinned shared dependencies')
    output.mkdir(parents=True, exist_ok=False)
    exported, omitted = {}, []
    child = subprocess.Popen(['git','archive','--format=tar',commit], cwd=ROOT, stdout=subprocess.PIPE)
    try:
        with tarfile.open(fileobj=child.stdout, mode='r|') as archive:
            for member in archive:
                path = output/member.name
                if not path.resolve().is_relative_to(output) or member.issym() or member.islnk():
                    raise ValueError('Unsafe Git export member')
                if member.isdir():
                    path.mkdir(exist_ok=True)
                elif member.isfile():
                    # Large historical research arrays are recoverable from Git;
                    # they are not inputs to this bounded candidate preflight.
                    if member.name.startswith('docs/') and member.name.endswith('-samples.npz'):
                        omitted.append(member.name)
                        continue
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with path.open('xb') as stream:
                        import shutil
                        shutil.copyfileobj(archive.extractfile(member), stream)
                    exported[member.name] = sha(path)
                else:
                    raise ValueError('Unsupported Git export member')
        if child.wait() != 0:
            raise RuntimeError('Git export failed')
    finally:
        child.stdout.close()
        if child.poll() is None:
            child.kill(); child.wait()
    changes = version_overlay(output)
    from scripts.qualify_current_runtime375 import protocol, verify_inputs
    from scripts.release_history import evidence_path
    p = protocol()
    verify_inputs(p)
    for name, expected in {**p['input_sha256'], **p['raw_jpl_sha256']}.items():
        source = evidence_path(ROOT, name)
        target = evidence_path(output, name)
        if not target.exists():
            target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as stream:
                stream.write(source.read_bytes())
        if sha(target) != expected:
            raise ValueError('Candidate scientific input differs: '+name)
    venv.EnvBuilder(with_pip=False).create(output/'.venv')
    packages = output/'.venv/Lib/site-packages'
    if not packages.is_dir():
        raise ValueError('This local staging command expects Windows venv layout')
    # Own wheel packages precede the shared immutable dependency directory.
    (packages/'shared-dependencies.pth').write_text(str(dependency_site)+'\n', encoding='utf8')
    write(output/'candidate-staging.json', dict(schema=1,base_commit=commit,
        candidate_version='0.3.3',metadata_overlay=changes,exported_SHA256=exported,
        omitted_recoverable_git_files=omitted,shared_dependency_site=str(dependency_site),
        isolated_native_required=True,scientifically_qualified=False,
        restore_before_full_acceptance='Restore omitted paths from exact base_commit; never replace historical results'))
    return output


def seal_plans(candidate, native_sha, environment):
    """Copy science byte-for-value; refresh only actual execution provenance."""
    candidate = Path(candidate).resolve()
    staging = json.loads((candidate/'candidate-staging.json').read_bytes())
    plans = candidate/'candidate-plans'; plans.mkdir(exist_ok=False)
    records = {}
    templates = {'375':'current-runtime-375-protocol.json',
        '376':'runtime-reliability-376-protocol-v2.json', '380':'two-q2-380-plan.json'}
    shared = Path(staging['shared_dependency_site'])
    for key, name in templates.items():
        p = json.loads((candidate/'scripts'/name).read_bytes())
        if key == '375':
            p['runtime_commit'] = staging['base_commit']
            p['candidate_native'] = dict(sha256=native_sha)
            p['candidate_environment'] = {k:v for k,v in environment.items() if k!='package_files'}
        else:
            p['base_commit'] = staging['base_commit']
            p['environment'] = environment
            sources = {}
            for name in p['source_SHA256']:
                path = candidate/name
                if not path.is_file() and name.startswith('.venv/Lib/site-packages/'):
                    path = shared/name.removeprefix('.venv/Lib/site-packages/')
                    name = str(path.resolve())
                sources[name] = sha(path)
            p['source_SHA256'] = sources
            if key == '380':
                # Fresh packet AND continuous controls; no historical array reuse.
                p['continuous_control'] = True
        path = plans/(key+'.json'); write(path,p)
        records[key] = dict(path=str(path),sha256=sha(path),executed=False)
    write(plans/'manifest.json',dict(base_commit=staging['base_commit'],
        staging_SHA256=sha(candidate/'candidate-staging.json'),plans=records,
        scientifically_qualified=False))
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--dependency-site', type=Path, required=True)
    args = parser.parse_args()
    print(stage(args.output,args.commit,args.dependency_site))


if __name__ == '__main__':
    main()
