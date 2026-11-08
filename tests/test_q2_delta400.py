"""Portable synthetic negative controls, no dependency on a local candidate checkout."""
import pytest
from scripts import q2_presentation_delta400 as delta


@pytest.fixture
def sources(monkeypatch):
    base={
        'src/solar_simulator/app.py':b'class Laboratory:\n def _update_profile_info(self):\n  if self.experiment.rotations:\n   self.model_info.set("old")\n',
        'src/solar_simulator/inspection.py':b'def report(experiment):\n limitations=[]\n return limitations\n',
        'src/solar_simulator/inspection_view.py':b'def rotation_text(payload):\n lines=[]\n return lines\n',
        'src/solar_simulator/simulation.py':b'G=6.67430e-11\ndef acceleration(r):return G/r**2\n',
        'src/solar_simulator/experiment.py':b'RTOL=1e-13\n',
        'rust/solar_native/src/lib.rs':b'fn force() -> f64 { 1.0 }\n',
    }
    target=dict(base)
    target['src/solar_simulator/app.py']=b'class Laboratory:\n def _update_profile_info(self):\n  if self.experiment.rotations:\n   self.model_info.set("old")\n   from .inspection import experimental_q2_warning\n   warning=experimental_q2_warning(self.experiment.rotations)\n   if warning:self.model_info.set(self.model_info.get()+" "+warning)\n'
    target['src/solar_simulator/inspection.py']=b'TWO_Q2_EXPERIMENTAL_WARNING="SYNTHETIC CONTROL ONLY"\ndef experimental_q2_warning(rotations):return TWO_Q2_EXPERIMENTAL_WARNING if len(rotations)==2 else ""\ndef report(experiment):\n limitations=[]\n if len(experiment.rotations)==2:\n  limitations.append(experimental_q2_warning(experiment.rotations))\n return limitations\n'
    target['src/solar_simulator/inspection_view.py']=b'def rotation_text(payload):\n lines=[]\n from .inspection import experimental_q2_warning\n warning=experimental_q2_warning(payload["rotations"])\n if warning:lines[:0]=[warning,""]\n return lines\n'
    monkeypatch.setattr(delta,'APPROVED',{k:delta.sha(target[k]) for k in delta.APPROVED})
    return base,target


def test_exact_presentation_sequence_is_required(sources):
    result=delta.review_maps(*sources)
    assert result['release_approved'] is False and result['application_acceptance_performed'] is False


@pytest.mark.parametrize('path,old,new',[
    ('src/solar_simulator/simulation.py',b'6.67430e-11',b'7.67430e-11'),
    ('src/solar_simulator/experiment.py',b'1e-13',b'1e-3'),
    ('rust/solar_native/src/lib.rs',b'1.0',b'2.0'),
    ('src/solar_simulator/app.py',b'set("old")',b'set("changed callback")'),
])
def test_force_tolerance_native_and_callback_mutations_are_rejected(sources,path,old,new):
    base,target=sources;changed=dict(target);assert old in changed[path]
    changed[path]=changed[path].replace(old,new)
    with pytest.raises(ValueError):delta.review_maps(base,changed)


def test_new_source_file_cannot_hide_behind_a_presentation_delta(sources):
    base,target=sources;target=dict(target,new_module=b'force=0')
    with pytest.raises(ValueError,match='inventory'):delta.review_maps(base,target)
