# Como o dashboard foi construído (Power BI Desktop)

> O dashboard pronto está em `dashboard/banda_larga_ro_mt.pbix` (e no projeto `.pbip`).
> Este documento registra cada decisão de modelagem, as medidas DAX e o layout, para quem quiser entender ou refazer o processo.

---

## 1. Importar os dados

`Página Inicial → Obter dados → Texto/CSV`, um arquivo por vez, da pasta `data/processed/`:

| Arquivo | O que é |
|---|---|
| `fato_acessos.csv` | Acessos por mês × município × prestadora × categoria × tecnologia |
| `fato_densidade.csv` | Acessos por 100 habitantes, por município e mês |
| `dim_municipio.csv` | 194 municípios de RO/MT, com latitude/longitude |
| `dim_prestadora.csv` | Prestadoras (CNPJ, nome, marca, porte) |

Na janela de importação: **Origem do arquivo = 65001: Unicode (UTF-8)** e **Delimitador = Ponto e vírgula**. Clique em **Transformar dados** (não em Carregar) e, no Power Query:

- `cod_ibge` e `cnpj` → tipo **Texto** (senão o CNPJ perde o zero à esquerda e os relacionamentos quebram)
- `data` → tipo **Data**
- `acessos` → **Número inteiro**; `densidade`, `latitude`, `longitude` → **Número decimal**
- Se os decimais vierem errados: botão direito na coluna → *Alterar tipo → Usando localidade → Português (Brasil)*

`Fechar e aplicar`.

## 2. Tabela calendário

`Modelagem → Nova tabela`:

```DAX
dCalendario =
ADDCOLUMNS (
    CALENDAR ( DATE ( 2019, 1, 1 ), EOMONTH ( MAX ( fato_acessos[data] ), 0 ) ),
    "Ano", YEAR ( [Date] ),
    "Mês", MONTH ( [Date] ),
    "Mês/Ano", FORMAT ( [Date], "mmm/yy" ),
    "AnoMes", YEAR ( [Date] ) * 100 + MONTH ( [Date] )
)
```

Selecione a tabela → `Ferramentas de tabela → Marcar como tabela de datas` → coluna `Date`.
Na coluna `Mês/Ano`: *Classificar por coluna → AnoMes*.

## 3. Relacionamentos (Exibição de modelo)

| De (1) | Para (*) |
|---|---|
| `dCalendario[Date]` | `fato_acessos[data]` |
| `dCalendario[Date]` | `fato_densidade[data]` |
| `dim_municipio[cod_ibge]` | `fato_acessos[cod_ibge]` |
| `dim_municipio[cod_ibge]` | `fato_densidade[cod_ibge]` |
| `dim_prestadora[cnpj]` | `fato_acessos[cnpj]` |

Todos um-para-muitos, filtro em direção única. É um **esquema estrela**. Vale mostrar um print dessa tela no README.

## 4. Medidas DAX

Crie uma tabela vazia `_Medidas` (Inserir dados → OK) para organizar.

> ⚠️ **Conceito-chave:** acessos são um **estoque** (clientes ativos no mês), não um fluxo como vendas.
> Somar janeiro + fevereiro conta o mesmo cliente duas vezes. Por isso a medida base pega sempre
> **o último mês do período selecionado**. Isso é o que se chama de medida semiaditiva, e é um ótimo ponto para citar no vídeo.

```DAX
Acessos =
VAR UltimoMes =
    CALCULATE (
        MAX ( fato_acessos[data] ),
        ALL ( fato_acessos[categoria], fato_acessos[tecnologia] ),
        ALL ( dim_municipio ),
        ALL ( dim_prestadora )
    )
RETURN
    CALCULATE ( SUM ( fato_acessos[acessos] ), dCalendario[Date] = UltimoMes )
```

```DAX
Share % =
DIVIDE ( [Acessos], CALCULATE ( [Acessos], REMOVEFILTERS ( fato_acessos[categoria] ) ) )

Share Regionais % =
CALCULATE ( [Share %], fato_acessos[categoria] = "Provedor regional" )

Share Grandes % =
CALCULATE ( [Share %], fato_acessos[categoria] = "Grande operadora" )

Share Satélite % =
CALCULATE ( [Share %], fato_acessos[categoria] = "Satélite" )

Share Regionais dez/2019 =
CALCULATE ( [Share Regionais %], REMOVEFILTERS ( dCalendario ), dCalendario[Date] = DATE ( 2019, 12, 1 ) )

Ganho Regionais (p.p.) =
( [Share Regionais %] - [Share Regionais dez/2019] ) * 100

Acessos 12m antes =
CALCULATE ( [Acessos], DATEADD ( dCalendario[Date], -12, MONTH ) )

Crescimento 12m % =
DIVIDE ( [Acessos] - [Acessos 12m antes], [Acessos 12m antes] )

Nº Prestadoras =
VAR UltimoMes = CALCULATE ( MAX ( fato_acessos[data] ), ALL ( dim_prestadora ), ALL ( fato_acessos[categoria] ) )
RETURN CALCULATE ( DISTINCTCOUNT ( fato_acessos[cnpj] ), dCalendario[Date] = UltimoMes )

Líder =
VAR t = ADDCOLUMNS ( VALUES ( dim_prestadora[marca] ), "@a", [Acessos] )
RETURN MAXX ( TOPN ( 1, t, [@a], DESC ), dim_prestadora[marca] )

Share do Líder % =
VAR t = ADDCOLUMNS ( VALUES ( dim_prestadora[marca] ), "@a", [Acessos] )
RETURN DIVIDE ( MAXX ( t, [@a] ), [Acessos] )

Acessos por 100 hab =
VAR UltimoMes = CALCULATE ( MAX ( fato_densidade[data] ), ALL ( dim_municipio ) )
RETURN CALCULATE ( AVERAGE ( fato_densidade[densidade] ), dCalendario[Date] = UltimoMes )
```

Formatos: medidas `%` → Porcentagem, 1 casa; `Acessos` → Número inteiro com separador de milhar; `Ganho (p.p.)` → Decimal, 1 casa.

> `Acessos por 100 hab` só faz sentido **por município** (tabela, mapa, dispersão). Não use em cartão de total do estado:
> a média das cidades não é a densidade do estado.

## 5. Tema e cores

`Exibir → Temas → Procurar temas` → `dashboard/tema_banda_larga.json`.

Fixe as cores das categorias em **todos** os visuais (Formatar → Colunas/Linhas → cor por categoria):

- **Provedor regional → verde-petróleo `#0F766E`** (o protagonista da história)
- **Grande operadora → cinza `#94A3B8`**
- **Satélite → âmbar `#D97706`**

Mesma cor, mesma categoria, em todas as páginas.

## 6. As 3 páginas

Tela 16:9 (padrão). Em cada página, **o título é a conclusão**, não o nome do gráfico.

### Página 1: Visão geral
**Título:** *"Em 6 anos, os provedores regionais saíram de 1/3 para 2/3 da banda larga em RO e MT"*

```
┌──────────────────────────────────────────────────────────────┐
│ Título-conclusão                          [Segm. UF] [Período]│
├──────────┬──────────┬──────────┬─────────────────────────────┤
│ Acessos  │ Share    │ Ganho    │ Crescimento 12m             │
│ totais   │ Regionais│ (p.p.)   │                             │
├──────────┴──────────┴──────────┴─────────────────────────────┤
│ Área 100% empilhada: Share % por mês × categoria  (≈60%)     │
├──────────────────────────────┬───────────────────────────────┤
│ Linhas: Acessos por mês      │ Barras: Acessos por tecnologia│
│ × categoria                  │ (último mês)                  │
└──────────────────────────────┴───────────────────────────────┘
```

- Cartões: `Acessos`, `Share Regionais %`, `Ganho Regionais (p.p.)`, `Crescimento 12m %`
- Gráfico principal: **Gráfico de área 100% empilhada**. Eixo X = `dCalendario[Date]` (hierarquia desligada), Y = `Acessos`, Legenda = `categoria`
- Segmentações: `dim_municipio[uf]` e `dCalendario[Ano]`

### Página 2: Municípios
**Título:** *"Regionais já lideram em 168 dos 194 municípios; Cuiabá e Porto Velho são as exceções"*

- **"Mapa" de bolhas** (gráfico de dispersão): X = média de `longitude`, Y = média de `latitude`, Tamanho = `Acessos`, Legenda = `uf`, eixos ocultos. Não usei o Azure Maps porque ele exige conta corporativa Microsoft; a dispersão por coordenadas funciona em qualquer conta e desenha o contorno dos dois estados.
- **Tabela** de municípios: `municipio`, `uf`, `Acessos`, `Share Regionais %`, `Ganho Regionais (p.p.)`, `Líder`, `Share do Líder %`, `Nº Prestadoras`. Formatação condicional (barras de dados) em `Share Regionais %`.
- **Barras horizontais:** Top 10 marcas por `Acessos` com filtro `categoria = Provedor regional` (use Filtro Top N no painel de filtros).
- Clicar num município no mapa filtra a tabela. Isso aparece bem no GIF.

### Página 3: Onde ainda há espaço
**Título:** *"Três tipos de oportunidade: capitais ainda das grandes, cidades pouco atendidas e demanda que só o satélite atende"*

- **Gráfico de dispersão:** Valores = `dim_municipio[municipio]`, X = `Acessos por 100 hab`, Y = `Share Grandes %`, Tamanho = `Acessos`, Legenda = `uf`. Adicione linhas de média (painel Análise) para dividir em quadrantes. Canto superior direito = mercado grande ainda dominado por operadoras nacionais.
- **Tabela "Baixa densidade"**: municípios com `Acessos por 100 hab` < 10 (filtro no visual), com `Líder` e `Share Satélite %`. Aqui aparece a Starlink liderando: **sinal de demanda sem oferta de fibra**.
- **Linha:** `Acessos` por mês com filtro `categoria = Satélite` (de ~19 mil em dez/22 para ~95 mil em jul/26).
- **Caixa de texto** com 3 recomendações (use as do README).

### Rodapé (todas as páginas)
Caixa de texto pequena: *"Fonte: Anatel, Dados Abertos (acessos SCM), jan/2019 a jul/2026. Elaboração: [seu nome]."*

## 7. Conferência antes de publicar

Os valores do dashboard devem bater com o script `scripts/02_analise_exploratoria.py`:

| Checagem (jul/2026, RO+MT) | Valor esperado |
|---|---|
| Acessos totais | 1.541.027 |
| Share regionais | ≈ 68,4% |
| Share regionais dez/2019 | ≈ 33,2% |
| Porto Velho: share grandes | ≈ 57,2% |
| Municípios onde regionais > 50% | 168 de 194 |

## 8. Material de vitrine

1. **Prints** (1 por página) → `img/pagina1.png`, `img/pagina2.png`, `img/pagina3.png`
2. **GIF** (15 a 25 s) com [ScreenToGif](https://www.screentogif.com/): troque a UF, clique num município no mapa, passe o mouse na dispersão → `img/demo.gif`
3. **PDF**: `Arquivo → Exportar → Exportar para PDF` → `dashboard/dashboard_banda_larga_ro_mt.pdf`
4. **Vídeo** (2 a 3 min, Loom ou YouTube não listado). Roteiro:
   - 0:00 a 0:20: a pergunta ("pequeno provedor está ganhando das grandes em RO e MT?")
   - 0:20 a 1:30: os 3 achados, uma página por vez
   - 1:30 a 2:15: o que um dono de provedor faz com isso (as recomendações)
   - 2:15 a 2:40: bastidores (dados da Anatel, Python, modelo estrela, medida semiaditiva)
