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
    line: int = 0
    annotations: dict[str, str] = field(default_factory=dict)


@dataclass
class Measure:
    name: str
    expression: str = ""
    format_string: str = ""
    display_folder: str = ""
    is_hidden: bool = False
    description: str = ""
    line: int = 0
    annotations: dict[str, str] = field(default_factory=dict)


@dataclass
class Partition:
    name: str
    kind: str = ""                # m | calculated | entity ...
    mode: str = ""
    source: str = ""
    line: int = 0


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
    line: int = 0
    annotations: dict[str, str] = field(default_factory=dict)
    level_columns: set[str] = field(default_factory=set)   # columns used by hierarchy levels

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
    line: int = 0

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
    roles: list[str] = field(default_factory=list)          # RLS filter expressions (roles/*.tmdl)

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
            table = Table(name=unquote(m.group("name")), file=path, description="\n".join(doc), line=i + 1)
            tables.append(table)
            doc, current = [], None
            i += 1
            continue
        if table is None:
            i += 1
            continue
        if m and depth == 1:
            kind, name, rest = m.group("kind"), unquote(m.group("name")), m.group("rest")
            i0 = i
            description = "\n".join(doc)
            doc = []
            if kind == "measure":
                expr, i = _collect_block(lines, i, rest or "", 3)
                current = Measure(name=name, expression=expr, description=description, line=i0 + 1)
                table.measures.append(current)
                continue
            if kind == "column":
                current = Column(name=name, description=description, line=i0 + 1)
                if rest is not None:
                    expr, i = _collect_block(lines, i, rest, 3)
                    current.expression = expr
                    table.columns.append(current)
                    continue
                table.columns.append(current)
            elif kind == "partition":
                current = Partition(name=name, kind=(rest or "").strip(), line=i0 + 1)
                table.partitions.append(current)
            else:
                current = None
            i += 1
            continue
        if depth == 1 and stripped.startswith("annotation "):
            key, _, value = stripped[len("annotation "):].partition("=")
            table.annotations[key.strip()] = value.strip()
            i += 1
            continue
        if depth >= 3 and current is None and stripped.startswith("column:"):
            table.level_columns.add(unquote(stripped.split(":", 1)[1]))
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
            if stripped.startswith("annotation ") and isinstance(current, (Column, Measure)):
                key, _, value = stripped[len("annotation "):].partition("=")
                current.annotations[key.strip()] = value.strip()
                i += 1
                continue
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
    for n, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        s = raw.strip()
        if not s or s.startswith("///"):
            continue
        if _tabs(raw) == 0 and s.startswith("relationship "):
            cur = Relationship(name=s.split(None, 1)[1], line=n)
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
    for f in sorted((definition / "roles").glob("*.tmdl")):
        txt = f.read_text(encoding="utf-8-sig")
        model.roles.extend(re.findall(rf"tablePermission\s+{NAME}\s*=\s*(.+)", txt))
    return model


def find_definition(src: Path) -> Path | None:
    hits = sorted(src.glob("*.SemanticModel/definition"))
    return hits[0] if hits else None




# --------------------------------------------------------------------------- audit

import argparse
import fnmatch
import json as _json
import sys as _sys

SEVERITIES = ("BLOCKER", "IMPORTANT", "SUGGESTION")

# id: (severity, law, title, Tabular Editor Best Practice Analyzer rule IDs covering the same check)
# Laws refer to SKILL.md §1. "gov" = governance/security, "a11y" = accessibility.
RULES: dict[str, tuple[str, str, str, tuple[str, ...]]] = {
    "PBI001": ("BLOCKER", "gov", "Data or local settings file inside the project", ()),
    "PBI002": ("BLOCKER", "gov", "No TMDL semantic model found", ()),
    "PBI003": ("BLOCKER", "4", "Hard-coded server or database in Power Query", ()),
    "PBI004": ("BLOCKER", "gov", "Invalid JSON in the report definition", ()),
    "PBI005": ("BLOCKER", "5", "Measure without a description", ("OBJECTS_WITH_NO_DESCRIPTION",)),
    "PBI006": ("BLOCKER", "8", "Report without a Documentation page", ()),
    "PBI010": ("IMPORTANT", "2", "Auto date/time is on", ("REMOVE_AUTO-DATE_TABLE",)),
    "PBI011": ("IMPORTANT", "2", "No table marked as date table",
               ("MODEL_SHOULD_HAVE_A_DATE_TABLE", "DATE/CALENDAR_TABLES_SHOULD_BE_MARKED_AS_A_DATE_TABLE")),
    "PBI012": ("IMPORTANT", "4", "More than one Power Query step", ("MINIMIZE_POWER_QUERY_TRANSFORMATIONS",)),
    "PBI013": ("IMPORTANT", "4", "Transformations in Power Query", ("MINIMIZE_POWER_QUERY_TRANSFORMATIONS",)),
    "PBI014": ("IMPORTANT", "2", "Calculated column in a fact table",
               ("REDUCE_NUMBER_OF_CALCULATED_COLUMNS",
                "REDUCE_USAGE_OF_CALCULATED_COLUMNS_THAT_USE_THE_RELATED_FUNCTION")),
    "PBI015": ("IMPORTANT", "2", "Bidirectional relationship",
               ("AVOID_EXCESSIVE_BI-DIRECTIONAL_OR_MANY-TO-MANY_RELATIONSHIPS",
                "CHECK_IF_BI-DIRECTIONAL_AND_MANY-TO-MANY_RELATIONSHIPS_ARE_VALID")),
    "PBI016": ("IMPORTANT", "2", "Many-to-many relationship",
               ("AVOID_EXCESSIVE_BI-DIRECTIONAL_OR_MANY-TO-MANY_RELATIONSHIPS",
                "CHECK_IF_BI-DIRECTIONAL_AND_MANY-TO-MANY_RELATIONSHIPS_ARE_VALID")),
    "PBI017": ("IMPORTANT", "2", "Time intelligence over the auto date/time hierarchy (.[Date])",
               ("REMOVE_AUTO-DATE_TABLE",)),
    "PBI018": ("IMPORTANT", "6", "Page with more than 8 data visuals", ()),
    "PBI019": ("IMPORTANT", "a11y", "Data visual without alt text", ()),
    "PBI020": ("IMPORTANT", "gov", "Legacy report format (report.json) instead of PBIR", ()),
    "PBI030": ("SUGGESTION", "5", "Measure without a format string", ("PROVIDE_FORMAT_STRING_FOR_MEASURES",)),
    "PBI031": ("SUGGESTION", "5", "Measure without a display folder", ()),
    "PBI032": ("SUGGESTION", "5", "Division with / instead of DIVIDE", ("USE_THE_DIVIDE_FUNCTION_FOR_DIVISION",)),
    "PBI033": ("SUGGESTION", "5", "IFERROR in a measure", ("AVOID_USING_THE_IFERROR_FUNCTION",)),
    "PBI034": ("SUGGESTION", "3", "Column never used", ("UNNECESSARY_COLUMNS",)),
    "PBI035": ("SUGGESTION", "2", "Floating point column (double)", ("AVOID_FLOATING_POINT_DATA_TYPES",)),
    "PBI036": ("SUGGESTION", "2", "Visible foreign key", ("HIDE_FOREIGN_KEYS",)),
    "PBI037": ("SUGGESTION", "2", "Relationship key is not an integer",
               ("RELATIONSHIP_COLUMNS_SHOULD_BE_OF_INTEGER_DATA_TYPE",)),
    "PBI038": ("SUGGESTION", "2", "Snowflaked dimension", ("SNOWFLAKE_SCHEMA_ARCHITECTURE",)),
    "PBI039": ("SUGGESTION", "3", "More than 12 source tables", ()),
    "PBI040": ("SUGGESTION", "7", "Pie or donut chart", ()),
    "PBI041": ("SUGGESTION", "7", "Custom visual in use: record the decision (ADR)", ()),
    "PBI042": ("SUGGESTION", "1", "Page with a generic name", ()),
    "PBI043": ("SUGGESTION", "8", "Project without README.md", ()),
}
BPA_TO_PBI: dict[str, set[str]] = {}
for _rid, (_sev, _law, _title, _bpa) in RULES.items():
    for _b in _bpa:
        BPA_TO_PBI.setdefault(_b, set()).add(_rid)

HARDCODED = re.compile(r'\b(?:Sql\.Databases?|SapHana\.Database|PostgreSQL\.Database|Oracle\.Database|'
                       r'MySQL\.Database|Snowflake\.Databases|Databricks\.Catalogs)\s*\(\s*"')
HEAVY = re.compile(r"\bTable\.(?:AddColumn|TransformColumns|TransformColumnTypes|SelectRows|Group|NestedJoin|"
                   r"Join|ExpandTableColumn|Pivot|Unpivot|UnpivotOtherColumns|ReplaceValue|Combine|Distinct|"
                   r"Sort|FillDown|SplitColumn|RenameColumns|RemoveColumns)\(")
DOC_PAGES = {"documentação", "documentacao", "documentation", "documentación"}
GENERIC_PAGE = re.compile(r"^(?:page|página|pagina|duplicate of .*|duplicado de .*)\s*\d*$", re.I)
DECORATIVE = {"textbox", "shape", "basicShape", "image", "actionButton", "pageNavigator", "bookmarkNavigator"}
IGNORE_ANNOTATIONS = {"PowerBIArchitect_IgnoreRules": "pbi", "BestPracticeAnalyzer_IgnoreRules": "bpa"}
CONFIG_FILE = ".pbiaudit.json"


def skill_version() -> str:
    skill_md = Path(__file__).resolve().parent.parent / "SKILL.md"
    if skill_md.exists():
        m = re.search(r'version:\s*"([^"]+)"', skill_md.read_text(encoding="utf-8"))
        if m:
            return m.group(1)
    return "unknown"


def steps(m: str) -> int:
    return len(re.findall(r'^\s*(?:#"[^"]+"|[A-Za-z_][\w.]*)\s*=', m, re.M))


def strip_dax(expr: str) -> str:
    """Remove comments and string literals so pattern checks only see code."""
    expr = re.sub(r"/\*.*?\*/", " ", expr, flags=re.S)
    expr = re.sub(r"(?://|--).*$", " ", expr, flags=re.M)
    return re.sub(r'"(?:[^"]|"")*"', '""', expr)


def ignored_rules(annotations: dict[str, str]) -> set[str]:
    """Rule IDs suppressed by PowerBIArchitect_IgnoreRules / BestPracticeAnalyzer_IgnoreRules annotations."""
    out: set[str] = set()
    for key, kind in IGNORE_ANNOTATIONS.items():
        raw = annotations.get(key)
        if not raw:
            continue
        try:
            ids = _json.loads(raw).get("RuleIDs", [])
        except (ValueError, AttributeError):
            ids = re.findall(r"[A-Z0-9_/().'-]+", raw)
        for rid in ids:
            out |= {rid} if kind == "pbi" else BPA_TO_PBI.get(rid, set())
    return out


def report_fields(report: Path) -> set[tuple[str, str]]:
    """(table, field) pairs referenced anywhere in a PBIR report definition."""
    used: set[tuple[str, str]] = set()

    def walk(o):
        if isinstance(o, dict):
            src = o.get("Expression", {}).get("SourceRef", {}) if isinstance(o.get("Expression"), dict) else {}
            if "Property" in o and isinstance(src, dict) and "Entity" in src:
                used.add((src["Entity"], o["Property"]))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    for f in report.rglob("*.json"):
        try:
            walk(_json.loads(f.read_text(encoding="utf-8-sig")))
        except ValueError:
            pass
    return used


def load_config(root: Path, path: Path | None) -> dict:
    cfg = path or root / CONFIG_FILE
    if cfg and cfg.exists():
        data = _json.loads(cfg.read_text(encoding="utf-8"))
        return {"disable": set(data.get("disable", [])), "ignore": data.get("ignore", [])}
    return {"disable": set(), "ignore": []}


def audit(root: Path, config: dict | None = None) -> list:
    config = config or {"disable": set(), "ignore": []}
    out: list[dict] = []

    def rel(p: Path) -> str:
        try:
            return p.relative_to(root).as_posix()
        except ValueError:
            return p.as_posix()

    def add(rule, path, msg, line=0, suppressed=frozenset()):
        if rule in config["disable"] or rule in suppressed:
            return
        for ig in config["ignore"]:
            if ig.get("rule") in (rule, None) and fnmatch.fnmatch(path, ig.get("path", "*")):
                return
        sev, law, title, bpa = RULES[rule]
        out.append({"rule": rule, "severity": sev, "law": law, "where": path, "line": line,
                    "message": msg, "bpa": list(bpa)})

    for bad in list(root.rglob("*.pbix")) + list(root.rglob("*.abf")) + list(root.rglob("localSettings.json")):
        add("PBI001", rel(bad), "data/local file inside the project — never commit it")
    defs = sorted(root.rglob("*.SemanticModel/definition"))
    if not defs:
        add("PBI002", rel(root), "no *.SemanticModel/definition (TMDL) found — save as PBIP with TMDL")
        return out
    reports = sorted(root.rglob("*.Report"))
    fields: set[tuple[str, str]] = set()
    for rep in reports:
        fields |= report_fields(rep / "definition")

    for d in defs:
        model = parse_model(d)
        model_ign = ignored_rules(model.annotations)
        mt = rel(d / "model.tmdl")
        if model.annotations.get("__PBI_TimeIntelligenceEnabled", "0") != "0":
            add("PBI010", mt, "auto date/time is ON — turn it off and use one date table", suppressed=model_ign)
        if not any(t.data_category == "Time" for t in model.tables):
            add("PBI011", mt, "no table marked as date table (dataCategory: Time)", suppressed=model_ign)
        rel_path = rel(d / "relationships.tmdl")
        from_tables = {split_ref(r.from_column)[0] for r in model.relationships}
        to_tables = {split_ref(r.to_column)[0] for r in model.relationships}
        rel_cols: set[tuple[str, str]] = set()
        for r in model.relationships:
            ft, fc, tt, tc = r.ends()
            rel_cols |= {(ft, fc), (tt, tc)}
        dax_all = "\n".join(m.expression for _, m in model.measures)
        dax_all += "\n" + "\n".join(c.expression for t in model.tables for c in t.columns if c.expression)
        dax_all += "\n" + "\n".join(p.source for t in model.tables for p in t.partitions if p.kind == "calculated")
        dax_all += "\n" + "\n".join(model.roles)
        dax_code = strip_dax(dax_all)
        date_tables = {t.name for t in model.tables if t.data_category == "Time"}
        has_report = bool(reports)

        for t in model.tables:
            path = rel(t.file)
            t_ign = model_ign | ignored_rules(t.annotations)
            types = {c.name: c.data_type for c in t.columns}
            for p in t.partitions:
                if p.kind != "m":
                    continue
                if HARDCODED.search(p.source):
                    add("PBI003", path, f"'{t.name}': hard-coded server — use parameters", p.line, t_ign)
                n = steps(p.source)
                if n > 1:
                    add("PBI012", path, f"'{t.name}': {n} Power Query steps — move logic to SQL (target: 1)",
                        p.line, t_ign)
                heavy = sorted({h.rstrip("(") for h in HEAVY.findall(p.source)})
                if heavy:
                    add("PBI013", path, f"'{t.name}': transformations in Power Query: {', '.join(heavy)}",
                        p.line, t_ign)
            for c in t.columns:
                c_ign = t_ign | ignored_rules(c.annotations)
                ref = f"'{t.name}'[{c.name}]"
                if c.expression and t.name in from_tables and t.name not in to_tables:
                    add("PBI014", path, f"calculated column {ref} in a fact — compute at source", c.line, c_ign)
                if c.data_type == "double":
                    add("PBI035", path, f"{ref} is double — use decimal (fixed) or int64", c.line, c_ign)
                if (t.name, c.name) in rel_cols and t.name in from_tables and not c.is_hidden \
                        and not t.is_hidden and t.name not in to_tables:
                    add("PBI036", path, f"foreign key {ref} is visible — hide it", c.line, c_ign)
                used = ((t.name, c.name) in rel_cols or (t.name, c.name) in fields or c.is_key
                        or c.name in t.level_columns
                        or any(o.sort_by == c.name for o in t.columns)
                        or re.search(rf"(?:'{re.escape(t.name)}'|\b{re.escape(t.name)})\s*\[{re.escape(c.name)}\]",
                                     dax_code)
                        or (re.search(rf"\[{re.escape(c.name)}\]", dax_code) is not None
                            and any(o.expression for o in t.columns)))
                if has_report and not used and not t.is_calculated and not c.expression:
                    add("PBI034", path, f"{ref} is imported but never used (measure, visual, relationship, "
                                        "sort, hierarchy or RLS)", c.line, c_ign)
            for m in t.measures:
                m_ign = t_ign | ignored_rules(m.annotations)
                code = strip_dax(m.expression)
                is_text = "FORMAT" in m.expression.upper() or m.expression.lstrip().startswith('"')
                if not m.description:
                    add("PBI005", path, f"measure [{m.name}] missing description", m.line, m_ign)
                if not (m.format_string or is_text):
                    add("PBI030", path, f"measure [{m.name}] missing formatString", m.line, m_ign)
                if not m.display_folder:
                    add("PBI031", path, f"measure [{m.name}] missing displayFolder", m.line, m_ign)
                if re.search(r"(?<![/*])/(?![/*])", code):
                    add("PBI032", path, f"measure [{m.name}] divides with / — use DIVIDE", m.line, m_ign)
                if re.search(r"\bIFERROR\s*\(", code, re.I):
                    add("PBI033", path, f"measure [{m.name}] uses IFERROR — handle the case explicitly",
                        m.line, m_ign)
                if re.search(r"\]\s*\.\s*\[Date\]", code):
                    add("PBI017", path, f"measure [{m.name}] uses the auto date/time hierarchy (.[Date]) — "
                                        "use the date table", m.line, m_ign)
        for r in model.relationships:
            ft, fc, tt, tc = r.ends()
            label = f"{r.from_column} → {r.to_column}"
            if r.cross_filter == "bothDirections":
                add("PBI015", rel_path, f"bidirectional {label}", r.line, model_ign)
            if r.from_cardinality == "many" and r.to_cardinality == "many":
                add("PBI016", rel_path, f"many-to-many {label}", r.line, model_ign)
            to_t = model.table(tt)
            if to_t and tt not in date_tables:
                key_type = {c.name: c.data_type for c in to_t.columns}.get(tc, "")
                if key_type and key_type != "int64":
                    add("PBI037", rel_path, f"{label}: key is {key_type} — prefer an int64 surrogate key",
                        r.line, model_ign)
        for name in sorted(from_tables & to_tables):
            t = model.table(name)
            if t and t.name not in date_tables:
                add("PBI038", rel(t.file), f"'{name}' is both a dimension and filtered by another dimension — "
                                           "flatten it into one dimension (star schema)", t.line,
                    model_ign | ignored_rules(t.annotations))
        src_tables = [t for t in model.tables if not t.is_calculated]
        if len(src_tables) > 12:
            add("PBI039", mt, f"{len(src_tables)} source tables — are all of them needed?", suppressed=model_ign)

    for rep in reports:
        if (rep / "report.json").exists():
            add("PBI020", rel(rep), "legacy report format (report.json) — save as PBIR")
            continue
        names = []
        rj = rep / "definition" / "report.json"
        if rj.exists():
            try:
                rdata = _json.loads(rj.read_text(encoding="utf-8-sig"))
                custom = sorted(set(rdata.get("publicCustomVisuals", [])))
                if custom:
                    add("PBI041", rel(rj), f"custom visual(s) in use: {', '.join(custom)} — keep an ADR")
            except ValueError:
                add("PBI004", rel(rj), "invalid JSON")
        for pj in sorted(rep.glob("definition/pages/*/page.json")):
            try:
                display = _json.loads(pj.read_text(encoding="utf-8-sig")).get("displayName", "")
            except ValueError:
                add("PBI004", rel(pj), "invalid JSON")
                continue
            names.append(display.lower())
            if GENERIC_PAGE.match(display.strip()):
                add("PBI042", rel(pj), f"page '{display}' — name it after the question it answers")
            data_visuals = 0
            for vj in sorted(pj.parent.glob("visuals/*/visual.json")):
                try:
                    v = _json.loads(vj.read_text(encoding="utf-8-sig")).get("visual", {})
                except ValueError:
                    add("PBI004", rel(vj), "invalid JSON")
                    continue
                vtype = v.get("visualType", "")
                if not vtype or vtype in DECORATIVE:
                    continue
                data_visuals += 1
                alt = (v.get("visualContainerObjects", {}).get("general", [{}]) or [{}])[0] \
                    .get("properties", {}).get("altText")
                if not alt:
                    add("PBI019", rel(vj), f"{vtype} on page '{display}' has no alt text")
                if vtype in ("pieChart", "donutChart"):
                    add("PBI040", rel(vj), f"{vtype} on page '{display}' — ≤ 3 slices, otherwise a sorted bar")
            if data_visuals > 8:
                add("PBI018", rel(pj), f"page '{display}' has {data_visuals} data visuals (target ≤ 8)")
        if not DOC_PAGES & set(names):
            add("PBI006", rel(rep), "no Documentation page (Documentação/Documentation)")
    for pbip in sorted(root.rglob("*.pbip")):
        if not any((pbip.parent / n).exists() for n in ("README.md", "readme.md", "LEIAME.md")):
            add("PBI043", rel(pbip.parent) or ".", f"no README.md next to {pbip.name}")
    order = {s: i for i, s in enumerate(SEVERITIES)}
    out.sort(key=lambda x: (order[x["severity"]], x["where"], x["line"], x["rule"]))
    return out


def to_sarif(issues: list) -> dict:
    level = {"BLOCKER": "error", "IMPORTANT": "warning", "SUGGESTION": "note"}
    rules = [{"id": rid, "name": title, "shortDescription": {"text": title},
              "defaultConfiguration": {"level": level[sev]},
              "properties": {"law": law, "bestPracticeAnalyzer": list(bpa)},
              "helpUri": "https://github.com/DaviMark/powerbi-architect/blob/main/docs/regras-auditoria.md"}
             for rid, (sev, law, title, bpa) in RULES.items()]
    results = []
    for i in issues:
        loc = {"physicalLocation": {"artifactLocation": {"uri": i["where"]}}}
        if i["line"]:
            loc["physicalLocation"]["region"] = {"startLine": i["line"]}
        results.append({"ruleId": i["rule"], "level": level[i["severity"]],
                        "message": {"text": i["message"]}, "locations": [loc]})
    return {"$schema": "https://json.schemastore.org/sarif-2.1.0.json", "version": "2.1.0",
            "runs": [{"tool": {"driver": {"name": "powerbi-architect audit", "version": skill_version(),
                                          "informationUri": "https://github.com/DaviMark/powerbi-architect",
                                          "rules": rules}},
                      "results": results}]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="audit_pbip.py",
        description="Offline, read-only governance audit for Power BI Project (PBIP) folders. "
                    "Part of the powerbi-architect skill.",
        epilog="Exit codes: 0 = no finding at or above --fail-on, 1 = findings, 2 = usage error. "
               f"Suppress rules in {CONFIG_FILE} or with TMDL annotations "
               "PowerBIArchitect_IgnoreRules / BestPracticeAnalyzer_IgnoreRules.")
    ap.add_argument("folder", nargs="?", help="folder that contains the .pbip project(s)")
    fmt = ap.add_mutually_exclusive_group()
    fmt.add_argument("--json", action="store_true", help="print findings as JSON")
    fmt.add_argument("--sarif", action="store_true", help="print findings as SARIF 2.1.0 (GitHub code scanning)")
    ap.add_argument("--config", type=Path, help=f"suppression file (default: <folder>/{CONFIG_FILE})")
    ap.add_argument("--fail-on", choices=["blocker", "important", "suggestion", "never"], default="blocker",
                    help="lowest severity that makes the exit code 1 (default: blocker)")
    ap.add_argument("--list-rules", action="store_true", help="list every rule and exit")
    ap.add_argument("--version", action="version", version=f"%(prog)s {skill_version()}")
    args = ap.parse_args(argv)
    if hasattr(_sys.stdout, "reconfigure"):
        try:
            _sys.stdout.reconfigure(encoding="utf-8")   # Windows consoles default to a legacy code page
        except ValueError:
            pass

    if args.list_rules:
        for rid, (sev, law, title, bpa) in RULES.items():
            extra = f"  [BPA: {', '.join(bpa)}]" if bpa else ""
            print(f"{rid}  {sev:<10} law {law:<4} {title}{extra}")
        return 0
    if not args.folder:
        ap.print_usage(_sys.stderr)
        print("audit_pbip.py: error: the folder argument is required", file=_sys.stderr)
        return 2
    root = Path(args.folder).resolve()
    if not root.is_dir():
        print(f"audit_pbip.py: error: not a folder: {args.folder}", file=_sys.stderr)
        return 2
    try:
        config = load_config(root, args.config)
    except ValueError as e:
        print(f"audit_pbip.py: error: invalid {args.config or CONFIG_FILE}: {e}", file=_sys.stderr)
        return 2
    issues = audit(root, config)
    if args.json:
        print(_json.dumps(issues, indent=2, ensure_ascii=False))
    elif args.sarif:
        print(_json.dumps(to_sarif(issues), indent=2, ensure_ascii=False))
    else:
        for i in issues:
            where = f"{i['where']}:{i['line']}" if i["line"] else i["where"]
            print(f"{i['rule']}  {i['severity']:<10} {where}  —  {i['message']}")
        b = sum(1 for i in issues if i["severity"] == "BLOCKER")
        print(f"\n{len(issues)} finding(s), {b} blocker(s).")
    if args.fail_on == "never":
        return 0
    limit = SEVERITIES.index(args.fail_on.upper())
    return 1 if any(SEVERITIES.index(i["severity"]) <= limit for i in issues) else 0


if __name__ == "__main__":
    raise SystemExit(main())
