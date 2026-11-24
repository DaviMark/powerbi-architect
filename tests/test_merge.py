"""Edits made by hand (in Desktop or in the files) survive a rebuild with pbir_layout.py."""
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
sys.path.insert(0, str(SCRIPTS))
import pbir_layout  # noqa: E402


def visuals(report: Path) -> dict:
    """{(page name, visual type, title or first field): (path, json)} for every visual."""
    out = {}
    for f in sorted(report.rglob("visual.json")):
        v = json.loads(f.read_text(encoding="utf-8"))
        page = json.loads((f.parents[2] / "page.json").read_text(encoding="utf-8"))["displayName"]
        vis = v["visual"]
        title = pbir_layout._lit(pbir_layout._prop(vis.get("visualContainerObjects") or {}, "title", "text"))
        out[(page, vis["visualType"], title or f.parent.name)] = (f, v)
    return out


def save(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=4), encoding="utf-8")      # Desktop formats files its own way


class TestManualEditsSurvive(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.proj = Path(self.tmp.name) / "proj"
        shutil.copytree(EXAMPLE, self.proj)
        self.report = self.proj / "ContasReceber.Report"
        self.spec = json.loads((EXAMPLE / "layout.json").read_text(encoding="utf-8"))

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, spec, force=False):
        b = pbir_layout.Builder(spec)
        b.build(self.report, force=force)
        b.register_resources(self.report, None)
        return b.merge

    def test_edits_by_hand_and_spec_changes_both_land(self):
        v = visuals(self.report)
        bar_path, bar = v[("Diagnóstico", "clusteredBarChart", "Vencido por segmento")]
        bar["position"]["x"] += 8                                   # moved in Desktop
        bar["visual"]["visualContainerObjects"]["title"][0]["properties"]["text"] = \
            {"expr": {"Literal": {"Value": "'Vencido por segmento (R$)'"}}}
        save(bar_path, bar)
        table_path, _ = v[("Diagnóstico", "tableEx", "Regionais acima da meta de vencido")]
        shutil.rmtree(table_path.parent)                            # deleted in Desktop
        mine = table_path.parents[1] / "meuvisual00000000000"
        mine.mkdir()
        (mine / "visual.json").write_text('{"name": "meuvisual00000000000", "position": {"x": 240, "y": 90, '
                                          '"z": 0, "width": 200, "height": 100}, "visual": {"visualType": "card"}}',
                                          encoding="utf-8")         # added in Desktop
        pages = self.report / "definition" / "pages" / "pages.json"
        order = json.loads(pages.read_text(encoding="utf-8"))
        order["pageOrder"].insert(0, order["pageOrder"].pop(2))     # pages reordered in Desktop
        save(pages, order)
        col_path, col = v[("Tooltip regional", "clusteredColumnChart", "Vencido por faixa nesta regional")]
        save(col_path, col)                                         # untouched, only reformatted

        spec = json.loads(json.dumps(self.spec))
        tip = next(p for p in spec["pages"] if p["name"] == "Tooltip regional")
        tip["visuals"][0]["title"] = "Vencido por faixa"                   # spec changes another visual
        diag = next(p for p in spec["pages"] if p["name"] == "Diagnóstico")
        diag["rows"][1]["visuals"][1]["sort"] = "asc"                      # and the visual the user moved
        spec["pages"].insert(3, {"name": "Nova", "icon": "chart-bar", "rows": [{"height": 88, "visuals": [
            {"type": "kpi", "measure": "Valor Aberto", "label": "Saldo"}]}]})
        m = self.build(spec)

        after = visuals(self.report)
        moved = after[("Diagnóstico", "clusteredBarChart", "Vencido por segmento (R$)")][1]
        self.assertEqual(moved["position"]["x"], bar["position"]["x"])              # your move kept
        self.assertEqual(moved["visual"]["query"]["sortDefinition"]["sort"][0]["direction"], "Ascending")
        self.assertIn(("Tooltip regional", "clusteredColumnChart", "Vencido por faixa"), after)   # spec applied
        self.assertNotIn(("Diagnóstico", "tableEx", "Regionais acima da meta de vencido"), after)
        self.assertTrue((mine / "visual.json").exists())
        new_order = json.loads(pages.read_text(encoding="utf-8"))["pageOrder"]
        self.assertEqual(new_order[:-1], [p for p in order["pageOrder"]])         # your order kept
        self.assertEqual(new_order[-1], pbir_layout.hid("page", "Nova"))           # new page appended
        self.assertTrue(m.merged and m.deleted_by_you)
        text = "\n".join(m.lines(self.report))
        self.assertIn("Vencido por segmento (R$)", text)

    def test_conflict_keeps_your_value_and_force_restores_the_spec(self):
        v = visuals(self.report)
        path, line = next(pv for k, pv in v.items() if k[0] == "Visão Geral" and k[1].startswith("architectTrend"))
        line["position"]["height"] = 300
        save(path, line)
        spec = json.loads(json.dumps(self.spec))
        spec["pages"][0]["rows"][1]["height"] = 248                 # spec also changes that height
        spec["pages"][0]["rows"][2]["height"] = 232
        m = self.build(spec)
        rel = path.relative_to(self.report).as_posix()
        self.assertIn("position.height", m.conflicts[rel])
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["position"]["height"], 300)
        self.build(spec, force=True)
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["position"]["height"], 248)

    def test_untouched_report_rebuilds_byte_for_byte(self):
        for f in self.report.rglob("*.json"):            # a Windows checkout (core.autocrlf) uses CRLF
            f.write_bytes(f.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        before = {p: p.read_bytes() for p in self.report.rglob("*.json")}
        m = self.build(self.spec)
        self.assertEqual((m.written, m.kept, m.merged, m.removed), ([], [], [], []))
        self.assertEqual(before, {p: p.read_bytes() for p in self.report.rglob("*.json")})

    def test_cli_reports_kept_edits(self):
        v = visuals(self.report)
        path, data = next(iter(v.values()))
        data["position"]["x"] += 4
        save(path, data)
        r = subprocess.run([sys.executable, str(SCRIPTS / "pbir_layout.py"), str(EXAMPLE / "layout.json"),
                            str(self.report)], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("with your edits kept", r.stdout)
        self.assertIn("kept your version", r.stdout)


if __name__ == "__main__":
    unittest.main()
