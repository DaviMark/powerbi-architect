#!/usr/bin/env python3
"""preview_pbir.py — see a PBIR report without Power BI Desktop (part of the powerbi-architect skill).

Python 3.9+ standard library only. Offline. Reads the <Name>.Report folder; writes one HTML file
(and one PNG per page with --png, using Edge, Chrome or Chromium in headless mode, or Playwright).

    python preview_pbir.py <Name>.Report [--out preview.html] [--sample sample.json] [--mobile]
                           [--png DIR]

Draws every visual at its real position and size with the report's custom theme (page colour,
backgrounds, borders, radius, fonts, type sizes), text boxes, the page navigator, icons and images,
and the data visuals: titles, KPI values and variation lines, KPIs with a trend, bars, columns,
waterfalls, lines, column-and-line combos, scatter plots, tables, matrices and slicers. Without --sample, values are neutral placeholders; with --sample, they come from a small
JSON file so labels, number lengths and legends look real:

    {"measures": {"Valor Vencido": "R$ 4,2 mi", "Texto Var % Vencido": "▲ 2,3 p.p. acima da meta"},
     "colors":   {"Cor Var % Vencido": "#CE2C31"},
     "fields":   {"dm_regional[Regional]": ["Sudeste", "Sul", "Nordeste", "Centro-Oeste", "Norte"]},
     "series":   {"dm_regional[Regional]": [4.2, 3.1, 2.4, 1.2, 0.8]}}   # by category field (or measure)

--mobile renders the phone layout (mobile.json) instead of the desktop pages.
Use it as the last step of every report change: render, look at each page, fix, render again.
"""
from __future__ import annotations

import argparse
import base64
import html
import json
import sys
from pathlib import Path

PT = 4 / 3  # Power BI font sizes are points; the canvas is in pixels.
FONT = "'Segoe UI', 'Selawik', 'Inter', 'Helvetica Neue', Arial, sans-serif"


def lit(o, default=None):
    try:
        v = o["expr"]["Literal"]["Value"]
    except (KeyError, TypeError):
        return default
    return v.strip("'") if isinstance(v, str) else v


def num(v, default=0.0):
    try:
        return float(str(v).rstrip("DLpt"))
    except (TypeError, ValueError):
        return default


def prop(objs: dict, obj: str, name: str, default=None):
    try:
        return (objs.get(obj) or [{}])[0].get("properties", {}).get(name, default)
    except (AttributeError, IndexError):
        return default


def measure_name(o):
    try:
        return o["expr"]["Measure"]["Property"]
    except (KeyError, TypeError):
        return None


class Preview:
    def __init__(self, report: Path, sample: dict | None):
        self.report = report
        self.sample = sample or {}
        self.theme = self.load_theme()
        self.ink = self.theme.get("foreground", "#252423")
        self.ink2 = self.theme.get("foregroundNeutralSecondary", "#605E5C")
        self.accent = (self.theme.get("dataColors") or ["#3E63DD"])[0]

    # ------------------------------------------------------------------ theme and data
    def load_theme(self) -> dict:
        rj = json.loads((self.report / "definition" / "report.json").read_text(encoding="utf-8-sig"))
        custom = (rj.get("themeCollection") or {}).get("customTheme")
        if custom:
            f = self.report / "StaticResources" / "RegisteredResources" / custom["name"]
            if f.exists():
                return json.loads(f.read_text(encoding="utf-8-sig"))
        return {}

    def style(self, vtype: str, obj: str, key: str, default=None):
        vs = self.theme.get("visualStyles", {})
        for t in (vtype, "*"):
            for item in ((vs.get(t) or {}).get("*") or {}).get(obj, []):
                if key in item and item.get("$id", "default") == "default":
                    v = item[key]
                    return v.get("solid", {}).get("color", default) if isinstance(v, dict) else v
        return default

    def color(self, o, default=None):
        """Literal colour, or the sample colour of a colour measure."""
        if not isinstance(o, dict):
            return default
        c = (o.get("solid") or {}).get("color")
        if isinstance(c, dict):
            m = measure_name(c)
            if m:
                return self.sample.get("colors", {}).get(m, default)
            return lit(c, default)
        return default

    def value(self, measure: str | None, placeholder: str) -> str:
        if measure and measure in self.sample.get("measures", {}):
            return html.escape(self.sample["measures"][measure])
        return placeholder

    def labels(self, field: str | None, n: int) -> list[str]:
        vals = self.sample.get("fields", {}).get(field or "", [])
        return vals[:n] if vals else []

    def series(self, measure: str | None, n: int, fallback: list[float]) -> list[float]:
        vals = self.sample.get("series", {}).get(measure or "", [])
        return (vals or fallback)[:n]

    def image_uri(self, objs: dict) -> str | None:
        url = prop(objs, "general", "imageUrl")
        try:
            item = url["expr"]["ResourcePackageItem"]["ItemName"]
        except (KeyError, TypeError):
            return None
        f = self.report / "StaticResources" / "RegisteredResources" / item
        if not f.exists():
            return None
        mime = "image/svg+xml" if f.suffix == ".svg" else f"image/{f.suffix.lstrip('.')}"
        return f"data:{mime};base64,{base64.b64encode(f.read_bytes()).decode()}"

    # ------------------------------------------------------------------ visuals
    @staticmethod
    def field_of(projection: dict) -> str:
        f = projection.get("field", {})
        kind = next(iter(f), "")
        ent = f.get(kind, {}).get("Expression", {}).get("SourceRef", {}).get("Entity", "")
        prop_ = f.get(kind, {}).get("Property", "")
        return prop_ if kind == "Measure" else f"{ent}[{prop_}]"

    def roles(self, vis: dict) -> dict:
        qs = (vis.get("query") or {}).get("queryState") or {}
        return {r: [self.field_of(p) for p in v.get("projections", [])] for r, v in qs.items()}

    def render_visual(self, v: dict, pos: dict, page_names: list[str], current: str) -> str:
        vis = v.get("visual", {}) or {}
        vtype = vis.get("visualType", "")
        objs = vis.get("objects", {}) or {}
        vco = vis.get("visualContainerObjects", {}) or {}
        ink, ink2 = self.ink, self.ink2

        bg_show = lit(prop(vco, "background", "show"), self.style(vtype, "background", "show", True))
        bg = self.color(prop(vco, "background", "color"), self.style(vtype, "background", "color", "#FFFFFF"))
        bd_show = lit(prop(vco, "border", "show"), self.style(vtype, "border", "show", False))
        bd = self.color(prop(vco, "border", "color"), self.style(vtype, "border", "color", "#E1DFDD"))
        radius = num(lit(prop(vco, "border", "radius"), self.style(vtype, "border", "radius", 0)))
        w, h = pos.get("width", 0), pos.get("height", 0)
        css = [f"left:{pos.get('x', 0)}px", f"top:{pos.get('y', 0)}px", f"width:{w}px", f"height:{h}px",
               f"z-index:{int(pos.get('z', 0))}", f"border-radius:{radius}px"]
        if str(bg_show).lower() != "false":
            css.append(f"background:{bg}")
        if str(bd_show).lower() != "false":
            css.append(f"box-shadow:inset 0 0 0 1px {bd}")
        roles = self.roles(vis)

        title_show = lit(prop(vco, "title", "show"), self.style(vtype, "title", "show", False))
        title_obj = prop(vco, "title", "text")
        title_text = lit(title_obj)
        if title_text is None and measure_name(title_obj):
            title_text = self.value(measure_name(title_obj), f"{measure_name(title_obj)} (título dinâmico)")
        tsize = num(self.style(vtype, "title", "fontSize", 10), 10)
        tink = self.style(vtype, "title", "fontColor", ink)
        tw = 600 if "Semibold" in str(self.style(vtype, "title", "fontFamily", "")) else 400
        title = ""
        if str(title_show).lower() != "false" and title_text:
            title = (f'<div style="font:{tw} {tsize * PT:.1f}px {FONT};color:{tink};padding:10px 12px 0;'
                     f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{title_text}</div>')
        inner = ""
        bar = lambda width, height=8: (f'<span style="display:inline-block;width:{width}%;height:{height}px;'  # noqa: E731
                                       f'background:#EBEBEB;border-radius:2px"></span>')

        if vtype == "textbox":
            for para in prop(objs, "general", "paragraphs", []) or []:
                runs = []
                for r in para.get("textRuns", []):
                    st = r.get("textStyle", {})
                    size = num(st.get("fontSize", "10pt"), 10)
                    wt = 600 if "Semibold" in st.get("fontFamily", "") or st.get("fontWeight") == "bold" else 400
                    runs.append(f'<span style="font:{wt} {size * PT:.1f}px {FONT};color:{st.get("color", ink)};'
                                f'white-space:pre">{html.escape(r.get("value", ""))}</span>')
                inner += f'<div style="padding:2px 4px">{"".join(runs)}</div>'
        elif vtype == "shape":
            fill = self.color(prop(objs, "fill", "fillColor"), "#FFFFFF")
            if "background" not in vco:
                css.append(f"background:{fill}")
            if lit(prop(objs, "shape", "tileShape")) == "rectangleRounded":
                css.append("border-radius:4px")
        elif vtype == "image":
            uri = self.image_uri(objs)
            if uri:
                inner = f'<img src="{uri}" style="width:100%;height:100%;object-fit:contain">'
        elif vtype == "pageNavigator":
            size = num(self.style("pageNavigator", "text", "fontSize", 10), 10) * PT
            margin = num(self.style("pageNavigator", "text", "leftMargin", 8), 8)
            gap = num(self.style("pageNavigator", "layout", "cellPadding", 2), 2)
            item = (h - gap * (len(page_names) - 1)) / max(len(page_names), 1)
            rows = []
            for name in page_names:
                sel = name == current
                rows.append(f'<div style="height:{item:.0f}px;margin-bottom:{gap}px;border-radius:8px;'
                            f'background:{"#E3E3E3" if sel else "transparent"};font:{600 if sel else 400} '
                            f'{size:.1f}px {FONT};color:{ink if sel else ink2};display:flex;align-items:center;'
                            f'padding-left:{margin}px">{html.escape(name)}</div>')
            inner = "".join(rows)
        elif vtype == "card":
            m = (roles.get("Values") or [None])[0]
            size = num(lit(prop(objs, "labels", "fontSize"), self.style("card", "labels", "fontSize", 20)), 20)
            vink = self.color(prop(objs, "labels", "color"), self.style("card", "labels", "color", ink)) or ink2
            fam = lit(prop(objs, "labels", "fontFamily"), self.style("card", "labels", "fontFamily", "Segoe UI"))
            wt = 600 if "Semibold" in str(fam) else 400
            if size < 12:   # a small line of text: "updated at" or a KPI's variation line
                text = self.value(m, html.escape(m or ""))
                align = "flex-end" if pos.get("y", 0) < 70 else "flex-start"
                inner = (f'<div style="font:{wt} {size * PT:.1f}px {FONT};color:{vink};height:100%;display:flex;'
                         f'align-items:center;justify-content:{align};white-space:nowrap">{text}</div>')
            else:
                text = self.value(m, bar(56, int(size * PT * 0.8)))
                inner = title + (f'<div style="font:{wt} {size * PT:.1f}px {FONT};color:{vink};'
                                 f'padding:4px 12px">{text}</div>')
        elif vtype == "slicer":
            hsize = num(self.style("slicer", "header", "textSize", 9), 9) * PT
            hink = self.style("slicer", "header", "fontColor", ink2)
            label = ((roles.get("Values") or ["Filtro"])[0]).split("[")[-1].rstrip("]")
            inner = (f'<div style="padding:4px 8px 0;font:400 {hsize:.1f}px {FONT};color:{hink}">{html.escape(label)}</div>'
                     f'<div style="margin:0 8px;font:400 {9 * PT:.1f}px {FONT};color:{ink};display:flex;'
                     f'justify-content:space-between">Todos<span style="color:{ink2}">&#8964;</span></div>')
        elif vtype == "kpi":
            m = (roles.get("Indicator") or [None])[0]
            size = num(self.style("kpi", "indicator", "fontSize", 20), 20) * PT
            wt = 600 if "Semibold" in str(self.style("kpi", "indicator", "fontFamily", "")) else 400
            trend = self.series(m, 12, [5, 5.6, 5.2, 6.1, 6.4, 6, 6.8, 7.1, 6.9, 7.6, 7.4, 8])
            peak, low = max(trend) or 1, min(trend)
            pts = " ".join(f"{i * 100 / (len(trend) - 1 or 1):.1f},{40 - 34 * (v - low) / ((peak - low) or 1):.1f}"
                           for i, v in enumerate(trend))
            goal = (roles.get("Goal") or [None])[0]
            goal_line = (f'<div style="font:400 {9 * PT:.1f}px {FONT};color:{ink2};padding:0 12px">'
                         f'Meta: {self.value(goal, bar(30, 8))}</div>') if goal else ""
            inner = (title + f'<div style="font:{wt} {size:.1f}px {FONT};color:{ink};padding:4px 12px 0">'
                     f'{self.value(m, bar(48, int(size * 0.8)))}</div>{goal_line}'
                     f'<svg viewBox="0 0 100 42" preserveAspectRatio="none" style="position:absolute;left:0;bottom:0;'
                     f'width:100%;height:{max(h * 0.35, 16):.0f}px"><polygon points="0,42 {pts} 100,42" '
                     f'fill="{self.accent}" fill-opacity=".12"/><polyline points="{pts}" fill="none" '
                     f'stroke="{self.accent}" stroke-width="1.5" vector-effect="non-scaling-stroke"/></svg>')
        elif vtype in ("tableEx", "pivotTable"):
            cols = roles.get("Rows", []) + roles.get("Values", [])
            across = self.labels((roles.get("Columns") or [None])[0], 4)
            if across and roles.get("Values"):             # matrix with columns: one value column per member
                cols = roles.get("Rows", []) + [f"[{a}]" for a in across]
            hl = {}
            for item in objs.get("values", []):
                sel = (item.get("selector") or {}).get("metadata", "")
                c = self.color(item.get("properties", {}).get("fontColor"))
                if sel and c:
                    hl[sel.split(".")[-1]] = c
            first = self.labels(cols[0] if cols else None, 14)
            n_rows = len(first) or 14
            size = 9 * PT
            head = "".join(f'<th style="text-align:{"left" if i == 0 else "right"};font-weight:600;color:{ink2};'
                           f'padding:6px 8px">{html.escape(c.split("[")[-1].rstrip("]"))}</th>' for i, c in enumerate(cols))
            body = ""
            for r in range(n_rows):
                cells = []
                for j, c in enumerate(cols):
                    name = c.split("[")[-1].rstrip("]")
                    if j == 0 and r < len(first):
                        content = html.escape(first[r])
                    else:
                        content = bar(40 + (r * 17 + j * 29) % 45)
                    style_ink = hl.get(name, ink)
                    cells.append(f'<td style="padding:6px 8px;color:{style_ink};text-align:{"left" if j == 0 else "right"};'
                                 f'border-top:1px solid #F1F1F1">{content}</td>')
                body += "<tr>" + "".join(cells) + "</tr>"
            inner = (title + f'<table style="width:calc(100% - 8px);margin:6px 4px;border-collapse:collapse;'
                     f'font:400 {size:.1f}px {FONT}"><tr>{head}</tr>{body}</table>')
        elif vtype:
            inner = title + self.chart(vtype, roles, objs, w, h)
        return f'<div class="v" style="{";".join(css)}">{inner}</div>'

    def chart(self, vtype: str, roles: dict, objs: dict, w: float, h: float) -> str:
        cat = (roles.get("Category") or [None])[0]
        m = (roles.get("Y") or [None])[0]
        kind = vtype.lower()
        body_h = h - 52
        if kind == "scatterchart":
            names = self.labels(cat, 12) or [""] * 12
            xs = self.series((roles.get("X") or [None])[0], len(names), [2, 3.5, 5, 6, 7.5, 3, 8, 4.5, 6.5, 9, 2.5, 5.5])
            ys = self.series(m, len(names), [3, 5, 4, 7, 6, 2, 8, 6.5, 4.5, 7.5, 5, 3.5])
            xp, yp = max(xs) or 1, max(ys) or 1
            dots = "".join(f'<div title="{html.escape(n)}" style="position:absolute;left:{4 + 90 * x / xp:.1f}%;'
                           f'top:{88 - 80 * y / yp:.1f}%;width:8px;height:8px;margin:-4px;border-radius:50%;'
                           f'background:{self.accent};opacity:.8"></div>' for n, x, y in zip(names, xs, ys))
            return (f'<div style="position:relative;height:{body_h - 16}px;margin:8px 12px;'
                    f'border-bottom:1px solid #EBEBEB;border-left:1px solid #EBEBEB">{dots}</div>')
        if kind in ("piechart", "donutchart"):
            labels = self.labels(cat, 6) or [""] * 5
            vals = (self.sample.get("series", {}).get(cat or "") or self.series(m, len(labels), [5, 4, 3, 2, 1]))[:len(labels)]
            palette = (self.theme.get("dataColors") or [self.accent, "#666666", "#999999", "#BBBBBB", "#DDDDDD"])
            total, acc, stops = sum(vals) or 1, 0.0, []
            for i, v in enumerate(vals):
                stops.append(f"{palette[i % len(palette)]} {acc / total * 360:.1f}deg {(acc + v) / total * 360:.1f}deg")
                acc += v
            d = max(min(body_h - 16, w - 24), 40)
            hole = (f'<div style="position:absolute;inset:30%;border-radius:50%;background:#FFFFFF"></div>'
                    if kind == "donutchart" else "")
            return (f'<div style="position:relative;width:{d}px;height:{d}px;margin:8px auto;border-radius:50%;'
                    f'background:conic-gradient({", ".join(stops)})">{hole}</div>')
        if kind == "lineclusteredcolumncombochart":
            labels = self.labels(cat, 12) or [""] * 12
            cols_v = self.series(m, len(labels), [6, 7, 6.5, 8, 7.5, 9, 8.5, 9.5, 9, 10, 9.8, 11])
            line_v = self.series((roles.get("Y2") or [None])[0], len(labels),
                                 [4, 4.2, 4.1, 4.6, 4.4, 5, 4.8, 5.3, 5.1, 5.6, 5.4, 6])
            peak = max(cols_v + line_v) or 1
            n = len(labels)
            bars = "".join(f'<rect x="{i * 100 / n + 100 / n * 0.2:.1f}" y="{66 - 60 * v / peak:.1f}" '
                           f'width="{100 / n * 0.6:.1f}" height="{60 * v / peak:.1f}" fill="{self.accent}"/>'
                           for i, v in enumerate(cols_v))
            pts = " ".join(f"{(i + 0.5) * 100 / n:.1f},{66 - 60 * v / peak:.1f}" for i, v in enumerate(line_v))
            line = self.ink2
            return (f'<svg viewBox="0 0 100 70" preserveAspectRatio="none" style="width:100%;height:{body_h}px;'
                    f'padding:8px 12px;box-sizing:border-box">{bars}<polyline points="{pts}" fill="none" stroke="{line}" stroke-width="2" '
                    f'vector-effect="non-scaling-stroke" stroke-linejoin="round"/></svg>')
        n = 5 if "bar" in kind or "column" in kind or kind == "waterfallchart" else 12
        labels = self.labels(cat, n) or [""] * n
        vals = (self.sample.get("series", {}).get(cat or "") or self.series(m, n, [9, 7.5, 6, 4.5, 3, 5, 6.5, 5.5, 7, 6, 8, 7.2]))[:len(labels)]
        peak = max(vals) or 1
        lab = f"font:400 {9 * PT:.1f}px {FONT};color:{self.ink2}"
        if "bar" in kind:
            rows = "".join(
                f'<div style="display:flex;align-items:center;margin:6px 0">'
                f'<div style="flex:none;width:96px;{lab};white-space:nowrap;overflow:hidden">{html.escape(l)}</div>'
                f'<div style="height:{max(body_h / 9, 10):.0f}px;width:{70 * v / peak:.0f}%;background:{self.accent};'
                f'border-radius:2px"></div><span style="{lab};margin-left:6px">{v:g}</span></div>'
                for l, v in zip(labels, vals))
            return f'<div style="padding:8px 12px">{rows}</div>'
        if "column" in kind or kind == "waterfallchart":
            waterfall = kind == "waterfallchart"
            sent = {k: self.color(prop(objs, "sentimentColors", k + "Fill"))
                    or self.style("waterfallChart", "sentimentColors", k + "Fill")
                    for k in ("increase", "decrease", "total")}
            steps, level = [], 0.0                   # (label, value, start, end, kind)
            for l, v in zip(labels, vals):
                if waterfall:
                    steps.append((l, v, level, level + v, "increase" if v >= 0 else "decrease"))
                    level += v
                else:
                    steps.append((l, v, 0.0, v, "column"))
            if waterfall:
                steps.append(("Total", level, 0.0, level, "total"))
            ends = [x for st in steps for x in st[2:4]] + [0.0]
            lo, hi = min(ends), max(ends)
            plot = body_h - 40                     # room for the value and category labels
            scale = plot / ((hi - lo) or 1)
            cols = []
            for l, v, a, b, k in steps:
                fill = self.accent if k == "column" else (sent.get(k) or {"total": "#666666"}.get(k, self.accent))
                top = (hi - max(a, b)) * scale
                cols.append(f'<div style="flex:1;margin:0 6px;position:relative;height:{plot + 18:.0f}px">'
                            f'<div style="position:absolute;left:0;right:0;top:{top - 16:.0f}px;{lab};'
                            f'text-align:center">{v:g}</div>'
                            f'<div style="position:absolute;left:0;right:0;top:{top:.0f}px;height:{max(abs(b - a) * scale, 1):.0f}px;'
                            f'background:{fill};border-radius:2px"></div>'
                            f'<div style="position:absolute;left:0;right:0;bottom:0;{lab};text-align:center;white-space:nowrap;'
                            f'overflow:hidden;height:18px">{html.escape(l)}</div></div>')
            return (f'<div style="display:flex;align-items:flex-end;height:{body_h}px;padding:24px 12px 0;'
                    f'box-sizing:border-box">{"".join(cols)}</div>')
        low = min(vals)                            # line axes fit the data, like Power BI's auto range
        low = 0 if low > 0 and low < peak * 0.5 else low
        pts = " ".join(f"{i * 100 / (len(vals) - 1 or 1):.1f},{62 - 52 * (v - low) / ((peak - low) or 1):.1f}"
                       for i, v in enumerate(vals))
        sw = num(self.style("lineChart", "lineStyles", "strokeWidth", 2), 2)
        return (f'<svg viewBox="0 0 100 70" preserveAspectRatio="none" style="width:100%;height:{body_h}px;'
                f'padding:8px 12px;box-sizing:border-box"><polyline points="{pts}" fill="none" stroke="{self.accent}" stroke-width="{sw}" '
                f'vector-effect="non-scaling-stroke" stroke-linejoin="round"/></svg>')

    # ------------------------------------------------------------------ pages
    def render(self, mobile: bool = False) -> str:
        return self.document("".join(f"<h2>{html.escape(t)}</h2>{body}" for t, _w, _h, body in self.pages(mobile)))

    @staticmethod
    def document(body: str, margin: int = 24) -> str:
        return ("<!doctype html><meta charset='utf-8'><title>PBIR preview</title><style>"
                f"body{{margin:{margin}px;background:#DADADA;font-family:{FONT}}}"
                f"h2{{font:600 14px {FONT};color:#333;margin:24px 0 8px}}"
                ".page{position:relative;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.15)}"
                ".v{position:absolute;box-sizing:border-box;overflow:hidden}</style>" + body)

    def pages(self, mobile: bool = False) -> list[tuple[str, int, int, str]]:
        """(title, width, height, html) for every page."""
        pages_dir = self.report / "definition" / "pages"
        meta = json.loads((pages_dir / "pages.json").read_text(encoding="utf-8-sig"))
        order = meta.get("pageOrder") or sorted(p.name for p in pages_dir.iterdir() if p.is_dir())
        pages = [json.loads((pages_dir / pid / "page.json").read_text(encoding="utf-8-sig")) for pid in order]
        nav = [p.get("displayName", p["name"]) for p in pages if p.get("visibility") != "HiddenInViewMode"]
        page_bg = self.style("page", "background", "color", "#FFFFFF")
        out = []
        for pid, p in zip(order, pages):
            items = []
            bottom = 0
            for f in sorted((pages_dir / pid / "visuals").glob("*/visual.json")):
                v = json.loads(f.read_text(encoding="utf-8-sig"))
                pos = v.get("position", {})
                if mobile:
                    mf = f.parent / "mobile.json"
                    if not mf.exists():
                        continue
                    pos = json.loads(mf.read_text(encoding="utf-8-sig")).get("position", {})
                bottom = max(bottom, pos.get("y", 0) + pos.get("height", 0))
                items.append(self.render_visual(v, pos, nav, p.get("displayName", "")))
            if mobile and not items:
                continue
            width = 320 if mobile else p.get("width", 1280)
            height = bottom + 8 if mobile else p.get("height", 720)
            bg = "#FFFFFF" if p.get("pageBinding", {}).get("type") == "Tooltip" else page_bg
            kind = {"Tooltip": " · tooltip", "Drillthrough": " · drill-through"}.get(
                p.get("pageBinding", {}).get("type", ""), "")
            out.append((f'{p.get("displayName", pid)}{kind}', width, height,
                        f'<div class="page" style="width:{width}px;height:{height}px;background:{bg}">'
                        f'{"".join(items)}</div>'))
        return out


BROWSERS = ["msedge", "microsoft-edge", "google-chrome", "chrome", "chromium", "chromium-browser",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"]


def find_browser() -> str | None:
    import os
    import shutil
    if os.environ.get("PBIR_PREVIEW_BROWSER"):
        return os.environ["PBIR_PREVIEW_BROWSER"]
    for b in BROWSERS:
        found = shutil.which(b) or (b if os.path.isabs(b) and os.path.exists(b) else None)
        if found:
            return found
    return None


def screenshot(preview: "Preview", mobile: bool, out_dir: Path) -> int:
    """One PNG per page: Playwright when installed, otherwise the local Edge/Chrome in headless mode."""
    out_dir.mkdir(parents=True, exist_ok=True)
    pages = preview.pages(mobile)
    names = [f"page-{i + 1}.png" for i in range(len(pages))]
    try:
        from playwright.sync_api import sync_playwright  # optional
        with sync_playwright() as p:
            b = p.chromium.launch()
            page = b.new_page()
            for (_t, w, h, body), name in zip(pages, names):
                page.set_viewport_size({"width": w, "height": h})
                page.set_content(Preview.document(body, margin=0))
                page.screenshot(path=str(out_dir / name))
            b.close()
        return len(pages)
    except ImportError:
        pass
    browser = find_browser()
    if not browser:
        print("! --png needs Microsoft Edge, Google Chrome or Chromium (or the playwright package); "
              "set PBIR_PREVIEW_BROWSER to the browser executable. Open the HTML file instead.")
        return 0
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        for (_t, w, h, body), name in zip(pages, names):
            f = Path(tmp) / "page.html"
            f.write_text(Preview.document(body, margin=0), encoding="utf-8")
            subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                            f"--user-data-dir={Path(tmp) / 'profile'}", f"--window-size={w},{h}",
                            f"--screenshot={(out_dir / name).resolve()}", f.resolve().as_uri()],
                           capture_output=True, timeout=120, check=False)
    return sum(1 for n in names if (out_dir / n).exists())


def main() -> int:
    ap = argparse.ArgumentParser(prog="preview_pbir.py", description=__doc__.splitlines()[0])
    ap.add_argument("report", type=Path, help="the <Name>.Report folder")
    ap.add_argument("--out", type=Path, default=Path("preview.html"))
    ap.add_argument("--sample", type=Path, help="JSON with sample measure values, category labels and series")
    ap.add_argument("--mobile", action="store_true", help="render the phone layout (mobile.json)")
    ap.add_argument("--png", type=Path, metavar="DIR", help="also save one PNG per page (needs playwright)")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")   # Windows consoles default to a legacy code page
        except ValueError:
            pass
    sample = json.loads(args.sample.read_text(encoding="utf-8")) if args.sample else None
    args.out.write_text(Preview(args.report, sample).render(mobile=args.mobile), encoding="utf-8")
    print(f"[ok] {args.out}")
    if args.png:
        n = screenshot(Preview(args.report, sample), args.mobile, args.png)
        if n:
            print(f"[ok] {n} PNG(s) in {args.png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
