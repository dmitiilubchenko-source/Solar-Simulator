"""One repeatable command for Python tests, Rust tests and documentation links."""
from pathlib import Path
from pathlib import PureWindowsPath
import re
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def check_links():
    count=0
    for path in (ROOT/"docs").glob("*.md"):
        for name,line in re.findall(r"\]\(([^)]+):([0-9]+)\)",path.read_text(encoding="utf-8")):
            source=project_source(name, ROOT)
            if not source.is_file() or not 1<=int(line)<=len(source.read_text(encoding="utf-8").splitlines()):
                raise ValueError(f"Invalid link: {path.name}: {name}:{line}")
            count+=1
    print(f"Documentation file/line links valid: {count}")


def project_source(name, root):
    """Resolve historical absolute project links inside this checkout only."""
    root=Path(root).resolve()
    candidate=Path(name)
    if candidate.is_absolute() and candidate.resolve().is_relative_to(root):
        source=candidate.resolve()
    else:
        parts=name.replace("\\", "/").split("/")
        anchors=[i for i,part in enumerate(parts) if part.casefold()=="solar-simulator"]
        if len(anchors)==1:
            candidate=Path(*parts[anchors[0]+1:])
        elif candidate.is_absolute() or PureWindowsPath(name).is_absolute() or len(anchors)>1:
            raise ValueError("Unknown project link root: "+name)
        source=(root/candidate).resolve()
    if not source.is_relative_to(root):raise ValueError("Project link escapes checkout: "+name)
    return source


def main():
    subprocess.run([sys.executable,"-X","utf8","-B","-m","pytest","-q","-p","no:cacheprovider"],check=True,cwd=ROOT)
    cargo=shutil.which("cargo") or str(Path.home()/".cargo/bin/cargo.exe")
    for crate in ("solar_core","solar_native"):
        subprocess.run([cargo,"fmt","--manifest-path",str(ROOT/f"rust/{crate}/Cargo.toml"),"--check"],check=True,cwd=ROOT)
    subprocess.run([cargo,"test","--manifest-path",str(ROOT/"rust/solar_core/Cargo.toml")],check=True,cwd=ROOT)
    check_links()


if __name__=="__main__":
    main()
