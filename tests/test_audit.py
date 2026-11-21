"""audit_pbip.py: rule codes, suppression, output formats and CLI. Standard library only."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "powerbi-architect" / "scripts" / "audit_pbip.py"
EXAMPLE = ROOT / "examples" / "contas-a-receber"
sys.path.insert(0, str(SCRIPT.parent))
import audit_pbip as ap  # noqa: E402


def run(*args, cwd=None):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True,
                          encoding="utf-8", cwd=cwd)


def copy_example(tmp: str) -> Path:
    dst = Path(tmp) / "proj"
    shutil.copytree(EXAMPLE, dst)
    return dst


def edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, old
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


class TestCli(unittest.TestCase):
    def test_help_and_version(self):
        r = run("--help")
        self.assertEqual(r.returncode, 0)
        self.assertIn("usage: audit_pbip.py", r.stdout)
        self.assertNotIn("BLOCKER", r.stdout)
        self.assertRegex(run("--version").stdout, r"audit_pbip\.py \d+\.\d+\.\d+")

    def test_missing_or_bad_folder_is_a_usage_error(self):
        self.assertEqual(run().returncode, 2)
        self.assertEqual(run("does-not-exist").returncode, 2)

    def test_list_rules_shows_codes_and_bpa_ids(self):
        out = run("--list-rules").stdout
        self.assertIn("PBI005", out)
        self.assertIn("BPA: REMOVE_AUTO-DATE_TABLE", out)

    def test_rules_are_consistent(self):
        laws = {"1", "2", "3", "4", "5", "6", "7", "8", "gov", "a11y"}
        for rid, (sev, law, title, bpa) in ap.RULES.items():
            self.assertRegex(rid, r"^PBI\d{3}$")
            self.assertIn(sev, ap.SEVERITIES)
            self.assertIn(law, laws, rid)
            self.assertTrue(title)
        covered = {law for _, law, _, _ in ap.RULES.values()}
        self.assertTrue({str(n) for n in range(1, 9)} <= covered, "every law needs at least one rule")


class TestDocs(unittest.TestCase):
    def test_every_rule_is_documented(self):
        doc = (ROOT / "docs" / "regras-auditoria.md").read_text(encoding="utf-8")
        missing = [rid for rid in ap.RULES if f"| {rid} |" not in doc]
        self.assertEqual(missing, [], "add the rule to docs/regras-auditoria.md")


class TestExample(unittest.TestCase):
    def test_example_is_clean(self):
        r = run(EXAMPLE, "--fail-on", "suggestion")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("0 finding(s)", r.stdout)


class TestRules(unittest.TestCase):
    def findings(self, root: Path, *extra):
        r = run(root, "--json", *extra)
        return json.loads(r.stdout), r.returncode

    def test_each_rule_fires_on_a_broken_copy(self):
        with tempfile.TemporaryDirectory() as d:
            p = copy_example(d)
            sm = p / "ContasReceber.SemanticModel" / "definition"
            edit(sm / "model.tmdl", "__PBI_TimeIntelligenceEnabled = 0", "__PBI_TimeIntelligenceEnabled = 1")
            edit(sm / "tables" / "_Medidas.tmdl", "DIVIDE ( [Valor Vencido], [Valor Aberto] )",
                 "IFERROR ( [Valor Vencido] / [Valor Aberto], 0 )")
            edit(sm / "tables" / "_Medidas.tmdl", "\t/// Saldo em aberto das parcelas, vencidas ou a vencer.\n", "")
            edit(sm / "tables" / "Fato Titulos.tmdl", "Sql.Database(Servidor, Banco)", 'Sql.Database("srv01", "dw")')
            edit(sm / "tables" / "Dim Cliente.tmdl", "\tcolumn Segmento\n\t\tdataType: string",
                 "\tcolumn Segmento\n\t\tdataType: string\n\n\tcolumn Score\n\t\tdataType: double\n"
                 "\t\tsummarizeBy: none\n\t\tsourceColumn: Score\n\n\tcolumn Segmento2\n\t\tdataType: string")
            edit(sm / "relationships.tmdl", "\tfromColumn: 'Fato Titulos'.id_cliente",
                 "\tcrossFilteringBehavior: bothDirections\n\tfromColumn: 'Fato Titulos'.id_cliente")
            (p / "README.md").unlink()
            found, code = self.findings(p)
            rules = {f["rule"] for f in found}
            for expected in ("PBI003", "PBI005", "PBI010", "PBI015", "PBI032", "PBI033", "PBI034", "PBI035",
                             "PBI043"):
                self.assertIn(expected, rules)
            self.assertEqual(code, 1)                                    # blockers present
            hard = next(f for f in found if f["rule"] == "PBI003")
            self.assertTrue(hard["where"].endswith("tables/Fato Titulos.tmdl"))
            self.assertGreater(hard["line"], 0)
            self.assertIn("REMOVE_AUTO-DATE_TABLE", next(f for f in found if f["rule"] == "PBI010")["bpa"])

    def test_report_rules(self):
        with tempfile.TemporaryDirectory() as d:
            p = copy_example(d)
            visuals = sorted((p / "ContasReceber.Report").rglob("visual.json"))
            bar = next(v for v in visuals if "clusteredBarChart" in v.read_text(encoding="utf-8"))
            data = json.loads(bar.read_text(encoding="utf-8"))
            data["visual"]["visualType"] = "pieChart"
            del data["visual"]["visualContainerObjects"]["general"]
            bar.write_text(json.dumps(data), encoding="utf-8")
            page = bar.parent.parent.parent / "page.json"
            pj = json.loads(page.read_text(encoding="utf-8"))
            pj["displayName"] = "Page 1"
            page.write_text(json.dumps(pj), encoding="utf-8")
            rules = {f["rule"] for f in self.findings(p)[0]}
            self.assertTrue({"PBI019", "PBI040", "PBI042"} <= rules, rules)


class TestSuppression(unittest.TestCase):
    def broken(self, d: str) -> Path:
        p = copy_example(d)
        edit(p / "ContasReceber.SemanticModel" / "definition" / "model.tmdl",
             "__PBI_TimeIntelligenceEnabled = 0", "__PBI_TimeIntelligenceEnabled = 1")
        return p

    def rules(self, p: Path, *extra):
        return {f["rule"] for f in json.loads(run(p, "--json", *extra).stdout)}

    def test_config_file_disables_rule(self):
        with tempfile.TemporaryDirectory() as d:
            p = self.broken(d)
            self.assertIn("PBI010", self.rules(p))
            (p / ".pbiaudit.json").write_text('{"disable": ["PBI010"]}', encoding="utf-8")
            self.assertNotIn("PBI010", self.rules(p))

    def test_config_ignore_by_path(self):
        with tempfile.TemporaryDirectory() as d:
            p = self.broken(d)
            (p / "cfg.json").write_text('{"ignore": [{"rule": "PBI010", "path": "*/model.tmdl"}]}', encoding="utf-8")
            self.assertNotIn("PBI010", self.rules(p, "--config", p / "cfg.json"))

    def test_bpa_ignore_annotation_is_honored(self):
        with tempfile.TemporaryDirectory() as d:
            p = self.broken(d)
            model = p / "ContasReceber.SemanticModel" / "definition" / "model.tmdl"
            model.write_text(model.read_text(encoding="utf-8") +
                             'annotation BestPracticeAnalyzer_IgnoreRules = {"RuleIDs":["REMOVE_AUTO-DATE_TABLE"]}\n',
                             encoding="utf-8")
            self.assertNotIn("PBI010", self.rules(p))

    def test_own_ignore_annotation_on_a_measure(self):
        with tempfile.TemporaryDirectory() as d:
            p = copy_example(d)
            m = p / "ContasReceber.SemanticModel" / "definition" / "tables" / "_Medidas.tmdl"
            edit(m, "DIVIDE ( [Valor Vencido], [Valor Aberto] )\n\t\tformatString: 0.0%",
                 '[Valor Vencido] / [Valor Aberto]\n\t\tformatString: 0.0%\n\t\t'
                 'annotation PowerBIArchitect_IgnoreRules = {"RuleIDs":["PBI032"]}')
            self.assertNotIn("PBI032", self.rules(p))


class TestOutputs(unittest.TestCase):
    def test_sarif(self):
        with tempfile.TemporaryDirectory() as d:
            p = copy_example(d)
            (p / "README.md").unlink()
            sarif = json.loads(run(p, "--sarif").stdout)
            self.assertEqual(sarif["version"], "2.1.0")
            run_ = sarif["runs"][0]
            self.assertEqual({r["id"] for r in run_["tool"]["driver"]["rules"]}, set(ap.RULES))
            self.assertEqual(run_["results"][0]["ruleId"], "PBI043")
            self.assertEqual(run_["results"][0]["level"], "note")

    def test_fail_on(self):
        with tempfile.TemporaryDirectory() as d:
            p = copy_example(d)
            (p / "README.md").unlink()                           # one SUGGESTION
            self.assertEqual(run(p).returncode, 0)
            self.assertEqual(run(p, "--fail-on", "suggestion").returncode, 1)
            self.assertEqual(run(p, "--fail-on", "never").returncode, 0)


if __name__ == "__main__":
    unittest.main()
