from pathlib import Path
import hashlib
import tarfile
import shutil
import sys

BASE = Path(__file__).resolve().parent
PARTS = sorted(BASE.glob("jdtls.part[0-9]*"))
MANIFEST = BASE / "SHA256SUMS"
ARCHIVE = BASE / "jdtls.tar.gz"
TARGET = BASE / "runtime"

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def main():
    if not PARTS or not MANIFEST.is_file():
        sys.exit("Missing parts or SHA256SUMS. Run the GitHub workflow first.")
    expected = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        sha, name = line.split(maxsplit=1)
        expected[name.lstrip("*")] = sha.lower()
    for p in PARTS:
        if digest(p) != expected.get(p.name):
            sys.exit(f"Checksum mismatch: {p.name}")
    with ARCHIVE.open("wb") as out:
        for p in PARTS:
            print("Joining", p.name)
            with p.open("rb") as inp:
                shutil.copyfileobj(inp, out, 1024 * 1024)
    if digest(ARCHIVE) != expected.get(ARCHIVE.name):
        sys.exit("Archive checksum mismatch")
    TARGET.mkdir(exist_ok=True)
    with tarfile.open(ARCHIVE, "r:gz") as tf:
        tf.extractall(TARGET, filter="data")
    print("Installed to", TARGET)
    print("Add this folder to PATH:", TARGET / "bin")
    print("Set JAVA_HOME to JDK 21 or newer, then restart OpenIDEA.")

if __name__ == "__main__":
    main()
