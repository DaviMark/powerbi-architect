# Benchmark: a skill em cada versão contra a IA sem a skill

Toda versão nova da skill passa pelo mesmo teste. A mesma IA recebe os mesmos dois pedidos duas vezes:
uma com a skill daquela versão e outra sem skill nenhuma. São 4 execuções por versão, poucos minutos ao
todo. As entregas são conferidas pelos mesmos
requisitos, sempre por ferramenta. Assim:
- **na versão X**, a comparação é a skill X contra a IA sem a skill;
- **na versão Y**, a comparação é a skill Y contra a IA sem a skill;
- **entre versões**, a página mostra quanto cada versão melhorou (ou piorou) nos mesmos critérios.

![Painel do benchmark da versão 1.3.0](painel.png)

## Versão 1.3.0, medida em 24/11/2026

Com Claude Sonnet 5.5 nas duas condições, 2 execuções com a skill e 2 sem:

| | Com a skill | Sem a skill |
|---|---|---|
| Requisitos atendidos | **13 de 14 (93%)** | 6 de 14 (43%) |
| Entregas que atendem a tudo | **1 de 2** | 0 de 2 |
| Abrem sem erro | **2 de 2** | 1 de 2 |
| Harmonia média das páginas | **100** | 43 |
| Tokens por execução (média) | 92 mil | 77 mil |
| Tempo por execução (média) | 47 s | 38 s |

Com a skill, a IA gasta cerca de 1,2 vez mais tokens e um pouco mais de tempo, porque roda a auditoria e
a crítica do preview e corrige o que encontram. Sem a skill, o relatório de logística nem abriria no
Power BI Desktop (erro de schema). A entrega com a skill que não atende a tudo é a reestilização: a
tabela de clientes tem mais linhas do que cabem no visual. Detalhes
por execução: [`results/1.3.0/README.md`](results/1.3.0/README.md).

**Abra [`index.html`](index.html)** para ver os números e as imagens. Os dados de cada versão ficam em
[`results/<versão>/`](results), com um resumo em Markdown, o `resultados.json`, o `consumo.json` e as
imagens das páginas entregues.

## Os dois cenários

| Cenário | O que a IA recebe | O que se pede |
|---|---|---|
| [Logística](scenarios/s1-logistica.json) | modelo de entregas que a skill não traz, sem relatório | visão geral para a diretoria e comparação de transportadoras |
| [Reestilizar](scenarios/s2-reestilizar.json) | relatório amador (título gigante, pizza, sem texto alternativo) | deixá-lo profissional sem perder informação |

Os dois cobrem as situações mais diferentes: criar do zero e consertar o que já existe. Cada cenário roda
uma vez com a skill e uma vez sem, e a ordem entre as condições alterna de um cenário para o outro.

## Os sete requisitos

| Requisito | Conferido por |
|---|---|
| Abre sem erro | JSON válido nos schemas da Microsoft e todo campo usado pelos visuais existe no modelo |
| Zero bloqueadores | `audit_pbip.py` |
| Harmonia ≥ 90 | `audit_pbip.py`, nota por página |
| Acessível | `audit_pbip.py`: título e texto alternativo em todo visual de dados, contraste do texto |
| Pixel a pixel | `preview_pbir.py --critique`: texto cortado, sobreposição, gutters, grade de colunas |
| Pedido atendido | as páginas pedidas existem; na reestilização, nenhum campo mostrado antes sumiu |
| Números seguros | `audit_pbip.py`: nenhum padrão de DAX ou SQL que devolve número errado (`PBI032`, `PBI070`–`PBI077`) |

Além dos requisitos, cada execução registra o **consumo**: tokens, chamadas de ferramenta e tempo,
como o agente informa ao terminar. O resumo traz a média por condição.

## Como medir uma versão nova

```bash
python benchmarks/run.py prepare
```

O comando cria as 4 pastas em `.tmp/benchmark/<versão>/` e o arquivo `runs.json` com o pedido de cada
execução. Rode cada pedido num agente novo, com o mesmo modelo nas duas condições:
- **Claude Code:** `claude -p "<pedido>" --output-format json`, de dentro da pasta da execução. O JSON de
  saída traz tokens e duração.
- **Subagentes**, como na primeira medição.

Registre o consumo de cada execução:

```bash
python benchmarks/run.py record s1-logistica-com --tokens 95105 --tools 10 --seconds 48 --model "Claude Sonnet 5.5"
```

Depois, confira os requisitos e gere as imagens:

```bash
python benchmarks/run.py score
```

Por fim, atualize a página com todas as versões medidas:

```bash
python benchmarks/run.py report
```

A versão vem do `SKILL.md`. Mude-a antes de medir, para não sobrescrever a anterior.

## Limites

- Dois cenários e uma execução por cenário e condição, para medir rápido. Diferenças pequenas podem ser
  acaso; o histórico de versões mostra a tendência.
- Os relatórios não são abertos no Power BI Desktop. As imagens vêm do preview da skill, que é uma
  aproximação.
- Todas as entregas são desenhadas com os mesmos dados de amostra. Uma medida criada pela IA que não está
  na amostra aparece no preview com o próprio nome no lugar do valor.
- A nota de harmonia e a crítica pixel a pixel são regras da própria skill, que a IA sem a skill não
  conhece. Por isso, há também requisitos gerais: abrir sem erro, acessibilidade e pedido atendido.
