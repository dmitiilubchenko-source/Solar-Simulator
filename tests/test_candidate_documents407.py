"""Source/UI references and document-only future packaging; no binary build."""
import hashlib,json,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def test_exact_public_composition_and_plain_runtime_warning_paths():
    from solar_simulator.inspection import TWO_Q2_EXPERIMENTAL_WARNING
    manifest=json.loads((ROOT/'docs/q2-document-composition-407.json').read_bytes())
    for name,row in manifest['files'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==row['SHA256']
    paths=re.findall(r'docs/[A-Za-z0-9_.-]+\.md',TWO_Q2_EXPERIMENTAL_WARNING)
    assert paths
    assert all((ROOT/name).is_file() for name in paths)
    assert '0.244795' in TWO_Q2_EXPERIMENTAL_WARNING and 'NO-GO' in TWO_Q2_EXPERIMENTAL_WARNING
    assert (ROOT/'docs/q2-gui-lifecycle-fix-404.md').is_file()
    assert 'не выпущен' in (ROOT/'docs/releases/v0.3.3.md').read_text()


def test_future_document_contract_keeps_limits_and_excludes_executable_research(tmp_path):
    from scripts.build_portable import copy_public_rotation_documents
    from scripts.check_portable import check_document_links
    copied=copy_public_rotation_documents(tmp_path,extra_seeds=('q2-application-acceptance-402.md','q2-gui-lifecycle-fix-404.md'))
    assert check_document_links(tmp_path)>100
    assert 'docs/q2-application-acceptance-402.md' in copied
    assert 'docs/q2-gui-lifecycle-fix-404.md' in copied
    assert not (tmp_path/'scripts/qualification404/audit.py').exists()
    assert not (tmp_path/'tests').exists()
    for name in ('q2-application-acceptance-402.md','q2-gui-lifecycle-fix-404.md'):
        original=(ROOT/'docs'/name).read_text();exported=(tmp_path/'docs'/name).read_text()
        # Link rewriting cannot delete or rewrite any report prose.
        prose=lambda text:re.sub(r'\]\([^)]+\)','](LINK)',text)
        assert prose(original)==prose(exported)
