"""Build/install the release PyO3 module into the current virtual environment."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", action="store_true", help="Build wheel into .tools/wheels instead of installing")
    args = parser.parse_args()
    if sys.prefix == sys.base_prefix:
        raise SystemExit("Run this script with the project's .venv Python")
    root = Path(__file__).resolve().parents[1]
    cargo = shutil.which("cargo") or str(Path.home() / ".cargo/bin/cargo.exe")
    if not Path(cargo).is_file():
        raise SystemExit("Rust/Cargo is required; install rustup first")
    env = os.environ.copy()
    env["PATH"] = str(Path(cargo).parent) + os.pathsep + env.get("PATH", "")
    # GNU Rust bundles dlltool; expose it only to this build process.
    rustc = Path(cargo).with_name("rustc.exe" if os.name == "nt" else "rustc")
    sysroot = Path(subprocess.check_output([str(rustc), "--print", "sysroot"], text=True).strip())
    version = subprocess.check_output([str(rustc), "-vV"], text=True)
    host = next(line.split(": ", 1)[1] for line in version.splitlines() if line.startswith("host: "))
    tools = sysroot / "lib/rustlib" / host / "bin/self-contained"
    if tools.is_dir():
        env["PATH"] = str(tools) + os.pathsep + env["PATH"]
    local_tools = root / ".tools/msys2/mingw64/bin"
    if local_tools.is_dir():
        env["PATH"] = str(local_tools) + os.pathsep + env["PATH"]
    env["VIRTUAL_ENV"] = sys.prefix
    env["PYO3_PYTHON"] = sys.executable
    command = [sys.executable, "-m", "maturin", "build" if args.wheel else "develop", "--release",
               "--manifest-path", str(root / "rust/solar_native/Cargo.toml")]
    if args.wheel:
        command += ["--interpreter", sys.executable, "--out", str(root / ".tools/wheels")]
    subprocess.run(command, env=env, check=True, cwd=root)


if __name__ == "__main__":
    main()
