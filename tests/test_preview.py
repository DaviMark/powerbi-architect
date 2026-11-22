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


if __name__ == "__main__":
    unittest.main()
