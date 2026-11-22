# Calibrar o preview com o Power BI Desktop

O `preview_pbir.py` desenha as páginas sem o Power BI, a partir dos arquivos PBIR e do tema. Posição,
tamanho, cores e fontes vêm direto dos arquivos e batem com o Desktop. Já os espaçamentos internos de
cada visual (onde o título começa, quanto o eixo ocupa, o recuo das células de uma tabela) são
aproximações. Elas ficam reunidas em `CALIBRATION`, no início do script, e esta página explica como
conferir essas aproximações contra o Desktop e propor ajustes.

## 1. Tirar as capturas no Desktop

1. Abra o projeto no Power BI Desktop (o [exemplo](../examples/contas-a-receber) serve).
2. Em **Exibir › Exibição da página**, escolha **Tamanho real**. A página de 1280 × 720 aparece em
   tamanho real.
3. Deixe a escala de exibição do Windows em 100 % e recolha os painéis de filtros, visualizações e dados.
4. Capture só a área da página (Ferramenta de Captura, modo retângulo) e salve uma imagem por página:
   `page-1.png`, `page-2.png`... na ordem das abas.

Se a imagem não tiver exatamente 1280 × 720, tudo bem: o preview a estica para o tamanho da página.
Mas quanto mais perto do tamanho real, mais confiável a comparação.

## 2. Comparar

```bash
python skills/powerbi-architect/scripts/preview_pbir.py examples/contas-a-receber/ContasReceber.Report \
  --sample examples/contas-a-receber/preview-sample.json --overlay capturas/ --out comparar.html
```

Abra `comparar.html`. Cada página mostra a captura do Desktop por cima do preview, e o controle no topo
muda a transparência. Onde os dois coincidem, a imagem fica nítida. Onde não coincidem, aparecem bordas
e textos duplicados, e é aí que o preview erra.

## 3. Ajustar

Crie um arquivo com só as chaves que quer mudar e gere de novo com `--calibration`:

```json
{"title_padding": "8px 12px 0", "chart_reserved_height": 56}
```

```bash
python skills/powerbi-architect/scripts/preview_pbir.py examples/contas-a-receber/ContasReceber.Report \
  --sample examples/contas-a-receber/preview-sample.json --overlay capturas/ \
  --calibration calibracao.json --out comparar.html
```

| Chave | O que controla |
|---|---|
| `title_padding` | recuo do título dentro do contêiner do visual |
| `card_value_padding` | recuo do valor do cartão abaixo do rótulo |
| `table_cell_padding` | recuo das células de tabela e matriz |
| `table_margin` | margem da grade da tabela dentro do contêiner |
| `slicer_header_padding` | recuo do cabeçalho da segmentação |
| `chart_padding` | recuo da área do gráfico |
| `chart_reserved_height` | altura que título e rótulos de eixo ocupam, em px |

Chaves desconhecidas são recusadas, com a lista das válidas.

## 4. Compartilhar

Achou valores que encaixam melhor? Abra um PR que altere `CALIBRATION` em
`skills/powerbi-architect/scripts/preview_pbir.py`. Na descrição, anexe uma captura do `comparar.html`
antes e depois do ajuste e informe a versão do Power BI Desktop usada. Diferenças que um número não
resolve, como um visual inteiro desenhado de outro jeito, viram uma issue **Bug** com as duas imagens.
