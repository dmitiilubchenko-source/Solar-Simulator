from pathlib import Path

import pytest

from scripts import check_project as checker


def test_historical_anchor_resolves_current_copy_and_never_reads_original_checkout(tmp_path,monkeypatch):
    root=tmp_path/"new checkout";root.mkdir();source=root/"src/model.py"
    source.parent.mkdir();source.write_text("first\nsecond\n",encoding="utf-8")
    docs=root/"docs";docs.mkdir()
    (docs/"report.md").write_text("[model](C:/Users/Admin/Desktop/Solar-simulator/src/model.py:2)",encoding="utf-8")
    monkeypatch.setattr(checker,"ROOT",root)
    checker.check_links()
    assert checker.project_source(str(source),root)==source
    assert checker.project_source("src/model.py",root)==source
    source.write_text("only first\n",encoding="utf-8")
    with pytest.raises(ValueError,match="Invalid link"):checker.check_links()


@pytest.mark.parametrize("name",["C:/Other/model.py","../outside.py",
    "C:/old/Solar-simulator/../../outside.py","C:/Solar-simulator/other/Solar-simulator/file.py"])
def test_outside_or_ambiguous_project_links_are_rejected(tmp_path,name):
    with pytest.raises(ValueError):checker.project_source(name,tmp_path)


def test_markdown_links_resolve_from_document_directory(tmp_path,monkeypatch):
    root=tmp_path/"checkout";root.mkdir()
    docs=root/"docs";docs.mkdir()
    source=root/"src/model.py";source.parent.mkdir()
    source.write_text("first\nsecond\n",encoding="utf-8")
    (docs/"release.md").write_text("correct document\n",encoding="utf-8")
    (root/"release.md").write_text("",encoding="utf-8")
    report=docs/"report.md"
    report.write_text("[release](release.md:1) [source](../src/model.py:2)",encoding="utf-8")
    monkeypatch.setattr(checker,"ROOT",root)
    checker.check_links()
    report.write_text("[missing](missing.md:1)",encoding="utf-8")
    with pytest.raises(ValueError,match="Invalid link"):checker.check_links()
    report.write_text("[bad line](release.md:2)",encoding="utf-8")
    with pytest.raises(ValueError,match="Invalid link"):checker.check_links()


@pytest.mark.parametrize("name",["../../outside.py","C:/Other/model.py",
    "C:/old/Solar-simulator/../../outside.py"])
def test_document_relative_resolution_keeps_checkout_boundary(tmp_path,name):
    root=tmp_path/"checkout";root.mkdir()
    with pytest.raises(ValueError):
        checker.project_source(name,root,relative_to=root/"docs")
