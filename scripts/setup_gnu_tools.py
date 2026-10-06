"""Fetch GNU build tools from official MSYS2 packages into ignored .tools.

Only executables/DLLs and licenses are unpacked. SHA256 is checked against
package metadata; installed versions and hashes are recorded locally.
"""
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import tarfile
from urllib.request import urlopen

PACKAGES = ["binutils", "gettext-runtime", "libwinpthread", "zlib", "zstd", "libiconv"]


def main():
    if sys.version_info < (3,14):
        raise SystemExit("This optional GNU bootstrap uses Python 3.14 tar.zst support; otherwise use installed GNU tools or MSVC")
    root = Path(__file__).resolve().parents[1] / ".tools/msys2"
    records = []
    for name in PACKAGES:
        package = "mingw-w64-x86_64-" + name
        with urlopen("https://packages.msys2.org/packages/" + package, timeout=60) as response:
            html = response.read().decode()
        url = re.search(r'https://mirror.msys2.org/mingw/mingw64/[^"<> ]+\.pkg\.tar\.zst', html).group()
        expected = re.search(r'SHA256:.*?([0-9a-f]{64})', html, re.S).group(1)
        with urlopen(url, timeout=60) as response:
            data = response.read()
        actual = hashlib.sha256(data).hexdigest()
        if actual != expected:
            raise RuntimeError("SHA256 mismatch: " + package)
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:zst") as archive:
            for member in archive:
                parts = Path(member.name).parts
                if not member.isfile() or ".." in parts or not parts or parts[0] != "mingw64":
                    continue
                if not (member.name.startswith("mingw64/bin/") or member.name.startswith("mingw64/share/licenses/")):
                    continue
                path = root.joinpath(*parts)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(archive.extractfile(member).read())
        records.append(dict(package=package, url=url, sha256=actual))
        print("Installed: " + package, flush=True)
    (root / "packages.json").write_text(json.dumps(records, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
