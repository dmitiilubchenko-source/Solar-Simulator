"""Organized public navigation must survive a clean checkout without private notes."""
from pathlib import Path
import re

from scripts.check_project import PRIVATE_DOCS, project_source


ROOT = Path(__file__).resolve().parents[1]


def test_organized_documentation_and_component_links_resolve():
    documents = [ROOT/'docs/README.md', ROOT/'docs/project-map.md',
                 ROOT/'src/solar_simulator/README.md']
    for category in ('user', 'development', 'verification', 'archive'):
        documents.extend((ROOT/'docs'/category).rglob('*.md'))
    documents.extend((ROOT/'rust').glob('*/README.md'))
    assert len(documents) >= 10
    for document in documents:
        for target in re.findall(r'\]\(([^)]+)\)', document.read_text(encoding='utf-8')):
            raw = target.split('#', 1)[0].strip('<>')
            if not raw or raw.startswith(('http://', 'https://', 'mailto:')):
                continue
            line = re.search(r':([0-9]+)$', raw)
            source = project_source(raw[:line.start()] if line else raw, ROOT, relative_to=document.parent)
            assert source.exists(), f'{document.relative_to(ROOT)} -> {target}'
            assert source.name not in PRIVATE_DOCS | {'AGENTS.md'}, f'Private navigation target: {source}'
            assert '.tools' not in source.relative_to(ROOT).parts, f'Local-only navigation target: {source}'
            if line:
                assert source.is_file()
                assert 1 <= int(line.group(1)) <= len(source.read_text(encoding='utf-8').splitlines()), target
