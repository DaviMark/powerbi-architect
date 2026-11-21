# E03 fixture: `bi.vw_titulos_receber` (SQL Server, 60 columns)

Paste this file into the prompt together with the business questions below.

## Business questions
1. How much is overdue today, by regional and by customer segment?
2. What is the average days past due (weighted by open amount) per month for the last 24 months?
3. Which 20 customers concentrate the overdue amount, and what share of the total do they represent?
4. How much was received per month versus how much was due in that month?

## Columns

| # | Column | Type |
|---|---|---|
| 1 | `id_titulo` | bigint |
| 2 | `numero_titulo` | varchar(20) |
| 3 | `parcela` | smallint |
| 4 | `id_cliente` | int |
| 5 | `cliente_nome` | varchar(120) |
| 6 | `cliente_cpf_cnpj` | varchar(18) |
| 7 | `cliente_email` | varchar(120) |
| 8 | `cliente_telefone` | varchar(20) |
| 9 | `cliente_endereco` | varchar(200) |
| 10 | `cliente_cidade` | varchar(60) |
| 11 | `cliente_uf` | char(2) |
| 12 | `cliente_segmento` | varchar(30) |
| 13 | `cliente_classificacao_risco` | char(1) |
| 14 | `id_vendedor` | int |
| 15 | `vendedor_nome` | varchar(80) |
| 16 | `vendedor_email` | varchar(120) |
| 17 | `id_regional` | int |
| 18 | `regional_nome` | varchar(40) |
| 19 | `id_filial` | int |
| 20 | `filial_nome` | varchar(60) |
| 21 | `filial_cnpj` | varchar(18) |
| 22 | `data_emissao` | date |
| 23 | `data_vencimento` | date |
| 24 | `data_vencimento_original` | date |
| 25 | `data_pagamento` | date |
| 26 | `data_baixa` | date |
| 27 | `data_cadastro` | datetime2 |
| 28 | `data_alteracao` | datetime2 |
| 29 | `usuario_cadastro` | varchar(40) |
| 30 | `usuario_alteracao` | varchar(40) |
| 31 | `valor_original` | decimal(18,2) |
| 32 | `valor_aberto` | decimal(18,2) |
| 33 | `valor_pago` | decimal(18,2) |
| 34 | `valor_juros` | decimal(18,2) |
| 35 | `valor_multa` | decimal(18,2) |
| 36 | `valor_desconto` | decimal(18,2) |
| 37 | `valor_abatimento` | decimal(18,2) |
| 38 | `moeda` | char(3) |
| 39 | `taxa_cambio` | decimal(18,6) |
| 40 | `id_forma_pagamento` | int |
| 41 | `forma_pagamento` | varchar(30) |
| 42 | `id_portador` | int |
| 43 | `portador_nome` | varchar(60) |
| 44 | `banco_codigo` | char(3) |
| 45 | `agencia` | varchar(10) |
| 46 | `conta` | varchar(20) |
| 47 | `nosso_numero` | varchar(30) |
| 48 | `linha_digitavel` | varchar(60) |
| 49 | `status_titulo` | varchar(20) |
| 50 | `flag_protestado` | bit |
| 51 | `flag_renegociado` | bit |
| 52 | `id_titulo_origem` | bigint |
| 53 | `observacao` | varchar(500) |
| 54 | `centro_custo` | varchar(20) |
| 55 | `conta_contabil` | varchar(20) |
| 56 | `id_pedido` | bigint |
| 57 | `numero_nota_fiscal` | varchar(20) |
| 58 | `serie_nota_fiscal` | varchar(5) |
| 59 | `chave_nfe` | varchar(44) |
| 60 | `hash_integracao` | varchar(64) |
