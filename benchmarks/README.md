# Benchmark: a skill em cada versão contra a IA sem a skill

Toda versão nova da skill passa pelo mesmo teste. A mesma IA recebe os mesmos pedidos duas vezes: uma
com a skill daquela versão e outra sem skill nenhuma. As entregas são conferidas pelos mesmos
requisitos, sempre por ferramenta. Assim:
- **na versão X**, a comparação é a skill X contra a IA sem a skill;
- **na versão Y**, a comparação é a skill Y contra a IA sem a skill;
- **entre versões**, a página mostra quanto cada versão melhorou (ou piorou) nos mesmos critérios.

![Painel do benchmark da versão 1.3.0](painel.png)

## Versão 1.3.0, medida em 24/11/2026

Com Claude Sonnet 5.5 nas duas condições, 5 execuções com a skill e 5 sem:

| | Com a skill | Sem a skill |
|---|---|---|
| Requisitos atendidos | **33 de 35 (94%)** | 17 de 35 (49%) |
| Entregas que atendem a tudo | **3 de 5** | 0 de 5 |
| Abrem sem erro | **5 de 5** | 3 de 5 |
| Harmonia média das páginas | **99,8** | 40 |
| Tokens por execução (média) | 99 mil | 81 mil |
| Tempo por execução (média) | 93 s | 46 s |

Com a skill, a IA gasta cerca de 1,2 vez mais tokens e o dobro do tempo, porque roda a auditoria e a
crítica do preview e corrige o que encontram. Sem a skill, duas das cinco entregas nem abririam no Power
BI Desktop (erro de schema). As duas entregas com a skill que não atendem a tudo falham na crítica pixel
a pixel: rótulos de clientes cortados numa página nova e uma tabela com mais linhas do que cabem. Detalhes
por execução: [`results/1.3.0/README.md`](results/1.3.0/README.md).

**Abra [`index.html`](index.html)** para ver os números e as imagens. Os dados de cada versão ficam em
[`results/<versão>/`](results), com um resumo em Markdown, o `resultados.json`, o `consumo.json` e as
imagens das páginas entregues.

## Os cinco cenários

| Cenário | O que a IA recebe | O que se pede |
|---|---|---|
| [Logística](scenarios/s1-logistica.json) | modelo de entregas que a skill não traz, sem relatório | visão geral para a diretoria e comparação de transportadoras |
| [Atendimento](scenarios/s2-atendimento.json) | modelo de chamados ([`models/atendimento.json`](models/atendimento.json)) | visão geral para a gerência e comparação de equipes |
| [Compras](scenarios/s3-compras.json) | modelo de pedidos de compra ([`models/compras.json`](models/compras.json)) | visão geral para a diretoria e avaliação de fornecedores |
| [Edições manuais](scenarios/s4-edicoes-manuais.json) | projeto de vendas editado à mão depois da última edição da IA | uma página nova, sem perder as edições |
| [Reestilizar](scenarios/s5-reestilizar.json) | relatório amador (título gigante, pizza, sem texto alternativo) | deixá-lo profissional sem perder informação |

Cada cenário roda uma vez com a skill e uma vez sem, e a ordem entre as condições alterna de um
cenário para o outro. São 5 execuções com a skill e 5 sem por versão.

## Os sete requisitos

| Requisito | Conferido por |
|---|---|
| Abre sem erro | JSON válido nos schemas da Microsoft e todo campo usado pelos visuais existe no modelo |
| Zero bloqueadores | `audit_pbip.py` |
| Harmonia ≥ 90 | `audit_pbip.py`, nota por página |
| Acessível | `audit_pbip.py`: título e texto alternativo em todo visual de dados, contraste do texto |
| Pixel a pixel | `preview_pbir.py --critique`: texto cortado, sobreposição, gutters, grade de colunas |
| Pedido atendido | as páginas pedidas existem; no cenário 4, as edições manuais continuam lá; no 5, nenhum campo mostrado antes sumiu |
| Números seguros | `audit_pbip.py`: nenhum padrão de DAX ou SQL que devolve número errado (`PBI032`, `PBI070`–`PBI077`) |

Além dos requisitos, cada execução registra o **consumo**: tokens, chamadas de ferramenta e tempo,
como o agente informa ao terminar. O resumo traz a média por condição.

## Como medir uma versão nova

```bash
python benchmarks/run.py prepare
```

O comando cria as 10 pastas em `.tmp/benchmark/<versão>/` e o arquivo `runs.json` com o pedido de cada
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

- Uma execução por cenário e condição. Diferenças pequenas podem ser acaso; o histórico de versões
  mostra a tendência.
- Os relatórios não são abertos no Power BI Desktop. As imagens vêm do preview da skill, que é uma
  aproximação.
- Todas as entregas são desenhadas com os mesmos dados de amostra. Uma medida criada pela IA que não está
  na amostra aparece no preview com o próprio nome no lugar do valor.
- No cenário 4, a crítica conta só os achados novos: o desalinhamento causado pela edição manual do
  usuário, que a IA é obrigada a manter, não pesa contra nenhuma das condições.
- A nota de harmonia e a crítica pixel a pixel são regras da própria skill, que a IA sem a skill não
  conhece. Por isso, há também requisitos gerais: abrir sem erro, acessibilidade e pedido atendido.
