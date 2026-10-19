from pathlib import Path

import pytest

from scripts import build_portable as builder


def test_public_rotation_document_closure_resolves_nested_links_and_excludes_personal_files(tmp_path,monkeypatch):
    root=tmp_path/'source';docs=root/'docs';docs.mkdir(parents=True)
    seeds=('nbody-rotation.md','rotation-year.md','lunar-spin-initial.md','conservative-rotation.md','harmonic-sphere-validation.md','chart-current-validation.md')
    for name in seeds:(docs/name).write_text('[nested](nested.md) [private](changes.md) [remote](https://example.org/)',encoding='utf-8')
    (docs/'nested.md').write_text('[data](report.json)',encoding='utf-8');(docs/'report.json').write_text('{"public":true}',encoding='utf-8')
    (docs/'changes.md').write_text('private data must remain local',encoding='utf-8')
    monkeypatch.setattr(builder,'ROOT',root);output=tmp_path/'portable'
    copied=builder.copy_public_rotation_documents(output)
    assert len(copied)==8 and (output/'docs/report.json').read_text(encoding='utf-8')=='{"public":true}'
    assert not (output/'docs/changes.md').exists()
    assert '(changes.md)' not in (output/'docs/nbody-rotation.md').read_text(encoding='utf-8')
    assert (docs/'changes.md').read_text(encoding='utf-8')=='private data must remain local'


def test_document_link_outside_project_rejected_before_copying_external_file(tmp_path,monkeypatch):
    root=tmp_path/'source';docs=root/'docs';docs.mkdir(parents=True)
    for name in ('rotation-year.md','lunar-spin-initial.md','conservative-rotation.md','harmonic-sphere-validation.md','chart-current-validation.md'):
        (docs/name).write_text('',encoding='utf-8')
    (docs/'nbody-rotation.md').write_text('[external](../../external.txt)',encoding='utf-8')
    (tmp_path/'external.txt').write_text('must not be copied',encoding='utf-8')
    monkeypatch.setattr(builder,'ROOT',root)
    with pytest.raises(ValueError,match='Nonpublic'):builder.copy_public_rotation_documents(tmp_path/'portable')
    assert not (tmp_path/'portable/external.txt').exists()


@pytest.mark.parametrize("name,allowed", [("ERFA-LICENSE.txt",True),("private-source.txt",False)])
def test_only_explicit_public_runtime_license_may_join_document_closure(tmp_path,monkeypatch,name,allowed):
    root=tmp_path/'source';docs=root/'docs';docs.mkdir(parents=True)
    data=root/'src/solar_simulator/data';data.mkdir(parents=True)
    (data/name).write_text('public license' if allowed else 'must stay local',encoding='utf-8')
    for seed in ('rotation-year.md','lunar-spin-initial.md','conservative-rotation.md','harmonic-sphere-validation.md','chart-current-validation.md'):
        (docs/seed).write_text('',encoding='utf-8')
    (docs/'nbody-rotation.md').write_text(f'[license](../src/solar_simulator/data/{name})',encoding='utf-8')
    monkeypatch.setattr(builder,'ROOT',root);output=tmp_path/'portable'
    if allowed:
        builder.copy_public_rotation_documents(output)
        assert (output/'src/solar_simulator/data'/name).read_text(encoding='utf-8')=='public license'
    else:
        with pytest.raises(ValueError,match='Unsupported portable document'):
            builder.copy_public_rotation_documents(output)
        assert not (output/'src/solar_simulator/data'/name).exists()


def test_actual_prepared_portable_has_complete_relative_document_links(tmp_path):
    import hashlib
    import shutil
    from scripts.check_portable import check_document_links
    builder.prepare_documents(tmp_path)
    # This asset is supplied by the runtime wheel, outside document preparation.
    license=Path('runtime/Lib/site-packages/solar_simulator/data/ERFA-LICENSE.txt')
    (tmp_path/license).parent.mkdir(parents=True)
    shutil.copy2(builder.ROOT/'src/solar_simulator/data/ERFA-LICENSE.txt',tmp_path/license)
    assert check_document_links(tmp_path)>500
    for name in builder.PUBLIC_DOCUMENT_ARCHIVES:
        assert hashlib.sha256((tmp_path/name).read_bytes()).digest()==hashlib.sha256((builder.ROOT/name).read_bytes()).digest()
    guide=(tmp_path/'USER-GUIDE.md').read_text(encoding='utf-8')
    for name in ('controlled-stop.md','runtime-stabilization.md','reproducibility.md','profile-selection.md'):
        assert f'(docs/{name})' in guide and (tmp_path/'docs'/name).is_file()
    assert not (tmp_path/'docs/changes.md').exists()


def test_exported_guide_rebases_new_links_and_keeps_anchors(tmp_path):
    docs=tmp_path/'docs';docs.mkdir()
    source=docs/'source.md';target=tmp_path/'USER-GUIDE.md'
    source.write_text('[new](future.md#usage) [here](#local) [remote](https://example.org/)',encoding='utf-8')
    builder.export_guide(source,target)
    assert target.read_text(encoding='utf-8')=='[new](docs/future.md#usage) [here](#local) [remote](https://example.org/)'


def test_packaged_document_validator_rejects_missing_and_escaping_targets(tmp_path):
    from scripts.check_portable import check_document_links
    guide=tmp_path/'guide.md'
    for link in ('missing.zip','../outside.txt'):
        guide.write_text(f'[bad]({link})',encoding='utf-8')
        with pytest.raises(ValueError,match='Broken portable document link'):check_document_links(tmp_path)


def test_unlisted_archives_cannot_join_public_closure(tmp_path,monkeypatch):
    root=tmp_path/'source';docs=root/'docs';docs.mkdir(parents=True)
    for name in ('nbody-rotation.md','rotation-year.md','lunar-spin-initial.md','conservative-rotation.md','harmonic-sphere-validation.md','chart-current-validation.md'):
        (docs/name).write_text('[archive](personal.zip)',encoding='utf-8')
    (docs/'personal.zip').write_bytes(b'private')
    monkeypatch.setattr(builder,'ROOT',root)
    with pytest.raises(ValueError,match='Unsupported portable document'):
        builder.copy_public_rotation_documents(tmp_path/'portable')
