#!/usr/bin/env python3
"""pbir_layout.py — build PBIR report pages from a short layout spec (part of the powerbi-architect skill).

Python 3.9+ standard library only. Offline. Writes only inside the <Name>.Report folder it is given.

    python pbir_layout.py <spec.json> <Name>.Report [--theme theme.json] [--check]

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
(options: "columns", "highlight": {"column": <measure>, "colorMeasure": <measure>}), slicer.
Every data visual needs "alt" (alt text) and "title" or "titleMeasure" (kpi uses "label").
Row heights plus 16 px gutters must fit the 616 px content area. --check validates without writing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
INK, INK3, LINE, ACCENT = "#333333", "#757575", "#EBEBEB", "#3E63DD"
PAGE_W, PAGE_H = 1280, 720
CONTENT_X, CONTENT_Y, CONTENT_W, CONTENT_H, GUTTER = 232, 80, 1024, 616, 16
NAV_X, NAV_Y, NAV_ITEM = 8, 76, 32
PHONE_W, PHONE_MARGIN = 320, 8
ICONS = Path(__file__).resolve().parent.parent / "templates" / "icons"
CHARTS = {"lineChart", "clusteredBarChart", "clusteredColumnChart", "waterfallChart"}


class SpecError(ValueError):
    pass


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
        self.measures = spec.get("measures", "_Medidas")
        self.app = spec.get("app", "Relatório")
        self.page_ids = {p["name"]: hid("page", p["name"]) for p in spec["pages"]}
        self.icons_used: set[str] = set()

    # ------------------------------------------------------------------ fields
    def ref(self, name: str):
        m = re.match(r"^(.+?)\[(.+)\]$", name)
        if m:
            return "Column", m.group(1).strip("'"), m.group(2)
        return "Measure", self.measures, name

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
        return {"$schema": f"{SCHEMA}/visualContainer/1.1.0/schema.json", "name": vid,
                "position": {"x": x, "y": y, "z": z, "width": w, "height": h, "tabOrder": z},
                "visual": visual}

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

    # ------------------------------------------------------------------ components
    def component(self, spec: dict, pos):
        """Return [(key, pos, visual), ...] for one spec visual placed at pos."""
        t = spec.get("type")
        alt = spec.get("alt") or spec.get("label") or spec.get("title")
        if not alt:
            raise SpecError(f"visual {spec} needs 'alt' text")
        x, y, w, h = pos
        key = spec.get("key") or f"{t}-{spec.get('measure') or spec.get('category') or spec.get('columns', [''])[0]}"
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
            roles = {cat_role: {"projections": [self.proj(spec["category"])]},
                     "Y": {"projections": [self.proj(m) for m in spec["values"]]}}
            sort = None
            if spec.get("sort") == "desc":
                sort = (spec["values"][0], "Descending")
            elif spec.get("sort") in ("asc", "category"):
                sort = (spec["category"], "Ascending")
            objects = None
            if t == "waterfallChart" and spec.get("sentiment"):
                s = spec["sentiment"]
                objects = {"sentimentColors": [{"properties": {k + "Fill": color(v) for k, v in s.items()}}]}
            return [(key, pos, self.data_visual(t, roles, alt, title=spec.get("title"),
                                                title_measure=spec.get("titleMeasure"), sort=sort,
                                                objects=objects, tooltip_page=spec.get("tooltipPage")))]
        if t == "tableEx":
            roles = {"Values": {"projections": [self.proj(c) for c in spec["columns"]]}}
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
            return [(key, pos, self.data_visual("tableEx", roles, alt, title=spec.get("title"),
                                                title_measure=spec.get("titleMeasure"), sort=sort, objects=objects))]
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
        rows = page.get("rows", [])
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
        for i, f in enumerate(reversed(slicers)):
            x = right - 176
            items.append((f"filtro-{i}", (x, 20, 176, 40), self.data_visual(
                "slicer", {"Values": {"projections": [self.proj(f)]}}, f"Filtro de {self.ref(f)[2]}",
                objects={"data": [{"properties": {"mode": lit("'Dropdown'")}}]})))
            right = x - GUTTER
        if self.spec.get("updated"):
            items.append(("atualizado", (right - 200, 28, 200, 24), self.data_visual(
                "card", {"Values": {"projections": [self.proj(self.spec["updated"])]}},
                "Data e hora da última carga", chrome=False,
                objects={"labels": [{"properties": {"fontSize": lit("9D"), "color": color(INK3),
                                                    "fontFamily": lit("'Segoe UI'")}}]})))
        return items

    def mobile(self, placed):
        """Stack the content visuals for the phone layout: slicers, KPIs, then the rest, full width."""
        out, y = {}, PHONE_MARGIN
        inner = PHONE_W - 2 * PHONE_MARGIN
        slicers = [p for p in placed if p[2].get("visualType") == "slicer"]
        kpis = [p for p in placed if p[2].get("visualType") == "card" and not p[0].endswith("-var")
                and p[0] != "atualizado"]
        others = [p for p in placed if p not in slicers and p not in kpis and p[0] != "atualizado"
                  and not p[0].endswith("-var") and p[2].get("visualType") not in ("shape", "textbox", "image",
                                                                                     "pageNavigator")]
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
    def build(self, report: Path, write: bool = True) -> list[str]:
        pages_dir = report / "definition" / "pages"
        visible = [p for p in self.spec["pages"] if p.get("kind", "page") == "page"]
        written = []
        if write and pages_dir.exists():
            shutil.rmtree(pages_dir)
        for page in self.spec["pages"]:
            kind = page.get("kind", "page")
            pid = self.page_ids[page["name"]]
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
            if write:
                (pages_dir / pid).mkdir(parents=True, exist_ok=True)
                (pages_dir / pid / "page.json").write_text(json.dumps(pdata, indent=2, ensure_ascii=False) + "\n",
                                                           encoding="utf-8", newline="\n")
                for i, (key, pos, visual) in enumerate(placed):
                    vid = hid("visual", page["name"], key)
                    vdir = pages_dir / pid / "visuals" / vid
                    vdir.mkdir(parents=True, exist_ok=True)
                    (vdir / "visual.json").write_text(
                        json.dumps(self.container(vid, pos, i * 1000, visual), indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8", newline="\n")
                    if key in mobile:
                        x, y, w, h = mobile[key]
                        (vdir / "mobile.json").write_text(json.dumps({
                            "$schema": f"{SCHEMA}/visualContainerMobileState/1.0.0/schema.json",
                            "position": {"x": x, "y": y, "z": i * 1000, "width": w, "height": h, "tabOrder": i * 1000}},
                            indent=2) + "\n", encoding="utf-8", newline="\n")
            written.append(pid)
        if write:
            order = [self.page_ids[p["name"]] for p in self.spec["pages"]]
            (pages_dir / "pages.json").write_text(json.dumps({
                "$schema": f"{SCHEMA}/pagesMetadata/1.0.0/schema.json", "pageOrder": order,
                "activePageName": order[0]}, indent=2) + "\n", encoding="utf-8", newline="\n")
        return written

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
            shutil.copyfile(theme, res / theme.name)
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
            shutil.copyfile(src, res / src.name)
            items.append({"name": src.name, "path": src.name, "type": "Image"})
        rj.setdefault("themeCollection", {})
        rj["resourcePackages"] = [p for p in rj.get("resourcePackages", []) if p["name"] != "RegisteredResources"]
        rj["resourcePackages"].append({"name": "RegisteredResources", "type": "RegisteredResources", "items": items})
        rj_path.parent.mkdir(parents=True, exist_ok=True)
        rj_path.write_text(json.dumps(rj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pbir_layout.py", description="Build PBIR pages from a layout spec.")
    ap.add_argument("spec", type=Path)
    ap.add_argument("report", type=Path, help="the <Name>.Report folder")
    ap.add_argument("--theme", type=Path, help="theme JSON to register as the custom theme")
    ap.add_argument("--check", action="store_true", help="validate the spec without writing")
    args = ap.parse_args(argv)
    try:
        spec = json.loads(args.spec.read_text(encoding="utf-8"))
        b = Builder(spec)
        pages = b.build(args.report, write=not args.check)
        if not args.check:
            b.register_resources(args.report, args.theme)
    except (SpecError, KeyError, json.JSONDecodeError) as e:
        print(f"pbir_layout.py: error: {e}", file=sys.stderr)
        return 2
    print(f"[ok] {len(pages)} page(s) {'checked' if args.check else 'written'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
