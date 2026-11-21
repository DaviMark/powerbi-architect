#!/usr/bin/env python3
"""Render PBIR pages as an HTML wireframe, to review layout without Power BI Desktop.

Development tool (not part of the skill). Standard library only, offline.

    python tools/preview_pbir.py <Name>.Report [--out preview.html]

Draws every visual at its real position and size with the report's custom theme (page colour,
backgrounds, borders, fonts), the text of text boxes, the page navigator, and placeholders for data
visuals (titles, card values, bars, lines, table rows, slicer boxes). It shows layout, alignment,
spacing and type scale; it does not query data or reproduce every formatting option.
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

PT = 4 / 3  # Power BI font sizes are points; the canvas is in pixels.


def lit(o, default=None):
    try:
        v = o["expr"]["Literal"]["Value"]
    except (KeyError, TypeError):
        return default
    return v.strip("'") if isinstance(v, str) else v


def color_of(o, default=None):
    try:
        return lit(o["solid"]["color"], default)
    except (KeyError, TypeError):
        return default


def prop(objs: dict, obj: str, name: str, default=None):
    try:
        return (objs.get(obj) or [{}])[0].get("properties", {}).get(name, default)
    except (AttributeError, IndexError):
        return default


def load_theme(report: Path) -> dict:
    rj = json.loads((report / "definition" / "report.json").read_text(encoding="utf-8-sig"))
    custom = (rj.get("themeCollection") or {}).get("customTheme")
    if custom:
        f = report / "StaticResources" / "RegisteredResources" / custom["name"]
        if f.exists():
            return json.loads(f.read_text(encoding="utf-8-sig"))
    return {}


def style(theme: dict, vtype: str, obj: str, key: str, default=None):
    vs = theme.get("visualStyles", {})
    for t in (vtype, "*"):
        for item in ((vs.get(t) or {}).get("*") or {}).get(obj, []):
            if key in item and item.get("$id", "default") == "default":
                v = item[key]
                return v.get("solid", {}).get("color", default) if isinstance(v, dict) else v
    return default


def render_visual(v: dict, theme: dict, page_names: list[str], current: str) -> str:
    pos = v.get("position", {})
    vis = v.get("visual", {}) or {}
    vtype = vis.get("visualType", "")
    objs = vis.get("objects", {}) or {}
    vco = vis.get("visualContainerObjects", {}) or {}
    ink = theme.get("foreground", "#252423")
    ink2 = theme.get("foregroundNeutralSecondary", "#605E5C")
    font = "'Segoe UI', 'Selawik', 'Inter', sans-serif"

    bg_show = lit(prop(vco, "background", "show"), style(theme, vtype, "background", "show", True))
    bg = color_of(prop(vco, "background", "color"), style(theme, vtype, "background", "color", "#FFFFFF"))
    bd_show = lit(prop(vco, "border", "show"), style(theme, vtype, "border", "show", False))
    bd = color_of(prop(vco, "border", "color"), style(theme, vtype, "border", "color", "#E1DFDD"))
    radius = lit(prop(vco, "border", "radius"), style(theme, vtype, "border", "radius", 0))
    radius = float(str(radius).rstrip("DL")) if radius not in (None, "") else 0
    css = [f"left:{pos.get('x', 0)}px", f"top:{pos.get('y', 0)}px", f"width:{pos.get('width', 0)}px",
           f"height:{pos.get('height', 0)}px", f"z-index:{int(pos.get('z', 0))}", f"border-radius:{radius}px"]
    if str(bg_show).lower() != "false":
        css.append(f"background:{bg}")
    if str(bd_show).lower() != "false":
        css.append(f"box-shadow:inset 0 0 0 1px {bd}")
    inner = ""

    title_show = lit(prop(vco, "title", "show"), style(theme, vtype, "title", "show", False))
    title_text = lit(prop(vco, "title", "text"))
    if title_text is None and isinstance(prop(vco, "title", "text"), dict):
        title_text = prop(vco, "title", "text")["expr"].get("Measure", {}).get("Property", "title") + " (título dinâmico)"
    title_size = style(theme, vtype, "title", "fontSize", 10)
    title_ink = style(theme, vtype, "title", "fontColor", ink)
    title_font = style(theme, vtype, "title", "fontFamily", "Segoe UI")
    weight = 600 if "Semibold" in str(title_font) else 400
    title = ""
    if str(title_show).lower() != "false" and title_text:
        title = (f'<div style="font:{weight} {title_size * PT:.1f}px {font};color:{title_ink};'
                 f'padding:10px 12px 0">{html.escape(str(title_text))}</div>')

    if vtype == "textbox":
        for para in prop(objs, "general", "paragraphs", []) or []:
            runs = []
            for r in para.get("textRuns", []):
                st = r.get("textStyle", {})
                size = float(str(st.get("fontSize", "10pt")).rstrip("pt"))
                w = 600 if "Semibold" in st.get("fontFamily", "") or st.get("fontWeight") == "bold" else 400
                runs.append(f'<span style="font:{w} {size * PT:.1f}px {font};color:{st.get("color", ink)};'
                            f'white-space:pre">{html.escape(r.get("value", ""))}</span>')
            inner += f'<div style="padding:2px 4px">{"".join(runs)}</div>'
    elif vtype == "shape":
        fill = color_of(prop(objs, "fill", "fillColor"), "#FFFFFF")
        rounded = lit(prop(objs, "shape", "tileShape")) == "rectangleRounded"
        if str(bg_show).lower() == "false" or "background" not in vco:
            css.append(f"background:{fill}")
        if rounded:
            css.append("border-radius:4px")
    elif vtype == "pageNavigator":
        size = style(theme, "pageNavigator", "text", "fontSize", 10) * PT
        gap = style(theme, "pageNavigator", "layout", "cellPadding", 2)
        rows = []
        for name in page_names:
            sel = name == current
            fill = "#E3E3E3" if sel else "transparent"
            w = 600 if sel else 400
            rows.append(f'<div style="height:28px;margin-bottom:{gap}px;border-radius:8px;background:{fill};'
                        f'font:{w} {size:.1f}px {font};color:{ink if sel else ink2};display:flex;'
                        f'align-items:center;padding-left:8px">{html.escape(name)}</div>')
        inner = "".join(rows)
    elif vtype == "card":
        size = lit(prop(objs, "labels", "fontSize"), style(theme, "card", "labels", "fontSize", 20))
        size = float(str(size).rstrip("DL"))
        ink_v = color_of(prop(objs, "labels", "color"), style(theme, "card", "labels", "color", ink))
        fam = lit(prop(objs, "labels", "fontFamily"), style(theme, "card", "labels", "fontFamily", "Segoe UI"))
        wt = 600 if "Semibold" in str(fam) else 400
        sample = ("Atualizado em 21/11/2026 08:00" if size < 12 else
                  f'<span style="display:inline-block;width:56%;height:{size * PT * 0.8:.0f}px;'
                  f'background:#EBEBEB;border-radius:4px"></span>')
        align = "flex-end" if size < 12 else "flex-start"
        pad = "0" if size < 12 else "6px 12px"
        inner = (title + f'<div style="font:{wt} {size * PT:.1f}px {font};color:{ink_v};padding:{pad};'
                 f'display:flex;justify-content:{align};height:100%;align-items:center">{sample}</div>'
                 if size < 12 else title + f'<div style="font:{wt} {size * PT:.1f}px {font};color:{ink_v};'
                 f'padding:{pad}">{sample}</div>')
    elif vtype == "slicer":
        header = style(theme, "slicer", "header", "textSize", 9) * PT
        hink = style(theme, "slicer", "header", "fontColor", ink2)
        field = (vis.get("query", {}).get("queryState", {}).get("Values", {}).get("projections") or [{}])[0]
        label = field.get("nativeQueryRef", "Filtro")
        inner = (f'<div style="padding:4px 8px;font:400 {header:.1f}px {font};color:{hink}">{label}</div>'
                 f'<div style="margin:0 8px;font:400 {9 * PT:.1f}px {font};color:{ink};display:flex;'
                 f'justify-content:space-between">Todos<span style="color:{ink2}">&#8964;</span></div>')
    elif vtype in ("tableEx", "pivotTable"):
        cols = [p.get("nativeQueryRef", "") for p in
                (vis.get("query", {}).get("queryState", {}).get("Values", {}).get("projections") or [])]
        size = 9 * PT
        head = "".join(f'<th style="text-align:left;font-weight:600;color:{ink2};padding:6px 8px">{html.escape(c)}</th>'
                       for c in cols)
        body = "".join("<tr>" + "".join(f'<td style="padding:6px 8px;color:{ink};border-top:1px solid #F1F1F1">'
                                         f'<span style="display:inline-block;width:{40 + (i * 17 + j * 29) % 45}%;'
                                         f'height:8px;background:#EBEBEB;border-radius:2px"></span></td>'
                                         for j, _ in enumerate(cols)) + "</tr>" for i in range(12))
        inner = (title + f'<table style="width:calc(100% - 8px);margin:6px 4px;border-collapse:collapse;'
                 f'font:400 {size:.1f}px {font}"><tr>{head}</tr>{body}</table>')
    elif vtype:
        colors = theme.get("dataColors", ["#3E63DD"])
        h = pos.get("height", 100) - 52
        if "Bar" in vtype:
            bars = "".join(f'<div style="height:{max(h / 7, 8):.0f}px;margin:6px 0;width:{90 - i * 13}%;'
                           f'background:{colors[0]};border-radius:2px"></div>' for i in range(5))
            inner = title + f'<div style="padding:8px 12px">{bars}</div>'
        elif "Column" in vtype:
            bars = "".join(f'<div style="flex:1;margin:0 6px;height:{[35, 60, 80, 50, 25][i]}%;'
                           f'background:{colors[0]};border-radius:2px 2px 0 0"></div>' for i in range(5))
            inner = title + (f'<div style="display:flex;align-items:flex-end;height:{h}px;'
                             f'padding:8px 12px 0">{bars}</div>')
        else:
            pts = " ".join(f"{i * 100 / 11:.1f},{60 - 25 * ((i * 7) % 5) / 4 - i * 2:.1f}" for i in range(12))
            inner = title + (f'<svg viewBox="0 0 100 70" preserveAspectRatio="none" style="width:100%;'
                             f'height:{h}px;padding:8px 12px"><polyline points="{pts}" fill="none" '
                             f'stroke="{colors[0]}" stroke-width="0.8" vector-effect="non-scaling-stroke"/></svg>')
    return f'<div class="v" style="{";".join(css)}">{inner}</div>'


def render(report: Path) -> str:
    theme = load_theme(report)
    pages_dir = report / "definition" / "pages"
    meta = json.loads((pages_dir / "pages.json").read_text(encoding="utf-8-sig"))
    order = meta.get("pageOrder") or sorted(p.name for p in pages_dir.iterdir() if p.is_dir())
    pages = [json.loads((pages_dir / pid / "page.json").read_text(encoding="utf-8-sig")) for pid in order]
    names = [p.get("displayName", p["name"]) for p in pages]
    page_bg = style(theme, "page", "background", "color", "#FFFFFF")
    out = []
    for pid, p in zip(order, pages):
        visuals = [json.loads(f.read_text(encoding="utf-8-sig"))
                   for f in sorted((pages_dir / pid / "visuals").glob("*/visual.json"))]
        body = "".join(render_visual(v, theme, names, p.get("displayName", "")) for v in visuals)
        out.append(f'<h2>{html.escape(p.get("displayName", pid))}</h2><div class="page" style="width:'
                   f'{p.get("width", 1280)}px;height:{p.get("height", 720)}px;background:{page_bg}">{body}</div>')
    return ("<!doctype html><meta charset='utf-8'><title>PBIR preview</title><style>"
            "body{margin:24px;background:#DADADA;font-family:'Segoe UI',sans-serif}"
            "h2{font:600 14px 'Segoe UI',sans-serif;color:#333;margin:24px 0 8px}"
            ".page{position:relative;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.15)}"
            ".v{position:absolute;box-sizing:border-box;overflow:hidden}</style>" + "".join(out))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("report", type=Path, help="the <Name>.Report folder")
    ap.add_argument("--out", type=Path, default=Path("preview.html"))
    args = ap.parse_args()
    args.out.write_text(render(args.report), encoding="utf-8")
    print(f"[ok] {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
