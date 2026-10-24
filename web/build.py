"""Puts the web app together in web/dist: the page, the card, the Python garden core, and (optionally) Pyodide.

    python web/build.py                       the app without Pyodide (enough for tests with the test server)
    python web/build.py --pyodide DIR         copy Pyodide files from DIR
    python web/build.py --download-pyodide    fetch Pyodide from its GitHub release
"""
import argparse
import io
import json
import shutil
import tarfile
import urllib.request
from pathlib import Path

PYODIDE = "0.27.7"
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "web"
INTEGRATION = ROOT / "custom_components" / "garden_tracker"
KEEP = ("pyodide.mjs", "pyodide.asm.js", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json", "pyodide.js")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(SRC / "dist"))
    ap.add_argument("--pyodide")
    ap.add_argument("--download-pyodide", action="store_true")
    args = ap.parse_args()
    out = Path(args.out)
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)

    version = json.loads((INTEGRATION / "manifest.json").read_text())["version"]
    for f in SRC.iterdir():
        if f.is_file() and f.name not in ("build.py",):
            shutil.copy(f, out / f.name)
    shutil.copy(INTEGRATION / "www" / "garden-card.js", out / "garden-card.js")

    core = out / "core"
    core.mkdir()
    names = sorted(p.name for p in (INTEGRATION / "core").glob("*.py"))
    for n in names:
        shutil.copy(INTEGRATION / "core" / n, core / n)
    shutil.copy(INTEGRATION / "core" / "species.json", core / "species.json")
    (core / "files.json").write_text(json.dumps(names))

    py = out / "pyodide"
    if args.pyodide:
        py.mkdir()
        for n in KEEP:
            if (Path(args.pyodide) / n).exists():
                shutil.copy(Path(args.pyodide) / n, py / n)
    elif args.download_pyodide:
        url = f"https://github.com/pyodide/pyodide/releases/download/{PYODIDE}/pyodide-{PYODIDE}.tar.bz2"
        with urllib.request.urlopen(url) as r:
            data = r.read()
        py.mkdir()
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:bz2") as t:
            for m in t.getmembers():
                if m.isfile() and Path(m.name).name in KEEP:
                    (py / Path(m.name).name).write_bytes(t.extractfile(m).read())

    sw = (out / "sw.js")
    sw.write_text(sw.read_text().replace("__VERSION__", version))
    precache = sorted(str(p.relative_to(out)) for p in out.rglob("*") if p.is_file() and p.name not in ("sw.js", "precache.json"))
    precache.append("./")
    (out / "precache.json").write_text(json.dumps(precache))
    print(f"Built {len(precache)} files for version {version} in {out}")


if __name__ == "__main__":
    main()
