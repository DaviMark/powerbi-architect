"""A deliberately messy PBIR report (no shell, odd sizes, a pie, no alt text) for restyle tests."""
import json
import shutil
from pathlib import Path

SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"


def _field(name: str):
    if "[" in name:
        ent, col = name[:-1].split("[", 1)
        return {"Column": {"Expression": {"SourceRef": {"Entity": ent}}, "Property": col}}
    return {"Measure": {"Expression": {"SourceRef": {"Entity": "_Medidas"}}, "Property": name}}


def _visual(vid, x, y, w, h, vtype, roles=None, title=None, objects=None):
    vis = {"visualType": vtype}
    if roles:
        vis["query"] = {"queryState": {r: {"projections": [{"field": _field(f), "queryRef": f} for f in fs]}
                                       for r, fs in roles.items()}}
    if title:
        vis["visualContainerObjects"] = {"title": [{"properties": {"text": {"expr": {"Literal": {"Value": f"'{title}'"}}}}}]}
    if objects:
        vis["objects"] = objects
    return {"$schema": f"{SCHEMA}/visualContainer/1.1.0/schema.json", "name": vid,
            "position": {"x": x, "y": y, "z": 0, "width": w, "height": h}, "visual": vis}


def make_legacy(example_report: Path, dest: Path) -> Path:
    """Copy the example report and replace its pages with one cluttered page."""
    shutil.copytree(example_report, dest)
    pages = dest / "definition" / "pages"
    shutil.rmtree(pages)
    pid = "legado"
    big = {"general": [{"properties": {"paragraphs": [{"textRuns": [{"value": "PAINEL DE COBRANÇA",
                                                                     "textStyle": {"fontSize": "28pt"}}]}]}}]}
    items = [
        _visual("titulo", 10, 5, 700, 60, "textbox", objects=big),
        _visual("k1", 10, 70, 310, 130, "card", {"Values": ["Valor Aberto"]}),
        _visual("k2", 325, 70, 310, 130, "card", {"Values": ["Valor Vencido"]}),
        _visual("k3", 640, 70, 310, 130, "card", {"Values": ["% Vencido"]}),
        _visual("k4", 955, 70, 315, 130, "card", {"Values": ["Atraso Médio (dias)"]}),
        _visual("pizza", 10, 210, 450, 290, "pieChart", {"Category": ["dm_regional[Regional]"], "Y": ["Valor Vencido"]},
                title="Valor Vencido por Regional"),
        _visual("linha", 470, 210, 800, 290, "lineChart", {"Category": ["dm_calendario[Ano-Mês]"], "Y": ["Valor Vencido"]},
                title="Valor Vencido por Ano-Mês"),
        _visual("filtro", 10, 510, 300, 200, "slicer", {"Values": ["dm_cliente[Segmento]"]}),
        _visual("tabela", 320, 510, 950, 200, "tableEx",
                {"Values": ["dm_cliente[Cliente]", "Valor Vencido", "% Vencido"]}, title="Clientes"),
    ]
    for v in items:
        d = pages / pid / "visuals" / v["name"]
        d.mkdir(parents=True)
        (d / "visual.json").write_text(json.dumps(v, ensure_ascii=False), encoding="utf-8")
    (pages / pid / "page.json").write_text(json.dumps({
        "$schema": f"{SCHEMA}/page/1.1.0/schema.json", "name": pid, "displayName": "Página 1",
        "displayOption": "FitToPage", "height": 720, "width": 1280}), encoding="utf-8")
    (pages / "pages.json").write_text(json.dumps({"$schema": f"{SCHEMA}/pagesMetadata/1.0.0/schema.json",
                                                  "pageOrder": [pid], "activePageName": pid}), encoding="utf-8")
    return dest
