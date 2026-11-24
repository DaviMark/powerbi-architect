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
     "colors":   {"Cor Var % Vencido": "#CE2C31",          # one colour, a list (one per bar) or
                  "Cor Meta": {"total": "#CE2C31", "byCategory": ["#3E63DD", "#CE2C31"]}},  # both
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
import re
import sys
from pathlib import Path

PT = 4 / 3  # Power BI font sizes are points; the canvas is in pixels.
ALERT_DEFAULT = "#CE2C31"
FONT = "'Segoe UI', 'Selawik', 'Inter', 'Helvetica Neue', Arial, sans-serif"
# How far the preview's boxes sit from Power BI's. Measured against Desktop screenshots with --overlay;
# override any of them with --calibration file.json (docs/calibrar-preview.md explains the procedure).
CALIBRATION = {
    "title_padding": "10px 12px 0",       # visual title inside its container
    "card_value_padding": "4px 12px",     # KPI value under its label
    "table_cell_padding": "6px 8px",      # table and matrix cells
    "table_margin": "6px 4px",            # table grid inside the container
    "slicer_header_padding": "4px 8px 0",  # slicer header text
    "chart_padding": "8px 12px",          # plot area inside a chart container
    "chart_reserved_height": 52,          # title and axis labels above and below the plot, in px
}
CAL = dict(CALIBRATION)


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


NUMBER = re.compile(r"^(.*?)(-?\d[\d.]*(?:,\d+)?)(.*)$")
# Deterministic wobble for values the sample does not give: plausible, never random between renders.
WOBBLE = [1.0, 0.93, 0.88, 0.97, 0.9, 1.04, 0.95, 0.86, 1.02, 0.91, 0.99, 0.94, 0.89, 1.01, 0.92, 0.97]
TREND = [0.95, 0.965, 0.955, 0.975, 0.985, 0.97, 0.99, 1.005, 0.995, 1.015, 1.0, 1.02]   # months: a gentle climb


def parse_like(like: str | None):
    """(prefix, value, decimals, suffix) of a formatted sample value such as 'R$ 3,1 mi' or '91,4%'."""
    m = NUMBER.match(like or "")
    if not m:
        return None
    digits = m.group(2)
    decimals = len(digits.split(",")[1]) if "," in digits else 0
    try:
        return m.group(1), float(digits.replace(".", "").replace(",", ".")), decimals, m.group(3)
    except ValueError:
        return None


def fmt(v: float, like: str | None = None) -> str:
    """A number written the way the sample writes its measure (pt-BR: 1.234,5), or a short default."""
    p = parse_like(like)
    if p:
        prefix, _, decimals, suffix = p
    else:
        prefix, suffix = "", ""
        decimals = 0 if abs(v) >= 100 or float(v).is_integer() else 1
    text = f"{v:,.{decimals}f}".replace(",", "§").replace(".", ",").replace("§", ".")
    return f"{prefix}{text}{suffix}"


def nice_ticks(lo: float, hi: float, n: int = 4) -> list[float]:
    """Round axis ticks covering lo..hi, like Power BI's value axis."""
    import math
    span = (hi - lo) or abs(hi) or 1
    raw = span / n
    mag = 10 ** math.floor(math.log10(raw))
    step = next(s * mag for s in (1, 2, 2.5, 5, 10) if s * mag >= raw)
    start = math.floor(lo / step) * step
    ticks, t = [], start
    while t <= hi + step * 0.001:
        ticks.append(round(t, 10))
        t += step
    if ticks[-1] < hi:
        ticks.append(round(t, 10))
    return ticks



def mix(a: str, b: str, t: float) -> str:
    """Colour between a (t = 0) and b (t = 1)."""
    ca, cb = (tuple(int(x.lstrip("#")[k:k + 2], 16) for k in (0, 2, 4)) for x in (a, b))
    return "#" + "".join(f"{round(p + (q - p) * t):02X}" for p, q in zip(ca, cb))

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
                c = self.sample.get("colors", {}).get(m, default)
                if isinstance(c, dict):                          # {"total": card colour, "byCategory": [...]}
                    return c.get("total", default)
                return c[0] if isinstance(c, list) and c else c    # a list is one colour per bar
            return lit(c, default)
        return default

    def value(self, measure: str | None, placeholder: str) -> str:
        if measure and measure in self.sample.get("measures", {}):
            return html.escape(self.sample["measures"][measure])
        return placeholder

    def labels(self, field: str | None, n: int) -> list[str]:
        vals = self.sample.get("fields", {}).get(field or "", [])
        return vals[:n] if vals else []

    @staticmethod
    def top_n(container: dict) -> int | None:
        """Rows kept by a Top N visual filter, if the visual has one."""
        for f in (container.get("filterConfig") or {}).get("filters", []):
            if f.get("type") == "TopN":
                try:
                    return int(f["filter"]["From"][0]["Expression"]["Subquery"]["Query"]["Top"])
                except (KeyError, IndexError, TypeError, ValueError):
                    return None
        return None

    def series(self, measure: str | None, n: int, fallback: list[float]) -> list[float]:
        vals = self.sample.get("series", {}).get(measure or "", [])
        return (vals or self.synth(measure, n) or fallback)[:n]

    def like(self, measure: str | None) -> str | None:
        """The sample's formatted value of a measure: the pattern every number of that measure follows."""
        v = self.sample.get("measures", {}).get(measure or "")
        return v if isinstance(v, str) and parse_like(v) else None

    def synth(self, measure: str | None, n: int, offset: int = 0, trend: bool = False) -> list[float]:
        """n plausible values of a measure the sample gives only as a total: rates and averages wobble
        around it, counts and amounts are shared among the n points."""
        p = parse_like(self.like(measure))
        if not p or n < 1:
            return []
        base = p[1]
        rate = "%" in p[3] or re.search(r"m[eé]di|\bpor\b|%|taxa|ticket|avg|average|per\b", measure or "", re.I)
        each = base if rate else base / n
        shape = TREND if trend else WOBBLE
        return [round(each * shape[(i + offset) % len(shape)], max(p[2], 1)) for i in range(n)]

    def num_text(self, v: float, measure: str | None) -> str:
        return html.escape(fmt(v, self.like(measure)))

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
            title = (f'<div style="font:{tw} {tsize * PT:.1f}px {FONT};color:{tink};padding:{CAL["title_padding"]};'
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
                                 f'padding:{CAL["card_value_padding"]}">{text}</div>')
        elif vtype == "slicer":
            hsize = num(self.style("slicer", "header", "textSize", 9), 9) * PT
            hink = self.style("slicer", "header", "fontColor", ink2)
            label = ((roles.get("Values") or ["Filtro"])[0]).split("[")[-1].rstrip("]")
            inner = (f'<div style="padding:{CAL["slicer_header_padding"]};font:400 {hsize:.1f}px {FONT};color:{hink}">{html.escape(label)}</div>'
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
            inner = (title + f'<div style="font:{wt} {size:.1f}px {FONT};color:{ink};padding:{CAL["card_value_padding"]} 0">'
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
            top = self.top_n(v)
            if top:                                        # Power BI's Top N filter keeps only these rows
                first, n_rows = first[:top], min(n_rows, top)
            size = 9 * PT
            filled = {}
            for j, c in enumerate(cols[1:], 1):            # numbers the sample can stand behind
                if "[" in c and not c.startswith("["):
                    vals = self.sample.get("fields", {}).get(c) or []
                    filled[j] = [html.escape(vals[(r * 7 + j) % len(vals)]) for r in range(n_rows)] if vals else []
                else:
                    meas = c if not c.startswith("[") else (roles.get("Values") or [None])[0]
                    raw = self.sample.get("series", {}).get(meas or "") or self.synth(meas, n_rows, offset=j * 3)
                    filled[j] = [self.num_text(x, meas) for x in raw[:n_rows]]
            is_text = lambda i: i == 0 or ("[" in cols[i] and not cols[i].startswith("["))  # noqa: E731
            head = "".join(f'<th style="text-align:{"left" if is_text(i) else "right"};font-weight:600;color:{ink2};'
                           f'padding:{CAL["table_cell_padding"]}">{html.escape(c.split("[")[-1].rstrip("]"))}</th>' for i, c in enumerate(cols))
            body = ""
            for r in range(n_rows):
                cells = []
                for j, c in enumerate(cols):
                    name = c.split("[")[-1].rstrip("]")
                    if j == 0 and r < len(first):
                        content = html.escape(first[r])
                    elif r < len(filled.get(j) or []):
                        content = filled[j][r]
                    else:
                        content = bar(40 + (r * 17 + j * 29) % 45)
                    style_ink = hl.get(name, ink)
                    cells.append(f'<td style="padding:{CAL["table_cell_padding"]};color:{style_ink};text-align:{"left" if is_text(j) else "right"};'
                                 f'border-top:1px solid #F1F1F1">{content}</td>')
                body += "<tr>" + "".join(cells) + "</tr>"
            # A full-height list scrolls in Power BI; a short table must fit its rows (the critic counts them).
            scroll = ' data-scroll="1"' if h >= 400 else ""
            inner = (title + f'<table{scroll} style="width:calc(100% - 8px);margin:{CAL["table_margin"]};border-collapse:collapse;'
                     f'font:400 {size:.1f}px {FONT}"><tr>{head}</tr>{body}</table>')
        elif vtype:
            try:
                srt = vis["query"]["sortDefinition"]["sort"][0]
                self._sort_desc = srt.get("direction") == "Descending" and "Measure" in srt.get("field", {})
            except (KeyError, IndexError, TypeError):
                self._sort_desc = False
            inner = title + self.chart(vtype, roles, objs, w, h)
        chromeless = str(title_show).lower() == "false" and str(bg_show).lower() == "false"
        tags = (f'data-t="{html.escape(vtype)}" data-name="{html.escape(str(v.get("name", "")))}" '
                f'data-title="{html.escape(str(title_text or ""))}"' + (' data-chromeless="1"' if chromeless else ""))
        return f'<div class="v" {tags} style="{";".join(css)}">{inner}</div>'

    def target_of(self, objs: dict) -> str | None:
        """Measure drawn as a dashed target line (lineStyles with lineStyle 'dashed' on one series)."""
        for item in objs.get("lineStyles", []):
            if lit((item.get("properties") or {}).get("lineStyle")) == "dashed":
                meta = (item.get("selector") or {}).get("metadata", "")
                return meta.split(".", 1)[-1] if meta else None
        return None

    def bar_colours(self, objs: dict, n: int, vals: list[float] | None = None) -> list[str]:
        """Accent for every bar, the sample colours of a colour measure (one per bar, or one for all), or
        the rule-based colour of a target ("target" in the layout spec): bars below it in the alert colour."""
        for item in objs.get("dataPoint", []):
            if (item.get("selector") or {}).get("data"):
                c = ((item.get("properties") or {}).get("fill") or {}).get("solid", {}).get("color") or {}
                cond = ((c.get("expr") or {}).get("Conditional") or {}) if isinstance(c, dict) else {}
                rule = ((c.get("expr") or {}).get("FillRule") or {}) if isinstance(c, dict) else {}
                grad = (rule.get("FillRule") or {}).get("linearGradient2") or {}
                if grad and vals:
                    def stop(k, default):
                        v = (((grad.get(k) or {}).get("color") or {}).get("Literal") or {}).get("Value")
                        return v.strip("'") if isinstance(v, str) else default
                    lo_c, hi_c = stop("min", "#D4D4D8"), stop("max", self.accent)
                    lo, hi = min(vals), max(vals)
                    return [mix(lo_c, hi_c, (v - lo) / (hi - lo) if hi > lo else 1) for v in vals][:n]
                if cond and vals:
                    case = (cond.get("Cases") or [{}])[0]
                    cmp_ = (case.get("Condition") or {}).get("Comparison") or {}
                    goal_m = ((cmp_.get("Right") or {}).get("Measure") or {}).get("Property")
                    goal = (self.sample.get("series", {}).get(goal_m or "") or [None])[0]
                    if goal is None:
                        p = parse_like(self.sample.get("measures", {}).get(goal_m or ""))
                        goal = p[1] if p else sorted(vals)[len(vals) // 2]   # no sample target: the median
                    hit = lit(case.get("Value"), ALERT_DEFAULT)
                    other = lit(cond.get("DefaultValue"), self.accent)
                    below = cmp_.get("ComparisonKind", 3) in (3, 4)
                    return [hit if (v < goal if below else v > goal) else other for v in vals][:n]
                m = measure_name(c)
                c = self.sample.get("colors", {}).get(m) if m else None
                if isinstance(c, dict):
                    c = c.get("byCategory") or c.get("total")
                if isinstance(c, list):
                    return (c * n)[:n]
                if isinstance(c, str):
                    return [c] * n
        return [self.accent] * n

    def inner_padding(self, vtype: str) -> float:
        """Share of each category slot left empty around a bar (Power BI's categoryAxis innerPadding, %)."""
        return min(max(num(self.style(vtype, "categoryAxis", "innerPadding", 20), 20), 0), 90) / 100

    def xy_plot(self, w: float, body_h: float, labels: list[str], layers: list[dict], measure: str | None,
                zero: bool, vtype: str = "") -> str:
        """Value axis with round ticks and light gridlines, category labels underneath, and the layers
        ({"kind": "col" | "line" | "target", "values": [...], "color": hex, "fills": [...]}) on one scale."""
        n = max(len(labels), max((len(x["values"]) for x in layers), default=1), 1)
        everything = [v for x in layers for v in x["values"]] or [0, 1]
        grid = self.style(vtype, "valueAxis", "gridlineColor", "#EDEDF0")
        lo, hi = min(everything), max(everything)
        if zero or lo > 0 and lo < hi * 0.5:
            lo = min(lo, 0)
        ticks = nice_ticks(lo if zero else lo - (hi - lo) * 0.1, hi)
        lo, hi = ticks[0], ticks[-1]
        like = self.like(measure)
        tick_text = [fmt(t, like) for t in ticks]
        left = 12 + max(len(t) for t in tick_text) * 6.4 + 6
        top, bottom, right = 8, 22, 14
        pw, ph = max(w - left - right, 20), max(body_h - top - bottom, 20)
        y = lambda v: ph - ph * (v - lo) / ((hi - lo) or 1)  # noqa: E731
        lab = f"font:400 {9 * PT:.1f}px {FONT};color:{self.ink2};white-space:nowrap;position:absolute"
        out = []
        for t, text in zip(ticks, tick_text):
            ty = top + y(t)
            out.append(f'<div style="position:absolute;left:{left:.0f}px;width:{pw:.0f}px;top:{ty:.1f}px;'
                       f'border-top:1px solid {"#D2D2D7" if t == 0 else grid}"></div>'
                       f'<div style="{lab};right:{w - left + 6:.0f}px;top:{ty - 8:.1f}px">{html.escape(text)}</div>')
        step = max(1, -(-n * 52 // int(pw)))                 # thin the category labels until they fit
        slot = pw / n
        for i, text in enumerate(labels[:n]):
            if i % step:
                continue
            cx = left + slot * (i + 0.5)
            anchor = "translateX(-50%)"
            if cx - 26 < 12:
                cx, anchor = 12, "none"
            out.append(f'<div style="{lab};top:{top + ph + 5:.0f}px;left:{cx:.0f}px;transform:{anchor}">'
                       f'{html.escape(text)}</div>')
        svg = []
        for layer in layers:
            vals = layer["values"][:n]
            if layer["kind"] == "col":
                fills = layer.get("fills") or [layer["color"]] * n
                bw = slot * (1 - self.inner_padding(vtype))
                for i, v in enumerate(vals):
                    y0, y1 = y(max(v, 0) if lo < 0 else v), y(0 if lo <= 0 else lo)
                    svg.append(f'<rect x="{slot * i + (slot - bw) / 2:.1f}" y="{min(y0, y1):.1f}" width="{bw:.1f}" '
                               f'height="{abs(y1 - y0):.1f}" rx="2" fill="{fills[i % len(fills)]}"/>')
            else:
                pts = " ".join(f"{slot * (i + 0.5):.1f},{y(v):.1f}" for i, v in enumerate(vals))
                if layer["kind"] == "target":
                    svg.append(f'<polyline points="{pts}" fill="none" stroke="#999999" stroke-width="1.5" '
                               f'stroke-dasharray="4 3"/>')
                else:
                    svg.append(f'<polyline points="{pts}" fill="none" stroke="{layer["color"]}" stroke-width="2" '
                               f'stroke-linejoin="round" stroke-linecap="round"/>')
        out.append(f'<svg width="{pw:.0f}" height="{ph:.0f}" style="position:absolute;left:{left:.0f}px;'
                   f'top:{top}px;overflow:visible">{"".join(svg)}</svg>')
        return f'<div style="position:relative;height:{body_h:.0f}px">{"".join(out)}</div>'

    def chart(self, vtype: str, roles: dict, objs: dict, w: float, h: float) -> str:
        cat = (roles.get("Category") or [None])[0]
        m = (roles.get("Y") or [None])[0]
        kind = vtype.lower()
        body_h = h - CAL["chart_reserved_height"]
        hidden = lambda o: str(lit(prop(objs, o, "show"))).lower() == "false"  # noqa: E731
        if kind == "linechart" and hidden("categoryAxis") and hidden("valueAxis"):
            # A trend inside a KPI card: one thin line on its own scale, no axes, no labels.
            labels = self.labels(cat, 12) or [""] * 12
            # The sample's own series when it has one; otherwise a gentle monthly climb with some noise
            # (unrounded: rounding a total shared by 12 months to the KPI's decimals draws steps).
            vals = self.sample.get("series", {}).get(m or "") or [
                TREND[i % len(TREND)] * (0.9 + 0.1 * WOBBLE[(i * 5 + len(m or "")) % len(WOBBLE)])
                for i in range(len(labels))]
            vals = vals[:len(labels)]
            lo, hi = min(vals), max(vals)
            span = (hi - lo) or 1
            stroke = self.color(prop(objs, "dataPoint", "fill"), self.ink2)
            pts = " ".join(f"{2 + i * (w - 4) / max(len(vals) - 1, 1):.1f},{h - 3 - (h - 6) * (v - lo) / span:.1f}"
                           for i, v in enumerate(vals))
            last = pts.split()[-1].split(",")
            return (f'<svg width="{w}" height="{h}" style="display:block"><polyline points="{pts}" fill="none" '
                    f'stroke="{stroke}" stroke-width="1.5" stroke-linejoin="round"/>'
                    f'<circle cx="{last[0]}" cy="{last[1]}" r="2.5" fill="{self.ink}"/></svg>')
        if kind == "scatterchart":
            names = self.labels(cat, 12) or [""] * 12
            xs = self.series((roles.get("X") or [None])[0], len(names), [2, 3.5, 5, 6, 7.5, 3, 8, 4.5, 6.5, 9, 2.5, 5.5])
            ys = self.series(m, len(names), [3, 5, 4, 7, 6, 2, 8, 6.5, 4.5, 7.5, 5, 3.5])
            x0, y0 = min(xs) * 0.9, min(ys) * 0.9           # axes fit the data, like Power BI
            xs, ys = [x - x0 for x in xs], [y - y0 for y in ys]
            xp, yp = max(xs) or 1, max(ys) or 1
            show_names = str(lit(prop(objs, "categoryLabels", "show"))).lower() == "true"
            lab_css = f"font:400 {9 * PT:.1f}px {FONT};color:{self.ink2};white-space:nowrap"
            dots = "".join(f'<div title="{html.escape(n)}" style="position:absolute;left:{4 + 90 * x / xp:.1f}%;'
                           f'top:{88 - 80 * y / yp:.1f}%;width:8px;height:8px;margin:-4px;border-radius:50%;'
                           f'background:{self.accent};opacity:.8">'
                           + (f'<span style="position:absolute;left:12px;top:-5px;{lab_css}">{html.escape(n)}</span>'
                              if show_names else "") + '</div>' for n, x, y in zip(names, xs, ys))
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
            target = self.target_of(objs)
            lines = [x for x in roles.get("Y2", []) if x != target]
            line_v = self.series(lines[0] if lines else None, len(labels),
                                 [4, 4.2, 4.1, 4.6, 4.4, 5, 4.8, 5.3, 5.1, 5.6, 5.4, 6]) if lines else []
            target_v = (self.sample.get("series", {}).get(target) or [max(cols_v) * 0.85] * len(labels)) if target else []
            shared = str(lit(prop(objs, "valueAxis", "secShow"))).lower() == "false"
            peak = max(cols_v + list(target_v) + (line_v if shared else [])) or 1
            if line_v and not shared:                      # secondary axis: the line has its own scale
                line_v = [v / (max(line_v) or 1) * peak * 0.9 for v in line_v]
            n = len(labels)
            fills = self.bar_colours(objs, n, cols_v)
            bars = "".join(f'<rect x="{i * 100 / n + 100 / n * 0.2:.1f}" y="{66 - 60 * v / peak:.1f}" '
                           f'width="{100 / n * 0.6:.1f}" height="{60 * v / peak:.1f}" fill="{fills[i]}"/>'
                           for i, v in enumerate(cols_v))
            del bars
            layers = [{"kind": "col", "values": cols_v, "fills": fills, "color": self.accent}]
            if line_v:
                layers.append({"kind": "line", "values": line_v, "color": self.ink2})
            if target_v:
                layers.append({"kind": "target", "values": list(target_v)[:n]})
            return self.xy_plot(w, body_h, labels, layers, m, zero=True, vtype=vtype)
        n = (min(len(self.labels(cat, 10)) or 5, 10) if "bar" in kind or "column" in kind or kind == "waterfallchart"
             else 12)
        labels = self.labels(cat, n) or [""] * n
        by_measure, by_category = (self.sample.get("series", {}).get(k or "") for k in (m, cat))
        # A time series belongs to the measure; a ranking belongs to the category it ranks.
        first, second = (by_measure, by_category) if kind == "linechart" else (by_category, by_measure)
        vals = (first or second or self.synth(m, n, trend=kind == "linechart")
                or [9, 7.5, 6, 4.5, 3, 5, 6.5, 5.5, 7, 6, 8, 7.2])[:len(labels)]
        if getattr(self, "_sort_desc", False) and kind != "linechart":     # Power BI applies the visual's sort
            pairs = sorted(zip(labels, vals), key=lambda lv: -lv[1])
            labels, vals = [lv[0] for lv in pairs], [lv[1] for lv in pairs]
        peak = max(vals) or 1
        lab = f"font:400 {9 * PT:.1f}px {FONT};color:{self.ink2}"
        if "bar" in kind:
            slot = (body_h + 20) / max(len(labels), 1)      # bars share the plot height, as in Power BI
            thick = min(max(slot * (1 - self.inner_padding(vtype)), 6), 24)
            fills = self.bar_colours(objs, len(labels), vals)
            name_w = min(max((max((len(x) for x in labels), default=4) * 6.6 + 8), 48), 140)
            rows = "".join(
                f'<div style="display:flex;align-items:center;height:{slot:.1f}px">'
                f'<div style="flex:none;width:{name_w:.0f}px;{lab};white-space:nowrap;overflow:hidden">{html.escape(l)}</div>'
                f'<div style="flex:1;display:flex;align-items:center;height:100%;border-left:1px solid #E6E6E6">'
                f'<div style="height:{thick:.0f}px;width:{78 * v / peak:.0f}%;background:{fills[i]};'
                f'border-radius:0 3px 3px 0"></div><span style="{lab};margin-left:6px;white-space:nowrap">'
                f'{self.num_text(v, m)}</span></div></div>'
                for i, (l, v) in enumerate(zip(labels, vals)))
            sparse = f' data-sparse="{len(labels)},{slot:.0f}"' if labels and slot > 60 else ""
            return f'<div{sparse} style="padding:4px 12px 0">{rows}</div>'
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
            col_fills = self.bar_colours(objs, len(steps), [st[1] for st in steps])
            ends = [x for st in steps for x in st[2:4]] + [0.0]
            lo, hi = min(ends), max(ends)
            plot = body_h - 40                     # room for the value and category labels
            scale = plot / ((hi - lo) or 1)
            cols = []
            for l, v, a, b, k in steps:
                fill = col_fills[len(cols)] if k == "column" else (sent.get(k) or {"total": "#666666"}.get(k, self.accent))
                top = (hi - max(a, b)) * scale
                inset = 50 * self.inner_padding(vtype)
                cols.append(f'<div style="flex:1 1 0;min-width:0;position:relative;height:{plot + 18:.0f}px">'
                            f'<div style="position:absolute;left:0;right:0;top:{top - 16:.0f}px;{lab};'
                            f'text-align:center;white-space:nowrap">{self.num_text(v, m)}</div>'
                            f'<div style="position:absolute;left:{inset:.0f}%;right:{inset:.0f}%;top:{top:.0f}px;'
                            f'height:{max(abs(b - a) * scale, 1):.0f}px;background:{fill};border-radius:2px"></div>'
                            f'<div style="position:absolute;left:0;right:0;bottom:0;{lab};text-align:center;white-space:nowrap;'
                            f'overflow:hidden;height:18px">{html.escape(l)}</div></div>')
            return (f'<div style="display:flex;align-items:flex-end;height:{body_h}px;padding:24px 12px 0;'
                    f'box-sizing:border-box">{"".join(cols)}</div>')
        target = self.target_of(objs)
        series = [vals]
        palette = [self.accent] + list((self.theme.get("dataColors") or [])[1:]) + ["#666666"]
        for extra in [x for x in roles.get("Y", [])[1:] if x != target]:
            series.append(self.series(extra, len(vals), [v * 0.7 for v in vals]))
        target_v = (self.sample.get("series", {}).get(target) or [max(vals) * 0.9] * len(vals))[:len(vals)] \
            if target else []
        layers = [{"kind": "line", "values": sr, "color": palette[i % len(palette)]}
                  for i, sr in enumerate(series)]
        if target_v:
            layers.append({"kind": "target", "values": list(target_v)})
        return self.xy_plot(w, body_h, labels, layers, m, zero=False, vtype=vtype)

    # ------------------------------------------------------------------ pages
    def render(self, mobile: bool = False, overlays: list[Path] | None = None) -> str:
        """HTML of every page. With overlays (one image per page, in page order), each page also shows
        that Power BI Desktop screenshot on top, with a slider for its opacity: misplaced boxes show
        as doubled edges."""
        out, overlays = [], overlays or []
        for i, (t, w, h, body) in enumerate(self.pages(mobile)):
            if i < len(overlays) and overlays[i].exists():
                uri = "data:image/png;base64," + base64.b64encode(overlays[i].read_bytes()).decode()
                body = body[:-len("</div>")] + (f'<img class="overlay" alt="" src="{uri}" style="position:absolute;'
                                               f'left:0;top:0;width:{w}px;height:{h}px;z-index:99999;'
                                               f'pointer-events:none;opacity:var(--overlay,.5)"></div>')
            out.append(f"<h2>{html.escape(t)}</h2>{body}")
        slider = ""
        if overlays:
            slider = ('<label style="position:sticky;top:0;display:block;background:#DADADA;padding:8px 0;'
                      'z-index:100000;font:400 13px sans-serif">Power BI Desktop por cima: '
                      '<input type="range" min="0" max="1" step="0.05" value="0.5" oninput="'
                      "document.documentElement.style.setProperty('--overlay', this.value)\"></label>")
        return self.document(slider + "".join(out))

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
                        f'<div class="page" data-page="{html.escape(p.get("displayName", pid))}" '
                        f'style="width:{width}px;height:{height}px;background:{bg}">'
                        f'{"".join(items)}</div>'))
        return out


# ---------------------------------------------------------------------- pixel critic
# Runs inside the rendered page and measures what a designer checks with a loupe. The result is written
# into the DOM, which the headless browser dumps back to Python.
CRITIC_JS = r"""
(function () {
  const out = [];
  const SHELL = new Set(["shape", "textbox", "image", "pageNavigator", "actionButton", "slicer"]);
  const add = (page, v, kind, msg) => out.push({page: page, visual: v ? v.dataset.name : "", type: v ? v.dataset.t : "",
                                               title: v ? v.dataset.title : "", kind: kind, message: msg});
  document.querySelectorAll(".page").forEach(pg => {
    const page = pg.dataset.page, P = pg.getBoundingClientRect();
    const all = [...pg.querySelectorAll(".v[data-t]")];
    const data = all.filter(v => !SHELL.has(v.dataset.t) && !v.dataset.chromeless && P.width > 400);
    all.forEach(v => {
      const r = v.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) return;
      const spilled = [];
      v.querySelectorAll("*").forEach(el => {
        const text = (el.childElementCount === 0 ? el.textContent : "").trim();
        if (!text) return;
        const row = el.closest("tr");
        if (row && row.getBoundingClientRect().bottom > r.bottom + 0.5) return;  // rows that do not fit: counted below
        const cs = getComputedStyle(el), rg = document.createRange();
        rg.selectNodeContents(el);
        const e = rg.getBoundingClientRect();                  // the glyphs, not the padded box
        if (el.scrollWidth > el.clientWidth + 1 && cs.overflow !== "visible")
          add(page, v, "truncated", "'" + text.slice(0, 60) + "' is cut (" + el.scrollWidth + " px of text in " + el.clientWidth + " px)");
        else if (e.right > r.right + 0.5 || e.bottom > r.bottom + 0.5 || e.left < r.left - 0.5 || e.top < r.top - 0.5)
          spilled.push(text.slice(0, 40));
        else if (!v.dataset.chromeless && !SHELL.has(v.dataset.t) && e.width > 0 &&
                 (e.left - r.left < 6 || r.right - e.right < 4))
          add(page, v, "tight", "'" + text.slice(0, 40) + "' touches the edge (" +
              Math.round(Math.min(e.left - r.left, r.right - e.right)) + " px) — keep ≥ 8 px of padding");
      });
      if (spilled.length) add(page, v, "clipped", spilled.length + " text(s) spill out of the visual, e.g. '" +
                                spilled[0] + "'");
      v.querySelectorAll("[data-sparse]").forEach(s => {
        const [n, slot] = s.dataset.sparse.split(",").map(Number);
        add(page, v, "sparse", n + " bars with " + slot + " px each (32 is enough) — the card is " + Math.round(r.height) +
            " px for " + (52 + 32 * n) + " px of bars: make the row \"height\": \"auto\" with \"items\": " + n);
      });
      v.querySelectorAll("table").forEach(t => {
        const trs = [...t.querySelectorAll("tr")].slice(1);
        const fit = trs.filter(tr => tr.getBoundingClientRect().bottom <= r.bottom + 0.5).length;
        if (fit < trs.length && !t.dataset.scroll)
          add(page, v, "rows", (trs.length - fit) + " of " + trs.length + " rows do not fit (room for " + fit +
              ") — keep the rows that fit (\"top\": " + Math.max(fit, 1) + " with \"sortBy\": \"<measure> desc\", " +
              "and say it in the title) or make the row \"height\": \"auto\" with \"items\": " + trs.length);
        if (t.scrollWidth > v.clientWidth + 1) add(page, v, "overflow", "the table is " + t.scrollWidth + " px wide in a " +
                                                   v.clientWidth + " px visual");
        const empty = r.bottom - t.getBoundingClientRect().bottom;
        if (r.height < 400 && empty > 120 && empty > r.height * 0.45)   // full-height lists scroll with real data
          add(page, v, "empty", Math.round(empty) + " px empty under the rows — size the card to its rows (\"height\": \"auto\" with \"items\")");
      });
    });
    for (let i = 0; i < data.length; i++) for (let j = i + 1; j < data.length; j++) {
      const a = data[i].getBoundingClientRect(), b = data[j].getBoundingClientRect();
      const w = Math.min(a.right, b.right) - Math.max(a.left, b.left), h = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
      if (w > 2 && h > 2) add(page, data[i], "overlap", "overlaps " + (data[j].dataset.title || data[j].dataset.t) + " by " +
                              Math.round(w) + "×" + Math.round(h) + " px");
    }
    const rows = [];
    data.slice().sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top).forEach(v => {
      const r = v.getBoundingClientRect(), row = rows.find(x => Math.abs(x.top - r.top) <= 2);
      row ? row.items.push(v) : rows.push({top: r.top, items: [v]});
    });
    const gaps = [];
    rows.forEach(row => {
      row.items.sort((a, b) => a.getBoundingClientRect().left - b.getBoundingClientRect().left);
      for (let k = 1; k < row.items.length; k++) {
        const g = row.items[k].getBoundingClientRect().left - row.items[k - 1].getBoundingClientRect().right;
        if (g > -1) gaps.push([g, row.items[k]]);
      }
    });
    for (let k = 1; k < rows.length; k++) {
      const above = Math.max(...rows[k - 1].items.map(v => v.getBoundingClientRect().bottom));
      const g = rows[k].top - above;
      if (g > -1) gaps.push([g, rows[k].items[0]]);
    }
    gaps.forEach(([g, v]) => {
      if (g < 8) add(page, v, "cramped", "only " + Math.round(g) + " px from its neighbour — use the 16 px gutter");
      else if (g > 32) add(page, v, "loose", Math.round(g) + " px from its neighbour — use the 16 px gutter");
    });
    const sizes = [...new Set(gaps.map(x => Math.round(x[0])).filter(g => g >= 8 && g <= 32))];
    if (sizes.length > 1) add(page, null, "uneven", "gutters of " + sizes.sort((a, b) => a - b).join(", ") + " px on one page — use one");
    const charts = rows.filter(x => x.items.length > 1 && x.items[0].getBoundingClientRect().height > 120);
    for (let k = 1; k < charts.length; k++) {
      const edges = x => x.items.slice(0, -1).map(v => Math.round(v.getBoundingClientRect().right)).join(",");
      if (edges(charts[k]) !== edges(charts[k - 1]))
        add(page, charts[k].items[0], "grid", "this row splits at x " + edges(charts[k]) + " and the one above at x " +
            edges(charts[k - 1]) + " — rows of charts read best on the same column grid");
    }
  });
  const box = document.createElement("script");
  box.type = "application/json"; box.id = "critique-result"; box.textContent = JSON.stringify(out);
  document.body.appendChild(box);
})();
"""


def critique(preview: "Preview", mobile: bool = False) -> list[dict] | None:
    """Render every page in a headless browser and measure it; None when no browser is available."""
    import re
    import subprocess
    import tempfile
    browser = find_browser()
    if not browser:
        return None
    body = "".join(b for _t, _w, _h, b in preview.pages(mobile))
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "critique.html"
        f.write_text(Preview.document(body, margin=0) + f"<script>{CRITIC_JS}</script>", encoding="utf-8")
        r = subprocess.run([browser, "--headless=new", "--disable-gpu", "--no-first-run", "--no-sandbox",
                            f"--user-data-dir={Path(tmp) / 'profile'}", "--window-size=1400,900",
                            "--virtual-time-budget=3000", "--dump-dom", f.resolve().as_uri()],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180, check=False)
    m = re.search(r'<script type="application/json" id="critique-result">(.*?)</script>', r.stdout, re.S)
    return json.loads(html.unescape(m.group(1))) if m else None


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


def screenshot(preview: "Preview", mobile: bool, out_dir: Path, scale: float = 1) -> int:
    """One PNG per page: Playwright when installed, otherwise the local Edge/Chrome in headless mode."""
    out_dir.mkdir(parents=True, exist_ok=True)
    pages = preview.pages(mobile)
    names = [f"page-{i + 1}{'-mobile' if mobile else ''}.png" for i in range(len(pages))]   # desktop PNGs stay
    try:
        from playwright.sync_api import sync_playwright  # optional
        with sync_playwright() as p:
            b = p.chromium.launch()
            page = b.new_page(device_scale_factor=scale)
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
                            f"--force-device-scale-factor={scale}", f"--screenshot={(out_dir / name).resolve()}", f.resolve().as_uri()],
                           capture_output=True, timeout=120, check=False)
    return sum(1 for n in names if (out_dir / n).exists())


def main() -> int:
    ap = argparse.ArgumentParser(prog="preview_pbir.py", description=__doc__.splitlines()[0])
    ap.add_argument("report", type=Path, help="the <Name>.Report folder")
    ap.add_argument("--out", type=Path, default=Path("preview.html"))
    ap.add_argument("--sample", type=Path, help="JSON with sample measure values, category labels and series")
    ap.add_argument("--mobile", action="store_true", help="render the phone layout (mobile.json)")
    ap.add_argument("--png", type=Path, metavar="DIR", help="also save one PNG per page (needs playwright)")
    ap.add_argument("--png-scale", type=float, default=1, metavar="N", help="pixel density of the PNGs (2 = retina)")
    ap.add_argument("--overlay", type=Path, nargs="+", metavar="PNG",
                    help="Power BI Desktop screenshots, one per page in page order (or one folder of page-N.png), "
                         "drawn over the preview to calibrate it")
    ap.add_argument("--critique", action="store_true",
                    help="measure the rendered pages (cut or spilled text, padding, overlaps, gutters, column grid, "
                         "empty space); exit 1 when something needs fixing (needs Edge, Chrome or Chromium)")
    ap.add_argument("--calibration", type=Path, metavar="JSON",
                    help="override the render constants in CALIBRATION (paddings, reserved heights)")
    args = ap.parse_args()
    for stream in (sys.stdin, sys.stdout, sys.stderr):   # Windows consoles default to a legacy code page
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except ValueError:
                pass
    sample = json.loads(args.sample.read_text(encoding="utf-8")) if args.sample else None
    if args.calibration:
        extra = json.loads(args.calibration.read_text(encoding="utf-8"))
        unknown = set(extra) - set(CALIBRATION)
        if unknown:
            print(f"preview_pbir.py: error: unknown calibration keys {sorted(unknown)}; known: {sorted(CALIBRATION)}",
                  file=sys.stderr)
            return 2
        CAL.update(extra)
    overlays = args.overlay or []
    if len(overlays) == 1 and overlays[0].is_dir():
        overlays = sorted(overlays[0].glob("page-*.png"), key=lambda f: int("".join(filter(str.isdigit, f.stem)) or 0))
    args.out.write_text(Preview(args.report, sample).render(mobile=args.mobile, overlays=overlays), encoding="utf-8")
    print(f"[ok] {args.out}")
    if args.png:
        n = screenshot(Preview(args.report, sample), args.mobile, args.png, args.png_scale)
        if n:
            print(f"[ok] {n} PNG(s) in {args.png}")
    if args.critique:
        found = critique(Preview(args.report, sample), args.mobile)
        if found is None:
            print("! --critique needs Microsoft Edge, Google Chrome or Chromium (set PBIR_PREVIEW_BROWSER)")
            return 2
        seen = set()
        for c in found:
            line = (f"{c['page']} › {c['type'] or 'page'}" + (f' "{c["title"]}"' if c["title"] else "")
                    + f": [{c['kind']}] {c['message']}")
            if line not in seen:
                seen.add(line)
                print(f"- {line}")
        print(f"[{'ok' if not seen else 'fix'}] critique: {len(seen)} finding(s)")
        return 1 if seen else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
