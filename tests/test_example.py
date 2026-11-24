"""Knowledge graph regressions on examples/contas-a-receber. Standard library only."""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "powerbi-architect" / "scripts" / "pbi_graph.py"
EXAMPLE = ROOT / "examples" / "contas-a-receber"


def graph(cwd: Path, *args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8")


class TestExampleGraph(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.repo = Path(cls.tmp.name) / "repo"
        shutil.copytree(EXAMPLE, cls.repo / "contas-a-receber")
        r = graph(cls.repo, "build", ".")
        assert r.returncode == 0, r.stderr
        cls.report = (cls.repo / "powerbi-graph" / "GRAPH_REPORT.md").read_text(encoding="utf-8")
        cls.data = json.loads((cls.repo / "powerbi-graph" / "graph.json").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_example_has_no_findings(self):
        findings = self.report.split("## Findings", 1)[1].split("##", 1)[0]
        self.assertIn("none", findings)

    def test_report_is_much_smaller_than_sources(self):
        line = next(ln for ln in self.report.splitlines() if ln.startswith("**Token budget:**"))
        numbers = [int(n.replace(",", "")) for n in re.findall(r"≈ ([\d,]+)", line)]
        source, report = numbers[0], numbers[1]
        self.assertGreater(source / report, 8, line)

    def test_readme_commands_work(self):
        """The commands shown in README.md must answer on the example."""
        impact = graph(self.repo, "impact", "ft_titulos[Dias Atraso]").stdout
        for expected in ("Valor Vencido", "Atraso Médio (dias)", "Visão Geral"):
            self.assertIn(expected, impact)
        self.assertIn("ft_titulos", graph(self.repo, "explain", "Valor Vencido").stdout)
        self.assertIn("Valor Vencido", graph(self.repo, "path", "Regional", "Valor Vencido").stdout)
        self.assertIn("Visão Geral", graph(self.repo, "query", "o que alimenta a página Visão Geral?").stdout)

    def rels(self, rel):
        nodes = {n["id"] if isinstance(n, dict) else n: n for n in (
            self.data["nodes"] if isinstance(self.data["nodes"], list) else self.data["nodes"].values())}
        edges = self.data.get("edges") or self.data.get("links")
        return [(nodes.get(e["source"], {}).get("label", e["source"]), nodes.get(e["target"], {}).get("label", e["target"]))
                for e in edges if e.get("rel") == rel]

    def test_hierarchy_levels_count_as_usage(self):
        targets = {t for _, t in self.rels("hierarchy_level")}
        self.assertTrue({"dm_calendario[Ano]", "dm_calendario[Mês]"} <= targets or {"Ano", "Mês"} <= targets, targets)

    def test_measure_in_dynamic_title_counts_as_usage(self):
        targets = {t for _, t in self.rels("uses_measure")}
        self.assertTrue(any("Titulo Vencido" in t for t in targets), targets)


class TestClaudeHooks(unittest.TestCase):
    def test_install_adds_graph_and_audit_hooks_once_and_uninstall_removes_them(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            shutil.copytree(EXAMPLE, repo / "contas-a-receber")
            settings = repo / ".claude" / "settings.json"
            settings.parent.mkdir()
            mine = {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo mine"}]}
            settings.write_text(json.dumps({"hooks": {"PostToolUse": [mine]}}), encoding="utf-8")
            for _ in range(2):
                self.assertEqual(graph(repo, "install", ".", "--no-agents").returncode, 0)
            post = json.loads(settings.read_text(encoding="utf-8"))["hooks"]["PostToolUse"]
            commands = [h["command"] for g in post for h in g["hooks"]]
            self.assertEqual(sum("audit_pbip.py" in c and "--hook" in c for c in commands), 1, commands)
            self.assertEqual(sum("pbi_graph.py" in c for c in commands), 1, commands)
            self.assertEqual(sum("pbip_changes.py accept" in c.replace('"', "") for c in commands), 1, commands)
            hooks = json.loads(settings.read_text(encoding="utf-8"))["hooks"]
            on_prompt = [h["command"] for g in hooks["UserPromptSubmit"] for h in g["hooks"]]
            self.assertEqual(len(on_prompt), 1)
            self.assertIn("pbip_changes.py status --hook", on_prompt[0].replace('"', ""))
            self.assertTrue(any("pbip_changes.py status --hook" in h["command"].replace('"', "")
                                for g in hooks["SessionStart"] for h in g["hooks"]))
            self.assertIn("echo mine", commands)
            self.assertEqual(graph(repo, "uninstall", ".").returncode, 0)
            left = json.loads(settings.read_text(encoding="utf-8"))["hooks"]
            self.assertEqual(left, {"PostToolUse": [mine]})


class TestCrossModelFindings(unittest.TestCase):
    def build_two(self, rename: bool):
        d = tempfile.TemporaryDirectory()
        repo = Path(d.name)
        shutil.copytree(EXAMPLE, repo / "a")
        shutil.copytree(EXAMPLE, repo / "b")
        model = "ContasReceber"
        if rename:
            (repo / "b" / "ContasReceber.SemanticModel").rename(repo / "b" / "Cobranca.SemanticModel")
            pbir = repo / "b" / "ContasReceber.Report" / "definition.pbir"
            pbir.write_text(pbir.read_text(encoding="utf-8").replace("ContasReceber.SemanticModel",
                                                                       "Cobranca.SemanticModel"), encoding="utf-8")
            model = "Cobranca"
        m = repo / "b" / f"{model}.SemanticModel" / "definition" / "tables" / "_Medidas.tmdl"
        m.write_text(m.read_text(encoding="utf-8").replace(
            "CALCULATE ( [Valor Aberto], ft_titulos[Dias Atraso] > 0 )",
            "CALCULATE ( [Valor Aberto], ft_titulos[Dias Atraso] > 30 )"), encoding="utf-8")
        self.assertEqual(graph(repo, "build", ".").returncode, 0)
        rep = (repo / "powerbi-graph" / "GRAPH_REPORT.md").read_text(encoding="utf-8")
        d.cleanup()
        return rep

    def check(self, rep):
        self.assertIn("dw.fato_titulos_receber", rep.split("read by more than one model", 1)[1].split("\n", 1)[0])
        self.assertIn("valor vencido", rep.split("different DAX", 1)[1].split("\n", 1)[0].lower())

    def test_shared_source_and_divergent_measure(self):
        self.check(self.build_two(rename=True))

    def test_models_with_the_same_name_in_different_folders(self):
        """Issue #11: two models named alike used to merge and hide both findings."""
        rep = self.build_two(rename=False)
        self.check(rep)
        self.assertIn("(`a/ContasReceber.SemanticModel`)", rep)


if __name__ == "__main__":
    unittest.main()
