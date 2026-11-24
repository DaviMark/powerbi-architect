#!/usr/bin/env python3
"""Screenshot of a local HTML page with the installed Edge, Chrome or Chromium (headless).

    python tools/screenshot.py <page.html>[#view] <out.png> [--size 1280x1600] [--scale 2] [--dark]

Used for the README images: the benchmark page (benchmarks/painel.png) and the Power BI Explorer
(docs/assets/explorer-*.png). Python 3.9+ standard library only.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "powerbi-architect" / "scripts"))
from preview_pbir import find_browser  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("page")
    ap.add_argument("out", type=Path)
    ap.add_argument("--size", default="1280x1600")
    ap.add_argument("--scale", type=float, default=2)
    ap.add_argument("--dark", action="store_true")
    a = ap.parse_args()
    browser = find_browser()
    if not browser:
        print("needs Edge, Chrome or Chromium (or set PBIR_PREVIEW_BROWSER)")
        return 2
    path, _, view = a.page.partition("#")
    uri = Path(path).resolve().as_uri() + (f"#{view}" if view else "")
    w, h = a.size.split("x")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run", "--no-sandbox",
               f"--user-data-dir={tmp}", f"--window-size={w},{h}", f"--force-device-scale-factor={a.scale}",
               "--virtual-time-budget=3000", f"--screenshot={a.out.resolve()}", uri]
        if a.dark:
            cmd.insert(1, "--force-dark-mode")
            cmd.insert(1, "--blink-settings=preferredColorScheme=0")
        subprocess.run(cmd, capture_output=True, timeout=90, check=False)
    print(f"[ok] {a.out}" if a.out.exists() else f"! no image written for {uri}")
    return 0 if a.out.exists() else 1


if __name__ == "__main__":
    raise SystemExit(main())
