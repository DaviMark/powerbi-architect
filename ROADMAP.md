# Roadmap

O que vem a seguir, em ordem de prioridade. Quer ajudar em algum item? Comente na issue ligada a ele ou
abra uma com o formulário **Ideia / melhoria**. Itens marcados com `good first issue` são um bom começo.

## Próxima versão

- **Avaliações com outros agentes.** A primeira rodada usou só o Claude. Rodar os mesmos casos no GitHub
  Copilot, Cursor, OpenAI Codex e Gemini CLI e publicar os resultados em `evals/results/`.
- **Caso E-graph nas avaliações.** Medir se a IA consulta o grafo antes de abrir arquivos, usando o
  projeto de exemplo.
- **Conferir o exemplo no Power BI Desktop.** O projeto de `examples/` passa nos schemas da Microsoft,
  mas ainda não foi aberto no Desktop. Abrir, registrar o que o Desktop reescreve e ajustar o gerador.
- **Calibrar o preview com capturas reais do Desktop.** As ferramentas estão prontas
  (`docs/calibrar-preview.md`); faltam capturas das páginas do exemplo e dos kits para ajustar os
  espaçamentos.
- **Conferir no Desktop os visuais modernos e o layout de celular.** O cartão novo, o slicer em botões,
  o botão com ícone e o tamanho da tela de celular foram montados a partir dos schemas, sem o Desktop.

- **Conferir no Desktop a meta tracejada, a cor por medida e o eixo único do combinado.** Os três foram
  montados a partir dos schemas e das propriedades de formatação do Power BI, sem abrir o Desktop.
- **Absorver no `layout.json` as edições feitas à mão**, para que a especificação volte a descrever o
  relatório inteiro (hoje elas ficam preservadas nos arquivos, mas não na especificação).

## Depois

- **Mais regras na auditoria**, a partir das regras do Best Practice Analyzer que ainda não têm
  equivalente (formatação de colunas de data, mês como texto sem ordenação, relacionamentos inativos que
  nunca são usados).
- **Modelos de página para os schemas PBIR mais novos** (`page/2.x`, `visualContainer/2.x`), além dos
  atuais (`1.1.0`).
- **Exemplo de modelo Direct Lake** seguindo `references/fabric-and-cicd.md`.
- **Mais kits iniciais** (compras, CRM, logística, atendimento), no formato de `templates/starter-kits/`.
- **Tradução das referências** para outros idiomas, mantendo o inglês como fonte.

## Feito recentemente

Veja o [CHANGELOG](CHANGELOG.md).
