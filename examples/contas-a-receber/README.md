# Contas a receber (exemplo)

Projeto PBIP sintético que segue todas as regras da skill. Serve para três coisas:

- **Ver o padrão pronto:** modelo estrela, Power Query de uma etapa, medidas documentadas, página de
  Documentação e tema acessível.
- **Testar as ferramentas:** a auditoria (`audit_pbip.py`) e o grafo de conhecimento (`pbi_graph.py`)
  rodam sobre ele nos testes do repositório.
- **Reproduzir os números do README:** quantos tokens o grafo economiza em relação aos arquivos-fonte.

Os dados não estão incluídos. As consultas apontam para os parâmetros `Servidor` e `Banco`
(`localhost` / `dw_exemplo`) e para tabelas `dw.*` que não existem fora deste exemplo.

## O que é

Responde a quatro perguntas de cobrança, para a diretoria financeira, com carga diária:

1. Quanto está vencido hoje, por regional e por segmento de cliente?
2. Qual o atraso médio, ponderado pelo saldo em aberto?
3. Quais clientes concentram o valor vencido?
4. Como o valor vencido evoluiu nos últimos 24 meses?

## Como usar

| Página | Pergunta |
|---|---|
| Visão Geral | Quanto está vencido, onde e há quanto tempo |
| Clientes | Quem concentra o valor vencido |
| Documentação | O que cada medida significa e quando foi a última carga |

## Cargas

| Tabela | Tipo | Grão | Fonte | Modo |
|---|---|---|---|---|
| Fato Titulos | fato | 1 linha por parcela | `dw.fato_titulos_receber` | Import |
| Dim Cliente | dimensão | 1 linha por cliente | `dw.dim_cliente` | Import |
| Dim Regional | dimensão | 1 linha por regional | `dw.dim_regional` | Import |
| Calendario | dimensão de datas | 1 linha por dia | calculada (DAX) | Import |

Cada tabela de fonte tem **uma etapa** no Power Query: `Value.NativeQuery` com o SQL e os parâmetros.
Filtros, nomes de colunas e faixas de atraso são resolvidos no SQL.

## Métricas

| Medida | Definição |
|---|---|
| Valor Aberto | Saldo em aberto das parcelas, vencidas ou a vencer |
| Valor Vencido | Saldo em aberto das parcelas com vencimento anterior à data da carga |
| % Vencido | Parcela do saldo em aberto que já venceu |
| Dias Atraso Medio | Média de dias de atraso das parcelas vencidas, ponderada pelo saldo |

O catálogo completo, com a expressão DAX, fica na página **Documentação** (gerada por `INFO.VIEW.MEASURES`).

## Como foi construído

- Modelo estrela com grão declarado, relacionamentos 1:* em direção única, auto date/time desligado.
- Só as colunas usadas por medidas, visuais, relacionamentos, ordenação ou segurança.
- Tema: [`powerbi-architect-acessivel.json`](../../skills/powerbi-architect/templates/theme/powerbi-architect-acessivel.json).
- **Validação:** todos os arquivos JSON passam nos schemas oficiais da Microsoft
  (`tools/validate_schemas.py`) e a auditoria não encontra nenhum problema. O projeto **não foi aberto no
  Power BI Desktop** durante a criação; se você abrir e o Desktop reescrever algum arquivo, abra uma issue.

## Segurança e privacidade

Sem dados pessoais. A função `Gestor Regional` aplica segurança por linha: cada gestor vê só a própria
regional, pelo e-mail do usuário logado.

## Experimente

```bash
python skills/powerbi-architect/scripts/audit_pbip.py examples/contas-a-receber
python skills/powerbi-architect/scripts/pbi_graph.py build examples/contas-a-receber --out .tmp/graph
python skills/powerbi-architect/scripts/pbi_graph.py impact "Fato Titulos[Dias Atraso]"
```
