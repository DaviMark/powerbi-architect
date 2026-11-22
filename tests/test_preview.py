"""scripts/preview_pbir.py on the example report. Standard library only."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "powerbi-architect" / "scripts"
EXAMPLE = ROOT / "examples" / "contas-a-receber"
REPORT = EXAMPLE / "ContasReceber.Report"
sys.path.insert(0, str(SCRIPTS))


def run(script, *args):
    return subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)], capture_output=True,
                          text=True, encoding="utf-8")


def visuals(report: Path):
    for f in sorted(report.rglob("visual.json")):
        yield f, json.loads(f.read_text(encoding="utf-8"))


class TestPreview(unittest.TestCase):
    def test_preview_with_sample_and_mobile(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "p.html"
            r = run("preview_pbir.py", REPORT, "--sample", EXAMPLE / "preview-sample.json", "--out", out)
            self.assertEqual(r.returncode, 0, r.stderr)
            html = out.read_text(encoding="utf-8")
            for text in ("Visão Geral", "Detalhe do cliente", "R$ 4,2 mi", "Sudeste", "data:image/png;base64"):
                self.assertIn(text, html)
            r = run("preview_pbir.py", REPORT, "--mobile", "--out", out)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("width:320px", out.read_text(encoding="utf-8"))

    def test_more_visual_types(self):
        sys.path.insert(0, str(SCRIPTS))
        import pbir_layout
        import shutil
        with tempfile.TemporaryDirectory() as d:
            report = Path(d) / "X.Report"
            shutil.copytree(REPORT, report)
            spec = json.loads((ROOT / "tests" / "fixtures" / "layout-more-visuals.json").read_text(encoding="utf-8"))
            pbir_layout.Builder(spec).build(report)
            out = Path(d) / "p.html"
            r = run("preview_pbir.py", report, "--sample", EXAMPLE / "preview-sample.json", "--out", out)
            self.assertEqual(r.returncode, 0, r.stderr)
            html = out.read_text(encoding="utf-8")
            for text in ("Meta: R$ 18,6 mi", "<polygon", "border-radius:50%", ">Varejo</th>", "Saldo e vencido por mês"):
                self.assertIn(text, html)

    def test_overlay_and_calibration(self):
        with tempfile.TemporaryDirectory() as d:
            shots = Path(d) / "desktop"
            shots.mkdir()
            png = (ROOT / "docs" / "assets" / "exemplo-visao-geral.png").read_bytes()
            for i in (1, 2):
                (shots / f"page-{i}.png").write_bytes(png)
            cal = Path(d) / "cal.json"
            cal.write_text('{"title_padding": "7px 13px 0"}', encoding="utf-8")
            out = Path(d) / "p.html"
            r = run("preview_pbir.py", REPORT, "--overlay", shots, "--calibration", cal, "--out", out)
            self.assertEqual(r.returncode, 0, r.stderr)
            html = out.read_text(encoding="utf-8")
            self.assertEqual(html.count('class="overlay"'), 2)
            self.assertIn('type="range"', html)
            self.assertIn("padding:7px 13px 0", html)
            cal.write_text('{"titel_padding": "0"}', encoding="utf-8")
            r = run("preview_pbir.py", REPORT, "--calibration", cal, "--out", out)
            self.assertEqual(r.returncode, 2)
            self.assertIn("unknown calibration keys", r.stderr)


if __name__ == "__main__":
    unittest.main()
