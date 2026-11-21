# Histórico de mudanças

Todas as mudanças relevantes do projeto ficam registradas aqui. O formato segue o
[Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e as versões seguem o
[Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Não publicado]
### Adicionado
- Arquivos de comunidade: formulários de issue (comportamento da IA, bug, ideia, resultado de avaliação,
  dúvida), template de pull request, `CODEOWNERS`, `SUPPORT.md` e labels gerenciadas
  (`.github/labels.json`).
- Workflow `release`: uma tag `vX.Y.Z` confere a versão do `SKILL.md` e o `CHANGELOG.md`, roda os testes
  e publica uma release no GitHub com a skill em `.zip`.
- `.gitattributes` mantém o `install.sh` com finais de linha LF em clones no Windows; `.editorconfig`.
### Alterado
- `CONTRIBUTING.md` ampliado (fluxo de trabalho, versões, processo de release e regra de idiomas).
- Documentação para pessoas (`SECURITY.md`, `evals/README.md`, `CHANGELOG.md`) e nomes dos jobs de CI
  em português do Brasil. Arquivos lidos pela IA continuam em inglês.
- O Dependabot agrupa as atualizações de GitHub Actions em um único PR mensal.
- CI: `actions/checkout` 7.0.1, `actions/setup-python` 7.1.0, `actions/setup-node` 7.1.0.
- Os instaladores e o `pbi_graph.py` mostram `[ok]` no lugar de um símbolo de check, para que a saída
  apareça igual em qualquer terminal e página de código. O banner do README desenha os checks como
  vetores.

## [1.1.0] — 2026-11-21
### Adicionado
- `scripts/pbi_graph.py`: grafo de conhecimento offline do Power BI (TMDL, PBIR, SQL, documentação,
  Python) com `GRAPH_REPORT.md`, cards por modelo, `graph.json`, `graph.html` e os comandos `query` /
  `explain` / `impact` / `path`. Achados: colunas e medidas sem uso, campos quebrados em visuais, fontes
  compartilhadas e medidas divergentes.
- `pbi_graph.py install|uninstall`: instruções para agentes no `AGENTS.md`/`CLAUDE.md`, hooks do Claude
  Code (início de sessão e após edições) e hooks do git que mantêm o grafo atualizado.
- `references/graph.md`; a seção 0 do `SKILL.md` agora diz "grafo antes dos arquivos".
- Os instaladores geram o grafo depois de copiar (`--no-graph`/`-NoGraph`, `--no-hooks`/`-NoHooks`).
### Alterado
- Framework renomeado: PBIP Blueprint → Power BI Workspaces (`config/workspaces.toml`, `tools/pbw.py`).
### Corrigido
- O `install.ps1` não era interpretado pelo Windows PowerShell 5.1 (UTF-8 sem BOM); agora é salvo com BOM.

## [1.0.0] — 2026-11-23
### Adicionado
- `SKILL.md` com oito princípios, workflow e árvores de decisão.
- Referências: workflow, modeling, power-query, dax, tmdl, pbir, report-design, visual-selection,
  custom-visuals, documentation, refactoring, performance, security, quality-checklist.
- Visual customizado de referência verificado em `templates/pbiviz-bullet-kpi` (API 5.11, pbiviz 7.2).
- Auditoria offline de PBIP em `scripts/audit_pbip.py`.
- Instaladores por projeto e globais (bash e PowerShell), avaliações e CI.
