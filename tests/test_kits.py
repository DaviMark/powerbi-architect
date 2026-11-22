"""scripts/new_project.py and the starter kits: every kit must come out clean. Standard library only."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "powerbi-architect" / "scripts"
KITS = sorted(p.stem for p in (ROOT / "skills" / "powerbi-architect" / "templates" / "starter-kits").glob("*.json"))
sys.path.insert(0, str(SCRIPTS))
import audit_pbip  # noqa: E402


def run(script, *args):
    return subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)], capture_output=True,
                          text=True, encoding="utf-8")


class TestKits(unittest.TestCase):
    def test_the_four_kits_are_listed(self):
        self.assertEqual(KITS, ["estoque", "financeiro", "rh", "vendas"])
        out = run("new_project.py", "--list").stdout
        for kit in KITS:
            self.assertIn(kit, out)

    def test_every_kit_generates_a_clean_project(self):
        for kit in KITS:
            with self.subTest(kit=kit), tempfile.TemporaryDirectory() as d:
                out = Path(d) / kit
                r = run("new_project.py", kit, out)
                self.assertEqual(r.returncode, 0, r.stderr)
                issues = audit_pbip.audit(out)
                self.assertEqual([(i["rule"], i["message"]) for i in issues], [])
                scores = audit_pbip.harmony(out, issues)
                self.assertTrue(scores and all(s == 100 for _, _, s in scores), scores)
                tables = [p.stem for p in out.rglob("tables/*.tmdl")]
                self.assertTrue(all(t.startswith(("ft_", "dm_", "_")) for t in tables), tables)
                self.assertTrue(any(t.startswith("ft_") for t in tables), tables)
                g = run("pbi_graph.py", "build", out)
                self.assertEqual(g.returncode, 0, g.stderr)
                report = (out / "powerbi-graph" / "GRAPH_REPORT.md").read_text(encoding="utf-8")
                self.assertIn("none", report.split("## Findings", 1)[1].split("##", 1)[0])
                sample = json.loads((out / "preview-sample.json").read_text(encoding="utf-8"))
                self.assertIn("Texto Atualizacao", sample["measures"])
                p = run("preview_pbir.py", next(out.glob("*.Report")), "--sample", out / "preview-sample.json",
                        "--out", Path(d) / "p.html")
                self.assertEqual(p.returncode, 0, p.stderr)

    def test_brand_colour_and_refusals(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "v"
            r = run("new_project.py", "vendas", out, "--primary", "#F5A623", "--name", "Comercial")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue((out / "Comercial.pbip").exists())
            theme = json.loads((out / "theme.json").read_text(encoding="utf-8"))
            self.assertNotEqual(theme["dataColors"][0], "#F5A623")         # darkened for contrast
            self.assertEqual(run("new_project.py", "vendas", out).returncode, 2)   # folder not empty
            self.assertEqual(run("new_project.py", "marketing", Path(d) / "m").returncode, 2)


if __name__ == "__main__":
    unittest.main()
