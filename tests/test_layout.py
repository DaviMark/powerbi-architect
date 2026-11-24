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

    def test_target_on_bars_paints_the_ones_below_it(self):
        spec = self.spec(rows=[{"height": 248, "visuals": [
            {"type": "clusteredBarChart", "category": "dm_x[X]", "values": ["% No Prazo"], "target": "Meta % No Prazo",
             "title": "t", "alt": "a", "items": 3}]}])
        files = self.build(spec)
        bar = next(v for v in files.values() if (v.get("visual") or {}).get("visualType") == "clusteredBarChart")
        rule = bar["visual"]["objects"]["dataPoint"][0]["properties"]["fill"]["solid"]["color"]["expr"]["Conditional"]
        cmp_ = rule["Cases"][0]["Condition"]["Comparison"]
        self.assertEqual(cmp_["ComparisonKind"], 3)                       # below the target
        self.assertEqual(cmp_["Right"]["Measure"]["Property"], "Meta % No Prazo")
        self.assertEqual(rule["Cases"][0]["Value"]["Literal"]["Value"], "'#CE2C31'")
        with tempfile.TemporaryDirectory() as d:                          # --extract gives the target back
            report = Path(d) / "X.Report"
            pbir_layout.Builder(spec).build(report)
            back, _ = pbir_layout.extract(report)
            chart = [v for r in back["pages"][0]["rows"] for v in r["visuals"] if v["type"] == "clusteredBarChart"][0]
            self.assertEqual(chart.get("target"), "Meta % No Prazo")

    def test_rankings_are_shaded_by_value_and_months_are_not(self):
        spec = self.spec(rows=[{"height": 248, "split": [1, 1], "visuals": [
            {"type": "clusteredBarChart", "category": "dm_x[Regional]", "values": ["M"], "title": "a", "alt": "a"},
            {"type": "clusteredColumnChart", "category": "dm_calendario[Ano-Mês]", "values": ["M"], "title": "b",
             "alt": "b"}]}])
        files = self.build(spec)
        charts = {v["visual"]["visualType"]: v["visual"] for v in files.values()
                  if (v.get("visual") or {}).get("visualType", "").startswith("clustered")}
        fill = charts["clusteredBarChart"]["objects"]["dataPoint"][0]["properties"]["fill"]["solid"]["color"]["expr"]
        grad = fill["FillRule"]["FillRule"]["linearGradient2"]
        self.assertEqual(fill["FillRule"]["Input"]["Measure"]["Property"], "M")
        self.assertNotEqual(grad["min"]["color"]["Literal"]["Value"], grad["max"]["color"]["Literal"]["Value"])
        self.assertNotIn("dataPoint", charts["clusteredColumnChart"].get("objects") or {})

    def test_the_skills_visuals_are_placed_and_packed_into_the_report(self):
        spec = self.spec(rows=[
            {"height": 104, "visuals": [{"type": "kpiCard", "measure": "M", "label": "Receita", "trend": "dm_c[Mês]",
                                         "reference": "Meta", "higherIsBetter": False, "alt": "a"}]},
            {"height": 248, "split": [2, 1], "visuals": [
                {"type": "trend", "category": "dm_c[Mês]", "values": ["M"], "title": "Receita por mês", "alt": "b"},
                {"type": "list", "item": "dm_x[Cliente]", "status": "Situação", "values": ["M"], "title": "Clientes",
                 "sortBy": "M desc", "top": 5, "alt": "c"}]},
            {"height": 228, "split": [1, 1], "visuals": [
                {"type": "ring", "category": "dm_x[Faixa]", "values": ["M"], "title": "Por faixa", "alt": "d"},
                {"type": "ring", "measure": "M", "target": "Meta", "title": "Contra a meta", "alt": "e"}]}])
        with tempfile.TemporaryDirectory() as d:
            report = Path(d) / "X.Report"
            b = pbir_layout.Builder(spec)
            b.build(report)
            b.register_resources(report, None)
            vis = {v["visual"]["visualType"]: v["visual"] for _, v in visuals(report)}
            kpi = vis[pbir_layout.ARCHITECT["kpiCard"][1]]
            self.assertEqual(kpi["query"]["queryState"]["value"]["projections"][0]["displayName"], "Receita")
            self.assertIn("reference", kpi["query"]["queryState"])
            self.assertEqual(kpi["visualContainerObjects"]["title"][0]["properties"]["show"]["expr"]["Literal"]["Value"],
                             "false")                                  # the visual draws its own label
            lst = vis[pbir_layout.ARCHITECT["list"][1]]
            self.assertEqual(lst["objects"]["list"][0]["properties"]["title"]["expr"]["Literal"]["Value"], "'Clientes'")
            rings = [v["visual"] for _, v in visuals(report) if v["visual"]["visualType"] == pbir_layout.ARCHITECT["ring"][1]]
            self.assertEqual(sorted(sorted(r["query"]["queryState"]) for r in rings),
                             [["category", "value"], ["target", "value"]])     # slices, or progress to a target
            rj = json.loads((report / "definition" / "report.json").read_text(encoding="utf-8"))
            packs = {p["name"] for p in rj["resourcePackages"] if p["type"] == "CustomVisual"}
            self.assertEqual(packs, {g for _, g in pbir_layout.ARCHITECT.values()})
            for guid in packs:
                self.assertTrue((report / "CustomVisuals" / guid / "resources" / f"{guid}.pbiviz.json").exists())
            back, notes = pbir_layout.extract(report)                       # --extract reads them back
            types = [v["type"] for r in back["pages"][0]["rows"] for v in r["visuals"]]
            self.assertEqual(types, ["kpiCard", "trend", "list", "ring", "ring"])
            self.assertEqual(back["pages"][0]["rows"][1]["visuals"][1]["top"], 5)
            self.assertIs(back["pages"][0]["rows"][0]["visuals"][0]["higherIsBetter"], False)
        titles = {t: audit_pbip.architect_title(v, t) for t, v in vis.items()}
        self.assertIn("Receita", titles.values())
        self.assertIn("Receita por mês", titles.values())

    def test_kpi_trend_is_a_quiet_line_that_extract_reads_back(self):
        spec = self.spec(rows=[{"height": 88, "visuals": [
            {"type": "kpi", "measure": "M", "label": "M", "alt": "m", "trend": "dm_calendario[Ano-Mês]"}]}])
        files = self.build(spec)
        line = next(v for v in files.values() if (v.get("visual") or {}).get("visualType") == "lineChart")
        self.assertEqual(line["visual"]["visualContainerObjects"]["title"][0]["properties"]["show"]["expr"]
                         ["Literal"]["Value"], "false")
        with tempfile.TemporaryDirectory() as d:
            report = Path(d) / "X.Report"
            pbir_layout.Builder(spec).build(report)
            back, _ = pbir_layout.extract(report)
            kpi = back["pages"][0]["rows"][0]["visuals"][0]
            self.assertEqual(kpi.get("trend"), "dm_calendario[Ano-Mês]")
            self.assertEqual(len(back["pages"][0]["rows"][0]["visuals"]), 1)

    def test_a_bar_row_much_taller_than_its_bars_is_noted(self):
        b = pbir_layout.Builder(self.spec(rows=[{"height": 400, "visuals": [
            {"type": "clusteredBarChart", "category": "dm_x[X]", "values": ["M"], "title": "Barras", "alt": "a", "items": 5}]}]))
        b.build(Path(tempfile.mkdtemp()) / "X.Report", write=False)
        self.assertTrue(any("5 bars in 400 px" in n for n in b.notes), b.notes)

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

    def test_target_line_colour_by_measure_and_auto_heights(self):
        spec = {"app": "A", "measures": "_Medidas", "pages": [{"name": "P", "rows": [
            {"height": 88, "visuals": [{"type": "kpi", "measure": "M", "label": "M"}]},
            {"height": "fill", "split": [3, 2], "visuals": [
                {"type": "lineChart", "category": "dm_calendario[Ano-Mês]", "values": ["M"], "target": "Meta",
                 "title": "M por mês", "alt": "m"},
                {"type": "clusteredBarChart", "category": "dm_x[X]", "values": ["M"], "colorMeasure": "Cor M",
                 "title": "M por X", "alt": "m", "items": 6}]},
            {"height": "auto", "visuals": [{"type": "clusteredBarChart", "category": "dm_y[Y]", "values": ["M"],
                                            "title": "M por Y", "alt": "m", "items": 5}]}]}]}
        files = self.build(spec)
        vis = {v["visual"]["visualType"] + str(v["position"]["y"]): v for k, v in files.items() if k.endswith("visual.json")}
        line = next(v for k, v in vis.items() if k.startswith("lineChart"))
        self.assertEqual([p["field"]["Measure"]["Property"] for p in line["visual"]["query"]["queryState"]["Y"]["projections"]],
                         ["M", "Meta"])
        style = line["visual"]["objects"]["lineStyles"][0]
        self.assertEqual((style["selector"]["metadata"], style["properties"]["lineStyle"]["expr"]["Literal"]["Value"]),
                         ("_Medidas.Meta", "'dashed'"))
        bars = sorted((v for k, v in vis.items() if k.startswith("clusteredBarChart")), key=lambda v: v["position"]["y"])
        fill = bars[0]["visual"]["objects"]["dataPoint"][0]
        self.assertEqual(fill["properties"]["fill"]["solid"]["color"]["expr"]["Measure"]["Property"], "Cor M")
        self.assertEqual(fill["selector"]["data"][0]["dataViewWildcard"]["matchingOption"], 1)
        self.assertEqual(bars[1]["position"]["height"], 52 + 32 * 5)                         # auto
        self.assertEqual(bars[0]["position"]["height"], 616 - 88 - 212 - 32)                # fill takes the rest
        with self.assertRaises(pbir_layout.SpecError):
            self.build(self.spec(rows=[{"height": 248, "visuals": [
                {"type": "waterfallChart", "category": "a[b]", "values": ["M"], "target": "T", "title": "t", "alt": "t"}]}]))

    def test_table_top_n_filter(self):
        table = {"type": "tableEx", "columns": ["dm_cliente[Cliente]", "Valor Vencido"], "sortBy": "Valor Vencido desc",
                 "top": 5, "title": "Os 5 clientes com mais valor vencido", "alt": "t"}
        files = self.build(self.spec(rows=[{"height": "auto", "visuals": [table]}]))
        c = next(v for k, v in files.items() if k.endswith("visual.json") and v["visual"]["visualType"] == "tableEx")
        flt = c["filterConfig"]["filters"][0]
        self.assertEqual(flt["type"], "TopN")
        self.assertEqual(flt["field"]["Column"]["Property"], "Cliente")
        q = flt["filter"]["From"][0]["Expression"]["Subquery"]["Query"]
        self.assertEqual((q["Top"], q["OrderBy"][0]["Direction"]), (5, 2))
        self.assertEqual(q["OrderBy"][0]["Expression"]["Measure"]["Property"], "Valor Vencido")
        self.assertEqual(c["position"]["height"], 64 + 28 * 5)          # the auto row fits the five rows
        self.assertNotIn("_filterConfig", c["visual"])
        for bad in ({**table, "sortBy": None}, {**table, "top": 0}, {**table, "top": "5"},
                    {**table, "columns": ["Valor Vencido", "dm_cliente[Cliente]"]}):
            with self.subTest(bad=bad), self.assertRaises(pbir_layout.SpecError):
                self.build(self.spec(rows=[{"height": 200, "visuals": [bad]}]))

    def test_short_table_without_top_gets_a_note(self):
        table = {"type": "tableEx", "columns": ["dm_cliente[Cliente]", "Valor Vencido"], "title": "Clientes", "alt": "t"}
        b = pbir_layout.Builder(self.spec(rows=[{"height": 200, "visuals": [table]}]))
        with tempfile.TemporaryDirectory() as d:
            b.build(Path(d) / "X.Report")
        self.assertEqual(len(b.notes), 1)
        self.assertIn('"top": 4', b.notes[0])
        b = pbir_layout.Builder(self.spec(rows=[{"height": 200, "visuals": [{**table, "top": 4,
                                                                             "sortBy": "Valor Vencido desc"}]}]))
        with tempfile.TemporaryDirectory() as d:
            b.build(Path(d) / "X.Report")
        self.assertEqual(b.notes, [])

    def test_table_top_n_survives_extract(self):
        table = {"type": "tableEx", "columns": ["dm_cliente[Cliente]", "Valor Vencido"], "sortBy": "Valor Vencido desc",
                 "top": 5, "title": "Os 5 clientes", "alt": "t"}
        with tempfile.TemporaryDirectory() as d:
            report = Path(d) / "X.Report"
            pbir_layout.Builder(self.spec(rows=[{"height": 200, "visuals": [table]}])).build(report)
            spec = pbir_layout.Extractor(report).run()
        got = [v for p in spec["pages"] for r in p["rows"] for v in r["visuals"] if v["type"] == "tableEx"][0]
        self.assertEqual((got["top"], got["sortBy"]), (5, "Valor Vencido desc"))

    def test_gallery_builds_on_the_example_model(self):
        spec = json.loads((ROOT / "docs" / "galeria" / "layout.json").read_text(encoding="utf-8"))
        types = {v["visual"]["visualType"] for k, v in self.build(spec).items() if k.endswith("visual.json")}
        for t in ("card", "kpi", "lineChart", "lineClusteredColumnComboChart", "clusteredBarChart",
                  "clusteredColumnChart", "waterfallChart", "scatterChart", "tableEx", "pivotTable"):
            self.assertIn(t, types)

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
            page.pop("id", None)
            for row in page.get("rows", []):
                if len(set(row.get("split", [0]))) == 1:
                    row.pop("split", None)
                for v in row["visuals"]:
                    for k in ("key", "id", "varId"):
                        v.pop(k, None)
            for v in page.get("visuals", []):
                for k in ("key", "id", "varId"):
                    v.pop(k, None)
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

    def test_extract_then_rebuild_lands_on_the_same_files(self):
        """E14: extracting a report the user edited and rebuilding it must not copy their visuals."""
        with tempfile.TemporaryDirectory() as d:
            report = Path(d) / "proj" / "ContasReceber.Report"
            shutil.copytree(EXAMPLE, report.parent)
            page = next(p for p in (report / "definition" / "pages").iterdir() if p.is_dir() and json.loads(
                (p / "page.json").read_text(encoding="utf-8"))["displayName"] == "Clientes")
            mine = page / "visuals" / "meuvisual0000000000a"
            mine.mkdir()
            (mine / "visual.json").write_text(json.dumps({
                "name": "meuvisual0000000000a", "position": {"x": 232, "y": 80, "width": 400, "height": 248},
                "visual": {"visualType": "clusteredBarChart", "query": {"queryState": {
                    "Category": {"projections": [{"field": {"Column": {"Expression": {"SourceRef": {"Entity": "dm_cliente"}},
                                                                       "Property": "Segmento"}}}]},
                    "Y": {"projections": [{"field": {"Measure": {"Expression": {"SourceRef": {"Entity": "_Medidas"}},
                                                                 "Property": "Valor Vencido"}}}]}}},
                    "visualContainerObjects": {"title": [{"properties": {"text": {"expr": {"Literal": {"Value": "'Meu'"}}}}}],
                                               "general": [{"properties": {"altText": {"expr": {"Literal": {"Value": "'m'"}}}}}]}}}),
                encoding="utf-8")
            before = sorted(p.relative_to(report).as_posix() for p in report.rglob("visual.json"))
            spec, _ = pbir_layout.extract(report)
            b = pbir_layout.Builder(spec)
            b.build(report)
            after = sorted(p.relative_to(report).as_posix() for p in report.rglob("visual.json"))
            self.assertEqual(before, after)                       # no copies, nothing lost

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
