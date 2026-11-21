"""Structural tests for the skill. Standard library only:  python -m unittest discover -s tests -v"""
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "powerbi-architect"


def frontmatter(text: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m, "SKILL.md must start with YAML frontmatter"
    out = {}
    for line in m.group(1).splitlines():
        if re.match(r"^[a-z_-]+:", line):
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip()
    return out


class TestSkill(unittest.TestCase):
    def test_frontmatter(self):
        fm = frontmatter((SKILL / "SKILL.md").read_text(encoding="utf-8"))
        self.assertEqual(fm.get("name"), "powerbi-architect")
        self.assertRegex(fm["name"], r"^[a-z0-9-]{1,64}$")
        self.assertTrue(0 < len(fm.get("description", "")) <= 1024)
        self.assertNotIn("<", fm["description"])

    def test_versions_are_in_sync(self):
        import json
        fm_version = re.search(r'version:\s*"([^"]+)"', (SKILL / "SKILL.md").read_text(encoding="utf-8")).group(1)
        plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual(plugin["version"], fm_version, "update .claude-plugin/plugin.json")
        self.assertEqual(market["plugins"][0]["version"], fm_version, "update .claude-plugin/marketplace.json")
        self.assertEqual(plugin["name"], "powerbi-architect")

    def test_skill_md_is_concise(self):
        lines = (SKILL / "SKILL.md").read_text(encoding="utf-8").count("\n")
        self.assertLess(lines, 500, "keep SKILL.md under 500 lines; move detail to references/")

    def test_relative_links_resolve(self):
        broken = []
        skip = {"node_modules", ".tmp", ".git", "powerbi-graph", "results"}
        for md in [p for p in ROOT.rglob("*.md") if not skip & set(p.relative_to(ROOT).parts)]:
            for target in re.findall(r"\]\((?!https?://|#|mailto:)([^)#\s]+)", md.read_text(encoding="utf-8")):
                if not (md.parent / target).exists():
                    broken.append(f"{md.relative_to(ROOT)} -> {target}")
        self.assertEqual(broken, [])

    def test_no_secrets_or_data(self):
        bad = [p for p in ROOT.rglob("*") if p.suffix.lower() in {".pbix", ".abf", ".pem", ".pfx"}]
        self.assertEqual(bad, [])

    def test_pbiviz_template_has_no_network_privileges(self):
        cap = (SKILL / "templates/pbiviz-bullet-kpi/capabilities.json").read_text(encoding="utf-8")
        self.assertIn('"privileges": []', cap)
        code = (SKILL / "templates/pbiviz-bullet-kpi/src/visual.ts").read_text(encoding="utf-8")
        for forbidden in ("fetch(", "XMLHttpRequest", "innerHTML", "eval(", "new Function"):
            self.assertNotIn(forbidden, code)


class TestAudit(unittest.TestCase):
    def test_audit_flags_bad_project(self):
        with tempfile.TemporaryDirectory() as d:
            sm = Path(d) / "X.SemanticModel" / "definition"
            (sm / "tables").mkdir(parents=True)
            (sm / "model.tmdl").write_text("model Model\n\tculture: en-US\n\nannotation __PBI_TimeIntelligenceEnabled = 1\n")
            (sm / "tables" / "Sales.tmdl").write_text(
                "table Sales\n\n\tmeasure Total = SUM ( Sales[v] )\n\n\tcolumn v\n\t\tdataType: double\n\t\tsourceColumn: v\n\n"
                "\tpartition Sales = m\n\t\tmode: import\n\t\tsource =\n\t\t\t\tlet\n"
                '\t\t\t\t    S = Sql.Database("srv", "db"),\n\t\t\t\t    T = Table.SelectRows(S, each true)\n'
                "\t\t\t\tin\n\t\t\t\t    T\n")
            (Path(d) / "X.Report" / "definition" / "pages" / "p1").mkdir(parents=True)
            (Path(d) / "X.Report" / "definition" / "pages" / "p1" / "page.json").write_text('{"displayName": "Home"}')
            r = subprocess.run([sys.executable, str(SKILL / "scripts" / "audit_pbip.py"), d],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            for expected in ("hard-coded server", "auto date/time", "Power Query steps",
                             "missing description", "Documentation page"):
                self.assertIn(expected, r.stdout)


def _mini_project(d: Path) -> None:
    """Tiny PBIP: fact + dim, 2 measures (one unused), 1 page with a card and a bar chart."""
    sm = d / "dash" / "src" / "M.SemanticModel" / "definition"
    (sm / "tables").mkdir(parents=True)
    (sm.parent / "definition.pbism").write_text("{}")
    (sm / "model.tmdl").write_text("model Model\n\tculture: pt-BR\n")
    (sm / "tables" / "Vendas.tmdl").write_text(
        "table Vendas\n\n\tcolumn id_loja\n\t\tdataType: int64\n\t\tsourceColumn: id_loja\n\n"
        "\tcolumn Valor\n\t\tdataType: decimal\n\t\tsourceColumn: Valor\n\n"
        "\tcolumn Lixo\n\t\tdataType: string\n\t\tsourceColumn: Lixo\n\n"
        "\tpartition Vendas = m\n\t\tmode: import\n\t\tsource =\n\t\t\t\tlet\n"
        '\t\t\t\t    Fonte = Value.NativeQuery(Sql.Database(Srv, Db), "SELECT v.id_loja, v.valor AS Valor FROM dw.fato_vendas v", null)\n'
        "\t\t\t\tin\n\t\t\t\t    Fonte\n")
    (sm / "tables" / "Loja.tmdl").write_text(
        "table Loja\n\n\tcolumn id_loja\n\t\tdataType: int64\n\t\tsourceColumn: id_loja\n\n"
        "\tcolumn Nome\n\t\tdataType: string\n\t\tsourceColumn: Nome\n")
    (sm / "tables" / "_Medidas.tmdl").write_text(
        "table _Medidas\n\n\t/// Soma das vendas.\n\tmeasure Total = SUM ( Vendas[Valor] )\n\t\tformatString: #,0\n\n"
        "\t/// Dobro.\n\tmeasure Dobro = [Total] * 2\n\t\tformatString: #,0\n")
    (sm / "relationships.tmdl").write_text(
        "relationship r1\n\tfromColumn: Vendas.id_loja\n\ttoColumn: Loja.id_loja\n")
    rp = d / "dash" / "src" / "M.Report"
    pg = rp / "definition" / "pages" / "p1"
    (rp / "definition.pbir").parent.mkdir(parents=True, exist_ok=True)
    (rp / "definition.pbir").write_text('{"datasetReference": {"byPath": {"path": "../M.SemanticModel"}}}')
    (pg / "visuals" / "v1").mkdir(parents=True)
    (pg / "visuals" / "v2").mkdir(parents=True)
    (pg / "page.json").write_text('{"name": "p1", "displayName": "Resumo"}')
    (d / "dash" / "ficha.toml").write_text(
        '[dashboard]\nname = "Painel"\nstatus = "draft"\n[data]\nconnection = "erp"\n', encoding="utf-8")
    proto = rp / "definition" / "pages" / "p2" / "visuals" / "b1"
    proto.mkdir(parents=True)
    (proto.parent.parent / "page.json").write_text('{"name": "p2", "displayName": "Clientes"}')
    (proto / "visual.json").write_text('{"visual": {"visualType": "textbox", "objects": {"general": [{"properties": '
                                       '{"paragraphs": [{"textRuns": [{"value": "PROTÓTIPO · sem dados"}]}]}}]}}}',
                                       encoding="utf-8")

    def field(kind, ent, prop):
        return {"field": {kind: {"Expression": {"SourceRef": {"Entity": ent}}, "Property": prop}}}
    import json
    (pg / "visuals" / "v1" / "visual.json").write_text(json.dumps(
        {"visual": {"visualType": "card", "query": {"queryState": {"Values": {"projections": [field("Measure", "_Medidas", "Total")]}}}}}))
    (pg / "visuals" / "v2" / "visual.json").write_text(json.dumps(
        {"visual": {"visualType": "barChart", "query": {"queryState": {
            "Category": {"projections": [field("Column", "Loja", "Nome")]},
            "Y": {"projections": [field("Measure", "_Medidas", "Total"), field("Measure", "_Medidas", "Sumiu")]}}}}}))


class TestGraph(unittest.TestCase):
    SCRIPT = SKILL / "scripts" / "pbi_graph.py"

    def run_graph(self, cwd, *args):
        return subprocess.run([sys.executable, str(self.SCRIPT), *args], cwd=cwd, capture_output=True,
                              text=True, encoding="utf-8")

    def test_build_query_impact_and_findings(self):
        with tempfile.TemporaryDirectory() as d:
            _mini_project(Path(d))
            r = self.run_graph(d, "build", ".")
            self.assertEqual(r.returncode, 0, r.stderr)
            out = Path(d) / "powerbi-graph"
            for f in ("GRAPH_REPORT.md", "graph.json", "graph.html", "manifest.json", "wiki/index.md"):
                self.assertTrue((out / f).exists(), f)
            rep = (out / "GRAPH_REPORT.md").read_text(encoding="utf-8")
            self.assertIn("Vendas[Lixo]", rep)                      # unused column
            self.assertIn("Dobro", rep)                             # unused measure
            self.assertIn("_Medidas[Sumiu]", rep)                   # broken visual field
            self.assertIn("| Painel | draft | erp |", rep)              # ficha.toml (Power BI Workspaces 2.x)
            self.assertIn("Prototype pages", rep)
            self.assertNotIn("Vendas[id_loja] (M)", rep.split("never used")[1].split("\n")[0])  # relationship = used
            imp = self.run_graph(d, "impact", "Vendas[Valor]").stdout
            self.assertIn("Total", imp)
            self.assertIn("Dobro", imp)
            self.assertIn("card", imp)
            self.assertIn("Resumo", imp)
            self.assertIn("dw.fato_vendas", self.run_graph(d, "explain", "Vendas").stdout)
            self.assertIn("Loja[Nome]", self.run_graph(d, "path", "Nome", "Total").stdout)
            self.assertIn("up to date", self.run_graph(d, "update", ".").stdout)

    def test_install_is_idempotent_and_reversible(self):
        with tempfile.TemporaryDirectory() as d:
            _mini_project(Path(d))
            (Path(d) / ".git" / "hooks").mkdir(parents=True)
            (Path(d) / "AGENTS.md").write_text("# rules\n")
            for _ in range(2):
                self.assertEqual(self.run_graph(d, "install", ".").returncode, 0)
            agents = (Path(d) / "AGENTS.md").read_text(encoding="utf-8")
            self.assertEqual(agents.count("powerbi-graph:start"), 1)
            self.assertTrue(agents.startswith("# rules"))
            settings = (Path(d) / ".claude" / "settings.json").read_text(encoding="utf-8")
            self.assertEqual(settings.count("pbi_graph.py"), 2)     # SessionStart + PostToolUse
            self.assertEqual((Path(d) / ".git/hooks/post-commit").read_text().count("powerbi-graph:start"), 1)
            self.run_graph(d, "uninstall", ".")
            self.assertNotIn("powerbi-graph", (Path(d) / "AGENTS.md").read_text(encoding="utf-8"))
            self.assertFalse((Path(d) / "powerbi-graph").exists())


if __name__ == "__main__":
    unittest.main()
