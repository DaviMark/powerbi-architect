"""Generate examples/contas-a-receber (synthetic PBIP project). Run from the repository root:

    python tools/generate_example.py

The example is committed; rerun only after changing this script, then run the tests and
tools/validate_schemas.py.
"""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path("examples/contas-a-receber")
NAME = "ContasReceber"
SM = ROOT / f"{NAME}.SemanticModel"
RP = ROOT / f"{NAME}.Report"
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric"


def hid(*parts: str) -> str:
    return hashlib.sha1("/".join(parts).encode()).hexdigest()[:20]


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def wjson(path: Path, obj) -> None:
    write(path, json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


if ROOT.exists():
    for p in (SM, RP, ROOT / f"{NAME}.pbip"):
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()

# ----------------------------------------------------------------------------- project files
wjson(ROOT / f"{NAME}.pbip", {
    "$schema": f"{SCHEMA}/pbip/pbipProperties/1.0.0/schema.json",
    "version": "1.0",
    "artifacts": [{"report": {"path": f"{NAME}.Report"}}],
    "settings": {"enableAutoRecovery": True},
})
wjson(SM / "definition.pbism", {
    "$schema": f"{SCHEMA}/item/semanticModel/definitionProperties/1.0.0/schema.json",
    "version": "4.0",
    "settings": {},
})
wjson(RP / "definition.pbir", {
    "$schema": f"{SCHEMA}/item/report/definitionProperties/2.0.0/schema.json",
    "version": "4.0",
    "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}},
})

# ----------------------------------------------------------------------------- semantic model (TMDL)
D = SM / "definition"
write(D / "database.tmdl", "database\n\tcompatibilityLevel: 1601\n")
write(D / "model.tmdl", """model Model
\tculture: pt-BR
\tdefaultPowerBIDataSourceVersion: powerBI_V3
\tdiscourageImplicitMeasures
\tsourceQueryCulture: pt-BR
\tdataAccessOptions
\t\tlegacyRedirects
\t\treturnErrorValuesAsNull

queryGroup Parametros

\tannotation PBI_QueryGroupOrder = 0

annotation __PBI_TimeIntelligenceEnabled = 0
""")
write(D / "expressions.tmdl", """/// Servidor SQL Server do data warehouse (troque pelo seu ao abrir o exemplo).
expression Servidor = "localhost" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
\tqueryGroup: Parametros

\tannotation PBI_ResultType = Text

/// Banco de dados do data warehouse.
expression Banco = "dw_exemplo" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
\tqueryGroup: Parametros

\tannotation PBI_ResultType = Text
""")


def col(name, dtype, *, hidden=False, fmt=None, sort_by=None, key=False, inferred=False, source=None):
    q = f"'{name}'" if any(ch in name for ch in " -%º") else name
    lines = [f"\tcolumn {q}", f"\t\tdataType: {dtype}"]
    if key:
        lines.append("\t\tisKey")
    if hidden:
        lines.append("\t\tisHidden")
    if fmt:
        lines.append(f"\t\tformatString: {fmt}")
    lines.append("\t\tsummarizeBy: none")
    if inferred:
        lines += ["\t\tisNameInferred", "\t\tisDataTypeInferred", f"\t\tsourceColumn: [{name}]"]
    else:
        lines.append(f"\t\tsourceColumn: {source or name}")
    if sort_by:
        lines.append(f"\t\tsortByColumn: '{sort_by}'")
    return "\n".join(lines) + "\n"


def sql_partition(table, sql):
    body = sql.replace('"', '""')
    return (f"\tpartition {table} = m\n\t\tmode: import\n\t\tsource =\n"
            f"\t\t\t\tlet\n"
            f"\t\t\t\t    Fonte = Value.NativeQuery(Sql.Database(Servidor, Banco), \"{body}\", null, [EnableFolding = true])\n"
            f"\t\t\t\tin\n\t\t\t\t    Fonte\n")


write(D / "tables" / "ft_titulos.tmdl",
      "/// Parcelas de títulos a receber em aberto ou pagas nos últimos 24 meses.\n"
      "/// Grão: 1 linha por parcela · Fonte: dw.fato_titulos_receber · Conexão: dw\n"
      "table ft_titulos\n\n"
      + col("id_cliente", "int64", hidden=True) + "\n"
      + col("id_regional", "int64", hidden=True) + "\n"
      + col("Data Vencimento", "dateTime", hidden=True, fmt="dd/mm/yyyy") + "\n"
      + col("Valor Aberto", "decimal", hidden=True, fmt=r"\R\$ #,0.00") + "\n"
      + "\t/// Dias entre o vencimento e a data da carga; 0 quando ainda não venceu.\n"
      + col("Dias Atraso", "int64", hidden=True, fmt="#,0") + "\n"
      + "\t/// Faixa de atraso: A vencer, 1-30, 31-60, 61-90, 90+.\n"
      + col("Faixa Atraso", "string", sort_by="Faixa Atraso Ordem") + "\n"
      + col("Faixa Atraso Ordem", "int64", hidden=True) + "\n"
      + sql_partition("ft_titulos",
                      "SELECT t.id_cliente, t.id_regional, t.data_vencimento AS [Data Vencimento], "
                      "t.valor_aberto AS [Valor Aberto], t.dias_atraso AS [Dias Atraso], "
                      "t.faixa_atraso AS [Faixa Atraso], t.faixa_atraso_ordem AS [Faixa Atraso Ordem] "
                      "FROM dw.fato_titulos_receber AS t WHERE t.valor_aberto > 0"))

write(D / "tables" / "dm_cliente.tmdl",
      "/// Clientes com título a receber.\n"
      "/// Grão: 1 linha por cliente · Fonte: dw.dim_cliente · Conexão: dw\n"
      "table dm_cliente\n\n"
      + col("id_cliente", "int64", hidden=True, key=True) + "\n"
      + col("Cliente", "string") + "\n"
      + col("Segmento", "string") + "\n"
      + sql_partition("dm_cliente",
                      "SELECT c.id_cliente, c.nome_fantasia AS Cliente, c.segmento AS Segmento FROM dw.dim_cliente AS c"))

write(D / "tables" / "dm_regional.tmdl",
      "/// Regionais de venda e o e-mail do gestor (usado na segurança por linha).\n"
      "/// Grão: 1 linha por regional · Fonte: dw.dim_regional · Conexão: dw\n"
      "table dm_regional\n\n"
      + col("id_regional", "int64", hidden=True, key=True) + "\n"
      + col("Regional", "string") + "\n"
      + col("Email Gestor", "string", hidden=True) + "\n"
      + sql_partition("dm_regional",
                      "SELECT r.id_regional, r.nome AS Regional, r.email_gestor AS [Email Gestor] FROM dw.dim_regional AS r"))

write(D / "tables" / "dm_calendario.tmdl",
      "/// Calendário de 24 meses até o fim do ano corrente. Marcado como tabela de datas.\n"
      "table dm_calendario\n\tdataCategory: Time\n\n"
      + col("Data", "dateTime", key=True, fmt="dd/mm/yyyy", inferred=True) + "\n"
      + col("Ano", "int64", fmt="0", inferred=True) + "\n"
      + col("Mês Nº", "int64", hidden=True, inferred=True) + "\n"
      + col("Mês", "string", sort_by="Mês Nº", inferred=True) + "\n"
      + col("Ano-Mês Nº", "int64", hidden=True, inferred=True) + "\n"
      + col("Ano-Mês", "string", sort_by="Ano-Mês Nº", inferred=True) + "\n"
      + "\thierarchy 'Ano > Mês'\n\n\t\tlevel Ano\n\t\t\tcolumn: Ano\n\n\t\tlevel Mês\n\t\t\tcolumn: Mês\n\n"
      + "\tpartition dm_calendario = calculated\n\t\tmode: import\n\t\tsource =\n"
      + "\t\t\t\tVAR _fim = DATE ( YEAR ( TODAY () ), 12, 31 )\n"
      + "\t\t\t\tVAR _inicio = DATE ( YEAR ( TODAY () ) - 1, 1, 1 )\n"
      + "\t\t\t\tRETURN\n"
      + "\t\t\t\t    ADDCOLUMNS (\n"
      + "\t\t\t\t        CALENDAR ( _inicio, _fim ),\n"
      + "\t\t\t\t        \"Ano\", YEAR ( [Date] ),\n"
      + "\t\t\t\t        \"Mês Nº\", MONTH ( [Date] ),\n"
      + "\t\t\t\t        \"Mês\", FORMAT ( [Date], \"mmm\" ),\n"
      + "\t\t\t\t        \"Ano-Mês Nº\", YEAR ( [Date] ) * 100 + MONTH ( [Date] ),\n"
      + "\t\t\t\t        \"Ano-Mês\", FORMAT ( [Date], \"mmm/yy\" ),\n"
      + "\t\t\t\t        \"Data\", [Date]\n"
      + "\t\t\t\t    )\n")

MEASURES = [
    ("Valor Aberto", "Saldo em aberto das parcelas, vencidas ou a vencer.",
     "SUM ( ft_titulos[Valor Aberto] )", r"\R\$ #,0", "Valores"),
    ("Valor Vencido", "Saldo em aberto das parcelas com vencimento anterior à data da carga.",
     "CALCULATE ( [Valor Aberto], ft_titulos[Dias Atraso] > 0 )", r"\R\$ #,0", "Valores"),
    ("% Vencido", "Parcela do saldo em aberto que já venceu.",
     "DIVIDE ( [Valor Vencido], [Valor Aberto] )", "0.0%", "Indicadores"),
    ("Dias Atraso Medio", "Média de dias de atraso das parcelas vencidas, ponderada pelo saldo em aberto.",
     "DIVIDE (\n\t\t\tSUMX (\n\t\t\t\tFILTER ( ft_titulos, ft_titulos[Dias Atraso] > 0 ),\n"
     "\t\t\t\tft_titulos[Dias Atraso] * ft_titulos[Valor Aberto]\n\t\t\t),\n\t\t\t[Valor Vencido]\n\t\t)",
     "#,0", "Indicadores"),
    ("Texto Atualizacao", "Data e hora da última carga, para a barra do topo.",
     "\"Atualizado em \" & FORMAT ( MAX ( '_Medidas'[Data Carga] ), \"dd/mm/yyyy hh:nn\" )", None, "Títulos"),
    ("Titulo Vencido", "Título dinâmico da página Visão Geral: valor vencido e participação no saldo.",
     "\"Vencido: \" & FORMAT ( [Valor Vencido], \"R$ #,0\" ) & \" (\" & FORMAT ( [% Vencido], \"0.0%\" ) & \" do saldo)\"",
     None, "Títulos"),
]


def measure_block(name, desc, expr, fmt, folder):
    q = f"'{name}'" if any(ch in name for ch in " -%") else name
    if "\n" in expr:
        head = f"\tmeasure {q} =\n\t\t\t" + expr.replace("\n\t\t", "\n\t\t\t")
    else:
        head = f"\tmeasure {q} = {expr}"
    lines = [f"\t/// {desc}", head]
    if fmt:
        lines.append(f"\t\tformatString: {fmt}")
    lines.append(f"\t\tdisplayFolder: {folder}")
    return "\n".join(lines) + "\n"


write(D / "tables" / "_Medidas.tmdl",
      "/// Medidas do relatório e data da última carga.\n"
      "table _Medidas\n\n"
      + "\n".join(measure_block(*m) for m in MEASURES) + "\n"
      + col("Data Carga", "dateTime", hidden=True, fmt="dd/mm/yyyy hh:nn", inferred=True) + "\n"
      + "\tpartition _Medidas = calculated\n\t\tmode: import\n\t\tsource = ROW ( \"Data Carga\", UTCNOW () - 3 / 24 )\n")

write(D / "tables" / "_Documentacao.tmdl",
      "/// Catálogo das medidas visíveis, gerado a partir das descrições do modelo.\n"
      "table _Documentacao\n\n"
      + "".join(col(c, "string", inferred=True) + "\n" for c in
                ("Tabela", "Pasta", "Medida", "Descrição", "Expressão DAX", "Formato"))
      + "\tpartition _Documentacao = calculated\n\t\tmode: import\n\t\tsource =\n"
      + "\t\t\t\tSELECTCOLUMNS (\n"
      + "\t\t\t\t    FILTER ( INFO.VIEW.MEASURES (), NOT [IsHidden] ),\n"
      + "\t\t\t\t    \"Tabela\", [Table],\n\t\t\t\t    \"Pasta\", [DisplayFolder],\n"
      + "\t\t\t\t    \"Medida\", [Name],\n\t\t\t\t    \"Descrição\", [Description],\n"
      + "\t\t\t\t    \"Expressão DAX\", [Expression],\n\t\t\t\t    \"Formato\", [FormatString]\n"
      + "\t\t\t\t)\n")

write(D / "tables" / "_Cargas.tmdl",
      "/// Tabelas carregadas das fontes e a data da última carga.\n"
      "table _Cargas\n\n"
      + "".join(col(c, "string", inferred=True) + "\n" for c in ("Tabela", "Descrição", "Armazenamento"))
      + col("Última Carga", "dateTime", fmt="dd/mm/yyyy hh:nn", inferred=True) + "\n"
      + "\tpartition _Cargas = calculated\n\t\tmode: import\n\t\tsource =\n"
      + "\t\t\t\tVAR _carga = MAX ( '_Medidas'[Data Carga] )\n"
      + "\t\t\t\tRETURN\n"
      + "\t\t\t\t    ADDCOLUMNS (\n"
      + "\t\t\t\t        SELECTCOLUMNS (\n"
      + "\t\t\t\t            FILTER ( INFO.VIEW.TABLES (), ISBLANK ( [Expression] ) && LEFT ( [Name], 1 ) <> \"_\" ),\n"
      + "\t\t\t\t            \"Tabela\", [Name], \"Descrição\", [Description], \"Armazenamento\", [StorageMode]\n"
      + "\t\t\t\t        ),\n"
      + "\t\t\t\t        \"Última Carga\", _carga\n"
      + "\t\t\t\t    )\n")

write(D / "relationships.tmdl", "".join(
    f"relationship {hid('rel', f, t)}\n\tfromColumn: {f}\n\ttoColumn: {t}\n\n" for f, t in (
        ("ft_titulos.id_cliente", "dm_cliente.id_cliente"),
        ("ft_titulos.id_regional", "dm_regional.id_regional"),
        ("ft_titulos.'Data Vencimento'", "dm_calendario.Data"),
    )).rstrip("\n") + "\n")

write(D / "roles" / "Gestor Regional.tmdl",
      "/// Cada gestor vê apenas a própria regional.\n"
      "role 'Gestor Regional'\n\tmodelPermission: read\n\n"
      "\ttablePermission dm_regional = dm_regional[Email Gestor] = USERPRINCIPALNAME ()\n")

# ----------------------------------------------------------------------------- report (PBIR)
R = RP / "definition"
wjson(R / "version.json", {"$schema": f"{SCHEMA}/item/report/definition/versionMetadata/1.0.0/schema.json",
                           "version": "2.0.0"})
theme_src = Path("skills/powerbi-architect/templates/theme/powerbi-architect-acessivel.json")
theme_name = theme_src.name
(RP / "StaticResources" / "RegisteredResources").mkdir(parents=True, exist_ok=True)
shutil.copyfile(theme_src, RP / "StaticResources" / "RegisteredResources" / theme_name)
wjson(R / "report.json", {
    "$schema": f"{SCHEMA}/item/report/definition/report/1.0.0/schema.json",
    "themeCollection": {"customTheme": {"name": theme_name, "reportVersionAtImport": "5.59",
                                        "type": "RegisteredResources"}},
    "layoutOptimization": "None",
    "resourcePackages": [{"name": "RegisteredResources", "type": "RegisteredResources",
                          "items": [{"name": theme_name, "path": theme_name, "type": "CustomTheme"}]}],
    "settings": {"useStylableVisualContainerHeader": True, "exportDataMode": "AllowSummarized",
                 "defaultDrillFilterOtherVisuals": True, "allowChangeFilterTypes": True,
                 "useEnhancedTooltips": True},
})


# ----------------------------------------------------------------------------- report helpers
INK, INK2, INK3, LINE, ACCENT = "#333333", "#666666", "#757575", "#EBEBEB", "#3E63DD"


def lit(v: str):
    return {"expr": {"Literal": {"Value": v}}}


def color(hex_):
    return {"solid": {"color": lit(f"'{hex_}'")}}


def field(kind, entity, prop):
    return {kind: {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}


def proj(kind, entity, prop):
    return {"field": field(kind, entity, prop), "queryRef": f"{entity}.{prop}", "nativeQueryRef": prop}


def container(vid, x, y, w, h, z, visual):
    return {"$schema": f"{SCHEMA}/item/report/definition/visualContainer/1.1.0/schema.json",
            "name": vid, "position": {"x": x, "y": y, "z": z, "width": w, "height": h, "tabOrder": z},
            "visual": visual}


def text_run(value, size, ink, semibold=False):
    return {"value": value, "textStyle": {"fontFamily": "Segoe UI Semibold" if semibold else "Segoe UI",
                                          "fontSize": f"{size}pt", "color": ink}}


def textbox(*runs):
    return {"visualType": "textbox",
            "objects": {"general": [{"properties": {"paragraphs": [{"textRuns": list(runs)}]}}]},
            "drillFilterOtherVisuals": True}


def shape(fill, *, panel=False, rounded=False):
    v = {"visualType": "shape",
         "objects": {"shape": [{"properties": {"tileShape": lit("'rectangleRounded'" if rounded else "'rectangle'")}}],
                     "fill": [{"properties": {"show": lit("true"), "fillColor": color(fill)}}],
                     "outline": [{"properties": {"show": lit("false")}}]},
         "drillFilterOtherVisuals": True}
    if panel:   # the white content panel: background and hairline border on the container, radius 8
        v["visualContainerObjects"] = {
            "background": [{"properties": {"show": lit("true"), "color": color("#FFFFFF")}}],
            "border": [{"properties": {"show": lit("true"), "color": color(LINE), "radius": lit("8D")}}]}
    return v


def data_visual(vtype, roles, alt, title=None, title_measure=None, sort=None, objects=None, chrome=True):
    v = {"visualType": vtype, "query": {"queryState": roles}}
    if sort:
        v["query"]["sortDefinition"] = {"sort": [{"field": field(*sort[0]), "direction": sort[1]}],
                                        "isDefaultSort": True}
    vco = {"general": [{"properties": {"altText": lit(f"'{alt}'")}}]}
    if title_measure:
        vco["title"] = [{"properties": {"show": lit("true"), "text": {"expr": field("Measure", "_Medidas", title_measure)}}}]
    elif title:
        vco["title"] = [{"properties": {"show": lit("true"), "text": lit(f"'{title}'")}}]
    if not chrome:  # sits directly on the top bar: no card around it
        vco["title"] = [{"properties": {"show": lit("false")}}]
        vco["background"] = [{"properties": {"show": lit("false")}}]
        vco["border"] = [{"properties": {"show": lit("false")}}]
    v["visualContainerObjects"] = vco
    if objects:
        v["objects"] = objects
    v["drillFilterOtherVisuals"] = True
    return v


# ----------------------------------------------------------------------------- shell (Twenty-style)
# Canvas 1280x720, 4 px grid. Sidebar 220 on the grey canvas; white panel x 220..1268, y 12..708 (12 px
# margins = Twenty spacing 3); top bar 56 px (y 12..68, content centred on y 40) inside the panel; content x 232..1256 (1024), y 80..696 (616).
M = "_Medidas"
APP = "Contas a receber"
pages = []


def shell(display, with_slicer):
    items = [
        ("painel", (220, 12, 1048, 696), shape("#FFFFFF", panel=True)),
        ("logo", (16, 20, 16, 16), shape(ACCENT, rounded=True)),
        ("app", (40, 16, 172, 24), textbox(text_run(APP, 10, INK, semibold=True))),
        ("secao", (8, 52, 204, 24), textbox(text_run("Páginas", 9, INK3))),
        ("navegacao", (8, 76, 204, 88), {"visualType": "pageNavigator", "drillFilterOtherVisuals": True}),
        ("caminho", (232, 28, 520, 24), textbox(text_run(f"{APP}  /  ", 12, INK3),
                                                 text_run(display, 12, INK, semibold=True))),
        ("linha", (220, 68, 1048, 1), shape(LINE)),
        ("atualizado", (864 if with_slicer else 1056, 28, 200, 24), data_visual(
            "card", {"Values": {"projections": [proj("Measure", M, "Texto Atualizacao")]}},
            "Data e hora da última carga", chrome=False,
            objects={"labels": [{"properties": {"fontSize": lit("9D"), "color": color(INK3),
                                                "fontFamily": lit("'Segoe UI'")}}]})),
    ]
    if with_slicer:
        items.append(("segmento", (1080, 20, 176, 40), data_visual(
            "slicer", {"Values": {"projections": [proj("Column", "dm_cliente", "Segmento")]}},
            "Filtro de segmento de cliente",
            objects={"data": [{"properties": {"mode": lit("'Dropdown'")}}]})))
    return items


def page(display, content, with_slicer=True):
    pid = hid("page", display)
    pages.append(pid)
    wjson(R / "pages" / pid / "page.json", {
        "$schema": f"{SCHEMA}/item/report/definition/page/1.1.0/schema.json",
        "name": pid, "displayName": display, "displayOption": "FitToPage", "height": 720, "width": 1280})
    for i, (key, pos, visual) in enumerate(shell(display, with_slicer) + content):
        vid = hid("visual", display, key)
        wjson(R / "pages" / pid / "visuals" / vid / "visual.json", container(vid, *pos, i * 1000, visual))


cards = [("Valor Aberto", "Saldo em aberto"), ("Valor Vencido", "Vencido"),
         ("% Vencido", "% do saldo vencido"), ("Dias Atraso Medio", "Dias de atraso, média ponderada")]
page("Visão Geral", [
    *[(f"card-{m}", (232 + i * 260, 80, 244, 88), data_visual(
        "card", {"Values": {"projections": [proj("Measure", M, m)]}}, f"{t}, na data da carga", title=t))
      for i, (m, t) in enumerate(cards)],
    ("tendencia", (232, 184, 672, 248), data_visual(
        "lineChart", {"Category": {"projections": [proj("Column", "dm_calendario", "Ano-Mês")]},
                      "Y": {"projections": [proj("Measure", M, "Valor Vencido")]}},
        "Valor vencido por mês de vencimento, últimos 24 meses", title_measure="Titulo Vencido",
        sort=(("Column", "dm_calendario", "Ano-Mês"), "Ascending"))),
    ("faixa", (920, 184, 336, 248), data_visual(
        "clusteredColumnChart", {"Category": {"projections": [proj("Column", "ft_titulos", "Faixa Atraso")]},
                                 "Y": {"projections": [proj("Measure", M, "Valor Vencido")]}},
        "Valor vencido por faixa de atraso, em reais", title="Vencido por faixa de atraso",
        sort=(("Column", "ft_titulos", "Faixa Atraso"), "Ascending"))),
    ("regional", (232, 448, 1024, 248), data_visual(
        "clusteredBarChart", {"Category": {"projections": [proj("Column", "dm_regional", "Regional")]},
                              "Y": {"projections": [proj("Measure", M, "Valor Vencido")]}},
        "Valor vencido por regional, do maior para o menor", title="Vencido por regional",
        sort=(("Measure", M, "Valor Vencido"), "Descending"))),
])
page("Clientes", [
    ("tabela", (232, 80, 1024, 616), data_visual(
        "tableEx", {"Values": {"projections": [
            proj("Column", "dm_cliente", "Cliente"), proj("Column", "dm_cliente", "Segmento"),
            proj("Measure", M, "Valor Vencido"), proj("Measure", M, "% Vencido"),
            proj("Measure", M, "Dias Atraso Medio")]}},
        "Tabela de clientes ordenada pelo valor vencido", title="Clientes que concentram o valor vencido",
        sort=(("Measure", M, "Valor Vencido"), "Descending"))),
])
page("Documentação", [
    ("medidas", (232, 80, 608, 616), data_visual(
        "tableEx", {"Values": {"projections": [proj("Column", "_Documentacao", c) for c in
                                               ("Pasta", "Medida", "Descrição", "Expressão DAX")]}},
        "Catálogo de medidas com pasta, descrição e expressão DAX", title="Medidas")),
    ("cargas", (856, 80, 400, 616), data_visual(
        "tableEx", {"Values": {"projections": [proj("Column", "_Cargas", c) for c in
                                               ("Tabela", "Descrição", "Armazenamento", "Última Carga")]}},
        "Tabelas carregadas e data da última carga", title="Cargas")),
], with_slicer=False)
wjson(R / "pages" / "pages.json", {
    "$schema": f"{SCHEMA}/item/report/definition/pagesMetadata/1.0.0/schema.json",
    "pageOrder": pages, "activePageName": pages[0]})
print("ok", sum(1 for _ in ROOT.rglob("*") if _.is_file()), "files")
