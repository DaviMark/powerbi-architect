# Como contribuir

Obrigado por ajudar a fazer agentes de IA trabalharem como desenvolvedores Power BI sêniores! Issues e
pull requests são bem-vindos em **português ou inglês**.

## Formas de ajudar

| Você tem… | Faça isto |
|---|---|
| Uma IA que ignorou a skill | Abra uma issue **Comportamento da IA**: prompt, regra esperada, resposta recebida |
| Um script, instalador ou exemplo quebrado | Abra uma issue **Bug** |
| Uma ideia de padrão DAX, conector, arquétipo de página ou achado do grafo | Abra uma issue **Ideia / melhoria** antes de PRs grandes |
| 15 minutos e um agente de IA | Rode um caso de [`evals/`](evals/README.md) e compartilhe em **Resultado de avaliação** |
| Uma correção pequena (erro de digitação, link, redação) | Abra um PR direto |

Primeira vez por aqui? Procure issues com a label
[`good first issue`](https://github.com/DaviMark/powerbi-architect/labels/good%20first%20issue).

## Regras da skill

1. O `SKILL.md` fica com **menos de 500 linhas**. Detalhes vão para `references/` (divulgação progressiva).
2. **Seja preciso.** Todo exemplo de sintaxe (TMDL, PBIR, M, DAX, TypeScript) precisa ser válido. Diga
   no PR como verificou (Power BI Desktop, Modeling MCP, `pbiviz package`…).
3. **Sem dados reais**, servidores, credenciais ou nomes de empresa em exemplos, issues ou PRs.
4. `scripts/` continua em **Python padrão e offline**. O `audit_pbip.py` só lê; o `pbi_graph.py` escreve
   apenas na pasta de saída e nos blocos/hooks marcados descritos em
   [`references/graph.md`](skills/powerbi-architect/references/graph.md).
5. **Idiomas:** arquivos lidos pela IA (`SKILL.md`, `references/`, `evals/cases.md`) ficam em
   **inglês**. Tudo o que pessoas leem (README, guias, templates, CHANGELOG, commits e PRs do projeto)
   fica em **português do Brasil**. O [`README.en.md`](README.en.md) é a versão em inglês do README e
   deve acompanhar as mudanças.
6. Mudou o comportamento? Crie ou atualize uma avaliação em [`evals/cases.md`](evals/cases.md).

## Fluxo de trabalho

```bash
git clone https://github.com/<seu-usuario>/powerbi-architect.git
cd powerbi-architect
git checkout -b fix/descricao-curta
python -m unittest discover -s tests -v      # precisa passar
```

Mudou o visual customizado? Compile do mesmo jeito que o CI: veja o job `pbiviz` em `.github/workflows/ci.yml`.

- Um assunto por PR; preencha o checklist do template.
- Mensagens de commit: resumo curto no infinitivo (`Adicionar padrão DAX de 12 meses móveis`), com
  um corpo explicando o motivo quando não for óbvio.
- Mudança visível para o usuário: adicione uma linha em `## [Não publicado]` no [`CHANGELOG.md`](CHANGELOG.md).
- O CI precisa estar verde. O mantenedor revisa todo PR (veja `.github/CODEOWNERS`); o merge é feito
  com squash.

## Versões e releases

A skill segue o [Versionamento Semântico](https://semver.org/lang/pt-BR/):

| Versão | Quando |
|---|---|
| **major** | caminhos de instalação, CLI ou formato de saída dos scripts mudam de forma incompatível |
| **minor** | nova orientação, referências, recursos ou achados nos scripts |
| **patch** | correções e esclarecimentos |

Para publicar, o mantenedor move `[Não publicado]` para uma nova versão no `CHANGELOG.md`, atualiza a
versão no `SKILL.md` (`metadata.version`) e em `.claude-plugin/plugin.json` e `marketplace.json`, e envia
uma tag `vX.Y.Z`. O workflow `release` confere tudo isso, roda os testes e publica uma release no GitHub
com o arquivo `powerbi-architect-vX.Y.Z.zip` e um atestado de procedência, que qualquer pessoa confere
com `gh attestation verify`.

Ferramentas de desenvolvimento (precisam de rede e de `pip install jsonschema`):

```bash
python tools/validate_schemas.py               # exemplo e modelos de página contra os schemas da Microsoft
python tools/validate_schemas.py --references  # exemplos JSON das referências
python tools/generate_example.py               # recria examples/contas-a-receber
python skills/powerbi-architect/scripts/preview_pbir.py <Nome>.Report --sample amostra.json   # prévia (sem rede)
```

## Conduta

Todos seguem o [Código de conduta](CODE_OF_CONDUCT.md). Problemas de segurança vão para o
[SECURITY.md](SECURITY.md), nunca para issues públicas.
