# Benchmark

**Página: <https://davimark.github.io/powerbi-architect/>**

A cada versão, a mesma IA recebe os mesmos dois pedidos duas vezes: com a skill e sem ela. As
entregas são conferidas por ferramenta, em sete requisitos, sem opinião.

| Versão | Com a skill | Sem a skill | Ganho | Entregas completas com a skill | Tokens com a skill |
|---|---|---|---|---|---|
| [1.3.0](versoes/1.3.0/README.md) | 93% (13 de 14) | 43% (6 de 14) | +50 p.p. | 1 de 2 | 92 mil |
| [1.4.0](versoes/1.4.0/README.md) | **100% (14 de 14)** | 29% (4 de 14) | **+71 p.p.** | **2 de 2** | 96 mil |
| [1.5.0](versoes/1.5.0/README.md) | **100% (14 de 14)** | 29% (4 de 14) | **+71 p.p.** | **2 de 2** | 96 mil |

Claude Sonnet 5.5 nas duas condições. As três versões foram pontuadas com as conferências de hoje. Na 1.5.0, cada execução rodou num
agente novo do Claude Code, com o mesmo pedido e a mesma pasta.

![Página do benchmark](painel.png)

## O que tem nesta pasta

```
benchmarks/
├── README.md        este guia
├── run.py           prepara, registra, pontua e gera a página
├── cenarios/        os dois pedidos (JSON)
├── versoes/<x.y.z>/ tudo o que foi medido em cada versão
│   ├── README.md        resumo em tabelas
│   ├── resultados.json  requisitos, métricas e consumo de cada execução
│   ├── consumo.json     tokens, ferramentas e tempo informados pelo agente
│   ├── execucoes.json   quais execuções existem
│   ├── amostras/        dados de amostra usados no preview
│   ├── entregas/        os projetos entregues, para pontuar de novo
│   └── imagens/         primeiras páginas de cada entrega
├── pagina.html      modelo da página (o run.py injeta os dados)
├── index.html       página gerada, publicada no GitHub Pages
└── painel.png       imagem da página para este README
```

## Os dois cenários

| Cenário | O que a IA recebe | O que se pede |
|---|---|---|
| [Logística](cenarios/s1-logistica.json) | um modelo de entregas que a skill não conhece, sem relatório | visão geral para a diretoria e comparação de transportadoras |
| [Reestilizar](cenarios/s2-reestilizar.json) | um relatório amador (título gigante, pizza, sem texto alternativo) | deixá-lo profissional sem perder informação |

## Os sete requisitos

| Requisito | Conferido por |
|---|---|
| Abre sem erro | schemas da Microsoft e todo campo usado existe no modelo |
| Zero bloqueadores | `audit_pbip.py` |
| Harmonia ≥ 90 | `audit_pbip.py`, nota por página |
| Acessível | `audit_pbip.py`: título e texto alternativo em todo visual, contraste do texto |
| Pixel a pixel | `preview_pbir.py --critique`: texto cortado, sobreposição, gutters, grade, barras com sobra |
| Pedido atendido | as páginas pedidas existem e, na reestilização, nenhum campo sumiu |
| Números seguros | `audit_pbip.py`: nenhum padrão de DAX ou SQL que devolve número errado |

## Medir uma versão nova

1. Mude a versão no `SKILL.md`, para não sobrescrever a anterior.
2. Prepare as quatro pastas e os pedidos:
   ```bash
   python benchmarks/run.py prepare
   ```
3. Rode cada pedido de `.tmp/benchmark/<versão>/runs.json` num agente novo, de dentro da pasta da
   execução. No Claude Code: `claude -p "<pedido>" --output-format json`.
4. Registre o consumo de cada execução:
   ```bash
   python benchmarks/run.py record s1-logistica-com --tokens 95105 --tools 10 --seconds 48 --model "Claude Sonnet 5.5"
   ```
5. Pontue e gere a página:
   ```bash
   python benchmarks/run.py score
   python benchmarks/run.py report
   ```

**Mesma régua para todas as versões.** Quando uma conferência muda, pontue de novo as versões
anteriores antes do `report`. As execuções não rodam outra vez; só a pontuação é refeita:

```bash
python benchmarks/run.py score --versao 1.3.0
```

A página é publicada no GitHub Pages a cada push na `main` que mexa em `benchmarks/`.

## Limites

- Uma execução por cenário e condição. Diferenças pequenas podem ser acaso.
- Os relatórios não são abertos no Power BI Desktop. As imagens vêm do preview da skill.
- A harmonia e a crítica pixel a pixel são regras da própria skill. Por isso há também requisitos
  gerais: abrir sem erro, acessibilidade e pedido atendido.
