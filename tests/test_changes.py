"""pbip_changes.py: edits made by hand are noticed, described in business terms and never lost."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "powerbi-architect" / "scripts" / "pbip_changes.py"
EXAMPLE = ROOT / "examples" / "contas-a-receber"


def run(repo: Path, *args, stdin=None):
    return subprocess.run([sys.executable, str(SCRIPT), *args, str(repo)], capture_output=True, text=True,
                          encoding="utf-8", input=stdin)


class TestManualChanges(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        shutil.copytree(EXAMPLE, self.repo)
        self.assertEqual(run(self.repo, "accept", "--quiet").returncode, 0)

    def tearDown(self):
        self.tmp.cleanup()

    def edit_by_hand(self):
        m = self.repo / "ContasReceber.SemanticModel" / "definition" / "tables" / "_Medidas.tmdl"
        text = m.read_text(encoding="utf-8").replace("ft_titulos[Dias Atraso] > 0 )", "ft_titulos[Dias Atraso] > 5 )", 1)
        m.write_text(text + "\n\t/// Feita no Desktop.\n\tmeasure 'Ticket Médio' = DIVIDE ( [Valor Aberto], 3 )\n",
                     encoding="utf-8")
        for f in sorted((self.repo / "ContasReceber.Report").rglob("visual.json")):
            v = json.loads(f.read_text(encoding="utf-8"))
            if v["visual"]["visualType"] == "clusteredBarChart":
                v["position"]["x"] += 8
                v["position"]["height"] += 20
                v["visual"]["visualContainerObjects"]["title"][0]["properties"]["text"] = \
                    {"expr": {"Literal": {"Value": "'Vencido por região'"}}}
                f.write_text(json.dumps(v), encoding="utf-8")
                break

    def test_status_describes_edits_in_business_terms(self):
        self.edit_by_hand()
        out = run(self.repo, "status").stdout
        self.assertIn("medida 'Valor Vencido' em _Medidas — expressão mudou para: CALCULATE ( [Valor Aberto], "
                      "ft_titulos[Dias Atraso] > 5 )", out)
        self.assertIn("medida 'Ticket Médio' criada em _Medidas", out)
        self.assertIn('Visão Geral: barras "Vencido por regional" — movido (232, 448) → (240, 448); '
                      'tamanho 1024×248 → 1024×268; título "Vencido por regional" → "Vencido por região"', out)

    def test_hook_reports_once_journals_and_stays_silent_otherwise(self):
        event = json.dumps({"hook_event_name": "UserPromptSubmit", "cwd": str(self.repo)})
        quiet = run(self.repo, "status", "--hook", stdin=event)
        self.assertEqual((quiet.returncode, quiet.stdout), (0, ""))
        self.edit_by_hand()
        first = run(self.repo, "status", "--hook", stdin=event)
        self.assertIn("O usuário mudou o projeto à mão", first.stdout)
        self.assertIn("Ticket Médio", first.stdout)
        self.assertEqual(run(self.repo, "status", "--hook", stdin=event).stdout, "")    # reported once
        journal = (self.repo / ".powerbi-architect" / "alteracoes.md").read_text(encoding="utf-8")
        self.assertIn("# Alterações feitas à mão", journal)
        self.assertIn("Ticket Médio", journal)
        self.assertEqual((self.repo / ".powerbi-architect" / ".gitignore").read_text(encoding="utf-8"),
                         "snapshot.json\n")

    def test_the_agents_own_edits_are_not_reported(self):
        self.edit_by_hand()
        run(self.repo, "accept", "--quiet")                       # PostToolUse after the agent's edit
        self.assertIn("Nada mudou", run(self.repo, "status").stdout)

    def test_pages_and_visuals_created_or_removed(self):
        pages = self.repo / "ContasReceber.Report" / "definition" / "pages"
        doc = next(p for p in pages.iterdir() if p.is_dir() and
                   json.loads((p / "page.json").read_text(encoding="utf-8"))["displayName"] == "Documentação")
        shutil.rmtree(doc)
        new = pages / "rascunho000000000000"
        (new / "visuals" / "v1").mkdir(parents=True)
        (new / "page.json").write_text('{"name": "rascunho000000000000", "displayName": "Rascunho"}', encoding="utf-8")
        (new / "visuals" / "v1" / "visual.json").write_text(
            '{"position": {"x": 0, "y": 0, "width": 100, "height": 100}, "visual": {"visualType": "card"}}',
            encoding="utf-8")
        out = run(self.repo, "status").stdout
        self.assertIn("página 'Documentação' removida", out)
        self.assertIn("página 'Rascunho' criada (1 visuais)", out)


if __name__ == "__main__":
    unittest.main()
