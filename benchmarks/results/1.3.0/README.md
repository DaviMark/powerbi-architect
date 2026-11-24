# Benchmark da versão 1.3.0

Medido em 2026-11-24, com Claude Sonnet 5.5 nas duas condições. Página com gráficos e imagens: [`benchmarks/index.html`](../../index.html).

| | Com a skill | Sem a skill |
|---|---|---|
| Requisitos atendidos | **13 de 14** (93%) | 6 de 14 (43%) |
| Entregas que atendem a tudo | **1 de 2** | 0 de 2 |
| Harmonia média | **100** | 43 |
| Achados médios da auditoria | **2.5** | 20.5 |
| Tokens por execução (média) | 92.431 | 76.980 |
| Chamadas de ferramenta (média) | 11 | 4 |
| Tempo por execução (média) | 47 s | 38 s |

## Por requisito

| Requisito | Com a skill | Sem a skill |
|---|---|---|
| Abre sem erro — JSON válido nos schemas da Microsoft e todo campo usado pelos visuais existe no modelo | 2 de 2 | 1 de 2 |
| Zero bloqueadores — Nenhum achado bloqueador na auditoria | 2 de 2 | 0 de 2 |
| Harmonia ≥ 90 — Todas as páginas com nota de harmonia de 90 ou mais | 2 de 2 | 0 de 2 |
| Acessível — Todo visual de dados com título e texto alternativo; texto com contraste ≥ 4,5:1 | 2 de 2 | 1 de 2 |
| Pixel a pixel — Nenhum achado da crítica do preview: texto cortado, sobreposição, gutters, grade | 1 de 2 | 0 de 2 |
| Pedido atendido — As páginas pedidas existem e nenhuma informação do relatório anterior sumiu | 2 de 2 | 2 de 2 |
| Números seguros — Nenhum padrão de DAX ou SQL que devolve número errado (PBI032, PBI070–PBI077) | 2 de 2 | 2 de 2 |

## Por execução

| Cenário | Condição | Requisitos | Harmonia | Tokens | O que faltou |
|---|---|---|---|---|---|
| Logística: relatório a partir do modelo | com a skill | 7/7 | 100 | 95.105 | — |
| Logística: relatório a partir do modelo | sem a skill | 2/7 | 10 | 75.917 | abre: 1 erro(s) de schema; bloqueadores: 1 bloqueador(es); harmonia: Visão Geral 0, Transportadoras 20; acessivel: PBI019, PBI056; pixel: 2 achado(s) |
| Relatório amador: deixar profissional sem perder informação | com a skill | 6/7 | 100 | 89.757 | pixel: 1 achado(s) |
| Relatório amador: deixar profissional sem perder informação | sem a skill | 4/7 | 76 | 78.044 | bloqueadores: 1 bloqueador(es); harmonia: Painel de Cobrança 76; pixel: 1 achado(s) |
