"""Render the component gallery (docs/galeria) from the example model. Run from the repository root:

    python tools/generate_gallery.py

Builds docs/galeria/layout.json into a temporary copy of the example report, then renders each page with
scripts/preview_pbir.py at 2x into docs/assets/galeria-*.png (needs Edge, Chrome or Chromium).
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "powerbi-architect" / "scripts"))
import pbir_layout  # noqa: E402
from preview_pbir import Preview, find_browser  # noqa: E402

EXAMPLE = ROOT / "examples" / "contas-a-receber"
SAMPLE_COLOURS = {"Cor % Vencido": ["#CE2C31", "#CE2C31", "#3E63DD", "#3E63DD", "#3E63DD"]}
SAMPLE_SERIES = {"% Vencido": [18.1, 19.4, 17.2, 20.8, 21.5, 19.9, 22.3, 23.1, 21.7, 22.9, 23.4, 22.6],
                 "Meta % Vencido": [15] * 12,
                 "Valor Aberto": [16.1, 16.4, 16.2, 16.9, 17.1, 17.4, 17.2, 17.8, 18.0, 18.3, 18.1, 18.6],
                 "Atraso Médio (dias)": [33, 35, 34, 36, 38, 37, 39, 41, 40, 42, 41, 41]}
SAMPLE_MEASURES = {"Meta % Vencido": "15%"}

with tempfile.TemporaryDirectory() as tmp:
    report = Path(tmp) / "Galeria.Report"
    shutil.copytree(EXAMPLE / "ContasReceber.Report", report)
    spec = json.loads((ROOT / "docs" / "galeria" / "layout.json").read_text(encoding="utf-8"))
    b = pbir_layout.Builder(spec)
    b.build(report, force=True)
    b.register_resources(report, None)
    sample = json.loads((EXAMPLE / "preview-sample.json").read_text(encoding="utf-8"))
    sample["colors"].update(SAMPLE_COLOURS)
    sample["series"].update(SAMPLE_SERIES)
    sample["measures"].update(SAMPLE_MEASURES)
    browser = find_browser()
    for i, (_title, w, h, body) in enumerate(Preview(report, sample).pages()):
        page = Path(tmp) / "page.html"
        page.write_text(Preview.document(body, margin=0), encoding="utf-8")
        out = ROOT / "docs" / "assets" / f"galeria-{i + 1}.png"
        subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-sandbox",
                        "--force-device-scale-factor=2", f"--user-data-dir={Path(tmp) / 'profile'}",
                        f"--window-size={w},{h}", f"--screenshot={out}", page.as_uri()],
                       capture_output=True, timeout=120, check=False)
        print(out.relative_to(ROOT), out.exists())
