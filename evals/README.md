# Avaliações

Como medir se a skill faz diferença:

1. Escolha um caso em [`cases.md`](cases.md). Os prompts ficam em inglês porque são lidos pela IA.
2. Rode o prompt numa sessão nova **sem** a skill e depois **com** a skill instalada.
3. Pontue cada item "must" (0/1) e cada item "must not" (0/1). Anote tokens e tempo, se quiser.
4. Compartilhe os resultados numa issue **Resultado de avaliação** (sem dados reais). Eles orientam a próxima versão.

Um caso passa quando todos os itens **must** aparecem e nenhum item **must not** acontece.

Os materiais de apoio dos casos (view de 60 colunas, metadados do `.pbit` legado, briefing com injeção
de instruções, estado do projeto) ficam em [`fixtures/`](fixtures).

## Resultados publicados

| Data | Modelo | Sem a skill | Com a skill | Detalhes |
|---|---|---|---|---|
| 21/11/2026 | Claude Sonnet 5.5 | 6 de 18 itens · 2 de 10 casos | 16 de 18 itens · 8 de 10 casos | [resultados](results/2026-11-21/README.md) |
| 21/11/2026 (design, E11–E12) | Claude Sonnet 5.5 | 3 de 8 itens · harmonia 0 e 22 | 8 de 8 itens · harmonia 100 | [resultados](results/2026-11-21-design/README.md) |
| 22/11/2026 (design, E13, modelo inédito) | Claude Sonnet 5.5 e Haiku 5.5 | 0 de 4 itens (os dois) · harmonia 0 | 4 de 4 itens (os dois) · harmonia 100 · preferido às cegas | [resultados](results/2026-11-22-design-e13/README.md) |
| 24/11/2026 (E13 rodada 2 e E14, edições manuais) | Claude Sonnet 5.5 | E14: edições preservadas | E14: edições preservadas, com um bug achado e corrigido; E13: avaliador cego preferiu a rodada 1 (confiança baixa) | [resultados](results/2026-11-24-e13r2-e14/README.md) |

Para corrigir sem viés, embaralhe as duas respostas de cada caso como "A" e "B" e só revele qual é qual
depois da pontuação.
