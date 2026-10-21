from scripts.check_environment import inspect_environment


def test_missing_data_fails_without_creating_or_restoring_any_file(tmp_path):
    report=inspect_environment(root=tmp_path)
    assert not report['passed']
    checks={row['name']:row for row in report['checks']}
    assert not checks['public_inputs']['ok'] and checks['public_inputs']['required']
    assert not checks['personal_context']['ok'] and not checks['personal_context']['required']
    assert not list(tmp_path.iterdir())


def test_missing_native_is_explicitly_required_only_on_request(monkeypatch):
    import scripts.native_audit
    def missing():raise RuntimeError('controlled missing solar_native')
    monkeypatch.setattr(scripts.native_audit,'require_native',missing)
    optional=inspect_environment()
    required=inspect_environment(require_native=True)
    for report,mandatory in ((optional,False),(required,True)):
        row=next(row for row in report['checks'] if row['name']=='solar_native')
        assert not row['ok'] and row['required']==mandatory and 'controlled missing' in row['detail']
    assert optional['passed'] and not required['passed']
