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

    def test_target_line_and_bar_colours(self):
        sys.path.insert(0, str(SCRIPTS))
        import pbir_layout
        import shutil
        with tempfile.TemporaryDirectory() as d:
            report = Path(d) / "X.Report"
            shutil.copytree(REPORT, report)
            spec = {"app": "A", "measures": "_Medidas", "pages": [{"name": "P", "rows": [{"height": 248, "visuals": [
                {"type": "lineChart", "category": "dm_calendario[Ano-Mês]", "values": ["Valor Vencido"],
                 "target": "Valor Aberto", "title": "t", "alt": "t"},
                {"type": "clusteredBarChart", "category": "dm_regional[Regional]", "values": ["Valor Vencido"],
                 "colorMeasure": "Cor % Vencido", "title": "t", "alt": "t"}]}]}]}
            pbir_layout.Builder(spec).build(report, force=True)
            sample = json.loads((EXAMPLE / "preview-sample.json").read_text(encoding="utf-8"))
            sample["colors"]["Cor % Vencido"] = ["#CE2C31", "#3E63DD"]
            sp = Path(d) / "s.json"
            sp.write_text(json.dumps(sample), encoding="utf-8")
            out = Path(d) / "p.html"
            self.assertEqual(run("preview_pbir.py", report, "--sample", sp, "--out", out).returncode, 0)
            html = out.read_text(encoding="utf-8")
            self.assertIn('stroke-dasharray="4 3"', html)
            self.assertIn("background:#CE2C31", html)

    @unittest.skipUnless(__import__("preview_pbir").find_browser(), "needs Edge, Chrome or Chromium")
    def test_critique_measures_the_rendered_page(self):
        import pbir_layout
        import shutil
        clean = run("preview_pbir.py", REPORT, "--sample", EXAMPLE / "preview-sample.json", "--critique",
                    "--out", Path(tempfile.gettempdir()) / "c.html")
        self.assertEqual(clean.returncode, 0, clean.stdout)                # the example is clean
        with tempfile.TemporaryDirectory() as d:
            report = Path(d) / "X.Report"
            shutil.copytree(REPORT, report)
            spec = {"app": "A", "measures": "_Medidas", "pages": [{"name": "P", "rows": [
                {"height": 248, "split": [1, 1], "visuals": [
                    {"type": "clusteredBarChart", "category": "dm_regional[Regional]", "values": ["Valor Vencido"],
                     "title": "Um título longo demais que não cabe de jeito nenhum neste cartão, mesmo com toda a largura que ele tem", "alt": "a"},
                    {"type": "tableEx", "columns": ["dm_cliente[Cliente]", "dm_cliente[Segmento]", "Valor Vencido",
                                                    "% Vencido", "Atraso Médio (dias)", "Valor Aberto"],
                     "title": "Tabela", "alt": "t"}]},
                {"height": 248, "split": [2, 1], "visuals": [
                    {"type": "lineChart", "category": "dm_calendario[Ano-Mês]", "values": ["Valor Vencido"],
                     "title": "Linha", "alt": "l"},
                    {"type": "clusteredColumnChart", "category": "ft_titulos[Faixa Atraso]",
                     "values": ["Valor Vencido"], "title": "Colunas", "alt": "c"}]}]}]}
            pbir_layout.Builder(spec).build(report, force=True)
            r = run("preview_pbir.py", report, "--sample", EXAMPLE / "preview-sample.json", "--critique",
                    "--out", Path(d) / "c.html")
            self.assertEqual(r.returncode, 1, r.stdout)
            for kind in ("[truncated]", "[rows]", "[grid]"):
                self.assertIn(kind, r.stdout)

    def test_critique_counts_table_rows_and_honours_top_n(self):
        import pbir_layout
        import shutil
        table = {"type": "tableEx", "columns": ["dm_cliente[Cliente]", "Valor Vencido"], "title": "Clientes", "alt": "t"}
        def critique(visual, height):
            with tempfile.TemporaryDirectory() as d:
                report = Path(d) / "X.Report"
                shutil.copytree(REPORT, report)
                spec = {"app": "A", "measures": "_Medidas", "pages": [{"name": "P", "rows": [
                    {"height": height, "visuals": [visual]}]}]}
                pbir_layout.Builder(spec).build(report, force=True)
                return run("preview_pbir.py", report, "--sample", EXAMPLE / "preview-sample.json", "--critique",
                           "--out", Path(d) / "c.html")
        short = critique(table, 200)                              # 14 sample clients in a 200 px table
        self.assertEqual(short.returncode, 1, short.stdout)
        self.assertIn("[rows]", short.stdout)
        self.assertIn('"top": 5', short.stdout)
        self.assertNotIn("[clipped]", short.stdout)
        fixed = critique({**table, "top": 5, "sortBy": "Valor Vencido desc"}, 200)
        self.assertEqual(fixed.returncode, 0, fixed.stdout)
        full = critique(table, "fill")                            # a full-height list scrolls in Power BI
        self.assertNotIn("[rows]", full.stdout)

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
