"""benchmarks/run.py: the scenarios load, their starting projects are sound, and the checks catch what they
claim to catch. Standard library only (schema checks run only when jsonschema is installed)."""
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("bench_run", ROOT / "benchmarks" / "run.py")
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)

BY_ID = {s["id"]: s for s in bench.scenarios()}


class TestScenarios(unittest.TestCase):
    def test_two_scenarios_with_their_inputs(self):
        self.assertEqual(sorted(BY_ID), ["s1-logistica", "s2-reestilizar"])
        for s in BY_ID.values():
            with self.subTest(s["id"]):
                for key in ("id", "nome", "tipo", "projeto", "pedido", "paginas"):
                    self.assertIn(key, s)
                self.assertIn(s["tipo"], ("relatorio", "reestilizar"))
                if s["tipo"] == "relatorio":
                    self.assertTrue((ROOT / s["modelo"]).exists(), s["modelo"])

    def test_every_requirement_has_a_name_and_a_description(self):
        ids = [k for k, _, _ in bench.REQUIREMENTS]
        self.assertEqual(ids, ["abre", "bloqueadores", "harmonia", "acessivel", "pixel", "pedido", "numeros"])
        for _, name, text in bench.REQUIREMENTS:
            self.assertTrue(name and text)

    def test_every_measured_version_keeps_its_deliveries(self):
        """`score --versao` re-checks earlier versions from the archive: it must be complete."""
        for res in sorted((ROOT / "benchmarks" / "versoes").glob("*/resultados.json")):
            d = res.parent
            with self.subTest(d.name):
                runs = json.loads((d / "execucoes.json").read_text(encoding="utf-8"))
                self.assertEqual(len(runs), 2 * len(BY_ID))
                for r in runs:
                    self.assertTrue(list((d / "entregas" / r["run"]).glob("*.Report")), r["run"])
                    self.assertTrue((d / "amostras" / f"{r['cenario']}.json").exists())

    def test_the_page_template_has_the_data_slot(self):
        self.assertIn("/*__DATA__*/null", (ROOT / "benchmarks" / "pagina.html").read_text(encoding="utf-8"))


class TestStartingProjects(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_model_without_report_opens_and_asks_for_the_pages(self):
        s = BY_ID["s1-logistica"]
        kit = json.loads((ROOT / s["modelo"]).read_text(encoding="utf-8"))
        folder = self.tmp / "s1"
        sample = bench.model_only(kit, folder, s["projeto"])
        self.assertTrue(sample.get("measures"))
        self.assertFalse(list(folder.glob("*.Report/definition/pages")))
        ok, why = bench.opens_cleanly(folder)
        self.assertTrue(ok, why)
        met, why = bench.request_met(s, folder, set())
        self.assertFalse(met)
        self.assertIn("falta página", why)

    def test_restyle_flags_lost_information(self):
        s = BY_ID["s2-reestilizar"]
        folder = self.tmp / "s2"
        bench.legacy_project(folder)
        report = folder / "ContasReceber.Report"
        before = bench.visual_fields(report)
        self.assertTrue(before)
        self.assertEqual(bench.request_met(s, folder, before), (True, ""))

        for f in report.rglob("visual.json"):
            f.unlink()
        met, why = bench.request_met(s, folder, before)
        self.assertFalse(met)
        self.assertIn("informação perdida", why)


if __name__ == "__main__":
    unittest.main()
