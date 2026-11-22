#!/usr/bin/env python3
"""new_project.py — start a PBIP project from a domain starter kit (part of the powerbi-architect skill).

Python 3.9+ standard library only. Offline. Writes only inside the output folder, which must not exist.

    python new_project.py --list
    python new_project.py <kit> <OutFolder> [--name Name] [--primary "#RRGGBB"] [--server S] [--database D]

Kits live in templates/starter-kits/<kit>.json (vendas, financeiro, rh, estoque). Each one describes a
star schema (ft_ facts, dm_ dimensions, SQL views as sources), documented measures with format strings
and display folders, and the report pages as a layout spec. The script writes:

- <Name>.pbip, <Name>.SemanticModel (TMDL): parameters Servidor/Banco, one native SQL query per table,
  dm_calendario (marked date table), _Medidas (+ "Texto Atualizacao"), _Documentacao and _Cargas
  (INFO.VIEW), relationships;
- <Name>.Report (PBIR) built by pbir_layout.py: the app shell, the kit's pages, a Documentação page,
  the theme (the skill's, or one made from --primary by make_theme.py);
- layout.json and preview-sample.json (edit and rebuild), README.md.

The SQL views named in the kit do not exist in your warehouse: map them (references/power-query.md)
before refreshing. Then run the loop of SKILL.md §6: preview, look, audit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KITS = HERE.parent / "templates" / "starter-kits"
THEME = HERE.parent / "templates" / "theme" / "powerbi-architect-acessivel.json"
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric"
sys.path.insert(0, str(HERE))
import pbir_layout  # noqa: E402



def write_lf(path: Path, text: str) -> None:
    """UTF-8 with LF line endings on every OS (write_text has no newline= before Python 3.10)."""
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)

def hid(*parts: str) -> str:
    return hashlib.sha1("/".join(parts).encode()).hexdigest()[:20]


def q(name: str) -> str:
    return name if re.fullmatch(r"[^\W\d]\w*", name) else "'" + name.replace("'", "''") + "'"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_lf(path, text)


def wjson(path: Path, obj) -> None:
    write(path, json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def column(c: dict, inferred: bool = False) -> str:
    lines = [f"\tcolumn {q(c['name'])}", f"\t\tdataType: {c['type']}"]
    if c.get("key"):
        lines.append("\t\tisKey")
    if c.get("hidden"):
        lines.append("\t\tisHidden")
    if c.get("format"):
        lines.append(f"\t\tformatString: {c['format']}")
    lines.append("\t\tsummarizeBy: none")
    if inferred:
        lines += ["\t\tisNameInferred", "\t\tisDataTypeInferred", f"\t\tsourceColumn: [{c['name']}]"]
    else:
        lines.append(f"\t\tsourceColumn: {c['name']}")
    if c.get("sortBy"):
        lines.append(f"\t\tsortByColumn: {q(c['sortBy'])}")
    out = "\n".join(lines) + "\n"
    return (f"\t/// {c['description']}\n" + out) if c.get("description") else out


def sql_of(table: dict) -> str:
    cols = []
    for c in table["columns"]:
        expr = c.get("sql") or f"t.{c['name']}"
        cols.append(expr if expr == f"t.{c['name']}" else f"{expr} AS [{c['name']}]")
    where = f" WHERE {table['where']}" if table.get("where") else ""
    return f"SELECT {', '.join(cols)} FROM {table['source']} AS t{where}"


def partition(name: str, sql: str) -> str:
    body = sql.replace('"', '""')
    return (f"\tpartition {q(name)} = m\n\t\tmode: import\n\t\tsource =\n\t\t\t\tlet\n"
            f"\t\t\t\t    Fonte = Value.NativeQuery(Sql.Database(Servidor, Banco), \"{body}\", null, "
            f"[EnableFolding = true])\n\t\t\t\tin\n\t\t\t\t    Fonte\n")


def measure(m: dict) -> str:
    expr = m["expr"]
    head = (f"\tmeasure {q(m['name'])} =\n" + "\n".join("\t\t\t" + ln for ln in expr.split("\n"))
            if "\n" in expr else f"\tmeasure {q(m['name'])} = {expr}")
    lines = [f"\t/// {m['description']}", head]
    if m.get("format"):
        lines.append(f"\t\tformatString: {m['format']}")
    lines.append(f"\t\tdisplayFolder: {m.get('folder', 'Medidas')}")
    return "\n".join(lines) + "\n"


CALENDAR = (
    "/// Calendário do ano anterior até o fim do ano corrente. Marcado como tabela de datas.\n"
    "table dm_calendario\n\tdataCategory: Time\n\n"
    + column({"name": "Data", "type": "dateTime", "key": True, "format": "dd/mm/yyyy"}, True) + "\n"
    + column({"name": "Ano", "type": "int64", "format": "0"}, True) + "\n"
    + column({"name": "Mês Nº", "type": "int64", "hidden": True}, True) + "\n"
    + column({"name": "Mês", "type": "string", "sortBy": "Mês Nº"}, True) + "\n"
    + column({"name": "Ano-Mês Nº", "type": "int64", "hidden": True}, True) + "\n"
    + column({"name": "Ano-Mês", "type": "string", "sortBy": "Ano-Mês Nº"}, True) + "\n"
    + "\thierarchy 'Ano > Mês'\n\n\t\tlevel Ano\n\t\t\tcolumn: Ano\n\n\t\tlevel Mês\n\t\t\tcolumn: Mês\n\n"
    + "\tpartition dm_calendario = calculated\n\t\tmode: import\n\t\tsource =\n"
    + "\t\t\t\tVAR _fim = DATE ( YEAR ( TODAY () ), 12, 31 )\n"
    + "\t\t\t\tVAR _inicio = DATE ( YEAR ( TODAY () ) - 1, 1, 1 )\n"
    + "\t\t\t\tRETURN\n\t\t\t\t    ADDCOLUMNS (\n\t\t\t\t        CALENDAR ( _inicio, _fim ),\n"
    + "\t\t\t\t        \"Ano\", YEAR ( [Date] ),\n\t\t\t\t        \"Mês Nº\", MONTH ( [Date] ),\n"
    + "\t\t\t\t        \"Mês\", FORMAT ( [Date], \"mmm\" ),\n"
    + "\t\t\t\t        \"Ano-Mês Nº\", YEAR ( [Date] ) * 100 + MONTH ( [Date] ),\n"
    + "\t\t\t\t        \"Ano-Mês\", FORMAT ( [Date], \"mmm/yy\" ),\n"
    + "\t\t\t\t        \"Data\", [Date]\n\t\t\t\t    )\n")

DOC_TABLES = {
    "_Documentacao": (
        "/// Catálogo das medidas visíveis, gerado a partir das descrições do modelo.\n"
        "table _Documentacao\n\n"
        + "".join(column({"name": c, "type": "string"}, True) + "\n"
                  for c in ("Tabela", "Pasta", "Medida", "Descrição", "Expressão DAX", "Formato"))
        + "\tpartition _Documentacao = calculated\n\t\tmode: import\n\t\tsource =\n"
        + "\t\t\t\tSELECTCOLUMNS (\n\t\t\t\t    FILTER ( INFO.VIEW.MEASURES (), NOT [IsHidden] ),\n"
        + "\t\t\t\t    \"Tabela\", [Table],\n\t\t\t\t    \"Pasta\", [DisplayFolder],\n"
        + "\t\t\t\t    \"Medida\", [Name],\n\t\t\t\t    \"Descrição\", [Description],\n"
        + "\t\t\t\t    \"Expressão DAX\", [Expression],\n\t\t\t\t    \"Formato\", [FormatString]\n\t\t\t\t)\n"),
    "_Cargas": (
        "/// Tabelas carregadas das fontes e a data da última carga.\n"
        "table _Cargas\n\n"
        + "".join(column({"name": c, "type": "string"}, True) + "\n" for c in ("Tabela", "Descrição", "Armazenamento"))
        + column({"name": "Última Carga", "type": "dateTime", "format": "dd/mm/yyyy hh:nn"}, True) + "\n"
        + "\tpartition _Cargas = calculated\n\t\tmode: import\n\t\tsource =\n"
        + "\t\t\t\tVAR _carga = MAX ( '_Medidas'[Data Carga] )\n\t\t\t\tRETURN\n\t\t\t\t    ADDCOLUMNS (\n"
        + "\t\t\t\t        SELECTCOLUMNS (\n"
        + "\t\t\t\t            FILTER ( INFO.VIEW.TABLES (), ISBLANK ( [Expression] ) && LEFT ( [Name], 1 ) <> \"_\" ),\n"
        + "\t\t\t\t            \"Tabela\", [Name], \"Descrição\", [Description], \"Armazenamento\", [StorageMode]\n"
        + "\t\t\t\t        ),\n\t\t\t\t        \"Última Carga\", _carga\n\t\t\t\t    )\n"),
}

UPDATED = {"name": "Texto Atualizacao", "description": "Data e hora da última carga, para a barra do topo.",
           "expr": "\"Atualizado em \" & FORMAT ( MAX ( '_Medidas'[Data Carga] ), \"dd/mm/yyyy hh:nn\" )",
           "folder": "Títulos", "sample": "Atualizado em 21/11/2026 08:00"}

DOC_PAGE = {"name": "Documentação", "icon": "file-description", "slicers": [], "rows": [
    {"height": 616, "split": [3, 2], "visuals": [
        {"type": "tableEx", "key": "medidas", "title": "Medidas",
         "columns": ["_Documentacao[Pasta]", "_Documentacao[Medida]", "_Documentacao[Descrição]",
                     "_Documentacao[Expressão DAX]"],
         "alt": "Catálogo de medidas com pasta, descrição e expressão DAX"},
        {"type": "tableEx", "key": "cargas", "title": "Cargas",
         "columns": ["_Cargas[Tabela]", "_Cargas[Descrição]", "_Cargas[Armazenamento]", "_Cargas[Última Carga]"],
         "alt": "Tabelas carregadas e data da última carga"}]}]}


def kits() -> dict[str, dict]:
    return {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in sorted(KITS.glob("*.json"))}


def generate(kit: dict, out: Path, name: str, server: str, database: str, primary: str | None) -> list[str]:
    if out.exists() and any(out.iterdir()):
        raise ValueError(f"{out} already exists and is not empty")
    sm, rp = out / f"{name}.SemanticModel", out / f"{name}.Report"
    notes = []
    wjson(out / f"{name}.pbip", {"$schema": f"{SCHEMA}/pbip/pbipProperties/1.0.0/schema.json", "version": "1.0",
                                 "artifacts": [{"report": {"path": f"{name}.Report"}}],
                                 "settings": {"enableAutoRecovery": True}})
    wjson(sm / "definition.pbism", {"$schema": f"{SCHEMA}/item/semanticModel/definitionProperties/1.0.0/schema.json",
                                    "version": "4.0", "settings": {}})
    wjson(rp / "definition.pbir", {"$schema": f"{SCHEMA}/item/report/definitionProperties/2.0.0/schema.json",
                                   "version": "4.0", "datasetReference": {"byPath": {"path": f"../{name}.SemanticModel"}}})
    write(out / ".gitignore", "**/.pbi/localSettings.json\n**/.pbi/cache.abf\n")

    d = sm / "definition"
    write(d / "database.tmdl", "database\n\tcompatibilityLevel: 1601\n")
    write(d / "model.tmdl", "model Model\n\tculture: pt-BR\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n"
                            "\tdiscourageImplicitMeasures\n\tsourceQueryCulture: pt-BR\n\tdataAccessOptions\n"
                            "\t\tlegacyRedirects\n\t\treturnErrorValuesAsNull\n\nqueryGroup Parametros\n\n"
                            "\tannotation PBI_QueryGroupOrder = 0\n\nannotation __PBI_TimeIntelligenceEnabled = 0\n")
    write(d / "expressions.tmdl",
          f"/// Servidor do data warehouse.\nexpression Servidor = \"{server}\" meta [IsParameterQuery=true, "
          "Type=\"Text\", IsParameterQueryRequired=true]\n\tqueryGroup: Parametros\n\n\tannotation PBI_ResultType = Text\n\n"
          f"/// Banco de dados do data warehouse.\nexpression Banco = \"{database}\" meta [IsParameterQuery=true, "
          "Type=\"Text\", IsParameterQueryRequired=true]\n\tqueryGroup: Parametros\n\n\tannotation PBI_ResultType = Text\n")

    rels = []
    names = {t["name"] for t in kit["tables"]}
    for t in kit["tables"]:
        if not re.match(r"^(ft|dm)_", t["name"]):
            raise ValueError(f"table {t['name']}: facts start with ft_, dimensions with dm_")
        head = f"/// {t['description']}\n/// Grão: {t['grain']} · Fonte: {t['source']} · Conexão: dw\n"
        body = "\n".join(column(c) for c in t["columns"])
        write(d / "tables" / f"{t['name']}.tmdl", head + f"table {q(t['name'])}\n\n" + body + "\n"
              + partition(t["name"], sql_of(t)))
        for c in t["columns"]:
            target = c.get("references")
            if target == "dm_calendario":
                rels.append((f"{t['name']}.{q(c['name'])}", "dm_calendario.Data"))
            elif target:
                if target not in names:
                    raise ValueError(f"{t['name']}[{c['name']}] references unknown table {target}")
                key = next(k["name"] for tt in kit["tables"] if tt["name"] == target for k in tt["columns"] if k.get("key"))
                rels.append((f"{t['name']}.{q(c['name'])}", f"{target}.{q(key)}"))
    write(d / "tables" / "dm_calendario.tmdl", CALENDAR)
    measures = kit["measures"] + [UPDATED]
    write(d / "tables" / "_Medidas.tmdl",
          f"/// Medidas do relatório de {kit['app'].lower()} e data da última carga.\ntable _Medidas\n\n"
          + "\n".join(measure(m) for m in measures) + "\n"
          + column({"name": "Data Carga", "type": "dateTime", "hidden": True, "format": "dd/mm/yyyy hh:nn"}, True) + "\n"
          + "\tpartition _Medidas = calculated\n\t\tmode: import\n\t\tsource = ROW ( \"Data Carga\", UTCNOW () - 3 / 24 )\n")
    for tname, text in DOC_TABLES.items():
        write(d / "tables" / f"{tname}.tmdl", text)
    write(d / "relationships.tmdl", "".join(f"relationship {hid('rel', f, t)}\n\tfromColumn: {f}\n\ttoColumn: {t}\n\n"
                                            for f, t in rels).rstrip("\n") + "\n")
    for role in kit.get("roles", []):
        write(d / "roles" / f"{role['name']}.tmdl",
              f"/// {role['description']}\nrole {q(role['name'])}\n\tmodelPermission: read\n\n"
              + "".join(f"\ttablePermission {q(tb)} = {flt}\n" for tb, flt in role["filters"].items()))

    spec = {"app": kit["app"], "measures": "_Medidas", "updated": UPDATED["name"],
            "slicers": kit.get("slicers", []), "pages": kit["pages"] + [DOC_PAGE]}
    wjson(out / "layout.json", spec)
    theme_path = THEME
    if primary:
        import make_theme
        theme, tnotes = make_theme.build(primary, kit["app"], "Segoe UI")
        theme_path = out / "theme.json"
        wjson(theme_path, theme)
        notes += tnotes
    wjson(rp / "definition" / "version.json",
          {"$schema": f"{SCHEMA}/item/report/definition/versionMetadata/1.0.0/schema.json", "version": "2.0.0"})
    b = pbir_layout.Builder(spec)
    b.build(rp)
    b.register_resources(rp, theme_path)

    sample = {"measures": {m["name"]: m["sample"] for m in measures if m.get("sample")},
              "colors": {m["name"]: m["sampleColor"] for m in measures if m.get("sampleColor")},
              "fields": {f"{t['name']}[{c['name']}]": c["examples"] for t in kit["tables"] for c in t["columns"]
                         if c.get("examples")},
              "series": kit.get("series", {})}
    sample["fields"].setdefault("dm_calendario[Ano-Mês]", ["dez/25", "jan/26", "fev/26", "mar/26", "abr/26", "mai/26",
                                                          "jun/26", "jul/26", "ago/26", "set/26", "out/26", "nov/26"])
    wjson(out / "preview-sample.json", sample)
    views = "\n".join(f"| `{t['name']}` | `{t['source']}` | {t['grain']} |" for t in kit["tables"])
    write(out / "README.md", f"""# {kit['app']}

{kit['description']}

Projeto criado com o kit `{kit['id']}` da skill powerbi-architect. Abra `{name}.pbip` no Power BI Desktop.

## Antes de atualizar

Os parâmetros `Servidor` e `Banco` apontam para `{server}` / `{database}`. As views abaixo não existem no
seu data warehouse: crie-as (ou troque o SQL de cada tabela) com as colunas descritas no TMDL.

| Tabela | View de origem | Grão |
|---|---|---|
{views}

## Mudar as páginas

Edite `layout.json` e gere de novo:

```bash
python <skill>/scripts/pbir_layout.py layout.json {name}.Report{' --theme theme.json' if primary else ''}
python <skill>/scripts/preview_pbir.py {name}.Report --sample preview-sample.json --png preview
python <skill>/scripts/audit_pbip.py . --min-harmony 90
```
""")
    return notes


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="new_project.py", description="Start a PBIP project from a starter kit.")
    ap.add_argument("kit", nargs="?", help="vendas, financeiro, rh or estoque (see --list)")
    ap.add_argument("out", nargs="?", type=Path, help="output folder (must not exist)")
    ap.add_argument("--list", action="store_true", help="list the kits")
    ap.add_argument("--name", help="project name (default: the kit's)")
    ap.add_argument("--primary", help="brand colour for the theme, #RRGGBB (default: the skill's theme)")
    ap.add_argument("--server", default="localhost")
    ap.add_argument("--database", default="dw")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")   # Windows consoles default to a legacy code page
        except ValueError:
            pass
    available = kits()
    if args.list:
        for k, v in available.items():
            print(f"{k:<11} {v['app']}: {v['description']}")
        return 0
    if not args.kit or not args.out:
        ap.error("kit and output folder are required (or --list)")
    if args.kit not in available:
        print(f"new_project.py: error: unknown kit '{args.kit}' (available: {', '.join(available)})", file=sys.stderr)
        return 2
    kit = available[args.kit]
    name = args.name or kit["project"]
    try:
        notes = generate(kit, args.out, name, args.server, args.database, args.primary)
    except (ValueError, pbir_layout.SpecError, KeyError) as e:
        print(f"new_project.py: error: {e}", file=sys.stderr)
        return 2
    for n in notes:
        print(f"- {n}")
    print(f"[ok] {args.out / (name + '.pbip')}: {len(kit['tables'])} tables, {len(kit['measures']) + 1} measures, "
          f"{len(kit['pages']) + 1} pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
