# Benchmark da versão 1.3.0

Medido em 2026-11-24, com Claude Sonnet 5.5 nas duas condições. Página com gráficos e imagens: [`benchmarks/index.html`](../../index.html).

| | Com a skill | Sem a skill |
|---|---|---|
| Requisitos atendidos | **33 de 35** (94%) | 17 de 35 (49%) |
| Entregas que atendem a tudo | **3 de 5** | 0 de 5 |
| Harmonia média | **99.8** | 40 |
| Achados médios da auditoria | **2.2** | 22 |
| Tokens por execução (média) | 99.303 | 81.138 |
| Chamadas de ferramenta (média) | 15 | 5 |
| Tempo por execução (média) | 93 s | 46 s |

## Por requisito

| Requisito | Com a skill | Sem a skill |
|---|---|---|
| Abre sem erro — JSON válido nos schemas da Microsoft e todo campo usado pelos visuais existe no modelo | 5 de 5 | 3 de 5 |
| Zero bloqueadores — Nenhum achado bloqueador na auditoria | 5 de 5 | 1 de 5 |
| Harmonia ≥ 90 — Todas as páginas com nota de harmonia de 90 ou mais | 5 de 5 | 1 de 5 |
| Acessível — Todo visual de dados com título e texto alternativo; texto com contraste ≥ 4,5:1 | 5 de 5 | 2 de 5 |
| Pixel a pixel — Nenhum achado da crítica do preview: texto cortado, sobreposição, gutters, grade | 3 de 5 | 0 de 5 |
| Pedido atendido — As páginas pedidas existem; edições do usuário preservadas; informação mantida | 5 de 5 | 5 de 5 |
| Números seguros — Nenhum padrão de DAX ou SQL que devolve número errado (PBI032, PBI070–PBI077) | 5 de 5 | 5 de 5 |

## Por execução

| Cenário | Condição | Requisitos | Harmonia | Tokens | O que faltou |
|---|---|---|---|---|---|
| Logística: relatório a partir do modelo | com a skill | 7/7 | 100 | 95.105 | — |
| Logística: relatório a partir do modelo | sem a skill | 2/7 | 10 | 75.917 | abre: 1 erro(s) de schema; bloqueadores: 1 bloqueador(es); harmonia: Visão Geral 0, Transportadoras 20; acessivel: PBI019, PBI056; pixel: 2 achado(s) |
| Atendimento: relatório a partir do modelo | sem a skill | 2/7 | 11 | 77.702 | abre: 1 erro(s) de schema; bloqueadores: 1 bloqueador(es); harmonia: Visão Geral 0, Equipes de Suporte 22; acessivel: PBI019, PBI056; pixel: 2 achado(s) |
| Atendimento: relatório a partir do modelo | com a skill | 7/7 | 100 | 111.334 | — |
| Compras: relatório a partir do modelo | com a skill | 7/7 | 100 | 97.127 | — |
| Compras: relatório a partir do modelo | sem a skill | 3/7 | 4 | 73.228 | bloqueadores: 1 bloqueador(es); harmonia: Visão Geral 0, Fornecedores 8; acessivel: PBI019, PBI056; pixel: 6 achado(s) |
| Edições feitas à mão: pedido novo sem perder nada | sem a skill | 6/7 | 99.2 | 100.798 | pixel: 3 achado(s) |
| Edições feitas à mão: pedido novo sem perder nada | com a skill | 6/7 | 99.2 | 103.190 | pixel: 3 achado(s) |
| Relatório amador: deixar profissional sem perder informação | com a skill | 6/7 | 100 | 89.757 | pixel: 1 achado(s) |
| Relatório amador: deixar profissional sem perder informação | sem a skill | 4/7 | 76 | 78.044 | bloqueadores: 1 bloqueador(es); harmonia: Painel de Cobrança 76; pixel: 1 achado(s) |
