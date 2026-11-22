# Histórico de mudanças

Todas as mudanças relevantes do projeto ficam registradas aqui. O formato segue o
[Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e as versões seguem o
[Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Não publicado]
### Adicionado
- Padrão visual inspirado no Twenty, o CRM open source: estrutura de página com sidebar de 220 px e
  navegação de páginas, painel branco com cantos de 8 px e barra do topo de 56 px (caminho da página, data
  da carga e filtros compactos), com a posição de cada peça em `references/report-design.md`.
- Escala tipográfica (9 · 10 · 12 · 20 pt), fonte padrão Segoe UI quando o projeto não tem identidade
  visual, grade de 4 px e uma seção de harmonia com a verificação final antes da entrega.
- Convenção de nomes de tabela: `ft_<assunto>` para fatos e `dm_<entidade>` para dimensões.
- Auditoria: regras `PBI046` (slicer grande demais), `PBI047` (fonte fora da escala), `PBI048` (visual
  fora da grade de 4 px), `PBI049` (tabela sem `ft_`/`dm_`), `PBI050` (mais de 2 slicers na página),
  `PBI051` (mais de uma família de fonte, ou fonte fora do padrão) e `PBI052` (visual fora da página).
- `scripts/pbir_layout.py`: gera as páginas PBIR a partir de um layout descrito em JSON (linhas de
  visuais), com todas as posições na grade de 4 px, a estrutura da página, ícones na navegação, KPIs com
  linha de contexto ou meta, gráficos, tabelas com uma cor condicional, páginas de drill-through com botão
  de voltar, páginas de tooltip e layout de celular (`mobile.json`).
- `scripts/preview_pbir.py`: prévia das páginas sem o Power BI Desktop, com dados de amostra (`--sample`),
  layout de celular (`--mobile`) e uma imagem por página (`--png`, com o Edge ou o Chrome da máquina). O
  `SKILL.md` passa a exigir que a IA olhe cada página antes de entregar.
- `scripts/make_theme.py`: tema a partir da cor da marca, escurecida até passar no contraste, com 6 cores
  de categoria sem as cores de status e recusa de fontes que o Power BI não renderiza.
- Auditoria: regras `PBI053` (ordem do teclado), `PBI054` (contraste do texto), `PBI055` (título
  automático), `PBI056` (visual sem título), `PBI057` (título de eixo) e `PBI058` (mais de 6 cores), e a
  nota de harmonia de 0 a 100 por página, com `--min-harmony`.
- Ícones de navegação (Tabler, licença MIT), seis arquétipos de página (visão geral, diagnóstico, lista
  operacional, detalhe por drill-through, tooltip e documentação) e três visuais modernos experimentais
  (cartão novo, slicer em botões e botão com ícone), ainda não conferidos no Power BI Desktop.
- Referência `copywriting.md` (títulos, nomes de medida, números e textos) e padrão de DAX para as linhas
  dos KPIs (contexto, meta e variação, com cor conforme o sentido bom da métrica).
- Avaliações de design E11 e E12, corrigidas pelas próprias ferramentas: com a skill, 8 de 8 itens e
  harmonia 100; sem a skill, 3 de 8 e harmonia 0 e 22 (`evals/results/2026-11-21-design`).
### Alterado
- Tema refeito com os neutros e as cores do Twenty, mantendo contraste de 4,5:1 no texto; estilos
  prontos para navegação de páginas, cartões, tabelas, slicers, caixas de texto e formas.
- Projeto de exemplo e modelos de página PBIR com a estrutura nova e as tabelas renomeadas
  (`ft_titulos`, `dm_cliente`, `dm_regional`, `dm_calendario`).
- A regra de no máximo 8 visuais por página (auditoria e grafo) deixa de contar os slicers, que têm
  limite próprio.
- O tema ganhou padrões de gráfico (linha de 2 px sem marcadores, cores de cascata, espaçamento das
  barras) e a navegação com espaço para os ícones.
- Projeto de exemplo gerado pelo `pbir_layout.py` a partir de `layout.json`, agora com seis páginas e
  medidas de contexto e meta para os KPIs; a medida `Dias Atraso Medio` passa a se chamar
  `Atraso Médio (dias)`.
- Linhas de texto sem moldura (variação do KPI, data da carga) não contam como visuais separados.

## [1.2.0] — 2026-11-21
### Adicionado
- Projeto PBIP de exemplo em `examples/contas-a-receber`, validado pelos schemas da Microsoft, sem
  nenhum achado na auditoria nem no grafo.
- Avaliações publicadas: com a skill, 16 de 18 itens e 8 de 10 casos; sem a skill, 6 de 18 e 2 de 10
  (`evals/results/2026-11-21`). Materiais de apoio dos casos em `evals/fixtures/`.
- Auditoria: códigos de regra (`PBI001`…`PBI043`) com arquivo e linha, `--help`, `--version`,
  `--list-rules`, `--json`, `--sarif`, `--fail-on`, supressão por `.pbiaudit.json` e por anotação TMDL,
  correspondência com as regras do Best Practice Analyzer do Tabular Editor (inclusive a anotação
  `BestPracticeAnalyzer_IgnoreRules`) e regras novas para que cada um dos oito princípios tenha
  verificação automática. Catálogo em `docs/regras-auditoria.md`.
- Modelos de página PBIR (`templates/pbir-pages`) e tema acessível (`templates/theme`).
- Referências `semantic-features.md` (calculation groups, field parameters, visual calculations, funções
  DAX) e `fabric-and-cicd.md` (Direct Lake, Git do Fabric, deployment pipelines, CI).
- Plugin do Claude Code: `/plugin install powerbi-architect --marketplace DaviMark/powerbi-architect`.
- Instaladores: `--status` e `--update` (`-Status` e `-Update` no PowerShell).
- Releases com o zip da skill e atestado de procedência (`gh attestation verify`).
- `ROADMAP.md`.
- Arquivos de comunidade: formulários de issue (comportamento da IA, bug, ideia, resultado de avaliação,
  dúvida), template de pull request, `CODEOWNERS`, `SUPPORT.md` e labels gerenciadas
  (`.github/labels.json`).
- Workflow `release`: uma tag `vX.Y.Z` confere a versão do `SKILL.md` e o `CHANGELOG.md`, roda os testes
  e publica uma release no GitHub com a skill em `.zip`.
- `.gitattributes` mantém o `install.sh` com finais de linha LF em clones no Windows; `.editorconfig`.
### Alterado
- CI roda os testes no Linux e no Windows, do Python 3.9 ao 3.13, valida os JSON pelos schemas da
  Microsoft e confere todo exemplo de código das referências.
- README: números de tokens medidos no projeto de exemplo (reproduzíveis), no lugar dos números de um
  projeto que não estava no repositório.
- `CONTRIBUTING.md` ampliado (fluxo de trabalho, versões, processo de release e regra de idiomas).
- Documentação para pessoas (`SECURITY.md`, `evals/README.md`, `CHANGELOG.md`) e nomes dos jobs de CI
  em português do Brasil. Arquivos lidos pela IA continuam em inglês.
- O Dependabot agrupa as atualizações de GitHub Actions em um único PR mensal.
- CI: `actions/checkout` 7.0.1, `actions/setup-python` 7.1.0, `actions/setup-node` 7.1.0.
- Os instaladores e o `pbi_graph.py` mostram `[ok]` no lugar de um símbolo de check, para que a saída
  apareça igual em qualquer terminal e página de código. O banner do README desenha os checks como
  vetores.
### Corrigido
- `audit_pbip.py --help` era tratado como caminho de pasta e gerava um BLOCKER.
- A auditoria podia falhar no console do Windows ao imprimir símbolos como → e ≤.
- O grafo apontava como sem uso as medidas usadas em título dinâmico de visual e as colunas usadas só em
  hierarquias.
- O `install.sh` tratava opções desconhecidas como pasta de destino.

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
