import hashlib
import json

import pytest

from scripts.kepler_cache import load_receipt


def fixture(tmp_path):
    source=tmp_path/'model.py';source.write_bytes(b'model')
    data=tmp_path/'result.npz';data.write_bytes(b'array bytes')
    receipt=tmp_path/'result.json'
    document={'npz_sha256':hashlib.sha256(data.read_bytes()).hexdigest(),
              'source_sha256':{'model.py':hashlib.sha256(source.read_bytes()).hexdigest()}}
    receipt.write_text(json.dumps(document),encoding='utf-8')
    return source,data,receipt,document


def test_valid_cache_accepts_a_new_elapsed_time_without_weakening_array_binding(tmp_path):
    _,_,path,document=fixture(tmp_path)
    first,_=load_receipt(path,tmp_path)
    document['wall_seconds']=99.12
    path.write_text(json.dumps(document),encoding='utf-8')
    second,_=load_receipt(path,tmp_path)
    assert first['npz_sha256']==second['npz_sha256']


@pytest.mark.parametrize('target,match',[('array','NPZ'),('source','source')])
def test_cache_rejects_corrupted_scientific_array_or_changed_source(tmp_path,target,match):
    source,data,path,_=fixture(tmp_path)
    (data if target=='array' else source).write_bytes(b'changed')
    with pytest.raises(ValueError,match=match):
        load_receipt(path,tmp_path)


def test_legacy_receipt_without_array_hash_requires_explicit_recomputation(tmp_path):
    _,_,path,document=fixture(tmp_path)
    del document['npz_sha256']
    path.write_text(json.dumps(document),encoding='utf-8')
    with pytest.raises(ValueError,match='Legacy'):
        load_receipt(path,tmp_path)
