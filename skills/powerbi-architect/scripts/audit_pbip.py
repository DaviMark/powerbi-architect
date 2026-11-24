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
    # PBI044 and PBI045 are reserved for open issues (month sort, inactive relationships).
    "PBI046": ("IMPORTANT", "6", "Oversized slicer", ()),
    "PBI047": ("IMPORTANT", "6", "Font larger than the type scale", ()),
    "PBI048": ("SUGGESTION", "6", "Visual off the 4 px grid", ()),
    "PBI049": ("IMPORTANT", "2", "Table name without the ft_ (fact) or dm_ (dimension) prefix", ()),
    "PBI050": ("IMPORTANT", "6", "More than 2 slicers on a page", ()),
    "PBI051": ("SUGGESTION", "6", "More than one font family, or a font outside the professional set", ()),
    "PBI052": ("IMPORTANT", "6", "Visual outside the page", ()),
    "PBI053": ("SUGGESTION", "a11y", "Keyboard (tab) order differs from the reading order", ()),
    "PBI054": ("IMPORTANT", "a11y", "Text colour below 4.5:1 contrast on white", ()),
    "PBI055": ("SUGGESTION", "6", "Generic auto-generated title (\"Sum of … by …\")", ()),
    "PBI056": ("SUGGESTION", "6", "Data visual without a title", ()),
    "PBI057": ("SUGGESTION", "6", "Axis title shown", ()),
    "PBI058": ("SUGGESTION", "6", "More than 6 colours on a page", ()),
    "PBI059": ("SUGGESTION", "6", "Title or label likely truncated by the visual width", ()),
    "PBI060": ("SUGGESTION", "6", "Table too narrow for its columns", ()),
    "PBI061": ("IMPORTANT", "1", "Dynamic title about something the visual does not show", ()),
    "PBI062": ("SUGGESTION", "7", "Time on the vertical axis of a bar chart", ()),
    "PBI063": ("SUGGESTION", "6", "KPI cards too narrow or too many in one row", ()),
    "PBI064": ("SUGGESTION", "6", "Chart too small to read", ()),
    "PBI065": ("SUGGESTION", "a11y", "Theme colours that look alike to people with colour-vision deficiency", ()),
    "PBI066": ("SUGGESTION", "6", "Corners rounder than 8 px (the generic 'AI dashboard' look)", ()),
    "PBI067": ("SUGGESTION", "6", "Shadow or glow on a visual", ()),
    "PBI068": ("SUGGESTION", "6", "Uneven, cramped or loose gutters between visuals", ()),
    "PBI069": ("SUGGESTION", "1", "Two visuals that show the same thing", ()),
}
CHART_TYPES = {"lineChart", "areaChart", "clusteredBarChart", "clusteredColumnChart", "barChart", "columnChart",
               "lineClusteredColumnComboChart", "lineStackedColumnComboChart", "scatterChart", "waterfallChart",
               "stackedBarChart", "stackedColumnChart", "ribbonChart"}
TIME_NAME = re.compile(r"^(?:data|date|dia|day|m[eê]s|month|ano[- ]?m[eê]s|year[- ]?month|trimestre|quarter|semana|week)\b",
                       re.I)
TEXT_WIDTH = 0.5        # average glyph width of Segoe UI, in em: estimates whether a title fits
# Harmony score: 100 per page minus these penalties for each finding on that page.
HARMONY_PENALTY = {"BLOCKER": 20, "IMPORTANT": 10, "SUGGESTION": 4}
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
SLICERS = {"slicer", "advancedSlicerVisual", "listSlicer", "textSlicer"}
BIG_NUMBER_VISUALS = {"card", "cardVisual", "multiRowCard", "kpi"}
# Type scale in pt (references/report-design.md §5): text boxes ≤ 14, KPI values ≤ 24, everything else ≤ 12.
MAX_PT = {"textbox": 14, "big": 24, "other": 12}
# Fonts that render everywhere Power BI runs and read as professional. Weights count as one family.
PRO_FONTS = {"segoe ui", "segoe ui light", "segoe ui semibold", "segoe ui bold", "segoe ui semilight"}
UGLY_FONTS = {"din", "comic sans ms", "impact", "arial black", "courier new", "wingdings", "symbol",
              "segoe print", "segoe script", "corbel"}
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


def _pt(value) -> float | None:
    """'14pt', '14D', '14L', 14 → 14.0."""
    if isinstance(value, (int, float)):
        return float(value)
    m = re.match(r"^'?\s*(\d+(?:\.\d+)?)\s*(?:pt|px|D|L)?\s*'?$", str(value))
    return float(m.group(1)) if m else None


def font_usage(visual: dict) -> tuple[list[float], set[str]]:
    """Font sizes (pt) and font families set on one visual (text runs and formatting objects)."""
    sizes: list[float] = []
    families: set[str] = set()

    def walk(o, key=""):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("fontSize", "textSize"):
                    lv = v.get("expr", {}).get("Literal", {}).get("Value") if isinstance(v, dict) else v
                    n = _pt(lv) if lv is not None else None
                    if n:
                        sizes.append(n)
                elif k == "fontFamily":
                    lv = v.get("expr", {}).get("Literal", {}).get("Value") if isinstance(v, dict) else v
                    if isinstance(lv, str):
                        families.update(f.strip().strip("'\"").lower() for f in lv.strip("'").split(",") if f.strip())
                else:
                    walk(v, k)
        elif isinstance(o, list):
            for x in o:
                walk(x, key)

    walk(visual)
    return sizes, families


def chromeless(container: dict) -> bool:
    """A data visual with no title, background or border annotates another element (a KPI's variation
    line, the "updated at" text): it does not count as a separate visual on the page."""
    vco = (container.get("visual") or {}).get("visualContainerObjects") or {}

    def off(obj: str) -> bool:
        v = ((vco.get(obj) or [{}])[0].get("properties", {}).get("show") or {})
        return str(v.get("expr", {}).get("Literal", {}).get("Value", "")).lower() == "false"
    return off("title") and off("background") and off("border")


GENERIC_TITLE = re.compile(r"^(sum|count|average|min|max|soma|contagem|média|media|mínimo|máximo|total) (of|de) .+ "
                           r"(by|por) ", re.I)
TEXT_COLOUR_KEYS = {"fontColor", "labelColor", "titleFontColor", "valueFontColor"}
FILL_KEYS = {"fill", "fillColor", "defaultColor", "increaseFill", "decreaseFill", "totalFill", "otherFill"}


def _hex(o) -> str | None:
    """'#RRGGBB' from a literal colour expression, a {"solid": …} wrapper or a plain string."""
    if isinstance(o, dict):
        if "solid" in o:
            return _hex(o["solid"].get("color"))
        v = o.get("expr", {}).get("Literal", {}).get("Value") if "expr" in o else None
        return _hex(v) if v is not None else None
    if isinstance(o, str):
        m = re.match(r"^'?(#[0-9A-Fa-f]{6})'?$", o.strip())
        return m.group(1).upper() if m else None
    return None


def _luminance(h: str) -> float:
    def lin(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast_on_white(h: str) -> float:
    return 1.05 / (_luminance(h) + 0.05)


def colour_usage(visual: dict) -> tuple[set[str], set[str]]:
    """(text colours, fill colours) set as literals on one visual."""
    text, fills = set(), set()

    def walk(o, parent=""):
        if isinstance(o, dict):
            for k, v in o.items():
                h = _hex(v) if (k in TEXT_COLOUR_KEYS or k in FILL_KEYS or k == "color") else None
                if h:
                    if k in TEXT_COLOUR_KEYS or (k == "color" and parent in ("labels", "categoryLabels", "textStyle")):
                        text.add(h)
                    elif k in FILL_KEYS:
                        fills.add(h)
                walk(v, k if k not in ("properties",) else parent)
        elif isinstance(o, list):
            for x in o:
                walk(x, parent)

    walk(visual)
    return text, fills


def is_neutral(h: str) -> bool:
    r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
    return max(r, g, b) - min(r, g, b) < 12


def family_of(font: str) -> str:
    return "segoe ui" if font.startswith("segoe ui") else font


def vco_or(visual: dict) -> dict:
    return visual.get("visualContainerObjects") or {}


def num_literal(o, raw: bool = False):
    """The value of a Literal expression ("8D" → 8.0); raw=True returns the text."""
    try:
        v = o["expr"]["Literal"]["Value"]
    except (KeyError, TypeError):
        return None
    if raw:
        return str(v).strip("'")
    try:
        return float(str(v).rstrip("DLM"))
    except ValueError:
        return None


def layout_review(boxes: list) -> list[tuple[str, str, str]]:
    """Gutters and repeated breakdowns on one page (data visuals only; KPI variation lines are excluded)."""
    found = []
    rows: list[list] = []
    for b in sorted(boxes, key=lambda b: (b[1], b[0])):
        row = next((r for r in rows if abs(r[0][1] - b[1]) <= 2), None)
        row.append(b) if row else rows.append([b])
    gaps = []
    for r in rows:
        r.sort(key=lambda b: b[0])
        gaps += [(r[i][0] - (r[i - 1][0] + r[i - 1][2]), r[i][4]) for i in range(1, len(r))]
    for i in range(1, len(rows)):
        above = max(b[1] + b[3] for b in rows[i - 1])
        gaps.append((rows[i][0][1] - above, rows[i][0][4]))
    gaps = [(g, w) for g, w in gaps if g >= 0]
    for g, w in gaps:
        if g < 8 or g > 32:
            found.append(("PBI068", w, f"{g:g} px between neighbouring visuals — use the 16 px gutter"))
    sizes = sorted({round(g) for g, _ in gaps if 8 <= g <= 32})
    if len(sizes) > 1:
        found.append(("PBI068", gaps[0][1], f"gutters of {', '.join(map(str, sizes))} px — use one size everywhere"))
    seen: dict[tuple, str] = {}
    for b in boxes:
        if b[5] in CHART_TYPES and b[6]:
            k = (b[5], b[6])
            if k in seen:
                found.append(("PBI069", b[4], f"two {b[5]} with the same fields ({', '.join(b[6][:3])}) — keep one "
                                              "and use the space for a different question"))
            seen.setdefault(k, b[4])
    return found


def projections(visual: dict) -> dict[str, list[tuple[str, str, str]]]:
    """{role: [(kind, entity, property)]} for a visual's query."""
    out: dict[str, list[tuple[str, str, str]]] = {}
    for role, body in ((visual.get("query") or {}).get("queryState") or {}).items():
        for p in body.get("projections", []):
            f = p.get("field") or {}
            kind = next(iter(f), "")
            inner = f.get(kind) or {}
            if kind == "Aggregation":
                inner = (inner.get("Expression") or {}).get("Column") or {}
            ent = ((inner.get("Expression") or {}).get("SourceRef") or {}).get("Entity", "")
            out.setdefault(role, []).append((kind, ent, inner.get("Property", "")))
    return out


def dax_refs(expr: str) -> set[str]:
    return set(re.findall(r"\[([^\]]+)\]", strip_dax(expr or "")))


def design_review(visual: dict, w: float, h: float, title: str, page_w: float,
                  measure_dax: dict[str, str], time_columns: set[tuple[str, str]]) -> list[tuple[str, str]]:
    """Art-director checks on one data visual: what a designer would catch at a glance."""
    found = []
    vtype = visual.get("visualType", "")
    roles = projections(visual)
    big = vtype in BIG_NUMBER_VISUALS
    title_px = (9 if big else 10) * 4 / 3
    if title and len(title) * title_px * TEXT_WIDTH + 24 > w:
        fits = int((w - 24) / (title_px * TEXT_WIDTH))
        found.append(("PBI059", f"title '{title}' ({len(title)} characters) does not fit {w:g} px — "
                                f"about {fits} fit; shorten it or widen the visual"))
    if vtype == "tableEx":
        cols = len(roles.get("Values", []))
        if cols and (w - 16) / cols < 80:
            found.append(("PBI060", f"{cols} columns in {w:g} px ({(w - 16) / cols:.0f} px each) — keep ≥ 80 px "
                                    "per column: drop columns or give the table the full width"))
    vco = visual.get("visualContainerObjects") or {}
    text = ((vco.get("title") or [{}])[0].get("properties") or {}).get("text") or {}
    title_measure = ((text.get("expr") or {}).get("Measure") or {}).get("Property") if isinstance(text, dict) else None
    if title_measure and title_measure in measure_dax:
        shown = {p for r in roles.values() for _, _, p in r}
        refs = dax_refs(measure_dax[title_measure])
        deep = set(refs)
        for r in refs:
            deep |= dax_refs(measure_dax.get(r, ""))
        if refs and shown and not (deep & shown):
            found.append(("PBI061", f"the title comes from [{title_measure}], which uses "
                                    f"{', '.join(sorted(refs)[:3])} — none of them is in the visual "
                                    f"({', '.join(sorted(shown)[:3])}); the title would describe something else"))
    if vtype in ("clusteredBarChart", "barChart", "stackedBarChart", "hundredPercentStackedBarChart"):
        cat = (roles.get("Category") or [("", "", "")])[0]
        if (cat[1], cat[2]) in time_columns:
            found.append(("PBI062", f"{cat[1]}[{cat[2]}] is time, shown down the vertical axis — time reads left "
                                    "to right: use a column or line chart"))
    if vtype in CHART_TYPES and page_w > 320 and (h < 140 or w < 200):
        found.append(("PBI064", f"{w:g}×{h:g} px is too small for a chart — at least 200×140, or use a card"))
    return found


def theme_colour_clashes(rep: Path) -> list[tuple[Path, str]]:
    """The custom theme's first 6 data colours that a person with colour-vision deficiency would confuse."""
    try:
        sys_path = str(Path(__file__).resolve().parent)
        if sys_path not in _sys.path:
            _sys.path.insert(0, sys_path)
        import make_theme
        rj = _json.loads((rep / "definition" / "report.json").read_text(encoding="utf-8-sig"))
        name = ((rj.get("themeCollection") or {}).get("customTheme") or {}).get("name")
        f = rep / "StaticResources" / "RegisteredResources" / name if name else None
        colours = _json.loads(f.read_text(encoding="utf-8-sig")).get("dataColors", [])[:6] if f and f.exists() else []
    except (OSError, ValueError, ImportError):
        return []
    out = []
    for i, a in enumerate(colours):
        for b in colours[i + 1:]:
            try:
                d = make_theme.distances(a, b)
            except ValueError:
                continue
            kind = min(("protanopia", "deuteranopia"), key=lambda k: d[k])
            if d[kind] < 8 or d["tritanopia"] < 5:
                kind = kind if d[kind] < 8 else "tritanopia"
                out.append((f, f"data colours {a} and {b} look alike with {kind} (ΔE {d[kind]:.1f}); about 1 in "
                               "12 men sees them as the same — `make_theme.py` picks a palette that stays apart"))
    return out


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

    measure_dax: dict[str, str] = {}
    time_columns: set[tuple[str, str]] = set()
    for d in defs:
        model = parse_model(d)
        for _t, _m in model.measures:
            measure_dax[_m.name] = _m.expression
        for _t in model.tables:
            for _c in _t.columns:
                if _c.data_type == "dateTime" or _t.data_category == "Time" or TIME_NAME.match(_c.name):
                    time_columns.add((_t.name, _c.name))
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
                is_text = ("FORMAT" in m.expression.upper() or m.expression.lstrip().startswith('"')
                           or re.search(r'"#[0-9A-Fa-f]{6}"', m.expression) is not None
                           or re.search(r'"\s*&|&\s*"', m.expression) is not None)
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
        for t in model.tables:
            if t.name.startswith("_"):
                continue
            is_fact = t.name in from_tables and t.name not in to_tables
            is_dim = t.name in to_tables or t.name in date_tables
            want = "ft_" if is_fact else "dm_" if is_dim else None
            if want and not t.name.startswith(want):
                kind = "fact" if is_fact else "dimension"
                add("PBI049", rel(t.file), f"{kind} '{t.name}' — name it {want}{re.sub(r'[^a-z0-9]+', '_', t.name.lower()).strip('_')}",
                    t.line, model_ign | ignored_rules(t.annotations))
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
        report_families: set[str] = set()
        for theme_file, pair in theme_colour_clashes(rep):
            add("PBI065", rel(theme_file), pair)
        for pj in sorted(rep.glob("definition/pages/*/page.json")):
            try:
                pdata = _json.loads(pj.read_text(encoding="utf-8-sig"))
            except ValueError:
                add("PBI004", rel(pj), "invalid JSON")
                continue
            display = pdata.get("displayName", "")
            page_w, page_h = pdata.get("width", 1280), pdata.get("height", 720)
            names.append(display.lower())
            if GENERIC_PAGE.match(display.strip()):
                add("PBI042", rel(pj), f"page '{display}' — name it after the question it answers")
            data_visuals = slicers = 0
            boxes: list[tuple[float, float, float, float, str, str, tuple]] = []
            cards: list[tuple[float, float, str]] = []
            tab_items: list[tuple[float, float, float, str]] = []
            page_fills: set[str] = set()
            for vj in sorted(pj.parent.glob("visuals/*/visual.json")):
                try:
                    container = _json.loads(vj.read_text(encoding="utf-8-sig"))
                except ValueError:
                    add("PBI004", rel(vj), "invalid JSON")
                    continue
                v = container.get("visual", {}) or {}
                vtype = v.get("visualType", "")
                pos = container.get("position", {}) or {}
                x, y = pos.get("x", 0), pos.get("y", 0)
                w, h = pos.get("width", 0), pos.get("height", 0)
                where_v = rel(vj)
                if x < 0 or y < 0 or x + w > page_w + 0.5 or y + h > page_h + 0.5:
                    add("PBI052", where_v, f"{vtype or 'visual'} on page '{display}' goes outside the "
                                           f"{page_w}×{page_h} page")
                off = [n for n, val in (("x", x), ("y", y), ("width", w), ("height", h))
                       if not (val <= 2 and n in ("width", "height")) and round(val) % 4]
                if off and min(w, h) > 2:
                    add("PBI048", where_v, f"{vtype or 'visual'} on page '{display}': {', '.join(off)} not a "
                                           "multiple of 4 px — align it to the grid")
                radius = num_literal(((vco_or(v).get("border") or [{}])[0].get("properties") or {}).get("radius"))
                if radius is not None and radius > 8:
                    add("PBI066", where_v, f"{vtype or 'visual'} on page '{display}': corner radius {radius:g} px — "
                                           "keep 0–8 px; very round cards read as a template, not a product")
                shadow = ((vco_or(v).get("dropShadow") or [{}])[0].get("properties") or {}).get("show")
                if str(num_literal(shadow, raw=True)).lower() == "true":
                    add("PBI067", where_v, f"{vtype or 'visual'} on page '{display}' has a shadow — use the "
                                           "hairline border; depth adds noise, not meaning")
                text_cols, fill_cols = colour_usage(v)
                page_fills |= {c for c in fill_cols if not is_neutral(c)}
                low = sorted(c for c in text_cols if contrast_on_white(c) < 4.5)
                if low:
                    add("PBI054", where_v, f"{vtype} on page '{display}': text colour {', '.join(low)} has "
                                           f"{contrast_on_white(low[0]):.1f}:1 on white (minimum 4.5:1)")
                vco_ = v.get("visualContainerObjects", {}) or {}
                for axis in ("valueAxis", "categoryAxis"):
                    shown = (((v.get("objects", {}) or {}).get(axis) or [{}])[0].get("properties", {})
                             .get("showAxisTitle", {}).get("expr", {}).get("Literal", {}).get("Value"))
                    if str(shown).lower() == "true":
                        add("PBI057", where_v, f"{vtype} on page '{display}' shows the {axis} title — the visual "
                                               "title already says what is measured")
                sizes, families = font_usage(v)
                report_families |= {family_of(f) for f in families}
                limit = MAX_PT["textbox"] if vtype == "textbox" else (
                    MAX_PT["big"] if vtype in BIG_NUMBER_VISUALS else MAX_PT["other"])
                if sizes and max(sizes) > limit:
                    add("PBI047", where_v, f"{vtype} on page '{display}' uses {max(sizes):g} pt — "
                                           f"keep it ≤ {limit} pt (see the type scale)")
                if vtype in SLICERS:
                    slicers += 1
                    tab_items.append((pos.get("tabOrder", pos.get("z", 0)), y, x, vtype))
                    mode = (((v.get("objects", {}).get("data") or [{}])[0].get("properties", {})
                             .get("mode", {}).get("expr", {}).get("Literal", {}).get("Value", "")) or "").strip("'")
                    compact = mode in ("Dropdown", "Between", "Before", "After")
                    max_h, max_w = (48, 240) if compact else (320, 320)
                    if h > max_h or w > max_w:
                        add("PBI046", where_v, f"{mode or 'list'} slicer on page '{display}' is {w:g}×{h:g} px "
                                               f"— keep it within {max_w}×{max_h} px")
                    continue
                if not vtype or vtype in DECORATIVE or chromeless(container):
                    continue
                data_visuals += 1
                tab_items.append((pos.get("tabOrder", pos.get("z", 0)), y, x, vtype))
                roles_ = projections(v)
                boxes.append((x, y, w, h, where_v, vtype,
                              tuple(sorted(f"{e}[{p_}]" for r_ in roles_.values() for _, e, p_ in r_))))
                tprops = ((vco_.get("title") or [{}])[0].get("properties", {}))
                title_show = str(tprops.get("show", {}).get("expr", {}).get("Literal", {}).get("Value", "")).lower()
                title_text = tprops.get("text", {})
                literal = str(title_text.get("expr", {}).get("Literal", {}).get("Value", "")).strip("'") \
                    if isinstance(title_text, dict) else ""
                has_title = title_show != "false" and bool(literal or "Measure" in str(title_text))
                if not has_title:
                    add("PBI056", where_v, f"{vtype} on page '{display}' has no title — say what it shows, "
                                           "in a sentence")
                elif literal and GENERIC_TITLE.match(literal):
                    add("PBI055", where_v, f"{vtype} on page '{display}': title '{literal}' is auto-generated — "
                                           "write the question or the conclusion")
                alt = (v.get("visualContainerObjects", {}).get("general", [{}]) or [{}])[0] \
                    .get("properties", {}).get("altText")
                if not alt:
                    add("PBI019", rel(vj), f"{vtype} on page '{display}' has no alt text")
                if vtype in ("pieChart", "donutChart"):
                    add("PBI040", rel(vj), f"{vtype} on page '{display}' — ≤ 3 slices, otherwise a sorted bar")
                for rule, msg in design_review(v, w, h, literal, page_w, measure_dax, time_columns):
                    add(rule, where_v, f"{vtype} on page '{display}': {msg}")
                if vtype in BIG_NUMBER_VISUALS:
                    cards.append((y, w, where_v))
            if data_visuals > 8:
                add("PBI018", rel(pj), f"page '{display}' has {data_visuals} data visuals (target ≤ 8)")
            if page_w > 320:
                for rule, where_g, msg in layout_review(boxes):
                    add(rule, where_g, f"page '{display}': {msg}")
            rows_of_cards: dict[float, list] = {}
            for cy, cw, where_c in cards:
                rows_of_cards.setdefault(round(cy / 8), []).append((cw, where_c))
            for row in rows_of_cards.values():
                narrow = [c for c in row if c[0] < 176]
                if len(row) > 5 or narrow:
                    add("PBI063", (narrow or row)[0][1], f"page '{display}': {len(row)} KPI cards in one row"
                        + (f", the narrowest {min(c[0] for c in row):g} px wide" if narrow else "")
                        + " — at most 5 per row, each at least 176 px, so values and context lines fit")
            by_tab = [t[3] + str(t[1:3]) for t in sorted(tab_items)]
            by_reading = [t[3] + str(t[1:3]) for t in sorted(tab_items, key=lambda t: (t[1], t[2]))]
            if by_tab != by_reading:
                add("PBI053", rel(pj), f"page '{display}': keyboard order does not follow the reading order "
                                       "(top to bottom, left to right) — set tabOrder accordingly")
            if len(page_fills) > 6:
                add("PBI058", rel(pj), f"page '{display}' uses {len(page_fills)} colours "
                                       f"({', '.join(sorted(page_fills))}) — keep ≤ 6, colour only what matters")
            if slicers > 2:
                add("PBI050", rel(pj), f"page '{display}' has {slicers} slicers — keep ≤ 2 on the page, "
                                       "move the rest to the filter pane")
        if not DOC_PAGES & set(names):
            add("PBI006", rel(rep), "no Documentation page (Documentação/Documentation)")
        odd = sorted(f for f in report_families if f in UGLY_FONTS or f not in PRO_FONTS)
        if len(report_families) > 1 or any(f in UGLY_FONTS for f in report_families):
            add("PBI051", rel(rep), f"fonts in use: {', '.join(sorted(report_families))} — one family "
                                    "(Segoe UI, two weights) unless the brand defines another"
                                    + (f"; avoid {', '.join(odd)}" if odd else ""))
    for pbip in sorted(root.rglob("*.pbip")):
        if not any((pbip.parent / n).exists() for n in ("README.md", "readme.md", "LEIAME.md")):
            add("PBI043", rel(pbip.parent) or ".", f"no README.md next to {pbip.name}")
    order = {s: i for i, s in enumerate(SEVERITIES)}
    out.sort(key=lambda x: (order[x["severity"]], x["where"], x["line"], x["rule"]))
    return out


def harmony(root: Path, issues: list) -> list[tuple[str, str, int]]:
    """(report, page, score) for every page: 100 minus HARMONY_PENALTY for each finding on that page."""
    out = []

    def order(pj: Path) -> tuple:
        try:
            meta = _json.loads((pj.parent.parent / "pages.json").read_text(encoding="utf-8-sig"))
            return (str(pj.parents[3]), meta.get("pageOrder", []).index(pj.parent.name))
        except (ValueError, OSError):
            return (str(pj.parents[3]), 10 ** 6)
    for pj in sorted(root.rglob("*.Report/definition/pages/*/page.json"), key=order):
        try:
            name = _json.loads(pj.read_text(encoding="utf-8-sig")).get("displayName", pj.parent.name)
        except ValueError:
            continue
        page_dir = pj.parent.relative_to(root).as_posix() + "/"
        report = pj.parents[3].name
        hits = [i for i in issues if i["where"].startswith(page_dir) or i["where"] == page_dir + "page.json"]
        out.append((report, name, max(0, 100 - sum(HARMONY_PENALTY[i["severity"]] for i in hits))))
    return out


def hook(stdin_text: str, min_harmony: int = 90) -> int:
    """Claude Code PostToolUse hook: audit the PBIP project the edited file belongs to.

    Silent (exit 0) when the project is fine; otherwise prints a short report to stderr and exits 2,
    which Claude Code shows to the agent right after its edit.
    """
    try:
        event = _json.loads(stdin_text or "{}")
    except ValueError:
        return 0
    tool_input = event.get("tool_input") or {}
    edited = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not edited:
        return 0
    path = Path(edited)
    if not path.is_absolute():
        path = Path(event.get("cwd") or ".") / path
    item = next((p for p in [path, *path.parents] if p.suffix in (".Report", ".SemanticModel")), None)
    if item is None:
        return 0
    root = item.parent
    issues = audit(root, load_config(root, None))
    scores = harmony(root, issues)
    blockers = [i for i in issues if i["severity"] == "BLOCKER"]
    low = [(p, sc) for _, p, sc in scores if sc < min_harmony]
    if not blockers and not low:
        return 0
    try:
        edited_rel = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        edited_rel = ""
    here = [i for i in issues if edited_rel and i["where"].startswith(edited_rel.rsplit("/", 1)[0])]
    lines = [f"powerbi-architect audit after editing {edited_rel or path.name}:"]
    for i in (blockers + [i for i in here if i not in blockers])[:12]:
        where = f"{i['where']}:{i['line']}" if i["line"] else i["where"]
        lines.append(f"  {i['rule']} {i['severity']:<10} {where} — {i['message']}")
    if scores:
        lines.append("  Harmony: " + " · ".join(f"{p} {sc}" for _, p, sc in scores)
                     + f" (deliver at {min_harmony}+)")
    lines.append(f"  Full list: python {Path(__file__).name} {root} --min-harmony {min_harmony}")
    print("\n".join(lines), file=_sys.stderr)
    return 2


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
    ap.add_argument("--min-harmony", type=int, metavar="N",
                    help="also fail when a page's harmony score is below N (the skill asks for 90)")
    ap.add_argument("--hook", action="store_true",
                    help="Claude Code PostToolUse hook: read the event from stdin, audit the edited project, "
                         "stay silent when it is fine (installed by pbi_graph.py install)")
    ap.add_argument("--version", action="version", version=f"%(prog)s {skill_version()}")
    args = ap.parse_args(argv)
    for stream in (_sys.stdin, _sys.stdout, _sys.stderr):   # Windows consoles default to a legacy code page
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except ValueError:
                pass

    if args.hook:
        return hook(_sys.stdin.read(), args.min_harmony if args.min_harmony is not None else 90)
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
        scores = harmony(root, issues)
        if scores:
            print("Harmony: " + " · ".join(f"{p} {s}" for _, p, s in scores))
    if args.min_harmony is not None and any(s < args.min_harmony for _, _, s in harmony(root, issues)):
        return 1
    if args.fail_on == "never":
        return 0
    limit = SEVERITIES.index(args.fail_on.upper())
    return 1 if any(SEVERITIES.index(i["severity"]) <= limit for i in issues) else 0


if __name__ == "__main__":
    raise SystemExit(main())
