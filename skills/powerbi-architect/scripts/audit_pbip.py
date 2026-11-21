#!/usr/bin/env python3
"""audit_pbip.py — governance audit for any Power BI Project (PBIP) folder.

Part of the powerbi-architect skill. Python 3.9+ standard library only, offline, read-only.

    python audit_pbip.py <folder-with-.pbip> [--json]

Exit code 1 when blockers are found.
"""


from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

NAME = r"(?:'(?:[^']|'')+'|[^\s=']+)"
OBJ_RE = re.compile(rf"^(?P<kind>table|column|measure|partition|hierarchy|calculationItem|relationship|expression)\s+(?P<name>{NAME})(?:\s*=\s*(?P<rest>.*))?$")
PROP_RE = re.compile(r"^(?P<key>[A-Za-z]+)\s*:\s*(?P<value>.*)$")
FLAG_RE = re.compile(r"^(?P<key>isHidden|isKey|isNameInferred|isDataTypeInferred|discourageImplicitMeasures)$")


def unquote(name: str) -> str:
    name = name.strip()
    if name.startswith("'") and name.endswith("'"):
        return name[1:-1].replace("''", "'")
    return name


def _tabs(line: str) -> int:
    n = 0
    for ch in line:
        if ch == "\t":
            n += 1
        elif ch == " ":
            # tolerate 4-space indentation
            n += 0.25  # type: ignore[assignment]
        else:
            break
    return int(n)


@dataclass
class Column:
    name: str
    data_type: str = ""
    source_column: str = ""
    expression: str = ""          # calculated column DAX
    format_string: str = ""
    is_hidden: bool = False
    is_key: bool = False
    sort_by: str = ""
    description: str = ""


@dataclass
class Measure:
    name: str
    expression: str = ""
    format_string: str = ""
    display_folder: str = ""
    is_hidden: bool = False
    description: str = ""


@dataclass
class Partition:
    name: str
    kind: str = ""                # m | calculated | entity ...
    mode: str = ""
    source: str = ""


@dataclass
class Table:
    name: str
    file: Path
    description: str = ""
    is_hidden: bool = False
    data_category: str = ""
    columns: list[Column] = field(default_factory=list)
    measures: list[Measure] = field(default_factory=list)
    partitions: list[Partition] = field(default_factory=list)

    @property
    def is_calculated(self) -> bool:
        return any(p.kind == "calculated" for p in self.partitions)


@dataclass
class Relationship:
    name: str
    from_column: str = ""
    to_column: str = ""
    cross_filter: str = ""
    is_active: bool = True
    from_cardinality: str = ""
    to_cardinality: str = ""

    def ends(self) -> tuple[str, str, str, str]:
        ft, fc = split_ref(self.from_column)
        tt, tc = split_ref(self.to_column)
        return ft, fc, tt, tc


@dataclass
class Model:
    folder: Path
    tables: list[Table] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    annotations: dict[str, str] = field(default_factory=dict)
    expressions: dict[str, str] = field(default_factory=dict)

    def table(self, name: str) -> Table | None:
        return next((t for t in self.tables if t.name == name), None)

    @property
    def measures(self) -> list[tuple[Table, Measure]]:
        return [(t, m) for t in self.tables for m in t.measures]


def split_ref(ref: str) -> tuple[str, str]:
    """Sales.'Order Date' -> ('Sales', 'Order Date')."""
    m = re.match(rf"^({NAME})\.({NAME})$", ref.strip())
    if not m:
        return ref, ""
    return unquote(m.group(1)), unquote(m.group(2))


def _collect_block(lines: list[str], i: int, first: str, min_indent: int) -> tuple[str, int]:
    """Collect a multi-line expression starting after `= first`."""
    body: list[str] = []
    first = first.rstrip()
    if first.startswith("```"):
        rest = first[3:]
        if rest.strip():
            body.append(rest)
        i += 1
        while i < len(lines) and not lines[i].strip().startswith("```"):
            body.append(lines[i].strip("\t"))
            i += 1
        return "\n".join(body).strip(), i + 1
    if first:
        body.append(first)
    i += 1
    while i < len(lines):
        ln = lines[i]
        if ln.strip() == "":
            # blank line inside an expression only if followed by deeper indentation
            j = i + 1
            if j < len(lines) and lines[j].strip() and _tabs(lines[j]) >= min_indent:
                body.append("")
                i += 1
                continue
            break
        if _tabs(ln) < min_indent:
            break
        body.append(ln.strip("\t"))
        i += 1
    return "\n".join(body).strip(), i


def parse_table_file(path: Path) -> list[Table]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    tables: list[Table] = []
    doc: list[str] = []
    table: Table | None = None
    current: Column | Measure | Partition | None = None
    i = 0
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()
        depth = _tabs(raw)
        if not stripped:
            i += 1
            continue
        if stripped.startswith("///"):
            doc.append(stripped[3:].strip())
            i += 1
            continue
        m = OBJ_RE.match(stripped)
        if m and depth == 0 and m.group("kind") == "table":
            table = Table(name=unquote(m.group("name")), file=path, description="\n".join(doc))
            tables.append(table)
            doc, current = [], None
            i += 1
            continue
        if table is None:
            i += 1
            continue
        if m and depth == 1:
            kind, name, rest = m.group("kind"), unquote(m.group("name")), m.group("rest")
            description = "\n".join(doc)
            doc = []
            if kind == "measure":
                expr, i = _collect_block(lines, i, rest or "", 3)
                current = Measure(name=name, expression=expr, description=description)
                table.measures.append(current)
                continue
            if kind == "column":
                current = Column(name=name, description=description)
                if rest is not None:
                    expr, i = _collect_block(lines, i, rest, 3)
                    current.expression = expr
                    table.columns.append(current)
                    continue
                table.columns.append(current)
            elif kind == "partition":
                current = Partition(name=name, kind=(rest or "").strip())
                table.partitions.append(current)
            else:
                current = None
            i += 1
            continue
        if depth == 1:
            pm = PROP_RE.match(stripped)
            if pm:
                key, value = pm.group("key"), pm.group("value").strip()
                if key == "dataCategory":
                    table.data_category = value
            elif stripped == "isHidden":
                table.is_hidden = True
            i += 1
            continue
        if depth == 2 and current is not None:
            if isinstance(current, Partition) and stripped.startswith("source"):
                after = stripped.split("=", 1)[1] if "=" in stripped else ""
                expr, i = _collect_block(lines, i, after.strip(), 3)
                current.source = expr
                continue
            pm = PROP_RE.match(stripped)
            if pm:
                key, value = pm.group("key"), pm.group("value").strip()
                if isinstance(current, Column):
                    if key == "dataType":
                        current.data_type = value
                    elif key == "sourceColumn":
                        current.source_column = value.strip("[]")
                    elif key == "formatString":
                        current.format_string = value
                    elif key == "sortByColumn":
                        current.sort_by = unquote(value)
                elif isinstance(current, Measure):
                    if key == "formatString":
                        current.format_string = value
                    elif key == "displayFolder":
                        current.display_folder = value
                elif isinstance(current, Partition) and key == "mode":
                    current.mode = value
            elif stripped == "isHidden" and isinstance(current, (Column, Measure)):
                current.is_hidden = True
            elif stripped == "isKey" and isinstance(current, Column):
                current.is_key = True
        i += 1
    return tables


def parse_relationships(path: Path) -> list[Relationship]:
    rels: list[Relationship] = []
    cur: Relationship | None = None
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        s = raw.strip()
        if not s or s.startswith("///"):
            continue
        if _tabs(raw) == 0 and s.startswith("relationship "):
            cur = Relationship(name=s.split(None, 1)[1])
            rels.append(cur)
            continue
        if cur is None:
            continue
        pm = PROP_RE.match(s)
        if pm:
            key, value = pm.group("key"), pm.group("value").strip()
            if key == "fromColumn":
                cur.from_column = value
            elif key == "toColumn":
                cur.to_column = value
            elif key == "crossFilteringBehavior":
                cur.cross_filter = value
            elif key == "isActive":
                cur.is_active = value.lower() != "false"
            elif key == "fromCardinality":
                cur.from_cardinality = value
            elif key == "toCardinality":
                cur.to_cardinality = value
    return rels


def parse_model(definition: Path) -> Model:
    model = Model(folder=definition)
    for f in sorted((definition / "tables").glob("*.tmdl")):
        model.tables.extend(parse_table_file(f))
    rel = definition / "relationships.tmdl"
    if rel.exists():
        model.relationships = parse_relationships(rel)
    mt = definition / "model.tmdl"
    if mt.exists():
        for raw in mt.read_text(encoding="utf-8-sig").splitlines():
            s = raw.strip()
            if _tabs(raw) == 0 and s.startswith("annotation "):
                key, _, value = s[len("annotation "):].partition("=")
                model.annotations[key.strip()] = value.strip()
    ex = definition / "expressions.tmdl"
    if ex.exists():
        for raw in ex.read_text(encoding="utf-8-sig").splitlines():
            s = raw.strip()
            if _tabs(raw) == 0 and s.startswith("expression "):
                key, _, value = s[len("expression "):].partition("=")
                model.expressions[unquote(key.strip())] = value.strip()
    return model


def find_definition(src: Path) -> Path | None:
    hits = sorted(src.glob("*.SemanticModel/definition"))
    return hits[0] if hits else None




# --------------------------------------------------------------------------- audit

import json as _json
import sys as _sys

HARDCODED = re.compile(r'\b(?:Sql\.Databases?|SapHana\.Database|PostgreSQL\.Database|Oracle\.Database|'
                       r'MySQL\.Database|Snowflake\.Databases|Databricks\.Catalogs)\s*\(\s*"')
HEAVY = re.compile(r"\bTable\.(?:AddColumn|TransformColumns|TransformColumnTypes|SelectRows|Group|NestedJoin|"
                   r"Join|ExpandTableColumn|Pivot|Unpivot|UnpivotOtherColumns|ReplaceValue|Combine|Distinct|"
                   r"Sort|FillDown|SplitColumn|RenameColumns|RemoveColumns)\(")
DOC_PAGES = {"documentação", "documentacao", "documentation", "documentación"}


def steps(m: str) -> int:
    return len(re.findall(r'^\s*(?:#"[^"]+"|[A-Za-z_][\w.]*)\s*=', m, re.M))


def audit(root: Path) -> list:
    out = []

    def add(sev, where, msg):
        out.append({"severity": sev, "where": where, "message": msg})

    for bad in list(root.rglob("*.pbix")) + list(root.rglob("*.abf")) + list(root.rglob("localSettings.json")):
        add("BLOCKER", str(bad.relative_to(root)), "data/local file inside the project — never commit it")
    defs = sorted(root.rglob("*.SemanticModel/definition"))
    if not defs:
        add("BLOCKER", str(root), "no *.SemanticModel/definition (TMDL) found — save as PBIP with TMDL")
        return out
    for d in defs:
        model = parse_model(d)
        if model.annotations.get("__PBI_TimeIntelligenceEnabled", "0") != "0":
            add("IMPORTANT", "model.tmdl", "auto date/time is ON — turn it off and use one date table")
        if not any(t.data_category == "Time" for t in model.tables):
            add("IMPORTANT", "model", "no table marked as date table (dataCategory: Time)")
        facts = {split_ref(r.from_column)[0] for r in model.relationships}
        for t in model.tables:
            where = f"tables/{t.file.name}"
            for p in t.partitions:
                if p.kind != "m":
                    continue
                if HARDCODED.search(p.source):
                    add("BLOCKER", where, f"'{t.name}': hard-coded server — use parameters")
                n = steps(p.source)
                if n > 1:
                    add("IMPORTANT", where, f"'{t.name}': {n} Power Query steps — move logic to SQL (target: 1)")
                heavy = sorted({h.rstrip("(") for h in HEAVY.findall(p.source)})
                if heavy:
                    add("IMPORTANT", where, f"'{t.name}': transformations in Power Query: {', '.join(heavy)}")
            for c in t.columns:
                if c.expression and t.name in facts:
                    add("IMPORTANT", where, f"calculated column '{t.name}'[{c.name}] in a fact — compute at source")
            for m in t.measures:
                is_text = "FORMAT" in m.expression.upper() or m.expression.lstrip().startswith('"')
                miss = [k for k, v in (("description", m.description),
                                       ("formatString", m.format_string or is_text),
                                       ("displayFolder", m.display_folder)) if not v]
                if miss:
                    sev = "BLOCKER" if "description" in miss else "SUGGESTION"
                    add(sev, where, f"measure [{m.name}] missing {', '.join(miss)}")
        for r in model.relationships:
            if r.cross_filter == "bothDirections":
                add("IMPORTANT", "relationships.tmdl", f"bidirectional {r.from_column} ↔ {r.to_column}")
            if r.from_cardinality == "many" and r.to_cardinality == "many":
                add("IMPORTANT", "relationships.tmdl", f"many-to-many {r.from_column} ↔ {r.to_column}")
        src_tables = [t for t in model.tables if not t.is_calculated]
        if len(src_tables) > 12:
            add("SUGGESTION", "model", f"{len(src_tables)} source tables — are all of them needed?")
    for rep in sorted(root.rglob("*.Report")):
        if (rep / "report.json").exists():
            add("IMPORTANT", rep.name, "legacy report format (report.json) — save as PBIR")
            continue
        names = []
        for pj in rep.glob("definition/pages/*/page.json"):
            try:
                names.append(_json.loads(pj.read_text(encoding="utf-8")).get("displayName", "").lower())
            except ValueError:
                add("BLOCKER", str(pj.relative_to(root)), "invalid JSON")
        for vj in rep.glob("definition/pages/*/visuals/*/visual.json"):
            try:
                _json.loads(vj.read_text(encoding="utf-8"))
            except ValueError:
                add("BLOCKER", str(vj.relative_to(root)), "invalid JSON")
        if not DOC_PAGES & set(names):
            add("BLOCKER", rep.name, "no Documentation page (Documentação/Documentation)")
    return out


def main() -> int:
    if len(_sys.argv) < 2:
        print(__doc__)
        return 2
    root = Path(_sys.argv[1]).resolve()
    issues = audit(root)
    if "--json" in _sys.argv:
        print(_json.dumps(issues, indent=2, ensure_ascii=False))
    else:
        order = {"BLOCKER": 0, "IMPORTANT": 1, "SUGGESTION": 2}
        for i in sorted(issues, key=lambda x: order[x["severity"]]):
            print(f"{i['severity']:<10} {i['where']}  —  {i['message']}")
        b = sum(1 for i in issues if i["severity"] == "BLOCKER")
        print(f"\n{len(issues)} finding(s), {b} blocker(s).")
    return 1 if any(i["severity"] == "BLOCKER" for i in issues) else 0


if __name__ == "__main__":
    raise SystemExit(main())
