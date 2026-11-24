#!/usr/bin/env python3
"""Benchmark: the skill at version X against no skill, on the same scenarios and the same requirements.

Run from the repository root. Python 3.9+; `jsonschema` is optional (schema checks), a local Edge,
Chrome or Chromium is optional (pixel critique and images).

    python benchmarks/run.py prepare  [--out .tmp/benchmark]          # 10 workspaces + the prompts
    python benchmarks/run.py record   <run> --tokens N --tools N --seconds S [--model M]
    python benchmarks/run.py score    [--out .tmp/benchmark]          # requirements, metrics, images
    python benchmarks/run.py report                                   # benchmarks/index.html

Each version runs every scenario twice: once with the skill (the agent reads the skill's SKILL.md and may
use its scripts) and once without (the agent may not read this repository). The order alternates
between conditions across scenarios. Every delivered report is checked against the same requirements by
tools, and the agent's consumption (tokens, tool calls, time) is recorded per run. Results land in
benchmarks/results/<version>/ and the page benchmarks/index.html compares every version measured so far.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmarks"
SKILL = ROOT / "skills" / "powerbi-architect"
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "tools"))
import audit_pbip  # noqa: E402
import new_project  # noqa: E402
import pbir_layout  # noqa: E402

CONDITIONS = ("com", "sem")
REQUIREMENTS = [
    ("abre", "Abre sem erro", "JSON válido nos schemas da Microsoft e todo campo usado pelos visuais existe no modelo"),
    ("bloqueadores", "Zero bloqueadores", "Nenhum achado bloqueador na auditoria"),
    ("harmonia", "Harmonia ≥ 90", "Todas as páginas com nota de harmonia de 90 ou mais"),
    ("acessivel", "Acessível", "Todo visual de dados com título e texto alternativo; texto com contraste ≥ 4,5:1"),
    ("pixel", "Pixel a pixel", "Nenhum achado da crítica do preview: texto cortado, sobreposição, gutters, grade"),
    ("pedido", "Pedido atendido", "As páginas pedidas existem; edições do usuário preservadas; informação mantida"),
    ("numeros", "Números seguros", "Nenhum padrão de DAX ou SQL que devolve número errado (PBI032, PBI070–PBI077)"),
]
NUMBER_RULES = {"PBI032", "PBI070", "PBI071", "PBI072", "PBI073", "PBI074", "PBI075", "PBI076", "PBI077"}


def version() -> str:
    return re.search(r'version:\s*"([^"]+)"', (SKILL / "SKILL.md").read_text(encoding="utf-8")).group(1)


def scenarios() -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted((BENCH / "scenarios").glob("*.json"))]


# ---------------------------------------------------------------------- prepare
MANUAL_VISUAL = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/1.1.0/schema.json",
    "name": "manual0000000000000a",
    "position": {"x": 748, "y": 448, "z": 9000, "width": 508, "height": 248, "tabOrder": 9000},
    "visual": {"visualType": "clusteredBarChart",
               "query": {"queryState": {
                   "Category": {"projections": [{"field": {"Column": {"Expression": {"SourceRef": {"Entity": "dm_cliente"}},
                                                                     "Property": "Segmento"}},
                                                 "queryRef": "dm_cliente.Segmento", "nativeQueryRef": "Segmento"}]},
                   "Y": {"projections": [{"field": {"Measure": {"Expression": {"SourceRef": {"Entity": "_Medidas"}},
                                                               "Property": "Receita"}},
                                          "queryRef": "_Medidas.Receita", "nativeQueryRef": "Receita"}]}}},
               "visualContainerObjects": {
                   "title": [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}},
                                             "text": {"expr": {"Literal": {"Value": "'Receita por segmento'"}}}}}],
                   "general": [{"properties": {"altText": {"expr": {"Literal": {"Value": "'Receita por segmento de cliente'"}}}}}]}}}


def model_only(kit: dict, out: Path, name: str) -> dict:
    """Generate a kit project, keep the model and an empty report; return the preview sample."""
    new_project.generate(kit, out, name, "localhost", "dw", None)
    rp = out / f"{name}.Report"
    pbir = (rp / "definition.pbir").read_text(encoding="utf-8")
    shutil.rmtree(rp)
    rp.mkdir()
    (rp / "definition.pbir").write_text(pbir, encoding="utf-8")
    sample = json.loads((out / "preview-sample.json").read_text(encoding="utf-8"))
    for f in ("layout.json", "README.md", "preview-sample.json"):
        (out / f).unlink()
    shutil.rmtree(out / ".powerbi-architect", ignore_errors=True)
    return sample


def edits_project(out: Path) -> dict:
    """The sales kit, then three edits made by hand after the agent's last edit (benchmark scenario 4)."""
    kit = json.loads((SKILL / "templates" / "starter-kits" / "vendas.json").read_text(encoding="utf-8"))
    new_project.generate(kit, out, "Vendas", "localhost", "dw", None)
    subprocess.run([sys.executable, str(SCRIPTS / "pbip_changes.py"), "accept", str(out), "--quiet"], check=True)
    rep = out / "Vendas.Report"
    for f in sorted(rep.rglob("visual.json")):
        v = json.loads(f.read_text(encoding="utf-8"))
        title = (((v["visual"].get("visualContainerObjects") or {}).get("title") or [{}])[0]
                 .get("properties", {}).get("text", {}).get("expr", {}).get("Literal", {}).get("Value", ""))
        if title == "'Receita por regional'":
            v["position"]["x"], v["position"]["width"] = 232, 500
            v["visual"]["visualContainerObjects"]["title"][0]["properties"]["text"] = \
                {"expr": {"Literal": {"Value": "'Receita por regional (gestão comercial)'"}}}
            f.write_text(json.dumps(v, indent=4), encoding="utf-8")
            manual = f.parent.parent / MANUAL_VISUAL["name"]
            manual.mkdir()
            (manual / "visual.json").write_text(json.dumps(MANUAL_VISUAL, indent=2), encoding="utf-8")
    m = out / "Vendas.SemanticModel" / "definition" / "tables" / "_Medidas.tmdl"
    m.write_text(m.read_text(encoding="utf-8").replace("measure 'Meta % Margem' = 0.30", "measure 'Meta % Margem' = 0.32"),
                 encoding="utf-8")
    return json.loads((out / "preview-sample.json").read_text(encoding="utf-8"))


def legacy_project(out: Path) -> dict:
    """The example model with a deliberately amateur report (benchmark scenario 5)."""
    from legacy_report import make_legacy
    example = ROOT / "examples" / "contas-a-receber"
    out.mkdir(parents=True)
    shutil.copytree(example / "ContasReceber.SemanticModel", out / "ContasReceber.SemanticModel")
    shutil.copy(example / "ContasReceber.pbip", out / "ContasReceber.pbip")
    make_legacy(example / "ContasReceber.Report", out / "ContasReceber.Report")
    return json.loads((example / "preview-sample.json").read_text(encoding="utf-8"))


PROMPT = {
    "com": ("You are working in the folder {folder} . It holds a Power BI project (PBIP).\n\n"
            "Task from the user (in Portuguese): \"{pedido}\"\n\n"
            "Use the Agent Skill at {skill}: read its SKILL.md first and follow it, including its references and "
            "scripts (run them with python3). Do not read anything else under {repo} outside your working folder "
            "(no examples/, evals/, benchmarks/, tests/, docs/, tools/). Write only inside your working folder. Do not ask questions: "
            "there is no human in this exercise, so make reasonable assumptions, skip human gates, and note the "
            "assumptions. When finished, reply with a short summary: what you changed, assumptions, what you checked."),
    "sem": ("You are working in the folder {folder} . It holds a Power BI project (PBIP).\n\n"
            "Task from the user (in Portuguese): \"{pedido}\"\n\n"
            "Use your own knowledge of Power BI, PBIP and the PBIR format. Do not read anything under {repo} outside "
            "your working folder. "
            "Write only inside your working folder. Do not ask questions: there is no human in this exercise, so "
            "make reasonable assumptions and note them. When finished, reply with a short summary: what you "
            "changed, assumptions, what you checked."),
}


def prepare(out: Path) -> None:
    v = version()
    base = out / v
    if base.exists():
        shutil.rmtree(base)
    (base / "_amostras").mkdir(parents=True)
    runs = []
    for i, s in enumerate(scenarios()):
        order = CONDITIONS if i % 2 == 0 else CONDITIONS[::-1]        # alternate who goes first
        for cond in order:
            folder = base / f"{s['id']}-{cond}"
            if s["tipo"] == "relatorio":
                kit = json.loads((ROOT / s["modelo"]).read_text(encoding="utf-8"))
                sample = model_only(kit, folder, s["projeto"])
            elif s["tipo"] == "edicoes":
                sample = edits_project(folder)
            else:
                sample = legacy_project(folder)
            (base / "_amostras" / f"{s['id']}.json").write_text(json.dumps(sample, ensure_ascii=False), encoding="utf-8")
            runs.append({"run": f"{s['id']}-{cond}", "cenario": s["id"], "condicao": cond, "pasta": str(folder),
                         "prompt": PROMPT[cond].format(folder=folder, pedido=s["pedido"], skill=SKILL, repo=ROOT)})
    (base / "runs.json").write_text(json.dumps(runs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] version {v}: {len(runs)} workspaces in {base}; prompts in {base / 'runs.json'}")


# ---------------------------------------------------------------------- record
def results_dir(v: str | None = None) -> Path:
    return BENCH / "results" / (v or version())


def record(run: str, tokens: int, tools: int, seconds: float, model: str) -> None:
    d = results_dir()
    d.mkdir(parents=True, exist_ok=True)
    f = d / "consumo.json"
    usage = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    usage[run] = {"tokens": tokens, "ferramentas": tools, "segundos": round(seconds, 1), "modelo": model}
    f.write_text(json.dumps(usage, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[ok] {run}: {tokens:,} tokens, {tools} tool call(s), {seconds:.0f} s")


# ---------------------------------------------------------------------- score
def field_refs(obj, out: set) -> None:
    """(entity, property) of every field a visual uses."""
    if isinstance(obj, dict):
        expr = obj.get("Expression")
        if isinstance(expr, dict) and "Property" in obj:
            ent = (expr.get("SourceRef") or {}).get("Entity")
            if ent:
                out.add((ent, obj["Property"]))
        for v in obj.values():
            field_refs(v, out)
    elif isinstance(obj, list):
        for v in obj:
            field_refs(v, out)


def opens_cleanly(folder: Path) -> tuple[bool, str]:
    names: set = set()
    for d in folder.rglob("*.SemanticModel/definition"):
        m = audit_pbip.parse_model(d)
        for t in m.tables:
            names |= {(t.name, c.name) for c in t.columns} | {(t.name, x.name) for x in t.measures}
            names |= {(t.name, lv) for lv in t.level_columns}
            names |= {(t.name, h) for h in re.findall(r"^\thierarchy\s+'?([^'\n]+)'?", t.file.read_text(encoding="utf-8"), re.M)}
    used: set = set()
    bad_json = []
    for f in folder.rglob("*.Report/definition/**/*.json"):
        try:
            field_refs(json.loads(f.read_text(encoding="utf-8-sig")), used)
        except ValueError:
            bad_json.append(f.name)
    missing = sorted(f"{e}[{p}]" for e, p in used - names)
    schema_errors = 0
    try:
        import validate_schemas as vs
        from referencing import Registry
        reg = Registry(retrieve=vs.retrieve)
        for f in folder.rglob("*.Report/**/*.json"):
            try:
                schema_errors += len(vs.validate(f, reg))
            except ValueError:
                schema_errors += 1
    except ImportError:
        pass
    ok = not bad_json and not missing and not schema_errors
    why = "; ".join(filter(None, [f"JSON inválido: {', '.join(bad_json[:3])}" if bad_json else "",
                                  f"campos inexistentes: {', '.join(missing[:4])}" if missing else "",
                                  f"{schema_errors} erro(s) de schema" if schema_errors else ""]))
    return ok, why


def critique(folder: Path, sample: dict) -> tuple[int | None, list[str]]:
    from preview_pbir import Preview, critique as crit
    reports = [r for r in folder.glob("*.Report") if (r / "definition" / "pages").exists()]
    if not reports:
        return None, []
    try:
        found = crit(Preview(reports[0], sample))
    except Exception as e:                                   # noqa: BLE001 - a broken report still gets a score
        return 1, [f"preview falhou: {e}"]
    if found is None:
        return None, []
    lines = sorted({f"{c['page']} › {c['type']}: [{c['kind']}] {c['message']}" for c in found})
    return len(lines), lines


def page_names(folder: Path) -> list[str]:
    out = []
    for pj in folder.glob("*.Report/definition/pages/*/page.json"):
        try:
            out.append(json.loads(pj.read_text(encoding="utf-8-sig")).get("displayName", ""))
        except ValueError:
            pass
    return out


def visual_fields(report: Path) -> set:
    used: set = set()
    for f in report.rglob("visual.json"):
        try:
            field_refs(json.loads(f.read_text(encoding="utf-8-sig")).get("visual", {}).get("query", {}), used)
        except ValueError:
            pass
    return used


def request_met(s: dict, folder: Path, legacy_fields: set) -> tuple[bool, str]:
    names = page_names(folder)
    missing = [p for p in s["paginas"] if not any(re.search(p, n, re.I) for n in names)]
    problems = [f"falta página /{p}/" for p in missing]
    if s["tipo"] == "edicoes":
        rep = folder / "Vendas.Report"
        vis = []
        for f in rep.rglob("visual.json"):
            try:
                vis.append((f, json.loads(f.read_text(encoding="utf-8-sig"))))
            except ValueError:
                pass
        mine = [v for f, v in vis if (((v.get("visual") or {}).get("visualContainerObjects") or {}).get("title") or [{}])[0]
                .get("properties", {}).get("text", {}).get("expr", {}).get("Literal", {}).get("Value")
                == "'Receita por regional (gestão comercial)'"]
        if not mine or mine[0]["position"]["width"] != 500 or mine[0]["position"]["x"] != 232:
            problems.append("o gráfico editado à mão perdeu título, largura ou posição")
        copies = [f for f, v in vis if f.parent.name == MANUAL_VISUAL["name"]]
        if not copies:
            problems.append("o gráfico criado à mão sumiu")
        m = (folder / "Vendas.SemanticModel/definition/tables/_Medidas.tmdl").read_text(encoding="utf-8")
        if "measure 'Meta % Margem' = 0.32" not in m:
            problems.append("a meta alterada à mão foi desfeita")
    if s["tipo"] == "reestilizar":
        after = visual_fields(folder / "ContasReceber.Report")
        lost = sorted(f"{e}[{p}]" for e, p in legacy_fields - after)
        if lost:
            problems.append(f"informação perdida: {', '.join(lost)}")
    return not problems, "; ".join(problems)


def score_run(s: dict, folder: Path, sample: dict, legacy_fields: set, baseline: frozenset = frozenset()) -> dict:
    """`baseline`: critique lines the starting project already had and the agent must not change (scenario 4:
    a grid finding caused by the user's own edit). Only new findings count."""
    issues = audit_pbip.audit(folder)
    scores = audit_pbip.harmony(folder, issues)
    rules = {i["rule"] for i in issues}
    sev = {k: sum(1 for i in issues if i["severity"] == k) for k in ("BLOCKER", "IMPORTANT", "SUGGESTION")}
    opens, why_open = opens_cleanly(folder)
    n_crit, crit_lines = critique(folder, sample)
    if n_crit is not None and baseline:
        crit_lines = [x for x in crit_lines if x not in baseline]
        n_crit = len(crit_lines)
    met, why_req = request_met(s, folder, legacy_fields)
    req = {
        "abre": [opens, why_open],
        "bloqueadores": [sev["BLOCKER"] == 0, f"{sev['BLOCKER']} bloqueador(es)" if sev["BLOCKER"] else ""],
        "harmonia": [bool(scores) and all(x >= 90 for _, _, x in scores),
                     ", ".join(f"{p} {x}" for _, p, x in scores if x < 90)],
        "acessivel": [not rules & {"PBI019", "PBI054", "PBI056"}, ", ".join(sorted(rules & {"PBI019", "PBI054", "PBI056"}))],
        "pixel": [n_crit == 0 if n_crit is not None else None, f"{n_crit} achado(s)" if n_crit else ""],
        "pedido": [met, why_req],
        "numeros": [not rules & NUMBER_RULES, ", ".join(sorted(rules & NUMBER_RULES))],
    }
    return {"requisitos": req,
            "metricas": {"harmonia_media": round(sum(x for _, _, x in scores) / len(scores), 1) if scores else 0,
                         "paginas": len(scores), "achados": sev, "critica": n_crit,
                         "regras": sorted(rules)},
            "critica_detalhe": crit_lines[:30]}


def render_images(folder: Path, sample: dict, dest: Path, prefix: str) -> list[str]:
    """First two pages of the delivered report, as PNGs (1280 wide)."""
    from preview_pbir import Preview, find_browser
    browser = find_browser()
    reports = [r for r in folder.glob("*.Report") if (r / "definition" / "pages").exists()]
    if not browser or not reports:
        return []
    import tempfile
    out = []
    try:
        pages = Preview(reports[0], sample).pages()
    except Exception:                                          # noqa: BLE001
        return []
    for i, (_t, w, h, body) in enumerate(pages[:2]):
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "p.html"
            page.write_text(Preview.document(body, margin=0), encoding="utf-8")
            png = dest / f"{prefix}-p{i + 1}.png"
            subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-sandbox",
                            f"--user-data-dir={Path(tmp) / 'profile'}", f"--window-size={w},{h}",
                            f"--screenshot={png}", page.as_uri()], capture_output=True, timeout=120, check=False)
            if png.exists():
                out.append(png.name)
    return out


def score(out: Path) -> None:
    v = version()
    base = out / v
    runs = json.loads((base / "runs.json").read_text(encoding="utf-8"))
    d = results_dir(v)
    (d / "imagens").mkdir(parents=True, exist_ok=True)
    usage = json.loads((d / "consumo.json").read_text(encoding="utf-8")) if (d / "consumo.json").exists() else {}
    from legacy_report import make_legacy
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        legacy_fields = visual_fields(make_legacy(ROOT / "examples" / "contas-a-receber" / "ContasReceber.Report",
                                                  Path(tmp) / "L.Report"))
    by_id = {s["id"]: s for s in scenarios()}
    baselines = {}
    for s in by_id.values():
        if s["tipo"] == "edicoes":                     # the user's edits stay, and so do the findings they cause
            with tempfile.TemporaryDirectory() as tmp:
                sample = edits_project(Path(tmp) / "b")
                baselines[s["id"]] = frozenset(critique(Path(tmp) / "b", sample)[1])
    results = []
    for r in runs:
        s = by_id[r["cenario"]]
        folder = Path(r["pasta"])
        sample = json.loads((base / "_amostras" / f"{s['id']}.json").read_text(encoding="utf-8"))
        res = score_run(s, folder, sample, legacy_fields, baselines.get(s["id"], frozenset()))
        res.update({"run": r["run"], "cenario": s["id"], "nome": s["nome"], "condicao": r["condicao"],
                    "consumo": usage.get(r["run"]), "imagens": render_images(folder, sample, d / "imagens", r["run"])})
        met = [x[0] for x in res["requisitos"].values() if x[0] is not None]
        res["atendidos"], res["avaliados"] = sum(met), len(met)
        results.append(res)
        print(f"{r['run']:<26} {res['atendidos']}/{res['avaliados']} requisitos · harmonia {res['metricas']['harmonia_media']}")
    summary = {}
    for cond in CONDITIONS:
        rs = [x for x in results if x["condicao"] == cond]
        us = [x["consumo"] for x in rs if x["consumo"]]
        avg = lambda k: round(sum(u[k] for u in us) / len(us), 1) if us else None  # noqa: E731
        summary[cond] = {
            "execucoes": len(rs),
            "requisitos_atendidos": sum(x["atendidos"] for x in rs), "requisitos_avaliados": sum(x["avaliados"] for x in rs),
            "entregas_completas": sum(1 for x in rs if x["atendidos"] == x["avaliados"]),
            "harmonia_media": round(sum(x["metricas"]["harmonia_media"] for x in rs) / len(rs), 1) if rs else 0,
            "achados_medios": round(sum(sum(x["metricas"]["achados"].values()) for x in rs) / len(rs), 1) if rs else 0,
            "tokens_medios": avg("tokens"), "ferramentas_medias": avg("ferramentas"), "segundos_medios": avg("segundos"),
            "por_requisito": {k: sum(1 for x in rs if x["requisitos"][k][0]) for k, _, _ in REQUIREMENTS},
        }
    data = {"versao": v, "data": dt.date.today().isoformat(),
            "modelo": sorted({u["modelo"] for u in usage.values()}) if usage else [],
            "requisitos": [{"id": k, "nome": n, "descricao": t} for k, n, t in REQUIREMENTS],
            "resumo": summary, "execucoes": results}
    (d / "resultados.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_version_readme(data, d)
    print(f"[ok] {d / 'resultados.json'}")


def write_version_readme(data: dict, d: Path) -> None:
    c, s = data["resumo"]["com"], data["resumo"]["sem"]
    pct = lambda x: f"{100 * x['requisitos_atendidos'] / max(x['requisitos_avaliados'], 1):.0f}%"  # noqa: E731
    fmt = lambda v, unit="": "—" if v is None else f"{v:,.0f}{unit}".replace(",", ".")  # noqa: E731
    lines = [f"# Benchmark da versão {data['versao']}", "",
             f"Medido em {data['data']}, com {', '.join(data['modelo']) or 'o mesmo modelo de IA'} nas duas condições. "
             "Página com gráficos e imagens: [`benchmarks/index.html`](../../index.html).", "",
             "| | Com a skill | Sem a skill |", "|---|---|---|",
             f"| Requisitos atendidos | **{c['requisitos_atendidos']} de {c['requisitos_avaliados']}** ({pct(c)}) | "
             f"{s['requisitos_atendidos']} de {s['requisitos_avaliados']} ({pct(s)}) |",
             f"| Entregas que atendem a tudo | **{c['entregas_completas']} de {c['execucoes']}** | {s['entregas_completas']} de {s['execucoes']} |",
             f"| Harmonia média | **{c['harmonia_media']:g}** | {s['harmonia_media']:g} |",
             f"| Achados médios da auditoria | **{c['achados_medios']:g}** | {s['achados_medios']:g} |",
             f"| Tokens por execução (média) | {fmt(c['tokens_medios'])} | {fmt(s['tokens_medios'])} |",
             f"| Chamadas de ferramenta (média) | {fmt(c['ferramentas_medias'])} | {fmt(s['ferramentas_medias'])} |",
             f"| Tempo por execução (média) | {fmt(c['segundos_medios'], ' s')} | {fmt(s['segundos_medios'], ' s')} |", "",
             "## Por requisito", "", "| Requisito | Com a skill | Sem a skill |", "|---|---|---|"]
    for r in data["requisitos"]:
        lines.append(f"| {r['nome']} — {r['descricao']} | {c['por_requisito'][r['id']]} de {c['execucoes']} | "
                     f"{s['por_requisito'][r['id']]} de {s['execucoes']} |")
    lines += ["", "## Por execução", "", "| Cenário | Condição | Requisitos | Harmonia | Tokens | O que faltou |",
              "|---|---|---|---|---|---|"]
    for x in data["execucoes"]:
        why = "; ".join(f"{k}: {v[1]}" for k, v in x["requisitos"].items() if v[0] is False and v[1]) or "—"
        tok = fmt((x["consumo"] or {}).get("tokens"))
        lines.append(f"| {x['nome']} | {'com' if x['condicao'] == 'com' else 'sem'} a skill | {x['atendidos']}/{x['avaliados']} | "
                     f"{x['metricas']['harmonia_media']:g} | {tok} | {why[:160]} |")
    (d / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------- report
def report() -> None:
    versions = []
    for f in sorted((BENCH / "results").glob("*/resultados.json"),
                    key=lambda p: [int(x) for x in re.findall(r"\d+", p.parent.name)]):
        versions.append(json.loads(f.read_text(encoding="utf-8")))
    if not versions:
        sys.exit("no results yet: run prepare, the runs, record and score first")
    template = (BENCH / "template.html").read_text(encoding="utf-8")
    page = template.replace("/*__DATA__*/null", json.dumps(versions, ensure_ascii=False))
    (BENCH / "index.html").write_text(page, encoding="utf-8")
    print(f"[ok] {BENCH / 'index.html'}: {len(versions)} version(s)")


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except ValueError:
                pass
    ap = argparse.ArgumentParser(prog="benchmarks/run.py", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--out", type=Path, default=ROOT / ".tmp" / "benchmark")
    r = sub.add_parser("record")
    r.add_argument("run")
    r.add_argument("--tokens", type=int, required=True)
    r.add_argument("--tools", type=int, required=True)
    r.add_argument("--seconds", type=float, required=True)
    r.add_argument("--model", default="")
    s = sub.add_parser("score")
    s.add_argument("--out", type=Path, default=ROOT / ".tmp" / "benchmark")
    sub.add_parser("report")
    a = ap.parse_args()
    if a.cmd == "prepare":
        prepare(a.out)
    elif a.cmd == "record":
        record(a.run, a.tokens, a.tools, a.seconds, a.model)
    elif a.cmd == "score":
        score(a.out)
    else:
        report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
