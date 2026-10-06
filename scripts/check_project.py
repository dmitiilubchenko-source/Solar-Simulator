"""One repeatable command for Python tests, Rust tests and documentation links."""
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def check_links():
    count=0
    for path in (ROOT/"docs").glob("*.md"):
        for name,line in re.findall(r"\]\(([^)]+):([0-9]+)\)",path.read_text(encoding="utf-8")):
            relative=Path(name).relative_to(ROOT)
            source=ROOT/relative
            if not source.is_file() or not 1<=int(line)<=len(source.read_text(encoding="utf-8").splitlines()):
                raise ValueError(f"Invalid link: {path.name}: {name}:{line}")
            count+=1
    print(f"Documentation file/line links valid: {count}")


def main():
    subprocess.run([sys.executable,"-B","-m","pytest","-q","-p","no:cacheprovider"],check=True,cwd=ROOT)
    cargo=shutil.which("cargo") or str(Path.home()/".cargo/bin/cargo.exe")
    for crate in ("solar_core","solar_native"):
        subprocess.run([cargo,"fmt","--manifest-path",str(ROOT/f"rust/{crate}/Cargo.toml"),"--check"],check=True,cwd=ROOT)
    subprocess.run([cargo,"test","--manifest-path",str(ROOT/"rust/solar_core/Cargo.toml")],check=True,cwd=ROOT)
    check_links()


if __name__=="__main__":
    main()
