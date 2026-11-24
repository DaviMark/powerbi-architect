# Regras da auditoria

O script `audit_pbip.py` verifica um projeto PBIP sem rede e sem alterar nada. Cada achado tem um código
`PBIxxx`, uma severidade e o princípio da skill a que se refere (seção 1 do `SKILL.md`). Quando existe uma
regra equivalente no Best Practice Analyzer (BPA) do Tabular Editor, o ID dela aparece na última coluna.

```bash
python skills/powerbi-architect/scripts/audit_pbip.py caminho/do/projeto            # texto
python skills/powerbi-architect/scripts/audit_pbip.py caminho/do/projeto --json     # JSON
python skills/powerbi-architect/scripts/audit_pbip.py caminho/do/projeto --sarif    # GitHub code scanning
python skills/powerbi-architect/scripts/audit_pbip.py --list-rules
```

O código de saída é 1 quando há achados na severidade de `--fail-on` ou acima (padrão: `blocker`);
use `--fail-on important` num pipeline mais rígido ou `--fail-on never` só para relatar.

## Regras

Os códigos `PBI044` e `PBI045` estão reservados para as regras propostas nas issues abertas.

| Código | Severidade | Princípio | O que verifica | Como corrigir | Regra do BPA |
|---|---|---|---|---|---|
| PBI001 | Bloqueador | governança | Arquivo de dados ou configuração local dentro do projeto | Remova `.pbix`, `.abf` e `localSettings.json` do repositório e coloque-os no `.gitignore`. | — |
| PBI002 | Bloqueador | governança | Nenhum modelo semântico em TMDL encontrado | Salve o projeto como PBIP com o formato TMDL ativado. | — |
| PBI003 | Bloqueador | 4 | Servidor ou banco fixo no Power Query | Use parâmetros (`Servidor`, `Banco`) no lugar de textos fixos. | — |
| PBI004 | Bloqueador | governança | JSON inválido na definição do relatório | Corrija o arquivo apontado; o Power BI Desktop não abre o relatório assim. | — |
| PBI005 | Bloqueador | 5 | Medida sem descrição | Escreva uma frase de negócio com `///` acima da medida. | `OBJECTS_WITH_NO_DESCRIPTION` |
| PBI006 | Bloqueador | 8 | Relatório sem página de Documentação | Crie a página Documentação com o catálogo de medidas e as cargas (`INFO.VIEW`). | — |
| PBI010 | Importante | 2 | Auto date/time ligado | Desligue em Opções e use uma única tabela de datas. | `REMOVE_AUTO-DATE_TABLE` |
| PBI011 | Importante | 2 | Nenhuma tabela marcada como tabela de datas | Marque a tabela de calendário como tabela de datas (`dataCategory: Time`). | `MODEL_SHOULD_HAVE_A_DATE_TABLE`, `DATE/CALENDAR_TABLES_SHOULD_BE_MARKED_AS_A_DATE_TABLE` |
| PBI012 | Importante | 4 | Mais de uma etapa no Power Query | Leve filtros, junções e conversões para o SQL; deixe uma etapa só. | `MINIMIZE_POWER_QUERY_TRANSFORMATIONS` |
| PBI013 | Importante | 4 | Transformações no Power Query | Faça a transformação no SQL ou na view de origem. | `MINIMIZE_POWER_QUERY_TRANSFORMATIONS` |
| PBI014 | Importante | 2 | Coluna calculada em tabela fato | Calcule a coluna na origem (SQL) ou troque por medida. | `REDUCE_NUMBER_OF_CALCULATED_COLUMNS`, `REDUCE_USAGE_OF_CALCULATED_COLUMNS_THAT_USE_THE_RELATED_FUNCTION` |
| PBI015 | Importante | 2 | Relacionamento bidirecional | Use direção única; se for mesmo necessário, registre a decisão (ADR). | `AVOID_EXCESSIVE_BI-DIRECTIONAL_OR_MANY-TO-MANY_RELATIONSHIPS`, `CHECK_IF_BI-DIRECTIONAL_AND_MANY-TO-MANY_RELATIONSHIPS_ARE_VALID` |
| PBI016 | Importante | 2 | Relacionamento muitos-para-muitos | Crie uma tabela ponte por desenho, ou corrija o grão das tabelas. | `AVOID_EXCESSIVE_BI-DIRECTIONAL_OR_MANY-TO-MANY_RELATIONSHIPS`, `CHECK_IF_BI-DIRECTIONAL_AND_MANY-TO-MANY_RELATIONSHIPS_ARE_VALID` |
| PBI017 | Importante | 2 | Inteligência de tempo sobre a hierarquia automática (`.[Date]`) | Use a coluna de data da tabela de calendário. | `REMOVE_AUTO-DATE_TABLE` |
| PBI018 | Importante | 6 | Página com mais de 8 visuais de dados | Divida a página: uma página, uma pergunta. | — |
| PBI019 | Importante | acessibilidade | Visual de dados sem texto alternativo | Preencha o texto alternativo descrevendo o que o visual mostra. | — |
| PBI020 | Importante | governança | Relatório no formato antigo (`report.json`) | Salve o relatório no formato PBIR. | — |
| PBI030 | Sugestão | 5 | Medida sem formato | Defina `formatString` (moeda, percentual, inteiro). | `PROVIDE_FORMAT_STRING_FOR_MEASURES` |
| PBI031 | Sugestão | 5 | Medida sem pasta | Defina `displayFolder` para organizar a lista de campos. | — |
| PBI032 | Sugestão | 5 | Divisão com `/` em vez de `DIVIDE` | Use `DIVIDE ( numerador, denominador )`, que trata zero e vazio. | `USE_THE_DIVIDE_FUNCTION_FOR_DIVISION` |
| PBI033 | Sugestão | 5 | `IFERROR` em medida | Trate o caso de erro de forma explícita (por exemplo com `DIVIDE` ou `IF`). | `AVOID_USING_THE_IFERROR_FUNCTION` |
| PBI034 | Sugestão | 3 | Coluna importada e nunca usada | Remova a coluna do `SELECT`: ela não aparece em medida, visual, relacionamento, ordenação, hierarquia ou RLS. | `UNNECESSARY_COLUMNS` |
| PBI035 | Sugestão | 2 | Coluna de ponto flutuante (`double`) | Use `decimal` para valores e `int64` para inteiros. | `AVOID_FLOATING_POINT_DATA_TYPES` |
| PBI036 | Sugestão | 2 | Chave estrangeira visível | Oculte as colunas de chave da tabela fato. | `HIDE_FOREIGN_KEYS` |
| PBI037 | Sugestão | 2 | Chave de relacionamento que não é inteira | Prefira uma chave substituta `int64` (relacionamentos com a tabela de datas são exceção). | `RELATIONSHIP_COLUMNS_SHOULD_BE_OF_INTEGER_DATA_TYPE` |
| PBI038 | Sugestão | 2 | Dimensão em floco de neve | Junte as dimensões encadeadas em uma só (esquema estrela). | `SNOWFLAKE_SCHEMA_ARCHITECTURE` |
| PBI039 | Sugestão | 3 | Mais de 12 tabelas de fonte | Confirme se todas respondem a alguma pergunta de negócio. | — |
| PBI040 | Sugestão | 7 | Gráfico de pizza ou rosca | Só com até 3 fatias; acima disso use barras ordenadas. | — |
| PBI041 | Sugestão | 7 | Visual customizado em uso | Registre o motivo em um ADR (árvore de decisão da skill). | — |
| PBI042 | Sugestão | 1 | Página com nome genérico | Dê à página o nome da pergunta que ela responde. | — |
| PBI043 | Sugestão | 8 | Projeto sem README.md | Crie o README ao lado do `.pbip` (o que é, como usar, cargas, métricas). | — |
| PBI046 | Importante | 6 | Slicer grande demais | Slicer suspenso (dropdown ou intervalo) até 240×48 px; em lista, até 320×320 px. Filtro é coadjuvante, não protagonista. | — |
| PBI047 | Importante | 6 | Fonte maior que a escala tipográfica | Caixas de texto até 14 pt, valor de KPI até 24 pt, todo o resto até 12 pt (escala em `references/report-design.md`). | — |
| PBI048 | Sugestão | 6 | Visual fora da grade de 4 px | Use posição e tamanho múltiplos de 4 px para que as bordas se alinhem. Linhas de 1 px são exceção. | — |
| PBI049 | Importante | 2 | Tabela sem o prefixo `ft_` (fato) ou `dm_` (dimensão) | Fatos começam com `ft_` e dimensões (inclusive a de datas) com `dm_`, em minúsculas e com `_`: `ft_vendas`, `dm_cliente`. Tabelas auxiliares começam com `_`. | — |
| PBI050 | Importante | 6 | Mais de 2 slicers na página | Deixe no máximo 2 na página; o resto vai para o painel de filtros. | — |
| PBI051 | Sugestão | 6 | Mais de uma família de fonte, ou fonte fora do padrão profissional | Uma família (Segoe UI, em dois pesos), a não ser que a identidade visual da empresa defina outra. Evite DIN, Comic Sans, Impact e similares. | — |
| PBI052 | Importante | 6 | Visual fora da página | Mantenha todo visual dentro da largura e da altura da página. | — |
| PBI053 | Sugestão | acessibilidade | Ordem do teclado diferente da ordem de leitura | Ajuste o `tabOrder` para seguir a leitura: de cima para baixo, da esquerda para a direita. | — |
| PBI054 | Importante | acessibilidade | Cor de texto com contraste abaixo de 4,5:1 sobre o branco | Escureça a cor do texto (ou da medida de cor) até 4,5:1. | — |
| PBI055 | Sugestão | 6 | Título gerado automaticamente ("Soma de Valor por Mês") | Escreva a pergunta que o visual responde ou a conclusão. | — |
| PBI056 | Sugestão | 6 | Visual de dados sem título | Todo visual diz o que mostra, numa frase. Linhas de texto sem moldura (variação do KPI, data da carga) são exceção. | — |
| PBI057 | Sugestão | 6 | Título de eixo visível | Esconda o título do eixo: o título do visual já diz o que está sendo medido. | — |
| PBI058 | Sugestão | 6 | Mais de 6 cores na página | Use no máximo 6 cores, além dos cinzas; cor só no que importa. | — |
| PBI059 | Sugestão | 6 | Título ou rótulo que não cabe na largura do visual | Encurte o título ou dê mais largura ao visual. A estimativa usa a largura média da Segoe UI no tamanho do título. | — |
| PBI060 | Sugestão | 6 | Tabela estreita demais para as colunas | Deixe pelo menos 80 px por coluna: tire colunas ou dê a largura inteira à tabela. | — |
| PBI061 | Importante | 1 | Título dinâmico sobre algo que o visual não mostra | A medida do título não usa nenhuma medida ou coluna do visual, nem diretamente nem através das medidas que ela chama. Use a medida de título certa para cada visual. | — |
| PBI062 | Sugestão | 7 | Tempo no eixo vertical de um gráfico de barras | O tempo se lê da esquerda para a direita: use colunas ou linha. | — |
| PBI063 | Sugestão | 6 | Cartões de KPI estreitos demais ou muitos na mesma linha | No máximo 5 cartões por linha, cada um com pelo menos 176 px, para caberem o valor e a linha de contexto. | — |
| PBI064 | Sugestão | 6 | Gráfico pequeno demais para ler | Pelo menos 200 × 140 px; menor que isso, prefira um cartão. Páginas de tooltip são exceção. | — |
| PBI065 | Sugestão | a11y | Cores do tema que se confundem para quem tem daltonismo | Duas das 6 primeiras cores de categoria ficam parecidas demais com protanopia, deuteranopia ou tritanopia simuladas (cerca de 1 em cada 12 homens). Gere o tema com `make_theme.py`, que escolhe uma paleta que continua distinguível. | — |
| PBI066 | Sugestão | 6 | Cantos mais arredondados que 8 px | Use de 0 a 8 px. Cartões muito arredondados parecem modelo pronto, a "cara de dashboard feito por IA", e não um produto. | — |
| PBI067 | Sugestão | 6 | Sombra ou brilho num visual | Use a borda fina. Profundidade acrescenta ruído, não significado. | — |
| PBI068 | Sugestão | 6 | Gutters irregulares, apertados ou largos demais | Mantenha 16 px entre vizinhos, o mesmo em toda a página. Menos de 8 px parece apertado; mais de 32 px desconecta. | — |
| PBI069 | Sugestão | 1 | Dois visuais mostrando a mesma coisa | Dois gráficos do mesmo tipo com os mesmos campos na mesma página, como uma cópia esquecida. Fique com um e use o espaço para outra pergunta. | — |
| PBI078 | Importante | 1 | Título dinâmico reaproveitado em visuais que mostram coisas diferentes | A mesma medida de título em dois visuais com categorias diferentes, como o título da tendência mensal repetido no gráfico por transportadora. O texto descreve outro visual. Crie um título para cada um. | — |
| PBI079 | Sugestão | 6 | Medida com meta mostrada sem a meta | O modelo tem `Meta % No Prazo`, mas a tendência de `% No Prazo` não mostra a linha da meta, ou as barras não destacam quem ficou abaixo. Use `"target"` no layout: linha cinza tracejada na tendência, barras abaixo da meta em vermelho. | — |
| PBI070 | Importante | 5 | Média de percentual | A média de percentuais não é o percentual do total: uma filial com 10 vendas pesa o mesmo que uma com 10 mil. Divida as somas: `DIVIDE ( SUM ( numerador ), SUM ( denominador ) )`. | — |
| PBI071 | Importante | 5 | Saldo ou estoque somado ao longo do tempo | Numa tabela de fotos (posição diária ou mensal), somar o saldo de um mês soma todas as posições. Pegue a última: `LASTNONBLANK` sobre o calendário. | — |
| PBI072 | Sugestão | 5 | Formato que não combina com a medida | Medida de percentual sem `%` no formato, ou de valor formatada como percentual. | — |
| PBI073 | Importante | 4 | Junção implícita ou sem chave no SQL de origem | `FROM a, b` ou `JOIN` sem `ON` cruzam todas as linhas e multiplicam os totais. Escreva `JOIN … ON` com a chave. | — |
| PBI074 | Importante | 4 | NOLOCK ou READ UNCOMMITTED no SQL de origem | Lê linhas em gravação: o total pode contar uma linha duas vezes ou nenhuma. | — |
| PBI075 | Sugestão | 4 | SELECT DISTINCT na consulta de uma fato | Se há linhas repetidas, corrija o join ou o grão; o DISTINCT também apaga linhas iguais legítimas (duas vendas idênticas). | — |
| PBI076 | Importante | 3 | SELECT * no SQL de origem | Liste as colunas: colunas novas na origem entrariam no modelo sem ninguém ver. | — |
| PBI077 | Sugestão | 4 | Função numa coluna do WHERE | `YEAR(data) = 2025` impede o uso do índice. Compare com um intervalo: `data >= '2025-01-01' AND data < '2026-01-01'`. | — |

## Placar de harmonia

Ao final do relatório de texto, a auditoria mostra uma nota de 0 a 100 para cada página:

```
Harmony: Visão Geral 100 · Diagnóstico 96 · Clientes 100
```

Cada página começa com 100 e perde 20 pontos por bloqueador, 10 por achado importante e 4 por sugestão
naquela página. A skill pede pelo menos 90 antes de entregar. Para usar o placar como critério de
pipeline:

```bash
python skills/powerbi-architect/scripts/audit_pbip.py caminho/do/projeto --min-harmony 90
```

O código de saída é 1 quando alguma página fica abaixo do mínimo.

## Auditoria a cada edição

Na instalação por repositório, o `pbi_graph.py install` registra no `.claude/settings.json` um hook que
roda `audit_pbip.py --hook` depois de cada `Edit`, `Write` ou `MultiEdit` do Claude Code. O hook não
diz nada enquanto o projeto está bom. Se a edição deixar um bloqueador ou uma página abaixo de 90, ele
devolve ao agente, na mesma hora, os achados do arquivo editado e o placar de cada página, e o agente
corrige antes de seguir. Arquivos fora de pastas `.Report` ou `.SemanticModel` são ignorados. O
`pbi_graph.py uninstall` remove o hook.

## Como silenciar uma regra

Silencie só com motivo, e registre o motivo junto.

**Arquivo `.pbiaudit.json` na pasta auditada** (ou outro caminho com `--config`):

```json
{
  "disable": ["PBI040"],
  "ignore": [
    { "rule": "PBI015", "path": "*/relationships.tmdl" }
  ]
}
```

`disable` desliga a regra no projeto inteiro. `ignore` desliga a regra só nos arquivos que casam com
`path` (padrão de nome de arquivo, como `*` e `?`).

**Anotação no modelo (TMDL)**, em um objeto específico. Vale para o objeto e, numa tabela, para as
colunas e medidas dela; no `model.tmdl`, vale para o modelo inteiro:

```tmdl
	measure 'Margem %' = [Margem] / [Receita]
		formatString: 0.0%
		annotation PowerBIArchitect_IgnoreRules = {"RuleIDs":["PBI032"]}
```

**Compatível com o Best Practice Analyzer:** a anotação `BestPracticeAnalyzer_IgnoreRules`, que o Tabular
Editor grava quando você ignora uma regra do BPA, também é respeitada. Se um objeto ignora
`REMOVE_AUTO-DATE_TABLE` no BPA, a auditoria deixa de acusar as regras equivalentes (`PBI010`, `PBI017`).
A auditoria não executa as expressões das regras do BPA; ela só reconhece os IDs da tabela acima.
