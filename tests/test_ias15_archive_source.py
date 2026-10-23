"""Structural audit rejects missing buffers and reads source without executing it."""
import hashlib
import io
import sys
import tarfile

import pytest

from scripts import audit_ias15_archive_source as subject


def declaration():
    fields = '\n'.join('double* REB_RESTRICT '+n+';' for n in (*subject.VECTORS, *subject.POLYNOMIALS))
    return ('struct reb_integrator_ias15_state {\n'
            'double epsilon;\ndouble min_dt;\n} adaptive_mode;\n'
            'uint64_t iterations_max_exceeded;\nsize_t N_allocated;\n'+fields+'\n};')


def descriptors():
    rows = []
    for name in subject.SCALARS:
        dtype = {'adaptive_mode':'REB_UINT','iterations_max_exceeded':'REB_UINT64'}.get(name, 'REB_DOUBLE')
        rows.append(f'{{"", {dtype}, "{name}", offsetof(struct reb_integrator_ias15_state, {name}), 0, 0, 0}}')
    for name in (*subject.VECTORS, *subject.POLYNOMIALS):
        size = 'sizeof(double)' if name in subject.VECTORS else '7*sizeof(double)'
        rows.append(f'{{"", REB_POINTER, "{name}", offsetof(struct reb_integrator_ias15_state, {name}), '
                    f'offsetof(struct reb_integrator_ias15_state, N_allocated), {size}, 0}}')
    return '\n'.join(rows)


def test_complete_field_inventory_distinguishes_buffers_and_derived_allocation():
    rows = subject.ias15_fields(declaration(), descriptors())
    assert len(rows) == 17 and 'N_allocated' not in rows
    assert sum(row['elements_per_allocated_coordinate'] or 0 for row in rows.values()) == 49
    assert rows['csb']['elements_per_allocated_coordinate'] == 7
    assert rows['csx']['elements_per_allocated_coordinate'] == 1


@pytest.mark.parametrize('damage', ['missing', 'extra', 'duplicate', 'alias', 'length', 'dtype', 'structure'])
def test_field_inventory_fails_closed_on_drift(damage):
    header, table = declaration(), descriptors()
    if damage == 'missing':table = '\n'.join(row for row in table.splitlines() if '"csb"' not in row)
    elif damage == 'extra':table += '\n'+table.splitlines()[0].replace('epsilon', 'unexpected')
    elif damage == 'duplicate':table += '\n'+table.splitlines()[0]
    elif damage == 'alias':table = table.replace('ias15_state, csb)', 'ias15_state, b)')
    elif damage == 'length':table = table.replace('7*sizeof(double)', '6*sizeof(double)')
    elif damage == 'dtype':table = table.replace('REB_UINT64', 'REB_DOUBLE')
    else:header = header.replace('double epsilon;', 'double unexpected;')
    with pytest.raises(ValueError):subject.ias15_fields(header, table)


def test_nested_global_member_is_a_real_serialized_field():
    text = '{"", REB_STRING, "integrator.name", offsetof(struct reb_simulation, integrator.name), 0, 0, 0}'
    assert subject.descriptors(text, 'reb_simulation')['integrator.name']['member'] == 'integrator.name'


def test_warning_audit_reports_bits_not_represented_in_python_without_executing_source():
    header = 'REB_BINARYDATA_WARNING_POINTERS = 4, REB_BINARYDATA_WARNING_CUSTOM_INTEGRATOR = 2048,'
    python = 'raise AssertionError("Do not execute source")\nBINARY_WARNINGS = [(False,4,"pointer")]'
    result = subject.warning_inventory(header, python)
    assert result['c_declared_not_python_mapped'] == {'REB_BINARYDATA_WARNING_CUSTOM_INTEGRATOR':2048}


def test_wrong_tar_sha_is_rejected_before_tar_parser(tmp_path, monkeypatch):
    path = tmp_path/'bad.tar.gz'
    path.write_bytes(b'not a trusted source archive')
    def forbidden(*args, **kwargs):raise AssertionError('Do not parse unverified tar')
    monkeypatch.setattr(tarfile, 'open', forbidden)
    with pytest.raises(ValueError, match='SHA'):subject.read_sources(path)


@pytest.mark.parametrize('damage', ['missing', 'duplicate', 'nonregular'])
def test_source_member_inventory_rejects_incomplete_or_ambiguous_archive(tmp_path, monkeypatch, damage):
    path = tmp_path/'source.tar.gz'
    with tarfile.open(path, 'w:gz') as archive:
        for name in subject.FILES:
            if damage == 'missing' and name == subject.FILES[0]:continue
            for _ in range(2 if damage == 'duplicate' and name == subject.FILES[0] else 1):
                item = tarfile.TarInfo('rebound-5.2.2/'+name)
                if damage == 'nonregular' and name == subject.FILES[0]:item.type = tarfile.SYMTYPE
                else:item.size = 1
                archive.addfile(item, io.BytesIO(b'x'))
    monkeypatch.setattr(subject, 'SDIST_SHA', hashlib.sha256(path.read_bytes()).hexdigest())
    with pytest.raises(ValueError, match='Missing, duplicate or non-regular'):subject.read_sources(path)


def test_existing_output_is_preserved_before_source_is_read(tmp_path, monkeypatch):
    output = tmp_path/'audit.json'
    output.write_bytes(b'earlier failure')
    monkeypatch.setattr(sys, 'argv', ['audit', '--source', str(tmp_path/'absent'), '--output', str(output)])
    with pytest.raises(FileExistsError):subject.main()
    assert output.read_bytes() == b'earlier failure'


def test_public_source_receipt_binds_current_auditor_protocol_and_test():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    report = json.loads((root/'docs/ias15-archive-source-validation.json').read_bytes())
    for name, expected in report['source_sha256'].items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest() == expected
    assert report['sdist_sha256'] == subject.SDIST_SHA
    assert len(report['ias15_written_fields']) == 17
    assert report['derived_fields'] == ['N_allocated']
    assert report['numerical_experiment_executed'] is False
    assert report['runtime_modified'] is False and report['production_eligible'] is False
