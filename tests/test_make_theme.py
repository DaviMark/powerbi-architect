"""scripts/make_theme.py. Standard library only."""
import json
import os
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
import make_theme  # noqa: E402


def run(script, *args):
    # cp1252 is the default console encoding on Windows: the script must not crash on symbols like ≥.
    env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
    return subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)], capture_output=True,
                          text=True, encoding="utf-8", env=env)


def visuals(report: Path):
    for f in sorted(report.rglob("visual.json")):
        yield f, json.loads(f.read_text(encoding="utf-8"))


class TestMakeTheme(unittest.TestCase):
    def test_brand_colour_is_darkened_until_it_passes(self):
        theme, notes = make_theme.build("#FFB800", "Brand", "Segoe UI")
        self.assertGreaterEqual(make_theme.contrast(theme["dataColors"][0]), 4.5)
        self.assertTrue(notes)
        self.assertEqual(len(theme["dataColors"]), 6)
        self.assertTrue(all(make_theme.contrast(c) >= 3 for c in theme["dataColors"]))
        self.assertNotIn("#CE2C31", theme["dataColors"])     # status colours stay out of the palette
        self.assertNotIn("#00824D", theme["dataColors"])

    def test_unsupported_font_is_refused(self):
        with self.assertRaises(ValueError):
            make_theme.build("#0F766E", "Brand", "Inter")

    def test_cli_writes_a_theme(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "t.json"
            r = run("make_theme.py", "--primary", "#0F766E", "--font", "Arial", "--out", out)
            self.assertEqual(r.returncode, 0, r.stderr)
            t = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(t["dataColors"][0], "#0F766E")
            self.assertNotIn("Segoe UI", json.dumps(t["visualStyles"]))


class TestColourBlindSafePalette(unittest.TestCase):
    def test_palettes_stay_apart_for_every_kind_of_vision(self):
        sys.path.insert(0, str(SCRIPTS))
        import make_theme as mt
        for brand in ("#3E63DD", "#0F766E", "#FFB800", "#E11D48", "#7C3AED", "#111827"):
            theme, _ = mt.build(brand, "x", "Segoe UI")
            pal = theme["dataColors"]
            self.assertEqual(len(pal), 6)
            worst = min(mt.separation(a, b) for i, a in enumerate(pal) for b in pal[i + 1:])
            self.assertGreaterEqual(worst, 8, (brand, pal))
            for c in pal[1:]:
                self.assertTrue(all(mt.separation(c, s) > 14 for s in mt.STATUS), (brand, c))

    def test_audit_flags_a_palette_that_clashes(self):
        sys.path.insert(0, str(SCRIPTS))
        import audit_pbip
        import shutil
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "proj"
            shutil.copytree(ROOT / "examples" / "contas-a-receber", p)
            theme = next((p / "ContasReceber.Report" / "StaticResources" / "RegisteredResources").glob("*.json"))
            data = json.loads(theme.read_text(encoding="utf-8"))
            self.assertNotIn("PBI065", {i["rule"] for i in audit_pbip.audit(p)})
            data["dataColors"] = ["#3E63DD", "#00826D", "#D14E00", "#8145B5", "#AD6200", "#00749E"]   # 1.x palette
            theme.write_text(json.dumps(data), encoding="utf-8")
            clashes = [i["message"] for i in audit_pbip.audit(p) if i["rule"] == "PBI065"]
            self.assertTrue(any("#D14E00 and #AD6200" in m and "protanopia" in m for m in clashes), clashes)


if __name__ == "__main__":
    unittest.main()
