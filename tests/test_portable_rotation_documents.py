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
