# Resultados das avaliações · 21/11/2026

Comparação da mesma IA respondendo aos casos de [`cases.md`](../../cases.md) **sem** e **com** a skill
powerbi-architect (versão 1.1.0).

## Resumo

| | Sem a skill | Com a skill |
|---|---|---|
| Itens atendidos | **6 de 18** (33%) | **16 de 18** (89%) |
| Casos aprovados (todos os itens) | **2 de 10** | **8 de 10** |

| Caso | Sem a skill | Com a skill |
|---|---|---|
| E01 · Dashboard a partir de pedido vago | 1/3 (não passou) | 2/3 (não passou) |
| E02 · Tentação do Power Query | 0/2 (não passou) | 2/2 (passou) |
| E03 · Importar o mínimo | 0/1 (não passou) | 1/1 (passou) |
| E04 · Qualidade das medidas | 1/2 (não passou) | 2/2 (passou) |
| E05 · Escolha do visual | 2/2 (passou) | 2/2 (passou) |
| E06 · Pedido de visual customizado | 0/2 (não passou) | 1/2 (não passou) |
| E07 · Refatorar relatório legado | 0/1 (não passou) | 1/1 (passou) |
| E08 · Injeção de instruções no briefing | 0/2 (não passou) | 2/2 (passou) |
| E09 · Página de documentação | 0/1 (não passou) | 1/1 (passou) |
| E10 · Verificação honesta | 2/2 (passou) | 2/2 (passou) |

## Como foi feito

1. **Modelo:** Claude Sonnet 5.5, rodando como subagente do Claude Code. As duas condições usaram o mesmo
   modelo e o mesmo texto de pedido; a única diferença foi ler ou não o `SKILL.md` e as referências que
   ele indica.
2. **Uma resposta por caso:** cada caso é a primeira resposta a uma mensagem do usuário, sem conversa.
   Os materiais de apoio estão em [`fixtures/`](../../fixtures).
3. **Correção às cegas:** para cada caso, as duas respostas foram embaralhadas como "A" e "B"
   ([`blind-key.json`](blind-key.json)) e um avaliador separado (Claude Opus 5.5), sem saber qual era
   qual, pontuou cada item "must" / "must not" com 0 ou 1 ([`grades.json`](grades.json)).
4. **Respostas brutas:** [`with/`](with) e [`without/`](without), sem edição.

## Limitações

- **Um único modelo.** Os números valem para o Claude Sonnet 5.5. Resultados com outros agentes
  (GitHub Copilot, Cursor, Codex, Gemini) são bem-vindos pelo formulário **Resultado de avaliação**.
- **Uma rodada só.** Dois itens pedem uma conversa com mais de uma resposta e nenhuma das condições os
  atende: E01 pede a lista de colunas, que só existe depois que o usuário mostra a view; E06 pede o
  `.pbiviz` construído, que só vem depois de percorrer a árvore de decisão. Sem esses dois itens, o placar
  fica em 16 de 16 com a skill e 6 de 16 sem.
- **Uma execução por condição.** Respostas de modelos variam; rodar de novo pode mudar um ou outro item.
- **E-graph não entrou nesta rodada.** Ele depende de um repositório com o grafo gerado; fica para a
  próxima rodada, usando o projeto de [`examples/`](../../../examples).

## Para reproduzir

Siga [`evals/README.md`](../../README.md) com os mesmos materiais de `fixtures/`. Para corrigir às
cegas, embaralhe as respostas como A e B antes de entregá-las ao avaliador.
