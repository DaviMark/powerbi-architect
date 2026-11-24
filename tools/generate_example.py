"""Generate examples/contas-a-receber (synthetic PBIP project). Run from the repository root:

    python tools/generate_example.py

The example is committed; rerun only after changing this script, then run the tests and
tools/validate_schemas.py.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path("examples/contas-a-receber")
NAME = "ContasReceber"
SM = ROOT / f"{NAME}.SemanticModel"
RP = ROOT / f"{NAME}.Report"
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric"



def write_lf(path: Path, text: str) -> None:
    """UTF-8 with LF line endings on every OS (write_text has no newline= before Python 3.10)."""
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)

def hid(*parts: str) -> str:
    return hashlib.sha1("/".join(parts).encode()).hexdigest()[:20]


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_lf(path, text)


def wjson(path: Path, obj) -> None:
    write(path, json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


if ROOT.exists():
    for p in (SM, RP, ROOT / f"{NAME}.pbip", ROOT / ".powerbi-architect"):
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
      "/// Calendário de 1º de janeiro de dois anos atrás até o fim do ano corrente: cobre os 24 meses das tabelas fato. Marcado como tabela de datas.\n"
      "table dm_calendario\n\tdataCategory: Time\n\n"
      + col("Data", "dateTime", key=True, fmt="dd/mm/yyyy", inferred=True) + "\n"
      + col("Ano", "int64", fmt="0", inferred=True) + "\n"
      + col("Mês Nº", "int64", hidden=True, inferred=True) + "\n"
      + col("Mês", "string", sort_by="Mês Nº", inferred=True) + "\n"
      + col("Ano-Mês Nº", "int64", hidden=True, inferred=True) + "\n"
      + col("Ano-Mês", "string", sort_by="Ano-Mês Nº", inferred=True) + "\n"
      + col("Trimestre Nº", "int64", hidden=True, inferred=True) + "\n"
      + col("Ano-Trimestre", "string", sort_by="Trimestre Nº", inferred=True) + "\n"
      + "\thierarchy 'Ano > Mês'\n\n\t\tlevel Ano\n\t\t\tcolumn: Ano\n\n\t\tlevel Mês\n\t\t\tcolumn: Mês\n\n"
      + "\tpartition dm_calendario = calculated\n\t\tmode: import\n\t\tsource =\n"
      + "\t\t\t\tVAR _fim = DATE ( YEAR ( TODAY () ), 12, 31 )\n"
      + "\t\t\t\tVAR _inicio = DATE ( YEAR ( TODAY () ) - 2, 1, 1 )\n"
      + "\t\t\t\tRETURN\n"
      + "\t\t\t\t    ADDCOLUMNS (\n"
      + "\t\t\t\t        CALENDAR ( _inicio, _fim ),\n"
      + "\t\t\t\t        \"Ano\", YEAR ( [Date] ),\n"
      + "\t\t\t\t        \"Mês Nº\", MONTH ( [Date] ),\n"
      + "\t\t\t\t        \"Mês\", FORMAT ( [Date], \"mmm\" ),\n"
      + "\t\t\t\t        \"Ano-Mês Nº\", YEAR ( [Date] ) * 100 + MONTH ( [Date] ),\n"
      + "\t\t\t\t        \"Ano-Mês\", FORMAT ( [Date], \"mmm/yy\" ),\n"
      + "\t\t\t\t        \"Trimestre Nº\", YEAR ( [Date] ) * 10 + QUARTER ( [Date] ),\n"
      + "\t\t\t\t        \"Ano-Trimestre\", \"T\" & QUARTER ( [Date] ) & \"/\" & FORMAT ( [Date], \"yy\" ),\n"
      + "\t\t\t\t        \"Data\", [Date]\n"
      + "\t\t\t\t    )\n")

sys.path.insert(0, str(Path("skills/powerbi-architect/scripts").resolve()))
from new_project import GRANULARITY  # noqa: E402  (the field parameter behind the header's period tabs)
write(D / "tables" / "_Granularidade.tmdl", GRANULARITY)

MEASURES = [
    ("Valor Aberto", "Saldo em aberto das parcelas, vencidas ou a vencer.",
     "SUM ( ft_titulos[Valor Aberto] )", r"\R\$ #,0", "Valores"),
    ("Valor Vencido", "Saldo em aberto das parcelas com vencimento anterior à data da carga.",
     "CALCULATE ( [Valor Aberto], ft_titulos[Dias Atraso] > 0 )", r"\R\$ #,0", "Valores"),
    ("% Vencido", "Parcela do saldo em aberto que já venceu.",
     "DIVIDE ( [Valor Vencido], [Valor Aberto] )", "0.0%", "Indicadores"),
    ("Atraso Médio (dias)", "Média de dias de atraso das parcelas vencidas, ponderada pelo saldo em aberto.",
     "DIVIDE (\n\t\t\tSUMX (\n\t\t\t\tFILTER ( ft_titulos, ft_titulos[Dias Atraso] > 0 ),\n"
     "\t\t\t\tft_titulos[Dias Atraso] * ft_titulos[Valor Aberto]\n\t\t\t),\n\t\t\t[Valor Vencido]\n\t\t)",
     "#,0", "Indicadores"),
    ("Vencido Ano Anterior", "Valor vencido no mesmo período do ano anterior, para comparar na tendência.",
     "CALCULATE ( [Valor Vencido], SAMEPERIODLASTYEAR ( dm_calendario[Data] ) )", r"\R\$ #,0", "Valores"),
    ("Valor a Vencer", "Saldo em aberto das parcelas que ainda não venceram.",
     "[Valor Aberto] - [Valor Vencido]", r"\R\$ #,0", "Valores"),
    ("Clientes Vencidos", "Quantidade de clientes com pelo menos uma parcela vencida.",
     "CALCULATE ( DISTINCTCOUNT ( ft_titulos[id_cliente] ), ft_titulos[Dias Atraso] > 0 )", "#,0", "Indicadores"),
    ("Meta % Vencido", "Meta da diretoria para a parcela vencida do saldo.", "0.15", "0%", "Metas"),
    ("Meta Dias Atraso", "Meta da diretoria para o atraso médio, em dias.", "30", "#,0", "Metas"),
    ("Texto A Vencer", "Linha de contexto do KPI de saldo: quanto ainda não venceu.",
     "FORMAT ( [Valor a Vencer], \"R$ #,0\" ) & \" ainda a vencer\"", None, "Textos"),
    ("Texto Clientes Vencidos", "Linha de contexto do KPI de vencido: quantos clientes estão em atraso.",
     "FORMAT ( [Clientes Vencidos], \"#,0\" ) & \" clientes em atraso\"", None, "Textos"),
    ("Texto Var % Vencido", "Distância do % vencido para a meta, em pontos percentuais, com seta.",
     "VAR _d = [% Vencido] - [Meta % Vencido] RETURN IF ( ISBLANK ( [% Vencido] ), BLANK (), "
     "IF ( _d > 0, \"▲ \", \"▼ \" ) & FORMAT ( ABS ( _d ) * 100, \"0.0\" ) & \" p.p. \" & "
     "IF ( _d > 0, \"acima\", \"abaixo\" ) & \" da meta de \" & FORMAT ( [Meta % Vencido], \"0%\" ) )",
     None, "Textos"),
    ("Cor Var % Vencido", "Cor da linha de meta do % vencido: vermelho acima da meta, verde abaixo.",
     "IF ( [% Vencido] > [Meta % Vencido], \"#CE2C31\", \"#00824D\" )", None, "Cores"),
    ("Texto Var Dias Atraso", "Distância do atraso médio para a meta, em dias, com seta.",
     "VAR _d = [Atraso Médio (dias)] - [Meta Dias Atraso] RETURN IF ( ISBLANK ( [Atraso Médio (dias)] ), BLANK (), "
     "IF ( _d > 0, \"▲ \", \"▼ \" ) & FORMAT ( ABS ( _d ), \"#,0\" ) & \" dias \" & "
     "IF ( _d > 0, \"acima\", \"abaixo\" ) & \" da meta de \" & FORMAT ( [Meta Dias Atraso], \"#,0\" ) )",
     None, "Textos"),
    ("Cor Var Dias Atraso", "Cor da linha de meta do atraso médio: vermelho acima da meta, verde abaixo.",
     "IF ( [Atraso Médio (dias)] > [Meta Dias Atraso], \"#CE2C31\", \"#00824D\" )", None, "Cores"),
    ("Cor % Vencido", "Cor do % vencido em tabelas: vermelho quando passa da meta.",
     "IF ( [% Vencido] > [Meta % Vencido], \"#CE2C31\", \"#333333\" )", None, "Cores"),
    ("Texto Atualizacao", "Data e hora da última carga, para a barra do topo.",
     "\"Atualizado em \" & FORMAT ( MAX ( '_Medidas'[Data Carga] ), \"dd/mm/yyyy hh:nn\" )", None, "Títulos"),
    ("Titulo Vencido", "Título dinâmico da página Visão Geral: valor vencido e participação no saldo.",
     "\"Vencido: \" & FORMAT ( [Valor Vencido], \"R$ #,0\" ) & \" (\" & FORMAT ( [% Vencido], \"0.0%\" ) & \" do saldo)\"",
     None, "Títulos"),
    ("Situação", "Situação do cliente para listas de cobrança: Atrasado acima de 60 dias, Em risco acima de 30, "
     "Em dia sem parcela vencida.",
     "SWITCH ( TRUE (), ISBLANK ( [Valor Aberto] ), BLANK (), [Atraso Médio (dias)] > 60, \"Atrasado\", "
     "[Atraso Médio (dias)] > 30, \"Em risco\", [Valor Vencido] > 0, \"A vencer\", \"Em dia\" )", None, "Textos"),
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
# Pages come from layout.json through the skill's layout engine (scripts/pbir_layout.py).
import sys  # noqa: E402

sys.path.insert(0, str(Path("skills/powerbi-architect/scripts").resolve()))
import pbir_layout  # noqa: E402

R = RP / "definition"
wjson(R / "version.json", {"$schema": f"{SCHEMA}/item/report/definition/versionMetadata/1.0.0/schema.json",
                           "version": "2.0.0"})
if (R / "report.json").exists():
    (R / "report.json").unlink()
spec = json.loads((ROOT / "layout.json").read_text(encoding="utf-8"))
builder = pbir_layout.Builder(spec)
builder.build(RP)
builder.register_resources(RP, Path("skills/powerbi-architect/templates/theme/powerbi-architect-acessivel.json"))
print("ok", sum(1 for _ in ROOT.rglob("*") if _.is_file()), "files")
