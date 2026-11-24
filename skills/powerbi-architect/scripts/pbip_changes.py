#!/usr/bin/env python3
"""pbip_changes.py — notice what the user changed by hand in a PBIP project (part of the powerbi-architect skill).

Python 3.9+ standard library only. Offline. Reads the PBIP files; writes only .powerbi-architect/.

    python pbip_changes.py status [REPO] [--hook]   # what changed by hand since the last snapshot
    python pbip_changes.py accept [REPO]            # take a snapshot (after the agent's own edits)
    python pbip_changes.py log    [REPO]            # the journal of changes made by hand

The user edits the project in Power BI Desktop or in the files between two requests; the agent must
see those edits without being told, keep them, and build on them. This script keeps a semantic snapshot
of every model and report in the repository (tables, columns, measures with their DAX, relationships,
roles, pages, visuals with type, position, title and fields, themes) and describes the difference in
business terms: "medida 'Receita' — expressão mudou", "Visão Geral › barras "Receita por regional" —
movido (x 232 → 240)".

`pbi_graph.py install` wires it into Claude Code:
- UserPromptSubmit and SessionStart run `status --hook`: when something changed by hand, the summary goes
  into the agent's context, is appended to .powerbi-architect/alteracoes.md, and becomes the new snapshot.
- PostToolUse (after the agent's own edits and commands) runs `accept`, so the agent's work is never
  reported as the user's.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
import sys
from pathlib import Path

STATE_DIR = ".powerbi-architect"
SNAPSHOT = "snapshot.json"
JOURNAL = "alteracoes.md"
SKIP = {".git", "node_modules", STATE_DIR, "powerbi-graph", ".pbi", "__pycache__"}
MAX_LINES = 30


# ---------------------------------------------------------------------- reading the project
def projects(repo: Path) -> list[Path]:
    """Every *.SemanticModel and *.Report folder in the repository."""
    out = []
    for p in sorted(repo.rglob("*")):
        if p.is_dir() and p.suffix in (".SemanticModel", ".Report") and not (SKIP & set(p.relative_to(repo).parts)):
            out.append(p)
    return out


def unquote(name: str) -> str:
    name = name.strip()
    return name[1:-1].replace("''", "'") if name.startswith("'") and name.endswith("'") else name


OBJ = re.compile(r"^\t(measure|column|hierarchy|partition)\s+('(?:[^']|'')+'|[^\s=]+)\s*(?:=\s*(.*))?$")


def read_tmdl_table(text: str) -> dict:
    """Columns and measures of one table file: {kind: {name: {prop: value}}} with the DAX of each measure."""
    out: dict = {"measure": {}, "column": {}}
    current = None
    for line in text.splitlines():
        m = OBJ.match(line)
        if m:
            kind, name, expr = m.groups()
            current = None
            if kind in out:
                current = out[kind].setdefault(unquote(name), {})
                if kind == "measure":
                    current["expressão"] = (expr or "").strip()
            continue
        if current is None or not line.startswith("\t\t"):
            if line.startswith("\t") and not line.startswith("\t\t") and line.strip():
                current = None
            continue
        body = line.strip()
        prop = re.match(r"^(formatString|displayFolder|dataType|isHidden|sortByColumn|summarizeBy)\b:?\s*(.*)$", body)
        if prop:
            current[prop.group(1)] = prop.group(2) or "true"
        elif "expressão" in current and not re.match(r"^\w+:", body) and not body.startswith(("annotation", "///")):
            current["expressão"] = (current["expressão"] + " " + body).strip()
    for m in out["measure"].values():
        m["expressão"] = re.sub(r"\s+", " ", m.get("expressão", ""))
    return out


def read_model(sm: Path) -> dict:
    d = sm / "definition"
    model: dict = {"tabelas": {}, "relacionamentos": [], "papéis": {}}
    for f in sorted((d / "tables").glob("*.tmdl")) if (d / "tables").exists() else []:
        model["tabelas"][f.stem] = read_tmdl_table(f.read_text(encoding="utf-8-sig"))
    rel = d / "relationships.tmdl"
    if rel.exists():
        text = rel.read_text(encoding="utf-8-sig")
        pairs = re.findall(r"fromColumn:\s*(.+)\n\s*toColumn:\s*(.+)", text)
        model["relacionamentos"] = sorted(f"{a.strip()} → {b.strip()}" for a, b in pairs)
    for f in sorted((d / "roles").glob("*.tmdl")) if (d / "roles").exists() else []:
        model["papéis"][f.stem] = hashlib.sha1(f.read_bytes()).hexdigest()[:12]
    return model


def lit(o):
    try:
        v = o["expr"]["Literal"]["Value"]
    except (KeyError, TypeError):
        return None
    return v[1:-1].replace("''", "'") if isinstance(v, str) and v.startswith("'") else v


def field_name(f: dict) -> str:
    kind = next(iter(f), "")
    body = f.get(kind) or {}
    if kind == "Measure":
        return body.get("Property", "?")
    if kind in ("Column", "HierarchyLevel"):
        ent = (body.get("Expression") or {}).get("SourceRef", {}).get("Entity") or \
            (body.get("Expression") or {}).get("Hierarchy", {}).get("Expression", {}).get("SourceRef", {}).get("Entity", "")
        return f"{ent}[{body.get('Property') or body.get('Level')}]"
    if kind == "Aggregation":
        return field_name(body.get("Expression") or {})
    return kind or "?"


def read_report(rp: Path) -> dict:
    pages_dir = rp / "definition" / "pages"
    report: dict = {"páginas": {}, "ordem": [], "tema": ""}
    if not pages_dir.exists():
        return report
    meta = pages_dir / "pages.json"
    if meta.exists():
        try:
            report["ordem"] = json.loads(meta.read_text(encoding="utf-8-sig")).get("pageOrder", [])
        except ValueError:
            pass
    for pj in sorted(pages_dir.glob("*/page.json")):
        try:
            page = json.loads(pj.read_text(encoding="utf-8-sig"))
        except ValueError:
            continue
        visuals = {}
        for vf in sorted((pj.parent / "visuals").glob("*/visual.json")):
            try:
                v = json.loads(vf.read_text(encoding="utf-8-sig"))
            except ValueError:
                continue
            vis = v.get("visual") or {}
            pos = v.get("position") or {}
            title = (vis.get("visualContainerObjects") or {}).get("title", [{}])[0].get("properties", {}).get("text")
            qs = ((vis.get("query") or {}).get("queryState")) or {}
            visuals[vf.parent.name] = {
                "tipo": vis.get("visualType") or ("grupo" if "visualGroup" in v else "?"),
                "posição": [pos.get(k, 0) for k in ("x", "y", "width", "height")],
                "título": lit(title) if lit(title) is not None else (field_name(title["expr"]) if title else ""),
                "campos": sorted(field_name(p.get("field") or {}) for r in qs.values() for p in r.get("projections", [])),
                "formatação": hashlib.sha1(json.dumps([vis.get("objects"), vis.get("visualContainerObjects")],
                                                      sort_keys=True).encode()).hexdigest()[:10],
            }
        report["páginas"][pj.parent.name] = {"nome": page.get("displayName", pj.parent.name),
                                             "oculta": page.get("visibility") == "HiddenInViewMode",
                                             "tamanho": [page.get("width"), page.get("height")],
                                             "visuais": visuals}
    res = rp / "StaticResources" / "RegisteredResources"
    themes = sorted(res.glob("*.json")) if res.exists() else []
    report["tema"] = hashlib.sha1(b"".join(t.read_bytes() for t in themes)).hexdigest()[:12] if themes else ""
    return report


def snapshot(repo: Path) -> dict:
    snap: dict = {}
    for p in projects(repo):
        key = p.relative_to(repo).as_posix()
        snap[key] = read_model(p) if p.suffix == ".SemanticModel" else read_report(p)
    return snap


# ---------------------------------------------------------------------- describing the difference
VISUAL_NAMES = {"clusteredBarChart": "barras", "clusteredColumnChart": "colunas", "lineChart": "linha",
                "card": "cartão", "tableEx": "tabela", "pivotTable": "matriz", "slicer": "segmentação",
                "waterfallChart": "cascata", "scatterChart": "dispersão", "kpi": "KPI", "textbox": "texto",
                "lineClusteredColumnComboChart": "colunas e linha", "pieChart": "pizza", "donutChart": "rosca",
                "shape": "forma", "image": "imagem", "pageNavigator": "navegação", "cardVisual": "cartão"}


def visual_label(v: dict) -> str:
    kind = VISUAL_NAMES.get(v.get("tipo", ""), v.get("tipo", "visual"))
    return f'{kind} "{v["título"]}"' if v.get("título") else kind


def diff_model(name: str, old: dict, new: dict) -> list[str]:
    out = []
    ot, nt = old.get("tabelas", {}), new.get("tabelas", {})
    for t in sorted(set(nt) - set(ot)):
        out.append(f"{name}: tabela '{t}' criada")
    for t in sorted(set(ot) - set(nt)):
        out.append(f"{name}: tabela '{t}' removida")
    for t in sorted(set(ot) & set(nt)):
        for kind, label in (("measure", "medida"), ("column", "coluna")):
            o, n = ot[t].get(kind, {}), nt[t].get(kind, {})
            for x in sorted(set(n) - set(o)):
                extra = f": {n[x]['expressão'][:90]}" if kind == "measure" and n[x].get("expressão") else ""
                out.append(f"{name}: {label} '{x}' criada em {t}{extra}")
            for x in sorted(set(o) - set(n)):
                out.append(f"{name}: {label} '{x}' removida de {t}")
            for x in sorted(set(o) & set(n)):
                changed = [k for k in sorted(set(o[x]) | set(n[x])) if o[x].get(k) != n[x].get(k)]
                if not changed:
                    continue
                parts = []
                for k in changed:
                    if k == "expressão":
                        parts.append(f"expressão mudou para: {n[x].get(k, '')[:90]}")
                    else:
                        parts.append(f"{k}: {o[x].get(k, '—')} → {n[x].get(k, '—')}")
                out.append(f"{name}: {label} '{x}' em {t} — " + "; ".join(parts))
    for r in sorted(set(new.get("relacionamentos", [])) - set(old.get("relacionamentos", []))):
        out.append(f"{name}: relacionamento criado {r}")
    for r in sorted(set(old.get("relacionamentos", [])) - set(new.get("relacionamentos", []))):
        out.append(f"{name}: relacionamento removido {r}")
    op, np_ = old.get("papéis", {}), new.get("papéis", {})
    for r in sorted(set(op) | set(np_)):
        if op.get(r) != np_.get(r):
            state = "criado" if r not in op else "removido" if r not in np_ else "alterado"
            out.append(f"{name}: papel de segurança '{r}' {state}")
    return out


def diff_report(name: str, old: dict, new: dict) -> list[str]:
    out = []
    op, np_ = old.get("páginas", {}), new.get("páginas", {})
    for pid in [p for p in np_ if p not in op]:
        out.append(f"{name}: página '{np_[pid]['nome']}' criada ({len(np_[pid]['visuais'])} visuais)")
    for pid in [p for p in op if p not in np_]:
        out.append(f"{name}: página '{op[pid]['nome']}' removida")
    for pid in [p for p in np_ if p in op]:
        a, b = op[pid], np_[pid]
        where = f"{name} › {b['nome']}"
        if a["nome"] != b["nome"]:
            out.append(f"{name}: página '{a['nome']}' renomeada para '{b['nome']}'")
        if a.get("oculta") != b.get("oculta"):
            out.append(f"{where}: página {'oculta' if b.get('oculta') else 'visível'}")
        av, bv = a["visuais"], b["visuais"]
        for vid in [v for v in bv if v not in av]:
            out.append(f"{where}: {visual_label(bv[vid])} criado em x {bv[vid]['posição'][0]}, y {bv[vid]['posição'][1]}")
        for vid in [v for v in av if v not in bv]:
            out.append(f"{where}: {visual_label(av[vid])} removido")
        for vid in [v for v in bv if v in av]:
            x, y = av[vid], bv[vid]
            parts = []
            if x["tipo"] != y["tipo"]:
                parts.append(f"tipo {VISUAL_NAMES.get(x['tipo'], x['tipo'])} → {VISUAL_NAMES.get(y['tipo'], y['tipo'])}")
            (x0, y0, w0, h0), (x1, y1, w1, h1) = x["posição"], y["posição"]
            if (x0, y0) != (x1, y1):
                parts.append(f"movido ({x0}, {y0}) → ({x1}, {y1})")
            if (w0, h0) != (w1, h1):
                parts.append(f"tamanho {w0}×{h0} → {w1}×{h1}")
            if x["título"] != y["título"]:
                parts.append(f'título "{x["título"]}" → "{y["título"]}"')
            if x["campos"] != y["campos"]:
                added = sorted(set(y["campos"]) - set(x["campos"]))
                gone = sorted(set(x["campos"]) - set(y["campos"]))
                parts.append("campos" + (f" + {', '.join(added)}" if added else "") + (f" − {', '.join(gone)}" if gone else ""))
            if x["formatação"] != y["formatação"] and not parts:
                parts.append("formatação mudou")
            elif x["formatação"] != y["formatação"]:
                parts.append("formatação")
            if parts:
                out.append(f"{where}: {visual_label(x)} — " + "; ".join(parts))
    if old.get("ordem") and new.get("ordem") and old["ordem"] != new["ordem"] and set(old["ordem"]) == set(new["ordem"]):
        names = [np_.get(p, {}).get("nome", p) for p in new["ordem"]]
        out.append(f"{name}: ordem das páginas → {', '.join(names)}")
    if old.get("tema") != new.get("tema"):
        out.append(f"{name}: tema alterado")
    return out


def diff(old: dict, new: dict) -> list[str]:
    out = []
    for key in sorted(set(old) | set(new)):
        short = key.rsplit("/", 1)[-1]
        if key not in old:
            out.append(f"{short}: projeto novo")
        elif key not in new:
            out.append(f"{short}: removido")
        elif key.endswith(".SemanticModel"):
            out += diff_model(short, old[key], new[key])
        else:
            out += diff_report(short, old[key], new[key])
    return out


# ---------------------------------------------------------------------- state
def state_dir(repo: Path) -> Path:
    return repo / STATE_DIR


def load(repo: Path) -> dict | None:
    f = state_dir(repo) / SNAPSHOT
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def save(repo: Path, snap: dict) -> None:
    d = state_dir(repo)
    d.mkdir(exist_ok=True)
    if not (d / ".gitignore").exists():
        (d / ".gitignore").write_text("snapshot.json\n", encoding="utf-8")
    (d / SNAPSHOT).write_text(json.dumps(snap, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def journal(repo: Path, lines: list[str]) -> Path:
    f = state_dir(repo) / JOURNAL
    head = "" if f.exists() else ("# Alterações feitas à mão\n\nRegistro automático do que foi mudado no Power BI "
                                  "Desktop ou nos arquivos, fora da IA. A IA lê este resumo antes de cada pedido.\n")
    stamp = _dt.datetime.now().strftime("%d/%m/%Y %H:%M")
    with open(f, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(head + f"\n## {stamp}\n\n" + "".join(f"- {ln}\n" for ln in lines))
    return f


def status(repo: Path, hook: bool) -> int:
    current = snapshot(repo)
    previous = load(repo)
    if previous is None:
        save(repo, current)
        if not hook:
            print("Primeira foto do projeto salva. A partir de agora, mudanças feitas à mão aparecem aqui.")
        return 0
    changes = diff(previous, current)
    if not changes:
        if not hook:
            print("Nada mudou à mão desde a última foto.")
        return 0
    if hook:
        f = journal(repo, changes)
        save(repo, current)
        shown = changes[:MAX_LINES]
        print("[powerbi-architect] O usuário mudou o projeto à mão (Power BI Desktop ou arquivos) desde a sua "
              "última edição. Trate isto como a versão atual e intencional: preserve, não desfaça e construa em "
              "cima; se o pedido contradisser alguma mudança, pergunte antes.")
        for ln in shown:
            print(f"- {ln}")
        if len(changes) > len(shown):
            print(f"- … mais {len(changes) - len(shown)} mudança(s) em {f.relative_to(repo).as_posix()}")
        return 0
    for ln in changes:
        print(f"- {ln}")
    print(f"\n{len(changes)} mudança(s) feitas à mão desde a última foto. "
          "`pbip_changes.py accept` registra o estado atual.")
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdin, sys.stdout, sys.stderr):   # Windows consoles default to a legacy code page
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except ValueError:
                pass
    ap = argparse.ArgumentParser(prog="pbip_changes.py", description="Notice edits made by hand in PBIP projects.")
    ap.add_argument("command", choices=("status", "accept", "log"))
    ap.add_argument("repo", nargs="?", type=Path, default=Path("."))
    ap.add_argument("--hook", action="store_true",
                    help="Claude Code hook mode: silent unless something changed; then report, journal and accept")
    ap.add_argument("--quiet", action="store_true", help="accept: print nothing")
    args = ap.parse_intermixed_args(argv)   # flags before or after the folder, on every Python version
    repo = args.repo.resolve()
    if args.hook:
        try:
            event = json.loads(sys.stdin.read() or "{}") if not sys.stdin.isatty() else {}
            repo = Path(event.get("cwd") or repo).resolve()
        except ValueError:
            pass
    if args.command == "status":
        return status(repo, args.hook)
    if args.command == "accept":
        save(repo, snapshot(repo))
        if not args.quiet:
            print(f"[ok] foto do projeto salva em {STATE_DIR}/{SNAPSHOT}")
        return 0
    f = state_dir(repo) / JOURNAL
    print(f.read_text(encoding="utf-8") if f.exists() else "Nenhuma alteração feita à mão registrada ainda.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
