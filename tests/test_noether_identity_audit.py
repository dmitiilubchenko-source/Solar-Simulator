"""Evidence guards and independently active negative controls."""
import json

import pytest

from scripts.assess_noether_identities import verified_pilot,controls_passed,run


def row(**changes):
    control=dict(missing_reaction_defect=.5,missing_static_energy_defect=.1,pair_only_pn_defect=.01,
        omitted_sources={'pn2':{'energy':1.,'momentum':1.,'angular':1.},'pn_q2':{'energy':1.,'momentum':1.,'angular':1.}})
    control.update(changes)
    return {'high':{'levels':[{'negative_controls':control}]}}


@pytest.mark.parametrize('field',['missing_reaction_defect','missing_static_energy_defect','pair_only_pn_defect'])
def test_missing_negative_control_cannot_be_hidden_by_other_successes(field):
    assert controls_passed([row()])
    assert not controls_passed([row(**{field:0.})])


def test_dropped_source_control_must_resolve_each_active_block():
    a=row();a['high']['levels'][-1]['negative_controls']['omitted_sources']['pn2']['momentum']=.1
    assert not controls_passed([a]) and not controls_passed([])


@pytest.mark.parametrize('kind',['incomplete','source','archive'])
def test_incompatible_pilot_receipt_is_rejected(tmp_path,kind):
    path=tmp_path/'pilot.json'
    doc=dict(complete=True,numerical_checks_passed=True,source_input_dependencies_unchanged=True,
        source_sha256={},input_sha256={},dependency_sha256={},npz_sha256='wrong')
    if kind=='incomplete':doc['complete']=False
    if kind=='source':doc['source_sha256']={str(path):'wrong'}
    path.with_suffix('.npz').write_bytes(b'previous data')
    path.write_text(json.dumps(doc),encoding='utf-8')
    with pytest.raises(ValueError):verified_pilot(path)


def test_previous_identity_audit_is_preserved_before_input_reads(monkeypatch,tmp_path):
    from scripts import assess_noether_identities as module
    monkeypatch.setattr(module,'ROOT',tmp_path)
    output=tmp_path/'.tools'/'kept';output.parent.mkdir()
    output.with_suffix('.json').write_bytes(b'saved failure')
    with pytest.raises(ValueError,match='fresh'):run(output,'unused')
    assert output.with_suffix('.json').read_bytes()==b'saved failure'
