#!/usr/bin/env python3
"""pbir_layout.py — build PBIR report pages from a short layout spec (part of the powerbi-architect skill).

Python 3.9+ standard library only. Offline. Writes only inside the <Name>.Report folder it is given.

    python pbir_layout.py <spec.json> <Name>.Report [--theme theme.json] [--check]
    python pbir_layout.py --extract <Name>.Report [--out layout.json]     # restyle an existing report

You describe each page as rows of visuals; the script computes every position on the 4 px grid and
writes the app shell of references/report-design.md §0 (sidebar with icons and page navigator, white
panel, top bar with breadcrumb, "updated at" and compact slicers), KPI cards with a variation line,
charts, tables with one conditional colour, drill-through pages with a back arrow, tooltip pages and a
phone layout (mobile.json, stacked). Misalignment becomes impossible: you never type a coordinate.

Spec (JSON):
{
  "app": "Contas a receber",                 # app name in the sidebar and breadcrumb
  "measures": "_Medidas",                    # table that holds the measures (bare names resolve here)
  "updated": "Texto Atualizacao",            # text measure for the top bar ("Atualizado em ...")
  "slicers": ["dm_cliente[Segmento]"],       # ≤ 2 compact slicers on every page that does not set "slicers"
  "pages": [
    {"name": "Visão Geral", "icon": "layout-dashboard",
     "rows": [
       {"height": 88, "visuals": [
          {"type": "kpi", "measure": "Valor Aberto", "label": "Saldo em aberto",
           "variation": "Texto Var Aberto", "variationColor": "Cor Var Aberto"}]},
       {"height": 248, "split": [2, 1], "visuals": [
          {"type": "lineChart", "category": "dm_calendario[Ano-Mês]", "values": ["Valor Vencido"],
           "titleMeasure": "Titulo Vencido", "alt": "...", "sort": "category"},
          {"type": "clusteredBarChart", "category": "dm_regional[Regional]", "values": ["Valor Vencido"],
           "title": "Vencido por regional", "alt": "...", "sort": "desc", "tooltipPage": "Tooltip regional"}]}]},
    {"name": "Detalhe do cliente", "kind": "drillthrough", "drillField": "dm_cliente[Cliente]",
     "parent": "Clientes", "rows": [...]},
    {"name": "Tooltip regional", "kind": "tooltip", "visuals": [...]}
  ]
}

Visual types: kpi, card, lineChart, clusteredBarChart, clusteredColumnChart, waterfallChart, tableEx
(options: "columns", "sortBy": "<measure> desc", "top": n, "highlight": {"column": <measure>,
"colorMeasure": <measure>}), slicer ("field"), and
  matrix    {"rows": [fields], "columns": [fields], "values": [measures], "sortBy", "top", "highlight": {...}}
"top": n writes Power BI's Top N visual filter (first column, ranked by the sortBy measure) and sizes an
"auto" row for n rows: a table on a summary page shows the rows that fit, and its title says so.
  combo     {"category": field, "values": [column measures], "lineValues": [line measures]}
  scatter   {"details": field, "x": measure, "y": measure, "size": measure, "labels": true (≤ 12 points)}
  kpiTrend  {"measure": m, "trend": date field, "goal": m, "label": "..."}   (native KPI visual)
Chart craft: "target": m on lineChart and combo adds the target as a thin grey dashed line;
combo puts the line on the columns' axis when it has a target ("sameAxis": true/false to choose);
"target": m on bar and column charts paints the bars below the target red and the rest in the accent
("higherIsBetter": false flips it, "belowColor" changes the red); "colorMeasure": m colours each bar from a
measure that returns a hex instead. Row "height": "auto" fits the content (bars: 52 + 32 per expected category,
set "items": n on the visual; tables: 64 + 28 per row); "fill" takes what is left of the 616 px.
A field parameter is just a column: use its column as "category" or "rows" and put a slicer on it.
Every data visual needs "alt" (alt text) and "title" or "titleMeasure" (kpi uses "label").
Row heights plus 16 px gutters must fit the 616 px content area. --check validates without writing.
Measures outside the "measures" table: "measureHome": {"Receita": "Vendas"}.

--extract reads an existing PBIR report (any layout) and writes the spec that rebuilds it on the
standard: visuals grouped into rows by position, widths turned into split weights, heights fitted to
the content area, titles, alt text, sorting, tooltips and drill-through kept; pies become sorted bars;
decoration (shapes, text boxes, images, buttons) is dropped. Notes on stderr list what needs a human.
Build the spec into the same folder to restyle it (pages are rewritten: commit first).
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import zlib
import math
from fractions import Fraction
import json
import re
import shutil
import sys
from pathlib import Path

SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
INK, INK3, LINE, ACCENT = "#333333", "#757575", "#EBEBEB", "#3E63DD"
TARGET = "#999999"   # target and reference series: visible, but quieter than the data
ALERT = "#CE2C31"    # bars on the wrong side of their target
PAGE_W, PAGE_H = 1280, 720
CONTENT_X, CONTENT_Y, CONTENT_W, CONTENT_H, GUTTER = 232, 80, 1024, 616, 16
NAV_X, NAV_Y, NAV_ITEM = 8, 76, 32
PHONE_W, PHONE_MARGIN = 320, 8
ICONS = Path(__file__).resolve().parent.parent / "templates" / "icons"
CHARTS = {"lineChart", "clusteredBarChart", "clusteredColumnChart", "waterfallChart"}
SPEC_TYPES = {"kpi", "card", "tableEx", "slicer", "matrix", "combo", "scatter", "kpiTrend"} | CHARTS



def write_lf(path: Path, text: str) -> None:
    """UTF-8 with LF line endings on every OS (write_text has no newline= before Python 3.10)."""
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)

class SpecError(ValueError):
    pass


# ---------------------------------------------------------------------- your edits survive a rebuild
# The engine remembers what it wrote last time in <project>/.powerbi-architect/<Name>.Report.layout-lock.json.
# On the next build every file is merged three ways, like git: base = what the engine wrote last time,
# theirs = what is on disk now (your edits in Desktop or by hand), ours = what the spec produces now.
# Your change wins wherever both sides changed the same property. Visuals and pages you added are left
# alone, visuals you deleted stay deleted, and files you never touched follow the spec.
MISSING = object()
LOCK_VERSION = 1


def lock_path(report: Path) -> Path:
    return report.parent / ".powerbi-architect" / f"{report.name}.layout-lock.json"


def pack(text: str) -> str:
    return base64.b64encode(zlib.compress(text.encode("utf-8"), 9)).decode("ascii")


def unpack(blob: str) -> str:
    return zlib.decompress(base64.b64decode(blob)).decode("utf-8")


def merge3(base, ours, theirs, path: str, conflicts: list):
    """Three-way merge of JSON values; on a real conflict the value on disk (the user's) wins."""
    if ours == theirs or theirs == base:
        return ours
    if ours == base:
        return theirs
    if all(isinstance(v, dict) for v in (base, ours, theirs) if v is not MISSING) and \
            isinstance(ours, dict) and isinstance(theirs, dict):
        b = base if isinstance(base, dict) else {}
        out = {}
        for k in list(theirs) + [k for k in ours if k not in theirs]:
            v = merge3(b.get(k, MISSING), ours.get(k, MISSING), theirs.get(k, MISSING), f"{path}.{k}", conflicts)
            if v is not MISSING:
                out[k] = v
        return out
    if path.endswith(".pageOrder") and isinstance(ours, list) and isinstance(theirs, list):
        kept = [p for p in theirs if p in ours]            # your order, minus pages the spec removed
        return kept + [p for p in ours if p not in kept]    # plus pages the spec added, at the end
    conflicts.append(path.lstrip("."))
    return theirs


class MergeResult:
    def __init__(self):
        self.written, self.kept, self.merged, self.removed, self.deleted_by_you = [], [], [], [], []
        self.conflicts: dict[str, list[str]] = {}
        self.fresh = False

    def lines(self, report: Path) -> list[str]:
        out = []
        for rel in self.merged:
            extra = f" (your value kept for {', '.join(self.conflicts[rel][:4])})" if self.conflicts.get(rel) else ""
            out.append(f"merged your edits and the spec in {describe(report, rel)}{extra}")
        out += [f"kept your version of {describe(report, rel)}" for rel in self.kept]
        out += [f"left deleted, as you did: {rel}" for rel in self.deleted_by_you]
        return out


def describe(report: Path, rel: str) -> str:
    """'Página › tipo "título"' for a visual, or the relative path."""
    try:
        data = json.loads((report / rel).read_text(encoding="utf-8-sig"))
        page = json.loads((report / rel).parents[2].joinpath("page.json").read_text(encoding="utf-8-sig"))
        vis = data.get("visual") or {}
        title = _lit(_prop(vis.get("visualContainerObjects") or {}, "title", "text")) or ""
        return f"{page.get('displayName', '?')} › {vis.get('visualType', '?')}" + (f' "{title}"' if title else "")
    except (OSError, ValueError, AttributeError, IndexError):
        return rel


def merge_write(report: Path, files: dict[str, str], scope: str, force: bool = False) -> MergeResult:
    """Write `files` under `report`, merging with what is on disk instead of overwriting it.

    scope is the path prefix these files own ("definition/pages/" for pages): base entries under it that
    the spec no longer produces are removed when you have not changed them.
    """
    res = MergeResult()
    lp = lock_path(report)
    lock = json.loads(lp.read_text(encoding="utf-8")) if lp.exists() else {}
    try:
        base_all = json.loads(unpack(lock["files"])) if lock.get("version") == LOCK_VERSION else {}
    except (KeyError, ValueError, TypeError, zlib.error):
        base_all = {}                                     # unreadable lock: behave like a first build
    base = {k: v for k, v in base_all.items() if k.startswith(scope)}
    fresh = force or not any((report / k).exists() for k in base)
    if fresh:
        res.fresh = True
        if scope.endswith("/") and (report / scope).exists():
            shutil.rmtree(report / scope)                 # first build (or --force): the spec owns the folder
        base = {}

    def load(text):
        try:
            return json.loads(text)
        except ValueError:
            return text

    for rel in sorted(set(files) | set(base)):
        target = report / rel
        new = files.get(rel)
        old = base.get(rel)
        disk = target.read_text(encoding="utf-8-sig") if target.exists() else None
        if new is not None:
            if disk is None:
                if old is None:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    write_lf(target, new)
                    res.written.append(rel)
                else:
                    res.deleted_by_you.append(rel)
                continue
            n, d = load(new), load(disk)
            if n == d:
                continue
            o = load(old) if old is not None else MISSING
            if d == o:
                write_lf(target, new)
                res.written.append(rel)
                continue
            if n == o:
                res.kept.append(rel)
                continue
            conflicts: list[str] = []
            merged = merge3(o, n, d, "", conflicts)
            if isinstance(merged, (dict, list)):
                write_lf(target, json.dumps(merged, indent=2, ensure_ascii=False) + "\n")
                res.merged.append(rel)
                res.conflicts[rel] = conflicts
            else:
                res.kept.append(rel)
        elif disk is not None:
            if load(disk) == load(old):
                target.unlink()
                res.removed.append(rel)
                for parent in target.parents:
                    if parent == report or any(parent.iterdir()):
                        break
                    parent.rmdir()
            else:
                res.kept.append(rel)
    kept_files = {**{k: v for k, v in base_all.items() if not k.startswith(scope)}, **files}
    lock = {"about": "Written by pbir_layout.py: what it generated last time, so your manual edits survive the "
                     "next build. Commit it with the report; do not edit it.",
            "version": LOCK_VERSION, "files": pack(json.dumps(kept_files, sort_keys=True, ensure_ascii=False))}
    lp.parent.mkdir(parents=True, exist_ok=True)
    lp.write_text(json.dumps(lock, indent=1) + "\n", encoding="utf-8")
    return res


def hid(*parts: str) -> str:
    return hashlib.sha1("/".join(parts).encode()).hexdigest()[:20]


def lit(v: str):
    return {"expr": {"Literal": {"Value": v}}}


def color(hex_: str):
    return {"solid": {"color": lit(f"'{hex_}'")}}


def quote(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


class Builder:
    def __init__(self, spec: dict):
        self.spec = spec
        self.current_page = ""
        self.measures = spec.get("measures", "_Medidas")
        self.measure_home = spec.get("measureHome", {})   # measures that live outside "measures"
        self.app = spec.get("app", "Relatório")
        self.accent = spec.get("accent", ACCENT)          # main data colour; --theme sets it from dataColors[0]
        # "id" pins a page or visual to an existing folder (set by --extract), so a rebuild lands on the
        # same files instead of creating copies; otherwise ids are derived from the names.
        self.page_ids = {p["name"]: p.get("id") or hid("page", p["name"]) for p in spec["pages"]}
        self.ids: dict[tuple[str, str], str] = {}
        self.icons_used: set[str] = set()
        self.notes: list[str] = []                      # printed after the build: things to decide

    # ------------------------------------------------------------------ fields
    def ref(self, name: str):
        m = re.match(r"^(.+?)\[(.+)\]$", name)
        if m:
            return "Column", m.group(1).strip("'"), m.group(2)
        return "Measure", self.measure_home.get(name, self.measures), name

    def field(self, name: str):
        kind, entity, prop = self.ref(name)
        return {kind: {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}

    def proj(self, name: str):
        kind, entity, prop = self.ref(name)
        return {"field": self.field(name), "queryRef": f"{entity}.{prop}", "nativeQueryRef": prop}

    def measure_expr(self, name: str):
        return {"expr": self.field(name)}

    # ------------------------------------------------------------------ primitives
    @staticmethod
    def container(vid, pos, z, visual):
        x, y, w, h = pos
        visual = dict(visual)
        filters = visual.pop("_filterConfig", None)          # visual-level filters live on the container
        out = {"$schema": f"{SCHEMA}/visualContainer/1.1.0/schema.json", "name": vid,
               "position": {"x": x, "y": y, "z": z, "width": w, "height": h, "tabOrder": z},
               "visual": visual}
        if filters:
            out["filterConfig"] = filters
        return out

    @staticmethod
    def textbox(*runs):
        return {"visualType": "textbox",
                "objects": {"general": [{"properties": {"paragraphs": [{"textRuns": list(runs)}]}}]},
                "drillFilterOtherVisuals": True}

    @staticmethod
    def run(value, size, ink, semibold=False):
        return {"value": value, "textStyle": {"fontFamily": "Segoe UI Semibold" if semibold else "Segoe UI",
                                              "fontSize": f"{size}pt", "color": ink}}

    @staticmethod
    def shape(fill, *, panel=False, rounded=False):
        v = {"visualType": "shape",
             "objects": {"shape": [{"properties": {"tileShape": lit("'rectangleRounded'" if rounded else "'rectangle'")}}],
                         "fill": [{"properties": {"show": lit("true"), "fillColor": color(fill)}}],
                         "outline": [{"properties": {"show": lit("false")}}]},
             "drillFilterOtherVisuals": True}
        if panel:
            v["visualContainerObjects"] = {
                "background": [{"properties": {"show": lit("true"), "color": color("#FFFFFF")}}],
                "border": [{"properties": {"show": lit("true"), "color": color(LINE), "radius": lit("8D")}}]}
        return v

    def image(self, icon: str, alt: str, back: bool = False):
        self.icons_used.add(icon)
        v = {"visualType": "image",
             "objects": {"general": [{"properties": {"imageUrl": {"expr": {"ResourcePackageItem": {
                 "PackageName": "RegisteredResources", "PackageType": 1, "ItemName": f"{icon}.png"}}}}}],
                 "imageScaling": [{"properties": {"imageScalingType": lit("'Fit'")}}]},
             "visualContainerObjects": {"general": [{"properties": {"altText": lit(quote(alt))}}],
                                        "background": [{"properties": {"show": lit("false")}}],
                                        "border": [{"properties": {"show": lit("false")}}]},
             "drillFilterOtherVisuals": True}
        if back:
            v["visualContainerObjects"]["visualLink"] = [{"properties": {"show": lit("true"), "type": lit("'Back'")}}]
        return v

    def data_visual(self, vtype, roles, alt, *, title=None, title_measure=None, sort=None, objects=None,
                    chrome=True, tooltip_page=None):
        v = {"visualType": vtype, "query": {"queryState": roles}}
        if sort:
            v["query"]["sortDefinition"] = {"sort": [{"field": self.field(sort[0]), "direction": sort[1]}],
                                            "isDefaultSort": True}
        vco = {"general": [{"properties": {"altText": lit(quote(alt))}}]}
        if title_measure:
            vco["title"] = [{"properties": {"show": lit("true"), "text": self.measure_expr(title_measure)}}]
        elif title:
            vco["title"] = [{"properties": {"show": lit("true"), "text": lit(quote(title))}}]
        if not chrome:
            vco["title"] = [{"properties": {"show": lit("false")}}]
            vco["background"] = [{"properties": {"show": lit("false")}}]
            vco["border"] = [{"properties": {"show": lit("false")}}]
        if tooltip_page:
            if tooltip_page not in self.page_ids:
                raise SpecError(f"tooltipPage '{tooltip_page}' is not a page in the spec")
            vco["visualTooltip"] = [{"properties": {"show": lit("true"), "type": lit("'ReportPage'"),
                                                     "section": lit(quote(self.page_ids[tooltip_page]))}}]
        v["visualContainerObjects"] = vco
        if objects:
            v["objects"] = objects
        v["drillFilterOtherVisuals"] = True
        return v

    # ------------------------------------------------------------------ chart craft
    def target_series(self, measure: str) -> dict:
        """The target as a thin grey dashed line without labels: context, not a second story."""
        _, entity, prop = self.ref(measure)
        sel = {"metadata": f"{entity}.{prop}"}
        return {"dataPoint": [{"properties": {"fill": color(TARGET)}, "selector": sel}],
                "lineStyles": [{"properties": {"lineStyle": lit("'dashed'"), "strokeWidth": lit("1D"),
                                               "showMarker": lit("false")}, "selector": sel}],
                "labels": [{"properties": {"showSeries": lit("false")}, "selector": sel}]}

    def top_filter(self, column: str, measure: str, n: int, descending: bool) -> dict:
        """Power BI's own Top N visual filter: the n rows of `column` with the highest (or lowest) `measure`."""
        ck, ce, cp = self.ref(column)
        mk, me, mp = self.ref(measure)
        if ck != "Column" or mk != "Measure":
            raise SpecError(f"'top' keeps the first column's top rows by a measure: first column '{column}', "
                            f"sortBy '{measure}' must be a measure")
        src = [{"Name": "c", "Entity": ce, "Type": 0}] + ([{"Name": "m", "Entity": me, "Type": 0}] if me != ce else [])
        col = {"Column": {"Expression": {"SourceRef": {"Source": "c"}}, "Property": cp}}
        query = {"Version": 2, "From": src,
                 "Select": [{**col, "Name": "field"}],
                 "OrderBy": [{"Direction": 2 if descending else 1,
                              "Expression": {"Measure": {"Expression": {"SourceRef": {"Source": "m" if me != ce else "c"}},
                                                         "Property": mp}}}],
                 "Top": n}
        return {"filters": [{"name": hid("top", column, measure, str(n)), "field": self.field(column), "type": "TopN",
                             "filter": {"Version": 2,
                                        "From": [{"Name": "subquery", "Expression": {"Subquery": {"Query": query}}, "Type": 2},
                                                 {"Name": "c", "Entity": ce, "Type": 0}],
                                        "Where": [{"Condition": {"In": {"Expressions": [col],
                                                                        "Table": {"SourceRef": {"Source": "subquery"}}}}}]}}]}

    def colour_by(self, measure: str) -> dict:
        """Bar colour from a measure that returns a hex per category (e.g. red below the target)."""
        return {"properties": {"fill": {"solid": {"color": self.measure_expr(measure)}}},
                "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}}

    def colour_by_target(self, measure: str, target: str, below: str = ALERT, higher_is_better: bool = True) -> dict:
        """Bars on the wrong side of the target in `below` (red), the others in the accent: Power BI's
        rule-based conditional colour, written as a Conditional expression (no extra DAX measure)."""
        kind = 3 if higher_is_better else 1          # LessThan / GreaterThan the target
        rule = {"Conditional": {
            "Cases": [{"Condition": {"Comparison": {"ComparisonKind": kind, "Left": self.field(measure),
                                                    "Right": self.field(target)}},
                       "Value": {"Literal": {"Value": f"'{below}'"}}}],
            "DefaultValue": {"Literal": {"Value": f"'{self.accent}'"}}}}
        return {"properties": {"fill": {"solid": {"color": {"expr": rule}}}},
                "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}}

    @staticmethod
    def auto_height(visuals: list[dict]) -> int:
        """Row height that fits its content: bars grow with the expected number of categories."""
        need = 0
        for v in visuals:
            t, n = v.get("type"), v.get("items") or v.get("top")
            if t in ("kpi", "card"):
                h = 88
            elif t == "kpiTrend":
                h = 120
            elif t == "clusteredBarChart" and n:
                h = 52 + 32 * n                         # title + 32 px per bar (24 bar + 8 gap)
            elif t in ("tableEx", "matrix") and n:
                h = 64 + 28 * min(n, 20)                # header + rows
            else:
                h = 248
            need = max(need, max(h, 160) if t not in ("kpi", "card") else h)
        return -(-need // 4) * 4

    # ------------------------------------------------------------------ components
    def component(self, spec: dict, pos):
        """Return [(key, pos, visual), ...] for one spec visual placed at pos."""
        t = spec.get("type")
        alt = spec.get("alt") or spec.get("label") or spec.get("title")
        if not alt:
            raise SpecError(f"visual {spec} needs 'alt' text")
        x, y, w, h = pos
        first = (spec.get("measure") or spec.get("category") or spec.get("details")
                 or (spec.get("columns") or spec.get("rows") or [""])[0])
        key = spec.get("key") or f"{t}-{first}"
        if spec.get("id"):
            self.ids[(self.current_page, key)] = spec["id"]
        if spec.get("varId"):
            self.ids[(self.current_page, key + "-var")] = spec["varId"]
        if t in ("kpi", "card"):
            out = [(key, pos, self.data_visual("card", {"Values": {"projections": [self.proj(spec["measure"])]}},
                                               alt, title=spec.get("label") or spec.get("title")))]
            if spec.get("variation"):
                objects = {"labels": [{"properties": {"fontSize": lit("9D"), "fontFamily": lit("'Segoe UI'"),
                                                      "color": {"solid": {"color": self.measure_expr(spec["variationColor"])}}
                                                      if spec.get("variationColor") else color(INK3)}}]}
                out.append((key + "-var", (x + 12, y + h - 28, w - 24, 20), self.data_visual(
                    "card", {"Values": {"projections": [self.proj(spec["variation"])]}},
                    f"Variação de {spec.get('label', spec['measure'])}", chrome=False, objects=objects)))
            return out
        if t in CHARTS:
            cat_role = "Category"
            values = list(spec["values"])
            if spec.get("target") and t == "lineChart":
                values.append(spec["target"])
            roles = {cat_role: {"projections": [self.proj(spec["category"])]},
                     "Y": {"projections": [self.proj(m) for m in values]}}
            sort = None
            if spec.get("sort") == "desc":
                sort = (spec["values"][0], "Descending")
            elif spec.get("sort") in ("asc", "category"):
                sort = (spec["category"], "Ascending")
            objects = {}
            if t == "waterfallChart" and spec.get("sentiment"):
                s = spec["sentiment"]
                objects = {"sentimentColors": [{"properties": {k + "Fill": color(v) for k, v in s.items()}}]}
            if spec.get("target") and t == "lineChart":
                objects.update(self.target_series(spec["target"]))
            if spec.get("colorMeasure"):
                if t not in ("clusteredBarChart", "clusteredColumnChart"):
                    raise SpecError(f"'colorMeasure' works on bar and column charts, not {t}")
                objects["dataPoint"] = [self.colour_by(spec["colorMeasure"])]
            elif spec.get("target") and t in ("clusteredBarChart", "clusteredColumnChart"):
                # Bars cannot carry a dashed line: the target colours the bars that miss it instead.
                objects["dataPoint"] = [self.colour_by_target(spec["values"][0], spec["target"],
                                                              spec.get("belowColor", ALERT),
                                                              spec.get("higherIsBetter", True))]
            elif spec.get("target") and t != "lineChart":
                raise SpecError(f"'target' works on lineChart, combo, bar and column charts, not {t}")
            objects = objects or None
            return [(key, pos, self.data_visual(t, roles, alt, title=spec.get("title"),
                                                title_measure=spec.get("titleMeasure"), sort=sort,
                                                objects=objects, tooltip_page=spec.get("tooltipPage")))]
        if t in ("tableEx", "matrix"):
            if t == "tableEx":
                roles = {"Values": {"projections": [self.proj(c) for c in spec["columns"]]}}
            else:
                roles = {"Rows": {"projections": [self.proj(c) for c in spec["rows"]]},
                         "Values": {"projections": [self.proj(m) for m in spec["values"]]}}
                if spec.get("columns"):
                    roles["Columns"] = {"projections": [self.proj(c) for c in spec["columns"]]}
            sort = None
            if spec.get("sortBy"):
                name, _, direction = spec["sortBy"].rpartition(" ")
                sort = (name, "Descending" if direction.lower() == "desc" else "Ascending")
            objects = None
            if spec.get("highlight"):
                hl = spec["highlight"]
                kind, entity, prop = self.ref(hl["column"])
                objects = {"values": [{"properties": {"fontColor": {"solid": {"color": self.measure_expr(hl["colorMeasure"])}}},
                                       "selector": {"metadata": f"{entity}.{prop}"}}]}
            vtype = "tableEx" if t == "tableEx" else "pivotTable"
            visual = self.data_visual(vtype, roles, alt, title=spec.get("title"),
                                      title_measure=spec.get("titleMeasure"), sort=sort, objects=objects)
            if spec.get("top") is not None:
                n = spec["top"]
                if not isinstance(n, int) or isinstance(n, bool) or n < 1:
                    raise SpecError(f"'top' is the number of rows to keep, e.g. 8 (got {n!r})")
                if not sort:
                    raise SpecError("'top' needs 'sortBy': \"<measure> desc\" — the rows are the top N by that measure")
                first = spec["columns"][0] if t == "tableEx" else spec["rows"][0]
                visual["_filterConfig"] = self.top_filter(first, sort[0], n, sort[1] == "Descending")
            return [(key, pos, visual)]
        if t == "combo":
            lines = list(spec.get("lineValues", [])) + ([spec["target"]] if spec.get("target") else [])
            roles = {"Category": {"projections": [self.proj(spec["category"])]},
                     "Y": {"projections": [self.proj(m) for m in spec["values"]]},
                     "Y2": {"projections": [self.proj(m) for m in lines]}}
            objects = self.target_series(spec["target"]) if spec.get("target") else {}
            if spec.get("sameAxis", bool(spec.get("target"))):
                # One scale for columns and line: a target or last year must sit on the columns' axis.
                objects["valueAxis"] = [{"properties": {"secShow": lit("false")}}]
            if spec.get("colorMeasure"):
                objects["dataPoint"] = objects.get("dataPoint", []) + [self.colour_by(spec["colorMeasure"])]
            sort = (spec["category"], "Ascending") if spec.get("sort", "category") in ("asc", "category") else None
            return [(key, pos, self.data_visual("lineClusteredColumnComboChart", roles, alt, title=spec.get("title"),
                                                title_measure=spec.get("titleMeasure"), sort=sort,
                                                objects=objects or None, tooltip_page=spec.get("tooltipPage")))]
        if t == "scatter":
            roles = {"Category": {"projections": [self.proj(spec["details"])]},
                     "X": {"projections": [self.proj(spec["x"])]}, "Y": {"projections": [self.proj(spec["y"])]}}
            if spec.get("size"):
                roles["Size"] = {"projections": [self.proj(spec["size"])]}
            scatter_objects = {"categoryLabels": [{"properties": {"show": lit("true"), "fontSize": lit("9D")}}]} \
                if spec.get("labels") else None
            return [(key, pos, self.data_visual("scatterChart", roles, alt, title=spec.get("title"),
                                                title_measure=spec.get("titleMeasure"), objects=scatter_objects,
                                                tooltip_page=spec.get("tooltipPage")))]
        if t == "kpiTrend":
            roles = {"Indicator": {"projections": [self.proj(spec["measure"])]},
                     "TrendLine": {"projections": [self.proj(spec["trend"])]}}
            if spec.get("goal"):
                roles["Goal"] = {"projections": [self.proj(spec["goal"])]}
            return [(key, pos, self.data_visual("kpi", roles, alt, title=spec.get("label") or spec.get("title")))]
        if t == "slicer":
            return [(key, pos, self.data_visual("slicer", {"Values": {"projections": [self.proj(spec["field"])]}},
                                                alt, objects={"data": [{"properties": {"mode": lit("'Dropdown'")}}]}))]
        raise SpecError(f"unknown visual type '{t}'")

    # ------------------------------------------------------------------ layout
    @staticmethod
    def split(total: int, weights: list[float], gutter: int = GUTTER) -> list[int]:
        free = total - gutter * (len(weights) - 1)
        raw = [free * w / sum(weights) for w in weights]
        sizes = [int(r // 4 * 4) for r in raw]
        sizes[-1] += free - sum(sizes)
        return sizes

    def rows(self, page: dict, x0=CONTENT_X, y0=CONTENT_Y, width=CONTENT_W, height=CONTENT_H):
        placed = []
        rows = [dict(r) for r in page.get("rows", [])]
        for r in rows:
            if r.get("height") == "auto":
                r["height"] = self.auto_height(r["visuals"])
        fills = [r for r in rows if r.get("height") == "fill"]
        if len(fills) > 1:
            raise SpecError(f"page '{page['name']}': only one row can use \"height\": \"fill\"")
        if fills:
            fixed = sum(r["height"] for r in rows if r is not fills[0]) + GUTTER * (len(rows) - 1)
            fills[0]["height"] = (height - fixed) // 4 * 4
            if fills[0]["height"] < 120:
                raise SpecError(f"page '{page['name']}': the 'fill' row would be {fills[0]['height']} px high")
        used = sum(r["height"] for r in rows) + GUTTER * max(len(rows) - 1, 0)
        if used > height:
            raise SpecError(f"page '{page['name']}': rows need {used} px, the content area has {height}")
        y = y0
        for r in rows:
            h = r["height"]
            if h % 4:
                raise SpecError(f"page '{page['name']}': row height {h} is not a multiple of 4")
            vis = r["visuals"]
            widths = self.split(width, r.get("split") or [1] * len(vis))
            x = x0
            for v, w in zip(vis, widths):
                if v.get("type") in ("tableEx", "matrix") and h < 400 and not v.get("top") and not v.get("items"):
                    fit = max((h - 64) // 28, 1)
                    self.notes.append(f"{page['name']}: table '{v.get('title', '')}' has room for about {fit} rows. "
                                      f"Unless the list is shorter for sure, set \"top\": {fit} with \"sortBy\": "
                                      "\"<measure> desc\" and say it in the title, or give it its own page")
                if v.get("type") == "clusteredBarChart" and v.get("items"):
                    need = self.auto_height([v])
                    if h > need + 64:
                        self.notes.append(f"{page['name']}: bar chart '{v.get('title', '')}' shows {v['items']} bars in "
                                          f"{h} px; {need} px fit them. Make the row \"height\": \"auto\" or put "
                                          "a visual under it, so the card has no empty band")
                placed += self.component(v, (x, y, w, h))
                x += w + GUTTER
            y += h + GUTTER
        return placed

    def shell(self, page: dict, visible_pages: list[dict]):
        name = page["name"]
        kind = page.get("kind", "page")
        slicers = page.get("slicers", self.spec.get("slicers", [])) if kind != "tooltip" else []
        if len(slicers) > 2:
            raise SpecError(f"page '{name}': at most 2 slicers in the top bar")
        items = [
            ("painel", (220, 12, 1048, 696), self.shape("#FFFFFF", panel=True)),
            ("marca", (16, 20, 16, 16), self.shape(ACCENT, rounded=True)),
            ("app", (40, 16, 172, 24), self.textbox(self.run(self.app, 10, INK, semibold=True))),
            ("secao", (8, 52, 204, 24), self.textbox(self.run(self.spec.get("navLabel", "Páginas"), 9, INK3))),
            ("navegacao", (NAV_X, NAV_Y, 204, NAV_ITEM * len(visible_pages)),
             {"visualType": "pageNavigator", "drillFilterOtherVisuals": True}),
            ("linha", (220, 68, 1048, 1), self.shape(LINE)),
        ]
        for i, p in enumerate(visible_pages):
            if p.get("icon"):
                items.append((f"icone-{i}", (16, NAV_Y + 8 + NAV_ITEM * i, 16, 16),
                              self.image(p["icon"], f"Ícone da página {p['name']}")))
        crumb_x = 232
        runs = [self.run(f"{self.app}  /  ", 12, INK3)]
        if kind == "drillthrough":
            items.append(("voltar", (232, 28, 24, 24), self.image("arrow-left", "Voltar para a página anterior", back=True)))
            crumb_x = 264
            if page.get("parent"):
                runs.append(self.run(f"{page['parent']}  /  ", 12, INK3))
        runs.append(self.run(name, 12, INK, semibold=True))
        items.append(("caminho", (crumb_x, 28, 520, 24), self.textbox(*runs)))
        right = 1256
        bar = []                                   # placed right to left, added left to right (tab order)
        for i, f in enumerate(reversed(slicers)):
            x = right - 176
            bar.append((f"filtro-{i}", (x, 20, 176, 40), self.data_visual(
                "slicer", {"Values": {"projections": [self.proj(f)]}}, f"Filtro de {self.ref(f)[2]}",
                objects={"data": [{"properties": {"mode": lit("'Dropdown'")}}]})))
            right = x - GUTTER
        if self.spec.get("updated"):
            bar.append(("atualizado", (right - 200, 28, 200, 24), self.data_visual(
                "card", {"Values": {"projections": [self.proj(self.spec["updated"])]}},
                "Data e hora da última carga", chrome=False,
                objects={"labels": [{"properties": {"fontSize": lit("9D"), "color": color(INK3),
                                                    "fontFamily": lit("'Segoe UI'")}}]})))
        return items + bar[::-1]

    @staticmethod
    def too_wide_for_phone(visual: dict) -> bool:
        """Tables with more than 3 columns do not fit 304 px: the phone shows the summary, not the sheet."""
        if visual.get("visualType") not in ("tableEx", "pivotTable"):
            return False
        qs = (visual.get("query") or {}).get("queryState") or {}
        return sum(len(r.get("projections", [])) for k, r in qs.items() if k in ("Values", "Rows")) > 3

    def mobile(self, placed):
        """Stack the content visuals for the phone layout: slicers, KPIs, then the rest, full width."""
        out, y = {}, PHONE_MARGIN
        inner = PHONE_W - 2 * PHONE_MARGIN
        slicers = [p for p in placed if p[2].get("visualType") == "slicer"]
        kpis = [p for p in placed if p[2].get("visualType") == "card" and not p[0].endswith("-var")
                and p[0] != "atualizado"]
        others = [p for p in placed if p not in slicers and p not in kpis and p[0] != "atualizado"
                  and not p[0].endswith("-var") and p[2].get("visualType") not in ("shape", "textbox", "image",
                                                                                     "pageNavigator")
                  and not self.too_wide_for_phone(p[2])]
        for key, *_ in slicers:
            out[key] = (PHONE_MARGIN, y, inner, 40)
            y += 40 + PHONE_MARGIN
        keys = {p[0] for p in placed}
        for key, *_rest in kpis:       # one KPI per row: values and variation lines need the full width
            out[key] = (PHONE_MARGIN, y, inner, 88)
            if f"{key}-var" in keys:
                out[f"{key}-var"] = (PHONE_MARGIN + 12, y + 60, inner - 24, 20)
            y += 88 + PHONE_MARGIN
        for key, pos, _ in others:
            h = min(pos[3], 240)
            out[key] = (PHONE_MARGIN, y, inner, h)
            y += h + PHONE_MARGIN
        return out

    # ------------------------------------------------------------------ pages
    def render(self) -> dict[str, str]:
        """Every file the spec produces under the report folder: {relative path: JSON text}."""
        files: dict[str, str] = {}
        visible = [p for p in self.spec["pages"] if p.get("kind", "page") == "page"]
        dump = lambda obj: json.dumps(obj, indent=2, ensure_ascii=False) + "\n"  # noqa: E731
        for page in self.spec["pages"]:
            kind = page.get("kind", "page")
            pid = self.page_ids[page["name"]]
            self.current_page = page["name"]
            if kind == "tooltip":
                vis = page.get("visuals", [])
                if len(vis) != 1:
                    raise SpecError(f"tooltip page '{page['name']}' takes exactly one visual (320×240)")
                placed = self.component(vis[0], (8, 8, 304, 224))
                pdata = {"$schema": f"{SCHEMA}/page/1.1.0/schema.json", "name": pid,
                         "displayName": page["name"], "displayOption": "FitToPage", "height": 240, "width": 320,
                         "visibility": "HiddenInViewMode",
                         "pageBinding": {"name": hid("binding", pid), "type": "Tooltip"},
                         "objects": {"background": [{"properties": {"color": color("#FFFFFF"),
                                                                    "transparency": lit("0D")}}]}}
                mobile = {}
            else:
                placed = self.shell(page, visible) + self.rows(page)
                pdata = {"$schema": f"{SCHEMA}/page/1.1.0/schema.json", "name": pid,
                         "displayName": page["name"], "displayOption": "FitToPage",
                         "height": PAGE_H, "width": PAGE_W}
                if kind == "drillthrough":
                    f = page.get("drillField")
                    if not f:
                        raise SpecError(f"drill-through page '{page['name']}' needs 'drillField'")
                    fid = hid("filter", pid)
                    pdata["visibility"] = "HiddenInViewMode"
                    pdata["filterConfig"] = {"filters": [{"name": fid, "field": self.field(f),
                                                          "type": "Categorical", "howCreated": "Drillthrough"}]}
                    pdata["pageBinding"] = {"name": hid("binding", pid), "type": "Drillthrough",
                                            "parameters": [{"name": hid("param", pid), "boundFilter": fid,
                                                            "fieldExpr": self.field(f)}]}
                mobile = self.mobile(placed) if kind == "page" else {}
            keys = [k for k, *_ in placed]
            if len(keys) != len(set(keys)):
                raise SpecError(f"page '{page['name']}': two visuals share a key; set 'key' on one of them")
            base = f"definition/pages/{pid}"
            files[f"{base}/page.json"] = dump(pdata)
            for i, (key, pos, visual) in enumerate(placed):
                vid = self.ids.get((page["name"], key)) or hid("visual", page["name"], key)
                files[f"{base}/visuals/{vid}/visual.json"] = dump(self.container(vid, pos, i * 1000, visual))
                if key in mobile:
                    x, y, w, h = mobile[key]
                    files[f"{base}/visuals/{vid}/mobile.json"] = dump({
                        "$schema": f"{SCHEMA}/visualContainerMobileState/1.0.0/schema.json",
                        "position": {"x": x, "y": y, "z": i * 1000, "width": w, "height": h, "tabOrder": i * 1000}})
        order = [self.page_ids[p["name"]] for p in self.spec["pages"]]
        files["definition/pages/pages.json"] = dump({"$schema": f"{SCHEMA}/pagesMetadata/1.0.0/schema.json",
                                                     "pageOrder": order, "activePageName": order[0]})
        return files

    def build(self, report: Path, write: bool = True, force: bool = False) -> list[str]:
        """Write the pages. Files you changed by hand since the last build are kept (see merge_write)."""
        files = self.render()
        if write:
            self.merge = merge_write(report, files, "definition/pages/", force=force)
        return [self.page_ids[p["name"]] for p in self.spec["pages"]]

    def register_resources(self, report: Path, theme: Path | None):
        res = report / "StaticResources" / "RegisteredResources"
        res.mkdir(parents=True, exist_ok=True)
        rj_path = report / "definition" / "report.json"
        rj = json.loads(rj_path.read_text(encoding="utf-8")) if rj_path.exists() else {
            "$schema": f"{SCHEMA}/report/1.0.0/schema.json", "layoutOptimization": "None",
            "settings": {"useStylableVisualContainerHeader": True, "exportDataMode": "AllowSummarized",
                         "defaultDrillFilterOtherVisuals": True, "allowChangeFilterTypes": True,
                         "useEnhancedTooltips": True}}
        items = []
        if theme:
            merge_write(report, {f"StaticResources/RegisteredResources/{theme.name}":
                                 theme.read_text(encoding="utf-8")}, f"StaticResources/RegisteredResources/{theme.name}")
            rj["themeCollection"] = {"customTheme": {"name": theme.name, "reportVersionAtImport": "5.59",
                                                     "type": "RegisteredResources"}}
            items.append({"name": theme.name, "path": theme.name, "type": "CustomTheme"})
        else:
            items += [i for p in rj.get("resourcePackages", []) if p["name"] == "RegisteredResources"
                      for i in p["items"] if i["type"] == "CustomTheme"]
        for icon in sorted(self.icons_used):
            src = ICONS / f"{icon}.png"
            if not src.exists():
                raise SpecError(f"icon '{icon}' not found in templates/icons")
            if not (res / src.name).exists() or (res / src.name).read_bytes() != src.read_bytes():
                shutil.copyfile(src, res / src.name)
            items.append({"name": src.name, "path": src.name, "type": "Image"})
        rj.setdefault("themeCollection", {})
        rj["resourcePackages"] = [p for p in rj.get("resourcePackages", []) if p["name"] != "RegisteredResources"]
        rj["resourcePackages"].append({"name": "RegisteredResources", "type": "RegisteredResources", "items": items})
        rj_path.parent.mkdir(parents=True, exist_ok=True)
        current = json.loads(rj_path.read_text(encoding="utf-8-sig")) if rj_path.exists() else None
        if current != rj:                    # an unchanged file keeps its bytes (line endings, formatting)
            write_lf(rj_path, json.dumps(rj, indent=2, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------- extract (restyle)
DECORATION = {"shape", "textbox", "image", "pageNavigator", "actionButton", "basicShape", "bookmarkNavigator"}
CARDS = {"card", "cardVisual", "multiRowCard"}
AS_CHART = {"lineChart": "lineChart", "areaChart": "lineChart", "stackedAreaChart": "lineChart",
            "clusteredBarChart": "clusteredBarChart", "barChart": "clusteredBarChart",
            "hundredPercentStackedBarChart": "clusteredBarChart",
            "clusteredColumnChart": "clusteredColumnChart", "columnChart": "clusteredColumnChart",
            "hundredPercentStackedColumnChart": "clusteredColumnChart", "waterfallChart": "waterfallChart",
            "pieChart": "clusteredBarChart", "donutChart": "clusteredBarChart", "funnel": "clusteredBarChart",
            "treemap": "clusteredBarChart"}
DEFAULT_ICONS = ["layout-dashboard", "chart-bar", "list-details", "file-description", "user"]


def _lit(o):
    try:
        v = o["expr"]["Literal"]["Value"]
    except (KeyError, TypeError):
        return None
    return v[1:-1].replace("''", "'") if isinstance(v, str) and v.startswith("'") else v


def _prop(objs: dict, obj: str, name: str):
    try:
        return objs[obj][0]["properties"].get(name)
    except (KeyError, IndexError, TypeError):
        return None


class Extractor:
    def __init__(self, report: Path):
        self.report = report
        self.notes: list[str] = []
        self.measure_tables: dict[str, str] = {}

    def name(self, f: dict, where: str) -> str:
        """Spec name of a PBIR field expression: bare measure name or Table[Column]."""
        kind = next(iter(f), "")
        body = f.get(kind, {})
        if kind == "Measure":
            ent = body["Expression"]["SourceRef"].get("Entity", "")
            self.measure_tables[body["Property"]] = ent
            return body["Property"]
        if kind == "Column":
            return f"{body['Expression']['SourceRef'].get('Entity', '')}[{body['Property']}]"
        if kind == "Aggregation":
            col = self.name(body.get("Expression", {}), where)
            self.notes.append(f"{where}: implicit aggregation of {col}; create an explicit measure and use it")
            return col
        if kind == "HierarchyLevel":
            h = body["Expression"]["Hierarchy"]
            ent = h["Expression"]["SourceRef"].get("Entity", "")
            return f"{ent}[{body['Level']}]"
        raise SpecError(f"{where}: unsupported field {kind}")

    def roles(self, vis: dict, where: str) -> dict:
        qs = (vis.get("query") or {}).get("queryState") or {}
        return {r: [self.name(p["field"], where) for p in v.get("projections", [])] for r, v in qs.items()}

    def title(self, vis: dict) -> tuple[str | None, str | None]:
        vco = vis.get("visualContainerObjects") or {}
        text = _prop(vco, "title", "text")
        if isinstance(text, dict) and "Measure" in (text.get("expr") or {}):
            return None, self.name(text["expr"], "title")
        return _lit(text), None

    @staticmethod
    def chromeless(vis: dict) -> bool:
        vco = vis.get("visualContainerObjects") or {}
        return str(_lit(_prop(vco, "title", "show"))).lower() == "false" and \
            str(_lit(_prop(vco, "background", "show"))).lower() == "false"

    def sort(self, vis: dict):
        try:
            s = vis["query"]["sortDefinition"]["sort"][0]
        except (KeyError, IndexError, TypeError):
            return None, None
        return self.name(s["field"], "sort"), s.get("direction", "Ascending")

    def visual(self, vis: dict, where: str, page_names: dict) -> dict | None:
        t = vis.get("visualType", "")
        r = self.roles(vis, where)
        title, title_measure = self.title(vis)
        alt = _lit(_prop(vis.get("visualContainerObjects") or {}, "general", "altText"))
        if not alt:
            first = (r.get("Values") or r.get("Indicator") or r.get("Y") or [None])[0]
            alt = title or (first if t in CARDS or t == "kpi" else None) or t
            self.notes.append(f"{where}: no alt text; used '{alt}', write a real one")
        out: dict = {}
        if t in CARDS:
            m = (r.get("Values") or r.get("Data") or r.get("Fields") or [None])[0]
            if not m:
                return None
            out = {"type": "kpi", "measure": m, "label": title or m}
        elif t == "kpi":
            out = {"type": "kpiTrend", "measure": r["Indicator"][0], "label": title or r["Indicator"][0]}
            if r.get("TrendLine"):
                out["trend"] = r["TrendLine"][0]
            if r.get("Goal"):
                out["goal"] = r["Goal"][0]
        elif t in AS_CHART:
            cat = (r.get("Category") or r.get("Series") or [None])[0]
            vals = r.get("Y") or r.get("Values") or []
            if not cat or not vals:
                self.notes.append(f"{where}: {t} without a category or values; skipped")
                return None
            out = {"type": AS_CHART[t], "category": cat, "values": vals}
            if t in ("pieChart", "donutChart", "funnel", "treemap"):
                out["sort"] = "desc"
                self.notes.append(f"{where}: {t} became a bar chart sorted by value")
            else:
                by, direction = self.sort(vis)
                if by == cat:
                    out["sort"] = "category"
                elif by:
                    out["sort"] = "desc" if direction == "Descending" else "asc"
                elif AS_CHART[t] == "lineChart":
                    out["sort"] = "category"
            if t == "waterfallChart":
                sc = (vis.get("objects") or {}).get("sentimentColors")
                if sc:
                    props = sc[0].get("properties", {})
                    out["sentiment"] = {k[:-4]: _lit(v["solid"]["color"]) for k, v in props.items()
                                        if k.endswith("Fill") and _lit(v["solid"]["color"])}
            objs = vis.get("objects") or {}
            for item in objs.get("lineStyles", []):            # dashed series = the target line
                if _lit((item.get("properties") or {}).get("lineStyle")) == "dashed":
                    name = ((item.get("selector") or {}).get("metadata") or "").split(".", 1)[-1]
                    if name in out["values"]:
                        out["values"] = [x for x in out["values"] if x != name]
                        out["target"] = name
            for item in objs.get("dataPoint", []):             # bars coloured against a target
                c = ((item.get("properties") or {}).get("fill") or {}).get("solid", {}).get("color", {})
                cases = (((c.get("expr") or {}).get("Conditional") or {}).get("Cases") or [{}])
                cmp_ = ((cases[0].get("Condition") or {}).get("Comparison") or {})
                if "Measure" in (cmp_.get("Right") or {}):
                    out["target"] = self.name(cmp_["Right"], where)
                    if cmp_.get("ComparisonKind") == 1:
                        out["higherIsBetter"] = False
                elif "Measure" in (c.get("expr") or {}):
                    out["colorMeasure"] = self.name(c["expr"], where)
        elif t in ("lineClusteredColumnComboChart", "lineStackedColumnComboChart"):
            out = {"type": "combo", "category": r["Category"][0], "values": r.get("Y", []),
                   "lineValues": r.get("Y2", [])}
        elif t == "scatterChart":
            out = {"type": "scatter", "details": (r.get("Category") or r.get("Details") or [""])[0],
                   "x": r["X"][0], "y": r["Y"][0]}
            if r.get("Size"):
                out["size"] = r["Size"][0]
        elif t in ("tableEx", "pivotTable"):
            if t == "tableEx":
                out = {"type": "tableEx", "columns": r.get("Values", [])}
            else:
                out = {"type": "matrix", "rows": r.get("Rows", []), "values": r.get("Values", [])}
                if r.get("Columns"):
                    out["columns"] = r["Columns"]
            by, direction = self.sort(vis)
            if by:
                out["sortBy"] = f"{by} {'desc' if direction == 'Descending' else 'asc'}"
            for flt in (vis.get("_filterConfig") or {}).get("filters", []):
                if flt.get("type") == "TopN":
                    try:
                        q = flt["filter"]["From"][0]["Expression"]["Subquery"]["Query"]
                        n, order = q["Top"], q["OrderBy"][0]
                    except (KeyError, IndexError, TypeError):
                        continue
                    out["top"] = n
                    if not by:
                        out["sortBy"] = f"{order['Expression']['Measure']['Property']} " \
                                        f"{'desc' if order.get('Direction') == 2 else 'asc'}"
            for item in (vis.get("objects") or {}).get("values", []):
                fc = (item.get("properties") or {}).get("fontColor") or {}
                expr = (fc.get("solid") or {}).get("color", {}).get("expr", {})
                sel = (item.get("selector") or {}).get("metadata", "")
                if "Measure" in expr and sel:
                    out["highlight"] = {"column": sel.split(".", 1)[1], "colorMeasure": self.name(expr, where)}
        elif t == "slicer":
            return {"type": "slicer", "field": (r.get("Values") or [""])[0]}
        else:
            self.notes.append(f"{where}: {t or 'unknown'} is not in the layout engine; rebuild it by hand")
            return None
        if out["type"] not in ("kpi", "kpiTrend"):
            if title_measure:
                out["titleMeasure"] = title_measure
            else:
                out["title"] = title or alt
        if out["type"] not in ("kpi", "kpiTrend") or alt != out.get("label"):
            out["alt"] = alt
        tip = _prop(vis.get("visualContainerObjects") or {}, "visualTooltip", "section")
        if _lit(tip) in page_names:
            out["tooltipPage"] = page_names[_lit(tip)]
        return out

    def page(self, pdir: Path, pdata: dict, page_names: dict, icon: str, shared_slicers: list) -> dict:
        name = pdata.get("displayName", pdir.name)
        binding = (pdata.get("pageBinding") or {}).get("type")
        page: dict = {"name": name}
        if pdir.name != hid("page", name):
            page["id"] = pdir.name            # keep the folder: a rebuild must land on the same files
        items = []
        for f in sorted((pdir / "visuals").glob("*/visual.json")):
            c = json.loads(f.read_text(encoding="utf-8-sig"))
            vis = c.get("visual")
            if vis and vis.get("visualType") == "textbox" and c.get("position", {}).get("y", 99) < CONTENT_Y - 8:
                runs = [r.get("value", "") for para in (_prop(vis.get("objects") or {}, "general", "paragraphs") or [])
                        for r in para.get("textRuns", [])]
                pos = c["position"]
                if pos.get("x", 0) < 220 and pos.get("y", 0) < 48 and pos.get("width", 999) <= 212 and runs:        # app name in the sidebar
                    self.app = self.app or "".join(runs).strip()
                elif len(runs) == 3 and binding == "Drillthrough":                # App / Parent / Page
                    page["parent"] = runs[1].strip().rstrip("/").strip()
            if not vis or vis.get("visualType") in DECORATION:
                continue
            if c.get("filterConfig"):
                vis = {**vis, "_filterConfig": c["filterConfig"]}
            items.append((c.get("position", {}), vis, f"{name}/{f.parent.name}"))
        top = [(p, v, w) for p, v, w in items if p.get("y", 0) + p.get("height", 0) <= CONTENT_Y - 8]
        body = [i for i in items if i not in top]
        slicers = []
        for p, v, w in top:                               # top bar of a report built by this engine
            if v["visualType"] == "slicer":
                slicers.append(self.roles(v, w)["Values"][0])
            elif v["visualType"] == "card" and self.chromeless(v):
                self.updated = self.roles(v, w)["Values"][0]
        cards = [(p, v, w) for p, v, w in body if v["visualType"] in CARDS and not self.chromeless(v)]
        variations = {}
        for p, v, w in body:                              # variation lines inside KPI cards
            if v["visualType"] == "card" and self.chromeless(v):
                host = next((c for c in cards if c[0]["x"] <= p["x"] <= c[0]["x"] + c[0]["width"]
                             and c[0]["y"] <= p["y"] <= c[0]["y"] + c[0]["height"]), None)
                if host:
                    m = self.roles(v, w)["Values"][0]
                    color_ = _prop(v.get("objects") or {}, "labels", "color") or {}
                    expr = (color_.get("solid") or {}).get("color", {}).get("expr", {})
                    variations[host[2]] = (m, self.name(expr, w) if "Measure" in expr else None, w.rsplit("/", 1)[-1])
        body = [(p, v, w) for p, v, w in body if not (v["visualType"] == "card" and self.chromeless(v))]
        loose_slicers = [(p, v, w) for p, v, w in body if v["visualType"] == "slicer"]
        body = [i for i in body if i not in loose_slicers]
        for p, v, w in loose_slicers:
            f = self.roles(v, w).get("Values", [None])[0]
            if f and f not in slicers:
                slicers.append(f)
        if binding == "Tooltip":
            page["kind"] = "tooltip"
            specs = [s for s in (self.visual(v, w, page_names) for _, v, w in body) if s]
            if len(specs) > 1:
                self.notes.append(f"{name}: tooltip page keeps only its first visual (of {len(specs)})")
            page["visuals"] = specs[:1]
            return page
        if binding == "Drillthrough":
            page["kind"] = "drillthrough"
            try:
                page["drillField"] = self.name(pdata["pageBinding"]["parameters"][0]["fieldExpr"], name)
            except (KeyError, IndexError):
                f = (pdata.get("filterConfig") or {}).get("filters", [{}])[0].get("field")
                if f:
                    page["drillField"] = self.name(f, name)
        else:
            page["icon"] = icon
        if slicers[2:]:
            self.notes.append(f"{name}: {len(slicers)} slicers; kept {slicers[:2]}, move the rest to the filter pane")
        if slicers[:2] != shared_slicers:
            page["slicers"] = slicers[:2]
        page["rows"] = self.rows(body, page_names, variations, name)
        return page

    def rows(self, body, page_names, variations, page_name) -> list[dict]:
        body = sorted(body, key=lambda i: (i[0].get("y", 0), i[0].get("x", 0)))
        groups: list[list] = []
        for item in body:
            p = item[0]
            if groups:
                g = groups[-1]
                top = min(q[0].get("y", 0) for q in g)
                bottom = max(q[0].get("y", 0) + q[0].get("height", 0) for q in g)
                mid = p.get("y", 0) + p.get("height", 0) / 2
                if top <= mid < bottom:
                    g.append(item)
                    continue
            groups.append([item])
        rows = []
        for g in groups:
            g.sort(key=lambda i: i[0].get("x", 0))
            specs, widths = [], []
            for p, v, w in g:
                s = self.visual(v, w, page_names)
                if not s:
                    continue
                folder = w.rsplit("/", 1)[-1]
                if s["type"] == "kpi" and w in variations:
                    s["variation"], color_, var_folder = variations[w]
                    if color_:
                        s["variationColor"] = color_
                    s["_var"] = var_folder
                s["_folder"] = folder
                specs.append(s)
                widths.append(p.get("width", 1))
            if not specs:
                continue
            row = {"_h": max(p.get("height", 0) for p, _, _ in g), "visuals": specs}
            if len(set(widths)) > 1:
                fr = [Fraction(x / min(widths)).limit_denominator(4) for x in widths]
                lcm = 1
                for f in fr:
                    lcm = lcm * f.denominator // math.gcd(lcm, f.denominator)
                row["split"] = [int(f * lcm) for f in fr]
                if len(set(row["split"])) == 1:
                    del row["split"]
            seen: dict[str, int] = {}
            for sp in specs:
                first = (sp.get("measure") or sp.get("category") or sp.get("details")
                         or (sp.get("columns") or sp.get("rows") or [""])[0])
                k = f"{sp['type']}-{first}"
                seen[k] = seen.get(k, 0) + 1
                if seen[k] > 1:
                    sp["key"] = f"{k}-{seen[k]}"
            for sp in specs:                       # pin to the existing folder when the name would differ
                key = sp.get("key") or f"{sp['type']}-" + (sp.get("measure") or sp.get("category") or sp.get("details")
                                                           or (sp.get("columns") or sp.get("rows") or [""])[0])
                folder, var_folder = sp.pop("_folder"), sp.pop("_var", None)
                if folder != hid("visual", page_name, key):
                    sp["id"] = folder
                if var_folder and var_folder != hid("visual", page_name, key + "-var"):
                    sp["varId"] = var_folder
            rows.append(row)
        kpi_rows = [r for r in rows if all(v["type"] == "kpi" for v in r["visuals"])]
        free = CONTENT_H - GUTTER * max(len(rows) - 1, 0) - 88 * len(kpi_rows)
        rest = [r for r in rows if r not in kpi_rows]
        total = sum(r["_h"] for r in rest) or 1
        for r in rows:
            h = r.pop("_h")
            r_h = 88 if r in kpi_rows else int(free * h / total) // 4 * 4
            if r not in kpi_rows and r_h < 160:
                self.notes.append(f"{page_name}: a row is only {r_h} px high; split the page in two")
            r["height"] = max(r_h, 40)
        return [{"height": r["height"], **({"split": r["split"]} if "split" in r else {}), "visuals": r["visuals"]}
                for r in rows]

    def run(self) -> dict:
        pages_dir = self.report / "definition" / "pages"
        meta = json.loads((pages_dir / "pages.json").read_text(encoding="utf-8-sig"))
        order = meta.get("pageOrder") or sorted(p.name for p in pages_dir.iterdir() if p.is_dir())
        datas = {pid: json.loads((pages_dir / pid / "page.json").read_text(encoding="utf-8-sig")) for pid in order}
        page_names = {pid: d.get("displayName", pid) for pid, d in datas.items()}
        self.updated = None
        self.app = None
        first_slicers: list = []
        pages, icon_i = [], 0
        for pid in order:
            visible = not (datas[pid].get("pageBinding") or {}).get("type")
            icon = DEFAULT_ICONS[icon_i % len(DEFAULT_ICONS)]
            page = self.page(pages_dir / pid, datas[pid], page_names, icon, first_slicers if pages else [])
            if not pages and "slicers" in page:
                first_slicers = page.pop("slicers")
            icon_i += visible
            pages.append(page)
        for p in pages:
            if "slicers" in p and p["slicers"] == first_slicers:
                del p["slicers"]
        counts: dict[str, int] = {}
        for ent in self.measure_tables.values():
            counts[ent] = counts.get(ent, 0) + 1
        home = max(counts, key=counts.get) if counts else "_Medidas"
        stem = self.report.name[:-len(".Report")] if self.report.name.endswith(".Report") else self.report.name
        spec = {"app": self.app or re.sub(r"(?<=[a-z])(?=[A-Z])", " ", stem), "measures": home}
        others = {m: e for m, e in self.measure_tables.items() if e != home}
        if others:
            spec["measureHome"] = dict(sorted(others.items()))
        if self.updated:
            spec["updated"] = self.updated
        else:
            self.notes.append("no 'updated at' measure; add one (references/dax.md) and set \"updated\"")
        spec["slicers"] = first_slicers
        spec["pages"] = pages
        return spec


def extract(report: Path) -> tuple[dict, list[str]]:
    ex = Extractor(report)
    spec = ex.run()
    return spec, ex.notes


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pbir_layout.py", description="Build PBIR pages from a layout spec.")
    ap.add_argument("spec", type=Path, nargs="?")
    ap.add_argument("report", type=Path, nargs="?", help="the <Name>.Report folder")
    ap.add_argument("--extract", type=Path, metavar="REPORT",
                    help="write the spec of an existing <Name>.Report (to restyle it) instead of building")
    ap.add_argument("--out", type=Path, help="with --extract: file for the spec (default: stdout)")
    ap.add_argument("--theme", type=Path, help="theme JSON to register as the custom theme")
    ap.add_argument("--check", action="store_true", help="validate the spec without writing")
    ap.add_argument("--force", action="store_true",
                    help="rewrite every page from the spec, discarding edits made by hand since the last build")
    args = ap.parse_args(argv)
    for stream in (sys.stdin, sys.stdout, sys.stderr):   # Windows consoles default to a legacy code page
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except ValueError:
                pass
    if args.extract:
        try:
            spec, notes = extract(args.extract)
        except (SpecError, KeyError, OSError, json.JSONDecodeError) as e:
            print(f"pbir_layout.py: error: {e}", file=sys.stderr)
            return 2
        text = json.dumps(spec, indent=2, ensure_ascii=False) + "\n"
        if args.out:
            args.out.write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
        for n in notes:
            print(f"- {n}", file=sys.stderr)
        print(f"[ok] {len(spec['pages'])} page(s) extracted, {len(notes)} note(s)", file=sys.stderr)
        return 0
    if not args.spec or not args.report:
        ap.error("spec and report are required (or use --extract REPORT)")
    try:
        spec = json.loads(args.spec.read_text(encoding="utf-8"))
        b = Builder(spec)
        if args.theme and args.theme.exists() and "accent" not in spec:
            b.accent = (json.loads(args.theme.read_text(encoding="utf-8-sig")).get("dataColors") or [ACCENT])[0]
        had_pages = (args.report / "definition" / "pages").exists()
        pages = b.build(args.report, write=not args.check, force=args.force)
        if not args.check:
            b.register_resources(args.report, args.theme)
    except (SpecError, KeyError, json.JSONDecodeError) as e:
        print(f"pbir_layout.py: error: {e}", file=sys.stderr)
        return 2
    if args.check:
        for note in b.notes:
            print(f"- {note}")
        print(f"[ok] {len(pages)} page(s) checked")
        return 0
    m = b.merge
    for line in m.lines(args.report):
        print(f"- {line}")
    for note in b.notes:
        print(f"- {note}")
    if m.fresh and had_pages and not args.force:
        print("- no layout lock yet: pages were rewritten from the spec. From now on, edits made by hand "
              "(in Desktop or in the files) are kept on every rebuild")
    print(f"[ok] {len(pages)} page(s): {len(m.written)} file(s) written, {len(m.removed)} removed, "
          f"{len(m.kept) + len(m.merged)} with your edits kept · lock: {lock_path(args.report)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
