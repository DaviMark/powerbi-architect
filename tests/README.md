# Testes

Só biblioteca padrão do Python. Rode tudo da raiz do repositório:

```bash
python -m unittest discover -s tests -v
```

Um arquivo só: `python -m unittest tests.test_audit -v`. O CI roda tudo no Linux e no Windows, do
Python 3.9 ao 3.13.

## O que cada arquivo testa

| Arquivo | Script testado | O que garante |
|---|---|---|
| `test_skill.py` | `SKILL.md` e `references/` | estrutura da skill, links que resolvem, custo de contexto dentro do orçamento |
| `test_references.py` | exemplos das referências | todo trecho de código das referências é válido |
| `test_audit.py` | `audit_pbip.py` | cada regra, silenciamento, formatos de saída, linha de comando |
| `test_layout.py` | `pbir_layout.py` | grade de 4 px, alturas automáticas, meta e cor nas barras, Top N, `--extract` |
| `test_merge.py` | `pbir_layout.py` | edições feitas à mão sobrevivem a uma nova geração |
| `test_changes.py` | `pbip_changes.py` | edições feitas à mão são percebidas e descritas |
| `test_preview.py` | `preview_pbir.py` | números no formato da amostra, meta, cores, crítica pixel a pixel |
| `test_make_theme.py` | `make_theme.py` | contraste, fontes e paleta do tema |
| `test_kits.py` | `new_project.py` | os quatro kits saem sem achados e com nota 100 |
| `test_example.py` | `pbi_graph.py` | grafo do projeto de exemplo e explorador visual |
| `test_reconcile.py` | `reconcile.py` | números do relatório contra a origem |
| `test_install.py` | `install/` | instaladores copiam, atualizam e geram o grafo |
| `test_benchmark.py` | `benchmarks/run.py` | cenários, projetos iniciais e conferências do benchmark |

## Arquivos de apoio

- `legacy_report.py` monta um relatório amador de propósito, usado nos testes de reestilização e no
  cenário de reestilizar do benchmark.
- `fixtures/` guarda entradas fixas dos testes.

Testes que precisam do Edge, Chrome ou Chromium (crítica pixel a pixel e imagens) são pulados quando
não há navegador. Os de schema só rodam com `jsonschema` instalado.
