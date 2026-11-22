"""scripts/pbir_layout.py on the example report. Standard library only."""
import json
import shutil
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
import pbir_layout  # noqa: E402
import audit_pbip  # noqa: E402
sys.path.insert(0, str(ROOT / "tests"))
from legacy_report import make_legacy  # noqa: E402


def run(script, *args):
    return subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)], capture_output=True,
                          text=True, encoding="utf-8")


def visuals(report: Path):
    for f in sorted(report.rglob("visual.json")):
        yield f, json.loads(f.read_text(encoding="utf-8"))


class TestLayoutEngine(unittest.TestCase):
    def spec(self, **page):
        base = {"name": "P", "rows": [{"height": 88, "visuals": [
            {"type": "kpi", "measure": "M", "label": "M", "alt": "m"}]}]}
        base.update(page)
        return {"app": "A", "measures": "_Medidas", "pages": [base]}

    def build(self, spec):
        with tempfile.TemporaryDirectory() as d:
            report = Path(d) / "X.Report"
            pbir_layout.Builder(spec).build(report)
            return {f.relative_to(report).as_posix(): json.loads(f.read_text(encoding="utf-8"))
                    for f in report.rglob("*.json")}

    def test_every_position_is_on_the_grid_and_inside_the_page(self):
        for f, v in visuals(REPORT):
            pos = v["position"]
            page = json.loads((f.parents[2] / "page.json").read_text(encoding="utf-8"))
            for key in ("x", "y", "width", "height"):
                if pos[key] > 2:
                    self.assertEqual(pos[key] % 4, 0, f"{f}: {key}={pos[key]}")
            self.assertLessEqual(pos["x"] + pos["width"], page["width"], f)
            self.assertLessEqual(pos["y"] + pos["height"], page["height"], f)

    def test_rows_that_do_not_fit_are_refused(self):
        spec = self.spec(rows=[{"height": 400, "visuals": [{"type": "card", "measure": "M", "title": "M", "alt": "m"}]},
                               {"height": 400, "visuals": [{"type": "card", "measure": "N", "title": "N", "alt": "n"}]}])
        with self.assertRaises(pbir_layout.SpecError):
            self.build(spec)

    def test_spec_errors(self):
        for bad in ({"rows": [{"height": 90, "visuals": [{"type": "kpi", "measure": "M", "label": "M"}]}]},
                    {"rows": [{"height": 88, "visuals": [{"type": "pie", "alt": "x"}]}]},
                    {"slicers": ["a[b]", "a[c]", "a[d]"]},
                    {"rows": [{"height": 88, "visuals": [{"type": "card", "measure": "M"}]}]}):
            with self.assertRaises((pbir_layout.SpecError, KeyError), msg=str(bad)):
                self.build(self.spec(**bad))

    def test_widths_split_the_content_area_exactly(self):
        for weights in ([1, 1, 1, 1], [2, 1], [1, 1], [3, 2]):
            sizes = pbir_layout.Builder.split(1024, weights)
            self.assertEqual(sum(sizes) + 16 * (len(weights) - 1), 1024)
            self.assertTrue(all(s % 4 == 0 for s in sizes), sizes)

    def test_drillthrough_tooltip_and_mobile(self):
        pages = {json.loads((p / "page.json").read_text(encoding="utf-8"))["displayName"]: p
                 for p in (REPORT / "definition" / "pages").iterdir() if p.is_dir()}
        drill = json.loads((pages["Detalhe do cliente"] / "page.json").read_text(encoding="utf-8"))
        self.assertEqual(drill["pageBinding"]["type"], "Drillthrough")
        self.assertEqual(drill["visibility"], "HiddenInViewMode")
        self.assertEqual(drill["pageBinding"]["parameters"][0]["boundFilter"], drill["filterConfig"]["filters"][0]["name"])
        tip = json.loads((pages["Tooltip regional"] / "page.json").read_text(encoding="utf-8"))
        self.assertEqual((tip["width"], tip["height"], tip["pageBinding"]["type"]), (320, 240, "Tooltip"))
        mobile = list(pages["Visão Geral"].rglob("mobile.json"))
        self.assertGreaterEqual(len(mobile), 8)
        for m in mobile:
            pos = json.loads(m.read_text(encoding="utf-8"))["position"]
            self.assertLessEqual(pos["x"] + pos["width"], 320)

    def test_kpi_variation_line_uses_a_colour_measure(self):
        found = [v for _, v in visuals(REPORT) if v["visual"].get("objects", {}).get("labels")
                 and "Measure" in json.dumps(v["visual"]["objects"]["labels"])]
        self.assertTrue(found, "KPI variation lines should take their colour from a measure")

    def test_icons_are_registered(self):
        rj = json.loads((REPORT / "definition" / "report.json").read_text(encoding="utf-8"))
        items = [i for p in rj["resourcePackages"] for i in p["items"] if i["type"] == "Image"]
        self.assertGreaterEqual(len(items), 4)
        for i in items:
            self.assertTrue((REPORT / "StaticResources" / "RegisteredResources" / i["path"]).exists())

    def test_matrix_combo_scatter_and_kpi_trend(self):
        spec = json.loads((ROOT / "tests" / "fixtures" / "layout-more-visuals.json").read_text(encoding="utf-8"))
        files = self.build(spec)
        by_type, roles = {}, {}
        for k, v in files.items():
            if k.endswith("visual.json"):
                t = v["visual"]["visualType"]
                by_type[t] = v["visual"]
                roles.setdefault(t, set()).update(v["visual"].get("query", {}).get("queryState", {}))
        self.assertEqual(roles["pivotTable"], {"Rows", "Columns", "Values"})
        self.assertEqual(roles["lineClusteredColumnComboChart"], {"Category", "Y", "Y2"})
        self.assertEqual(roles["scatterChart"], {"Category", "X", "Y"})
        self.assertEqual(roles["kpi"], {"Indicator", "TrendLine", "Goal"})
        for t in ("pivotTable", "lineClusteredColumnComboChart", "scatterChart", "kpi"):
            self.assertIn("altText", json.dumps(by_type[t]["visualContainerObjects"]["general"]), t)

    def test_check_mode_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            r = run("pbir_layout.py", EXAMPLE / "layout.json", Path(d) / "Y.Report", "--check")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse((Path(d) / "Y.Report").exists())


class TestExtract(unittest.TestCase):
    @staticmethod
    def normalised(spec):
        spec = json.loads(json.dumps(spec))
        for page in spec["pages"]:
            for row in page.get("rows", []):
                if len(set(row.get("split", [0]))) == 1:
                    row.pop("split", None)
                for v in row["visuals"]:
                    v.pop("key", None)
            for v in page.get("visuals", []):
                v.pop("key", None)
        return spec

    def test_round_trip_on_the_example(self):
        """Extracting the example gives back the spec it was built from."""
        spec, notes = pbir_layout.extract(REPORT)
        self.assertEqual(notes, [])
        original = json.loads((EXAMPLE / "layout.json").read_text(encoding="utf-8"))
        self.assertEqual(self.normalised(spec), self.normalised(original))

    def test_restyle_a_legacy_report(self):
        with tempfile.TemporaryDirectory() as d:
            proj = Path(d) / "proj"
            shutil.copytree(EXAMPLE / "ContasReceber.SemanticModel", proj / "ContasReceber.SemanticModel")
            report = make_legacy(REPORT, proj / "ContasReceber.Report")
            before = audit_pbip.harmony(proj, audit_pbip.audit(proj))
            spec, notes = pbir_layout.extract(report)
            self.assertTrue(any("pieChart became a bar chart" in n for n in notes), notes)
            self.assertTrue(any("no alt text" in n for n in notes), notes)
            rows = spec["pages"][0]["rows"]
            self.assertEqual([len(r["visuals"]) for r in rows], [4, 2, 1])
            self.assertEqual(spec["slicers"], ["dm_cliente[Segmento]"])
            b = pbir_layout.Builder(spec)
            b.build(report)
            b.register_resources(report, None)
            after = audit_pbip.harmony(proj, audit_pbip.audit(proj))
            self.assertLess(before[0][2], 60, before)
            self.assertGreaterEqual(after[0][2], 90, after)

    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "layout.json"
            r = run("pbir_layout.py", "--extract", REPORT, "--out", out)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("6 page(s) extracted", r.stderr)
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["app"], "Contas a receber")
            self.assertEqual(run("pbir_layout.py").returncode, 2)


if __name__ == "__main__":
    unittest.main()
