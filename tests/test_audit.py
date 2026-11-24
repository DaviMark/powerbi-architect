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


class TestTargetsAndTitles(unittest.TestCase):
    def test_a_measure_with_a_target_shown_without_it(self):
        visual = {"visualType": "lineChart", "query": {"queryState": {"Y": {"projections": [
            {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": "_M"}}, "Property": "% No Prazo"}}}]}}}}
        measures = {"% No Prazo": "", "Meta % No Prazo": "0.95", "Entregas": ""}
        self.assertIn("Meta % No Prazo", ap.target_review(visual, measures))
        visual["query"]["queryState"]["Y"]["projections"].append(
            {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": "_M"}}, "Property": "Meta % No Prazo"}}})
        self.assertIsNone(ap.target_review(visual, measures))             # the target is drawn
        self.assertIsNone(ap.target_of("Entregas", measures))

    def test_a_dynamic_title_reused_on_another_visual(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = copy_example(tmp)
            titled = [f for f in proj.rglob("visual.json") if '"Measure"' in json.dumps(
                (json.loads(f.read_text(encoding="utf-8")).get("visual") or {}).get("visualContainerObjects", {}).get("title", ""))]
            charts = [f for f in proj.rglob("visual.json") if json.loads(f.read_text(encoding="utf-8")).get("visual", {})
                      .get("visualType") == "clusteredBarChart"]
            self.assertTrue(titled and charts)
            title = json.loads(titled[0].read_text(encoding="utf-8"))["visual"]["visualContainerObjects"]["title"]
            bar = json.loads(charts[0].read_text(encoding="utf-8"))
            bar["visual"].setdefault("visualContainerObjects", {})["title"] = title
            charts[0].write_text(json.dumps(bar), encoding="utf-8")
            rules = [i["rule"] for i in ap.audit(proj)]
            self.assertIn("PBI078", rules)

    def test_machine_sounding_titles(self):
        for text in ("Vencido — concentrado no Sul", "Visão robusta da carteira", "Além disso, o atraso cresce",
                     "Vencido por regional 🚀"):
            self.assertIsNotNone(ap.machine_text(text), text)
        for text in ("Vencido por regional", "Clientes que concentram o vencido", "▲ 2,3 p.p. acima da meta",
                     "Pedido perfeito por transportadora", "Faixa 0-30 dias"):
            self.assertIsNone(ap.machine_text(text), text)


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
            edit(sm / "tables" / "ft_titulos.tmdl", "Sql.Database(Servidor, Banco)", 'Sql.Database("srv01", "dw")')
            edit(sm / "tables" / "dm_cliente.tmdl", "\tcolumn Segmento\n\t\tdataType: string",
                 "\tcolumn Segmento\n\t\tdataType: string\n\n\tcolumn Score\n\t\tdataType: double\n"
                 "\t\tsummarizeBy: none\n\t\tsourceColumn: Score\n\n\tcolumn Segmento2\n\t\tdataType: string")
            edit(sm / "relationships.tmdl", "\tfromColumn: ft_titulos.id_cliente",
                 "\tcrossFilteringBehavior: bothDirections\n\tfromColumn: ft_titulos.id_cliente")
            (p / "README.md").unlink()
            found, code = self.findings(p)
            rules = {f["rule"] for f in found}
            for expected in ("PBI003", "PBI005", "PBI010", "PBI015", "PBI032", "PBI033", "PBI034", "PBI035",
                             "PBI043"):
                self.assertIn(expected, rules)
            self.assertEqual(code, 1)                                    # blockers present
            hard = next(f for f in found if f["rule"] == "PBI003")
            self.assertTrue(hard["where"].endswith("tables/ft_titulos.tmdl"))
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


    def test_layout_typography_and_naming_rules(self):
        with tempfile.TemporaryDirectory() as d:
            p = copy_example(d)
            sm = p / "ContasReceber.SemanticModel" / "definition"
            for f in (sm / "tables" / "dm_cliente.tmdl", sm / "relationships.tmdl"):
                f.write_text(f.read_text(encoding="utf-8").replace("dm_cliente", "Clientes"), encoding="utf-8")
            page_dir = next(pj.parent / "visuals" for pj in (p / "ContasReceber.Report").rglob("page.json")
                            if json.loads(pj.read_text(encoding="utf-8"))["displayName"] == "Visão Geral")
            slicer = next(v for v in page_dir.rglob("visual.json") if '"slicer"' in v.read_text(encoding="utf-8"))
            data = json.loads(slicer.read_text(encoding="utf-8"))
            data["position"].update(width=400, height=120)                    # PBI046
            slicer.write_text(json.dumps(data), encoding="utf-8")
            for i in range(2):                                                # PBI050: 3 slicers
                copy = page_dir / f"extra{i}" / "visual.json"
                copy.parent.mkdir()
                data["position"].update(width=176, height=40)
                copy.write_text(json.dumps(data), encoding="utf-8")
            box = next(v for v in page_dir.rglob("visual.json") if '"textbox"' in v.read_text(encoding="utf-8"))
            data = json.loads(box.read_text(encoding="utf-8"))
            first_run = data["visual"]["objects"]["general"][0]["properties"]["paragraphs"][0]["textRuns"][0]
            first_run["textStyle"].update(fontSize="28pt", fontFamily="DIN")         # PBI047, PBI051
            data["position"].update(x=1201, width=200)                        # PBI048, PBI052
            box.write_text(json.dumps(data), encoding="utf-8")
            rules = {f["rule"] for f in json.loads(run(p, "--json").stdout)}
            for expected in ("PBI046", "PBI047", "PBI048", "PBI049", "PBI050", "PBI051", "PBI052"):
                self.assertIn(expected, rules)


    def test_accessibility_title_and_colour_rules(self):
        with tempfile.TemporaryDirectory() as d:
            p = copy_example(d)
            page_dir = next(pj.parent / "visuals" for pj in (p / "ContasReceber.Report").rglob("page.json")
                            if json.loads(pj.read_text(encoding="utf-8"))["displayName"] == "Diagnóstico")
            files = sorted(page_dir.rglob("visual.json"))
            charts = [f for f in files if '"clusteredBarChart"' in f.read_text(encoding="utf-8")
                      or '"waterfallChart"' in f.read_text(encoding="utf-8")]
            bar = json.loads(charts[0].read_text(encoding="utf-8"))
            vco = bar["visual"]["visualContainerObjects"]
            vco["title"] = [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}},
                                            "text": {"expr": {"Literal": {"Value": "'Soma de Valor por Regional'"}}}}}]
            bar["visual"]["objects"] = {
                "valueAxis": [{"properties": {"showAxisTitle": {"expr": {"Literal": {"Value": "true"}}}}}],
                "labels": [{"properties": {"color": {"solid": {"color": {"expr": {"Literal": {"Value": "'#BBBBBB'"}}}}}}}],
                "dataPoint": [{"properties": {"fill": {"solid": {"color": {"expr": {"Literal": {"Value": f"'{c}'"}}}}}}}
                              for c in ("#E11D48", "#F59E0B", "#10B981", "#6366F1", "#EC4899", "#14B8A6", "#84CC16")]}
            bar["position"]["tabOrder"] = -1                                    # PBI053: jumps ahead
            charts[0].write_text(json.dumps(bar), encoding="utf-8")             # PBI054, PBI055, PBI057, PBI058
            line = json.loads(charts[1].read_text(encoding="utf-8"))
            line["visual"]["visualContainerObjects"].pop("title")               # PBI056
            charts[1].write_text(json.dumps(line), encoding="utf-8")
            r = run(p, "--json", "--min-harmony", "90")
            rules = {f["rule"] for f in json.loads(r.stdout)}
            for expected in ("PBI053", "PBI054", "PBI055", "PBI056", "PBI057", "PBI058"):
                self.assertIn(expected, rules)
            self.assertEqual(r.returncode, 1)                                   # harmony below 90
            text = run(p).stdout
            self.assertRegex(text, r"Diagnóstico \d+")
            self.assertNotIn("Diagnóstico 100", text)


class TestArtDirector(unittest.TestCase):
    """PBI059–PBI064: what a designer catches at a glance."""

    def test_each_design_rule_fires(self):
        with tempfile.TemporaryDirectory() as d:
            p = copy_example(d)
            files = {}
            for f in sorted((p / "ContasReceber.Report").rglob("visual.json")):
                v = json.loads(f.read_text(encoding="utf-8"))
                files.setdefault(v["visual"]["visualType"], []).append((f, v))
            col_f, col = max(files["clusteredColumnChart"], key=lambda fv: fv[1]["position"]["width"])
            col["visual"]["visualContainerObjects"]["title"][0]["properties"]["text"] = \
                {"expr": {"Literal": {"Value": "'" + "Um título longo demais para um gráfico estreito " * 2 + "'"}}}
            col_f.write_text(json.dumps(col), encoding="utf-8")              # PBI059
            fall_f, fall = files["waterfallChart"][0]
            fall["position"]["height"] = 120                                 # PBI064
            fall_f.write_text(json.dumps(fall), encoding="utf-8")
            table_f, table = next((f, v) for f, v in files["tableEx"] if len(
                v["visual"]["query"]["queryState"]["Values"]["projections"]) == 5)
            table["position"]["width"] = 360                                 # PBI060
            table_f.write_text(json.dumps(table), encoding="utf-8")
            bar_f, bar = files["clusteredBarChart"][0]
            bar["visual"]["visualContainerObjects"]["title"][0]["properties"]["text"] = \
                {"expr": {"Measure": {"Expression": {"SourceRef": {"Entity": "_Medidas"}}, "Property": "Texto Atualizacao"}}}
            cat = bar["visual"]["query"]["queryState"]["Category"]["projections"][0]["field"]["Column"]
            cat["Expression"]["SourceRef"]["Entity"], cat["Property"] = "dm_calendario", "Ano-Mês"   # PBI062
            bar_f.write_text(json.dumps(bar), encoding="utf-8")                                  # PBI061
            card_f, card = next((f, v) for f, v in files["card"] if v["position"]["height"] == 88)
            card["position"]["width"] = 160                                  # PBI063
            card_f.write_text(json.dumps(card), encoding="utf-8")
            found = {(i["rule"], Path(i["where"]).parent.name) for i in ap.audit(p)}
            for rule, f in (("PBI059", col_f), ("PBI064", fall_f), ("PBI060", table_f), ("PBI061", bar_f),
                            ("PBI062", bar_f), ("PBI063", card_f)):
                self.assertIn((rule, f.parent.name), found, rule)


class TestNoAiLook(unittest.TestCase):
    def test_round_corners_shadows_gutters_and_copies(self):
        with tempfile.TemporaryDirectory() as d:
            p = copy_example(d)
            bars = [f for f in sorted((p / "ContasReceber.Report").rglob("visual.json"))
                    if '"clusteredBarChart"' in f.read_text(encoding="utf-8")]
            f = bars[0]
            v = json.loads(f.read_text(encoding="utf-8"))
            vco = v["visual"].setdefault("visualContainerObjects", {})
            vco["border"] = [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}},
                                             "radius": {"expr": {"Literal": {"Value": "20D"}}}}}]
            vco["dropShadow"] = [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}}}}]
            f.write_text(json.dumps(v), encoding="utf-8")
            copy = f.parent.parent / "copia000000000000000"
            copy.mkdir()
            v2 = json.loads(json.dumps(v))
            v2["name"] = copy.name
            v2["position"]["y"] += 4
            (copy / "visual.json").write_text(json.dumps(v2), encoding="utf-8")
            line = next(f for f in sorted((p / "ContasReceber.Report").rglob("visual.json"))
                        if '"lineChart"' in f.read_text(encoding="utf-8"))
            lv = json.loads(line.read_text(encoding="utf-8"))
            lv["position"]["width"] -= 8                     # 24 px to its neighbour, 16 px everywhere else
            line.write_text(json.dumps(lv), encoding="utf-8")
            rules = {i["rule"] for i in ap.audit(p) if i["where"].endswith(("visual.json",))}
            self.assertTrue({"PBI066", "PBI067", "PBI068", "PBI069"} <= rules, rules)


class TestNumbersRight(unittest.TestCase):
    """PBI070–PBI077: DAX and SQL that return the wrong number without any error."""

    def test_dax_and_sql_pitfalls(self):
        with tempfile.TemporaryDirectory() as d:
            p = copy_example(d)
            tables = p / "ContasReceber.SemanticModel" / "definition" / "tables"
            m = tables / "_Medidas.tmdl"
            m.write_text(m.read_text(encoding="utf-8") + (
                "\n\t/// Média do percentual por título.\n"
                "\tmeasure 'Média % Vencido' = AVERAGEX ( ft_titulos, [% Vencido] )\n"
                "\t\tformatString: 0.0%\n\t\tdisplayFolder: Indicadores\n"
                "\n\t/// Saldo no período.\n"
                "\tmeasure 'Saldo Período' = SUM ( ft_titulos[Saldo] )\n"
                "\t\tformatString: \\R\\$ #,0\n\t\tdisplayFolder: Valores\n"
                "\n\t/// Percentual com formato errado.\n"
                "\tmeasure '% Atrasados' = DIVIDE ( [Valor Vencido], [Valor Aberto] )\n"
                "\t\tformatString: #,0\n\t\tdisplayFolder: Indicadores\n"), encoding="utf-8")
            ft = tables / "ft_titulos.tmdl"
            text = ft.read_text(encoding="utf-8")
            text = text.replace("/// Parcelas de títulos", "/// Foto diária da posição das parcelas de títulos", 1)
            text = text.replace("\tcolumn id_cliente", "\tcolumn Saldo\n\t\tdataType: decimal\n\t\tsourceColumn: Saldo\n\n"
                                "\tcolumn id_cliente", 1)
            text = text.replace("FROM dw.fato_titulos_receber AS t WHERE t.valor_aberto > 0",
                                "FROM dw.fato_titulos_receber AS t WITH (NOLOCK), dw.dim_cliente c "
                                "WHERE YEAR(t.data_vencimento) = 2025")
            ft.write_text(text, encoding="utf-8")
            dm = tables / "dm_cliente.tmdl"
            dm.write_text(dm.read_text(encoding="utf-8").replace("SELECT c.id_cliente, c.nome_fantasia AS Cliente, "
                                                                 "c.segmento AS Segmento", "SELECT *"), encoding="utf-8")
            rules = {i["rule"] for i in ap.audit(p)}
            for rule in ("PBI070", "PBI071", "PBI072", "PBI073", "PBI074", "PBI076", "PBI077"):
                self.assertIn(rule, rules)

    def test_distinct_in_a_fact(self):
        self.assertIn("PBI075", {r for r, _ in ap.sql_review("SELECT DISTINCT a, b FROM f", True)})
        self.assertEqual(ap.sql_review("SELECT a FROM f JOIN d ON d.k = f.k CROSS JOIN x", True), [])


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


class TestHook(unittest.TestCase):
    """--hook: the Claude Code PostToolUse audit installed by pbi_graph.py install."""

    def hook(self, payload):
        return subprocess.run([sys.executable, str(SCRIPT), "--hook"], input=payload, capture_output=True,
                              text=True, encoding="utf-8")

    def event(self, path: Path) -> str:
        return json.dumps({"tool_name": "Edit", "tool_input": {"file_path": str(path)}})

    def test_silent_on_a_clean_project_and_on_unrelated_files(self):
        with tempfile.TemporaryDirectory() as d:
            p = copy_example(d)
            visual = next((p / "ContasReceber.Report").rglob("visual.json"))
            for payload in (self.event(visual), self.event(p / "README.md"), "not json", "{}"):
                r = self.hook(payload)
                self.assertEqual((r.returncode, r.stderr), (0, ""), payload)

    def test_reports_back_to_the_agent_when_the_edit_breaks_the_page(self):
        with tempfile.TemporaryDirectory() as d:
            p = copy_example(d)
            bar = next(v for v in sorted((p / "ContasReceber.Report").rglob("visual.json"))
                       if "clusteredBarChart" in v.read_text(encoding="utf-8"))
            data = json.loads(bar.read_text(encoding="utf-8"))
            data["position"]["x"] += 3                       # off the 4px grid, overlaps nothing else
            data["visual"]["visualType"] = "pieChart"
            del data["visual"]["visualContainerObjects"]["general"]   # no alt text
            bar.write_text(json.dumps(data), encoding="utf-8")
            r = self.hook(self.event(bar))
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("PBI019", r.stderr)
            self.assertIn("Harmony:", r.stderr)
            self.assertIn("--min-harmony 90", r.stderr)


if __name__ == "__main__":
    unittest.main()
