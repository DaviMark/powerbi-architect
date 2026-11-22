<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/hero-dark.svg">
  <img alt="Power BI Architect — a skill que faz qualquer IA pensar como especialista em Power BI" src="docs/assets/hero-light.svg" width="100%">
</picture>

<br>

[![skill-ci](https://github.com/DaviMark/powerbi-architect/actions/workflows/ci.yml/badge.svg)](https://github.com/DaviMark/powerbi-architect/actions/workflows/ci.yml)
![License](https://img.shields.io/badge/licença-MIT-1F2328)
![Agent Skills](https://img.shields.io/badge/Agent%20Skills-SKILL.md-F2C811?labelColor=1F2328)
![pbiviz](https://img.shields.io/badge/pbiviz-API%205.x%20·%20verificado-1A7F37)
![Rede](https://img.shields.io/badge/acesso%20à%20rede-nenhum-1A7F37)

**[Instalar](#instalação)** ·
**[O que tem dentro](#o-que-tem-dentro)** ·
**[Power BI Workspaces](https://github.com/DaviMark/powerbi-workspaces)** ·
**[English](README.en.md)**

</div>

---

Sua IA sabe *escrever* DAX. Esta skill ensina ela a **pensar como um desenvolvedor Power BI sênior**:
importar o mínimo, desenhar star schema, deixar o Power Query com **uma etapa**, documentar cada
métrica, desenhar páginas que respondem uma pergunta em três segundos — e só criar um visual
customizado (`.pbiviz`) quando **nenhum visual nativo** resolve.

Funciona em **GitHub Copilot, Claude Code, Cursor, OpenAI Codex, Gemini CLI** e qualquer agente
compatível com o padrão aberto **[Agent Skills](https://agentskills.io)** (`SKILL.md`). Sozinha ou
dentro do **[Power BI Workspaces](https://github.com/DaviMark/powerbi-workspaces)**.

## Antes e depois

| Você pede: *"faça um dashboard de contas a receber"* | IA genérica | IA com Power BI Architect |
|---|---|---|
| Primeira resposta | começa a gerar visuais | faz ≤ 5 perguntas que mudam o modelo (grão, regra de "vencido", público) |
| Modelo | importa a view inteira | star schema com grão declarado, só colunas usadas, lista do que **não** importou |
| Power Query | renomeia, filtra, muda tipos | **1 etapa**: SQL nativo no dialeto da fonte, com parâmetros |
| DAX | medidas soltas, sem formato | base → derivadas, `DIVIDE`, descrição de negócio, formato e pasta em todas |
| Relatório | 15 visuais, pizza, legenda | título-conclusão, 4 KPIs, 3 visuais de explicação, grid de 8 px, alt text |
| Visual customizado | "vou criar um .pbiviz" | árvore de decisão: nativo → formatação → AppSource → só então `.pbiviz`, com ADR |
| Entrega | "pronto!" | gate de aprovação, conferência de números, página **Documentação**, checklist honesto |

**Medido, não prometido.** Nas [avaliações publicadas](evals/results/2026-11-21/README.md), a mesma IA
atendeu **16 de 18** itens esperados com a skill e **6 de 18** sem ela (8 de 10 casos aprovados contra 2),
com correção às cegas. As respostas brutas estão no repositório.

## Os oito princípios

1. **Pergunta primeiro** — todo objeto e todo visual responde uma pergunta de negócio.
2. **Star schema** — fatos com grão declarado, dimensões conformadas, 1:* em direção única.
3. **Importe o mínimo** — só colunas usadas por medida, visual, relacionamento, ordenação ou RLS.
4. **Zero lógica no Power Query** — uma etapa; regras de negócio no SQL/views.
5. **Medidas explícitas** — descrição, formato e pasta, sempre.
6. **Uma página, uma pergunta** — conclusão no título, KPIs → tendência → explicação → detalhe.
7. **Visual nativo primeiro** — `.pbiviz` é o último recurso, documentado.
8. **Autodocumentado** — página Documentação no relatório + README vivo.

## Pensa como designer de produto

A parte de design não é "deixar bonito". É começar pela **decisão** que a pessoa precisa tomar e
trabalhar de trás para frente até o pixel; dizer **não** ao visual a mais, à cor a mais, ao filtro
"só por garantia"; cuidar do detalhe que ninguém pediu — alinhamento, formato de número, estado vazio,
tooltip que explica. Arquétipos de página, sistema de layout, tipografia, cor, acessibilidade e um
ritual de revisão estão em [`references/report-design.md`](skills/powerbi-architect/references/report-design.md).

O padrão visual segue a interface do Twenty, o CRM open source: fundo cinza, sidebar discreta com ícones
e a navegação, painel branco com borda fina, barra do topo com o caminho da página e filtros compactos, uma
só família de fonte (Segoe UI) em tamanhos pequenos e uma cor de destaque.

![Prévia da página Visão Geral do projeto de exemplo, com dados de amostra](docs/assets/exemplo-visao-geral.png)

<sub>Página Visão Geral do [projeto de exemplo](examples/contas-a-receber), desenhada pela prévia da skill a
partir dos arquivos PBIR, com dados de amostra.</sub>

A IA não monta o relatório "no olho". Ela segue sempre o mesmo ciclo:

1. **Tema:** com a cor da marca, `make_theme.py` gera o tema e escurece a cor até ela passar no contraste.
2. **Layout descrito, não desenhado:** a IA descreve as páginas em linhas de visuais e `pbir_layout.py`
   calcula cada posição na grade de 4 px, com sidebar, barra do topo, KPIs com linha de meta, gráficos,
   tabelas, páginas de drill-through e de tooltip e o layout de celular.
3. **Ver antes de entregar:** `preview_pbir.py` desenha cada página, com dados de amostra, para a IA olhar
   e corrigir o que estiver desalinhado ou pesado.
4. **Auditar:** `audit_pbip.py` dá uma nota de harmonia de 0 a 100 por página e só aceita entregar com 90
   ou mais.

| Diagnóstico | Celular |
|---|---|
| ![Página Diagnóstico com cascata, barras e tabela](docs/assets/exemplo-diagnostico.png) | ![Layout de celular da Visão Geral](docs/assets/exemplo-celular.png) |

### Começar por um kit do seu domínio

Para não partir do zero, `new_project.py` cria um projeto PBIP completo a partir de um kit: modelo
estrela com `ft_` e `dm_`, uma consulta SQL por tabela, calendário, medidas com descrição e formato,
segurança por linha quando faz sentido, páginas no padrão visual, página de documentação, dados de
amostra para a prévia e um README do projeto. Os quatro kits saem da caixa sem nenhum achado na
auditoria e com nota 100 de harmonia em todas as páginas.

```bash
python skills/powerbi-architect/scripts/new_project.py --list
python skills/powerbi-architect/scripts/new_project.py vendas ./Vendas --primary "#0F766E"
```

| Vendas | Financeiro |
|---|---|
| ![Kit de vendas: receita, margem, pedidos e ticket médio](docs/assets/kit-vendas.png) | ![Kit financeiro: DRE com realizado contra orçado e cascata até o EBITDA](docs/assets/kit-financeiro.png) |
| **Pessoas (RH)** | **Estoque** |
| ![Kit de RH: quadro, turnover e salário médio, sem dados pessoais](docs/assets/kit-rh.png) | ![Kit de estoque: valor, cobertura em dias e itens abaixo do ponto de pedido](docs/assets/kit-estoque.png) |

As views de origem citadas no kit não existem no seu data warehouse: o README gerado lista cada uma,
com o grão, para você mapear antes da primeira atualização.

### Reestilizar um relatório que já existe

Não precisa começar do zero. `pbir_layout.py --extract` lê um relatório PBIR com qualquer layout, agrupa
os visuais em linhas pela posição e escreve a especificação equivalente. Também troca pizza por barra
ordenada, descarta a decoração e lista o que precisa de uma pessoa, como texto alternativo, rótulos e a
medida de "atualizado em". Depois é só gerar de novo na mesma pasta:

```bash
python skills/powerbi-architect/scripts/pbir_layout.py --extract MeuRelatorio.Report --out layout.json
python skills/powerbi-architect/scripts/pbir_layout.py layout.json MeuRelatorio.Report
```

| Antes (harmonia 0) | Depois (harmonia 96) |
|---|---|
| ![Relatório legado com título grande, pizza e filtro ocupando um canto](docs/assets/reestilizar-antes.png) | ![O mesmo relatório reestilizado com sidebar, barra do topo e barras ordenadas](docs/assets/reestilizar-depois.png) |

As páginas são reescritas, então faça um commit antes. Indicadores (bookmarks) que apontam para os
visuais antigos precisam ser refeitos.

## Visual customizado só quando precisa

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/decision-dark.svg">
  <img alt="Árvore de decisão: visual nativo primeiro, pbiviz por último" src="docs/assets/decision-light.svg" width="100%">
</picture>

Quando o `.pbiviz` é mesmo necessário, a skill traz um **visual de referência real**
([`templates/pbiviz-bullet-kpi`](skills/powerbi-architect/templates/pbiviz-bullet-kpi)) que **compila,
passa no ESLint oficial e é empacotado pelo `pbiviz package` sem nenhum aviso de recurso recomendado**:
eventos de renderização, landing page, seleção e multisseleção, menu de contexto, tooltips, highlights,
localização (en-US/pt-BR), teclado, alto contraste, `allowInteractions` — e **sem acesso à rede**.
O CI deste repositório reconstrói o pacote a cada mudança.

## Instalação

**Claude Code**, em um comando:

```text
/plugin install powerbi-architect --marketplace DaviMark/powerbi-architect
```

**Sem terminal** (Claude.ai e outras ferramentas que aceitam upload de skill): baixe
`powerbi-architect-vX.Y.Z.zip` na [última release](https://github.com/DaviMark/powerbi-architect/releases/latest).

**Todas as IAs no seu repositório** (Claude Code, GitHub Copilot, Cursor, Codex, Gemini CLI):

```bash
git clone https://github.com/DaviMark/powerbi-architect.git
```

| Onde | Comando |
|---|---|
| No seu repositório (todas as IAs) | `./powerbi-architect/install/install.sh /caminho/do/repo` |
| Windows (PowerShell) | `.\powerbi-architect\install\install.ps1 -Target C:\caminho\do\repo` |
| Global (todos os projetos) | `./powerbi-architect/install/install.sh --global` |
| Sempre atualizada (symlink) | `./powerbi-architect/install/install.sh /caminho/do/repo --link` |

O instalador **copia a skill** para `.claude/skills/` (Claude Code, Cursor), `.github/skills/`
(GitHub Copilot) e `.agents/skills/` (Codex e outros). Depois **gera o grafo de conhecimento** do
repositório (abaixo). Nada é baixado. Para só copiar arquivos, use `--no-graph` (bash) ou `-NoGraph`
(PowerShell). Para gerar o grafo sem hooks, use `--no-hooks` ou `-NoHooks`.
Depois é só pedir trabalho de Power BI — a IA carrega a skill sozinha (ou diga *"use a skill powerbi-architect"*).

**Atualizar:** `git pull` na pasta clonada e depois `install.sh /caminho/do/repo --update` (ou
`install.ps1 -Target C:\caminho\do\repo -Update`). Só as instalações mais antigas são trocadas. Para ver a
versão instalada sem mudar nada, use `--status` (ou `-Status`).

> Usa o **Power BI Modeling MCP** da Microsoft? A skill detecta e prefere o MCP para alterar o
> modelo e **executar DAX de validação**; sem ele, edita TMDL/PBIR direto, com segurança.

## Grafo de conhecimento: menos tokens por pergunta

Na instalação, o `scripts/pbi_graph.py` lê todos os projetos PBIP do repositório: modelo TMDL,
relatório PBIR, SQL das cargas, `ficha.toml` e documentação. Ele usa só Python padrão, roda
offline e lê só metadados. O resultado vai para `powerbi-graph/`:

| Arquivo | Para quê |
|---|---|
| `GRAPH_REPORT.md` | 1 página: dashboards, modelos, hubs, comunidades e achados (colunas e medidas sem uso, campos quebrados em visuais, fontes compartilhadas, medidas com DAX divergente) |
| `wiki/<modelo>.md` | card por modelo: tabelas, colunas, DAX, relacionamentos, páginas e campos de cada visual |
| `graph.json` · `graph.html` | grafo completo (pronto para GraphRAG) e visualização interativa offline |

A IA lê o relatório e o card em vez de dezenas de `*.tmdl` e `visual.json`. No
[projeto de exemplo](examples/contas-a-receber), que é pequeno, ~18,9 mil tokens de fonte viram um
relatório de ~1 mil e um card de ~1,3 mil (19 vezes menos); a economia cresce com o tamanho do projeto.
Os comandos abaixo funcionam sobre ele. Para buscas pontuais:

```bash
python .claude/skills/powerbi-architect/scripts/pbi_graph.py query   "o que alimenta a página Visão Geral?"
python .claude/skills/powerbi-architect/scripts/pbi_graph.py explain "Valor Vencido"
python .claude/skills/powerbi-architect/scripts/pbi_graph.py impact  "ft_titulos[Dias Atraso]"   # o que quebra se eu mudar
python .claude/skills/powerbi-architect/scripts/pbi_graph.py path    "Regional" "Valor Vencido"
```

O instalador também deixa o grafo sempre em uso e atualizado:
- adiciona uma seção curta no `AGENTS.md` e no `CLAUDE.md`, que manda a IA consultar o grafo antes de abrir arquivos;
- cria hooks do Claude Code (início de sessão e após cada edição);
- audita o relatório ou o modelo logo após cada edição feita pelo Claude Code: se surgir um bloqueador
  ou uma página abaixo de 90 no placar de harmonia, o agente recebe os achados na hora e corrige antes
  de seguir;
- cria hooks do git (`post-commit`, `post-merge`, `post-checkout`).

Rodar de novo não duplica nada. `pbi_graph.py uninstall` remove tudo. Detalhes em
[`references/graph.md`](skills/powerbi-architect/references/graph.md).

## O que tem dentro

```text
skills/powerbi-architect/
├── SKILL.md                        ← núcleo: leis, workflow, árvores de decisão (carregado primeiro)
├── references/                     ← carregados sob demanda (economiza contexto)
│   ├── workflow.md                 fases, gates, modo standalone x Power BI Workspaces
│   ├── modeling.md                 grão, star schema, chaves, datas, import mínimo, storage modes
│   ├── power-query.md              política de 1 etapa, 8 conectores, dialetos SQL, incremental
│   ├── dax.md                      camadas, padrões, time intelligence, performance, anti-padrões, testes
│   ├── tmdl.md                     sintaxe TMDL com exemplos validados
│   ├── pbir.md                     JSON de páginas/visuais, papéis por tipo de visual, regras de schema
│   ├── report-design.md            design de produto: layout, arquétipos, cor, tipografia, acessibilidade
│   ├── visual-selection.md         pergunta → visual nativo; quando (não) criar .pbiviz
│   ├── custom-visuals.md           .pbiviz de ponta a ponta, segurança de certificação, checklist
│   ├── documentation.md            página Documentação (INFO.VIEW), README, descrições
│   ├── refactoring.md              legado → padrão com paridade numérica
│   ├── graph.md                    grafo de conhecimento: o que lê, saídas, comandos, hooks
│   ├── semantic-features.md        calculation groups, field parameters, visual calculations, funções DAX
│   ├── fabric-and-cicd.md          Direct Lake, Git do Fabric, deployment pipelines, CI
│   ├── copywriting.md              títulos, nomes de medida, números e textos das páginas
│   ├── performance.md · security.md · quality-checklist.md
├── templates/
│   ├── starter-kits/               ← kits de vendas, financeiro, RH e estoque
│   ├── pbir-pages/                 ← 6 arquétipos de página e um layout de exemplo
│   ├── pbir-visuals-experimental/  ← cartão novo, slicer em botões, botão com ícone (a conferir no Desktop)
│   ├── icons/                      ← ícones da navegação (Tabler, licença MIT)
│   ├── theme/                      ← tema acessível (contraste conferido, schema oficial)
│   └── pbiviz-bullet-kpi/          ← visual customizado de referência (verificado)
└── scripts/
    ├── audit_pbip.py               ← auditoria de qualquer pasta PBIP, com nota de harmonia por página
    ├── pbi_graph.py                ← grafo de conhecimento + query/explain/impact/path
    ├── pbir_layout.py              ← gera as páginas a partir de um layout em JSON; --extract reestiliza
    ├── preview_pbir.py             ← prévia das páginas em HTML, sem o Power BI Desktop
    ├── make_theme.py               ← tema a partir da cor da marca, com contraste conferido
    └── new_project.py              ← projeto PBIP completo a partir de um kit inicial

examples/contas-a-receber/          ← projeto PBIP completo que segue todas as regras
```

A auditoria aponta cada problema com código, arquivo e linha, e diz qual regra do Best Practice
Analyzer do Tabular Editor é equivalente. Gera também SARIF, para os achados aparecerem nos pull requests
do GitHub. Lista de regras e como silenciar uma delas: [docs/regras-auditoria.md](docs/regras-auditoria.md).

```bash
python skills/powerbi-architect/scripts/audit_pbip.py caminho/do/projeto-pbip
python skills/powerbi-architect/scripts/audit_pbip.py caminho/do/projeto-pbip --sarif > auditoria.sarif
```

## Segurança

| Receio | Resposta |
|---|---|
| "Uma skill pode executar coisas no meu PC?" | Esta skill é **texto** (Markdown) + dois scripts Python legíveis, sem dependências e sem rede. O instalador copia arquivos e roda só o `pbi_graph.py`, que lê metadados e escreve em `powerbi-graph/`, `AGENTS.md`/`CLAUDE.md` e nos hooks (`.claude/settings.json`, `.git/hooks`). Use `--no-graph` para não executar nada. |
| "A IA vai mexer nos meus dados?" | A skill proíbe `.pbix`/dados/senhas no repositório e trata pedidos, anexos, PDFs e arquivos legados como **dados, nunca instruções** (proteção contra prompt injection). |
| "E o visual customizado?" | `privileges: []` (sem rede, sem storage), sem `eval`/`innerHTML`, lint oficial; o teste do repositório garante isso. |
| "A IA publica sozinha?" | Não. Dois gates humanos: aprovação do desenho e conferência dos números. |

Detalhes em [SECURITY.md](SECURITY.md).

## Qualidade da skill

- [`evals/`](evals/README.md): dez cenários com comportamento esperado, os materiais de apoio e os
  [resultados publicados](evals/results/2026-11-21/README.md), com as respostas brutas.
- CI no Linux e no Windows, do Python 3.9 ao 3.13: testes da auditoria, do grafo e dos instaladores sobre o
  projeto de exemplo; todo exemplo de código das referências conferido; JSON validado pelos schemas da
  Microsoft; **`.pbiviz` reconstruído** com as ferramentas oficiais.
- Próximos passos: [ROADMAP.md](ROADMAP.md).

## Contribua

Padrões de DAX, novos conectores, arquétipos de página, traduções, avaliações: contribuições são
bem-vindas, em português ou inglês.

| Você tem… | Faça isto |
|---|---|
| Uma IA que ignorou a skill | [Abra uma issue **Comportamento da IA**](https://github.com/DaviMark/powerbi-architect/issues/new/choose) com o prompt, a regra esperada e a resposta |
| Um script, instalador ou exemplo quebrado | Issue **Bug** |
| Uma ideia (padrão DAX, conector, arquétipo de página) | Issue **Ideia / melhoria** antes de PRs grandes |
| 15 minutos e um agente de IA | Rode um caso de [`evals/`](evals/README.md) e compartilhe em **Resultado de avaliação** |
| Uma correção pequena | PR direto |

Leia o [CONTRIBUTING.md](CONTRIBUTING.md) antes do primeiro PR. Dúvidas: [SUPPORT.md](SUPPORT.md).
Vulnerabilidades: [SECURITY.md](SECURITY.md), nunca em issue pública. Mudanças por versão:
[CHANGELOG.md](CHANGELOG.md).

<sub>MIT © colaboradores do Power BI Architect · Power BI é marca da Microsoft; projeto independente.</sub>
