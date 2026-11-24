# Benchmark da versão 1.4.0

Medido em 2026-11-24, com Claude Sonnet 5.5 nas duas condições. Página com gráficos e imagens: [`benchmarks/index.html`](../../index.html).

| | Com a skill | Sem a skill |
|---|---|---|
| Requisitos atendidos | **14 de 14** (100%) | 4 de 14 (29%) |
| Entregas que atendem a tudo | **2 de 2** | 0 de 2 |
| Harmonia média | **98** | 5 |
| Achados médios da auditoria | **3.5** | 25 |
| Tokens por execução (média) | 96.098 | 76.183 |
| Chamadas de ferramenta (média) | 12 | 4 |
| Tempo por execução (média) | 59 s | 31 s |

## Por requisito

| Requisito | Com a skill | Sem a skill |
|---|---|---|
| Abre sem erro — JSON válido nos schemas da Microsoft e todo campo usado pelos visuais existe no modelo | 2 de 2 | 0 de 2 |
| Zero bloqueadores — Nenhum achado bloqueador na auditoria | 2 de 2 | 0 de 2 |
| Harmonia ≥ 90 — Todas as páginas com nota de harmonia de 90 ou mais | 2 de 2 | 0 de 2 |
| Acessível — Todo visual de dados com título e texto alternativo; texto com contraste ≥ 4,5:1 | 2 de 2 | 0 de 2 |
| Pixel a pixel — Nenhum achado da crítica do preview: texto cortado, sobreposição, gutters, grade | 2 de 2 | 0 de 2 |
| Pedido atendido — As páginas pedidas existem e nenhuma informação do relatório anterior sumiu | 2 de 2 | 2 de 2 |
| Números seguros — Nenhum padrão de DAX ou SQL que devolve número errado (PBI032, PBI070–PBI077) | 2 de 2 | 2 de 2 |

## Por execução

| Cenário | Condição | Requisitos | Harmonia | Tokens | O que faltou |
|---|---|---|---|---|---|
| Logística: relatório a partir do modelo | com a skill | 7/7 | 96 | 92.142 | — |
| Logística: relatório a partir do modelo | sem a skill | 2/7 | 6 | 73.441 | abre: 2 erro(s) de schema; bloqueadores: 1 bloqueador(es); harmonia: Visão Geral 0, Transportadoras 12; acessivel: PBI019, PBI056; pixel: 2 achado(s) |
| Relatório amador: deixar profissional sem perder informação | sem a skill | 2/7 | 4 | 78.925 | abre: 9 erro(s) de schema; bloqueadores: 1 bloqueador(es); harmonia: Painel de Cobrança 4; acessivel: PBI019, PBI056; pixel: 1 achado(s) |
| Relatório amador: deixar profissional sem perder informação | com a skill | 7/7 | 100 | 100.054 | — |
