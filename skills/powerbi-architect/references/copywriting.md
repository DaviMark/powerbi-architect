# Copywriting: the words on the page

Half of what makes a report feel designed is the text: titles, labels, numbers, empty states. Write in
the user's language (examples below are Brazilian Portuguese, the most common case for this skill) and
in the business's words, never the database's.

## 1. Titles
| Element | Rule | Good | Bad |
|---|---|---|---|
| Page (breadcrumb) | the topic, 1–3 words | `Visão Geral`, `Clientes`, `Diagnóstico` | `Página 1`, `Dashboard Principal` |
| Visual | the question it answers or the conclusion, sentence case | `Vencido por regional`, `Clientes que concentram o vencido` | `Soma de Valor por Regional`, `Gráfico 3` |
| Dynamic title (measure) | the conclusion with the number | `Vencido: R$ 4,2 mi (22,6% do saldo)` | `Valor Vencido (R$)` |
| KPI label | what the number is, ≤ 4 words | `Saldo em aberto`, `% do saldo vencido` | `Total Valor Aberto Soma` |

Sentence case (only the first word and proper nouns capitalized). No final period. No unit in the
title if the number already shows it.

## 2. Names users see
- **Measures** are read in tooltips, tables and the field list: business words with accents,
  `Atraso Médio (dias)`, `% Vencido`, `Ticket Médio`. Never `Dias Atraso Medio`, `vl_total`, `Measure 3`.
- **Columns** shown in visuals: `Cliente`, `Segmento`, `Faixa de Atraso`, not `nm_cliente`, `ds_segmento`.
  Table names (`ft_`, `dm_`) are for developers; users never see them in a good report.
- **Folders** group measures by meaning: `Valores`, `Indicadores`, `Metas`, `Textos`, `Cores`.

## 3. Numbers
| Where | Format (pt-BR) | Example |
|---|---|---|
| KPI value | compact, 1 decimal | `R$ 4,2 mi`, `R$ 812 mil`, `22,6%`, `41` |
| Table / tooltip | full, thousands separator | `R$ 4.218.300`, `22,6%` |
| Percentage points | `p.p.` | `▲ 2,3 p.p.` |
| Days, counts | integer + unit in the label | `41 dias`, `312 clientes` |
| Dates | `dd/mm/aaaa`; months `mmm/aa` | `21/11/2026`, `nov/26` |

One precision per measure everywhere. Units in the title or the label, never both.

## 4. Lines that explain
- **KPI line**: context or distance to a reference, with the arrow first:
  `▲ 7,6 p.p. acima da meta de 15%`, `312 clientes com parcela vencida`, `R$ 14,4 mi ainda a vencer`.
- **Updated at**: `Atualizado em 21/11/2026 08:00` (top bar, right).
- **Empty state** (measure returning text when there is no data): `Sem dados para o filtro selecionado`.
- **Tooltip pages**: a title that names the hovered item: `Vencido por faixa nesta regional`.
- **Alt text**: what the visual shows and the key takeaway, one sentence:
  `Valor vencido por regional, do maior para o menor`.

## 5. Tone
Neutral, precise, short. No exclamation marks, no emoji, no jargon (`YoY`, `MTD` only if the audience
uses them), no blame (`clientes inadimplentes` → `clientes com parcela vencida`).

## 6. Words that sound machine-written
Readers spot generated text in a second, and then stop trusting the numbers next to it. This applies to
titles, alt text, KPI lines, the documentation page, the README and the delivery message.
`audit_pbip.py` flags the first three, and emoji, in visual titles and alt text (PBI080).

| Pattern | Instead |
|---|---|
| A dash joining two clauses: `Vencido — concentrado no Sul` | a colon, a comma or two sentences: `Vencido concentrado no Sul` |
| Empty praise: `robusto`, `abrangente`, `poderoso`, `incrível`, `insights` | the property itself: `atualizado às 8h`, `com 312 clientes` |
| Filler openers: `Além disso`, `Vale ressaltar`, `Vale destacar`, `É importante notar`, `Em resumo`, `Em suma` | start with the fact |
| Lists of three by habit (`rápido, confiável e escalável`) | as many items as there are: two, four |
| Bold or italics on every paragraph | bold marks structure (labels, key terms), not emphasis |
| Sentences about the text itself: `Esta página mostra…`, `Aqui você encontra…` | say what it shows: `Vencido por regional` |
| The same point said twice in different words | keep the one with the number |

## 7. Before delivering
Read only the words of each page from top to bottom: breadcrumb, KPI labels and lines, visual titles.
They should tell the story on their own. Then check one measure name in a tooltip and one empty state,
and read the delivery text once against §6.
