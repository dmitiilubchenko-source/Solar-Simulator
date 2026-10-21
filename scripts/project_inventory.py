"""Check or refresh the file index; scientific provenance is checked separately."""
import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = Path("docs/project-inventory.json")
PRIVATE_DOCS = {
    "changes.md", "development-plan.md", "learning-log.md", "project-review.md",
    "session-handoff.md", "session-handoff-archive.md", "project-context.md",
}
IGNORED_PARTS = {"__pycache__", ".pytest_cache", "target"}


def inventory(root):
    """Index public component trees, excluding generated and personal files."""
    groups = {}
    for directory in ("src", "rust", "scripts", "tests", "docs", "examples", "requirements", ".github"):
        for path in sorted((root / directory).rglob("*")):
            relative = path.relative_to(root)
            if not path.is_file() or IGNORED_PARTS.intersection(relative.parts):
                continue
            if any(part.endswith(".egg-info") for part in relative.parts):
                continue
            if relative == INDEX or (directory == "docs" and path.name in PRIVATE_DOCS):
                continue
            if directory == "src" and "data" in relative.parts:
                group = "runtime_data"
            elif directory == "scripts" and "validation" in relative.parts:
                group = "frozen_validation"
            else:
                group = directory
            groups.setdefault(group, []).append(relative.as_posix())
    groups["root"] = sorted(p.name for p in root.iterdir() if p.is_file() and (
        p.suffix in {".md", ".toml", ".cmd"} or p.name in {".gitignore", ".gitattributes"}
    ) and p.name != "AGENTS.md")
    return {"schema_version": 1, "groups": {key: sorted(groups[key]) for key in sorted(groups)}}


def check_inventory(root=ROOT):
    expected = json.loads((root / INDEX).read_text(encoding="utf-8"))
    actual = inventory(root)
    if actual != expected:
        before = {p for paths in expected["groups"].values() for p in paths}
        after = {p for paths in actual["groups"].values() for p in paths}
        raise ValueError(
            f"Project inventory stale: added={sorted(after-before)}, removed={sorted(before-after)}. "
            "Review docs/project-map.md, then run scripts/project_inventory.py --write."
        )
    print(f"Project inventory valid: {sum(map(len, actual['groups'].values()))} files")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Refresh after reviewing the project map")
    args = parser.parse_args()
    if args.write:
        (ROOT / INDEX).write_text(json.dumps(inventory(ROOT), ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8")
    check_inventory()


if __name__ == "__main__":
    main()
