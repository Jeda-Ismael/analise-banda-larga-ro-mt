# Banda larga em Rondônia e Mato Grosso: os provedores regionais estão vencendo?

> **Em dezembro de 2019, as grandes operadoras (Oi, Claro, Vivo) tinham 64% dos acessos de banda larga fixa em RO e MT.
> Em julho de 2026, os provedores regionais têm 68%.** Análise de 7 anos de dados abertos da Anatel, 194 municípios e mais de 900 prestadoras.

<!-- Adicionar quando estiverem prontos:
![Demonstração do dashboard](img/demo.gif)
🎥 [Vídeo de 3 minutos explicando os achados](LINK_DO_VIDEO) · 📄 [Dashboard em PDF](dashboard/dashboard_banda_larga_ro_mt.pdf)
-->

📊 **[Baixar o dashboard (.pbix)](dashboard/banda_larga_ro_mt.pbix)**

---

## A pergunta

Donos de provedores de internet (ISPs) do interior querem saber três coisas:
1. **O mercado está mudando?** Quanto os pequenos provedores ganharam das grandes operadoras?
2. **Onde?** Em quais cidades essa virada já aconteceu, e em quais não?
3. **Onde ainda dá para crescer?** Quais municípios têm espaço para um novo provedor ou para expansão?

## Principais achados

**1. O mercado virou, e as grandes operadoras ficaram paradas.**
Os acessos em RO e MT passaram de 628 mil para **1,54 milhão** (×2,5). Os provedores regionais foram de 208 mil para **1,05 milhão** de acessos (×5). As grandes operadoras ficaram praticamente no mesmo lugar (403 mil → 392 mil). Todo o crescimento do mercado foi dos regionais.

| | dez/2019 | jul/2026 |
|---|---|---|
| Provedores regionais | 33% | **68%** |
| Grandes operadoras | 64% | 25% |
| Satélite | 3% | 6% |

**2. Os regionais já lideram em 168 dos 194 municípios.**
Em cidades médias a virada foi completa: em Nova Olímpia (MT), Guajará-Mirim (RO) e Ouro Preto do Oeste (RO), o share dos regionais passa de 90%. As exceções são as maiores cidades: em **Porto Velho (57%)** e **Cuiabá (55%)** as grandes ainda detêm a maior parte do mercado.

**3. O satélite virou o termômetro da demanda não atendida.**
Os acessos via satélite foram de ~19 mil (dez/2022) para **95 mil** (jul/2026), puxados pela Starlink. Ela **é a líder em 31 municípios**, quase todos pequenos, de baixa densidade e sem fibra suficiente. Onde o cliente paga mais caro por satélite, há demanda esperando por fibra.

**4. O mercado se consolida.** O maior "provedor regional" já é um grupo consolidador (Brasil TecPar, 231 mil acessos, ×10 desde 2019), maior que Oi, Claro ou Vivo somando os dois estados.

## Recomendações (para um provedor regional)

1. **Expansão por fibra em cidades lideradas por satélite:** os 31 municípios onde a Starlink lidera têm demanda comprovada e cliente disposto a pagar.
2. **Capitais e cidades-polo** (Porto Velho, Cuiabá, Rondonópolis) são o último mercado grande ainda nas mãos das operadoras nacionais, mas exigem escala.
3. **Atenção à consolidação:** em cidades onde um único grupo passa de 50% de share, a próxima disputa é por aquisição, não por instalação.

## Como foi feito

```
Anatel (zip ~1 GB, 8 GB de CSV)
   │  scripts/01_preparar_dados.py   → leitura em streaming, filtro RO/MT, limpeza, classificação
   ▼
data/processed/  (modelo estrela: 2 fatos + 3 dimensões)
   │  scripts/02_analise_exploratoria.py → números-chave e validação
   ▼
Power BI  (modelo estrela, DAX com medidas semiaditivas, 3 páginas, salvo como .pbip + .pbix)
```

**Ferramentas:** Python (pandas), Power BI (Power Query, DAX), Git.

**Decisões de tratamento que mudam o resultado:**
- **Porte da prestadora:** usei a classificação oficial da Anatel (Pequeno/Grande Porte), mas pelo porte **mais recente de cada CNPJ**, aplicado ao histórico. A base original tem inconsistências: em 2021 a Oi aparece como "Pequeno Porte", o que criava um falso salto de até 44 p.p. no share dos regionais naquele ano (RO).
- **Satélite separado:** a Anatel classifica a Starlink como pequeno porte. Sem separar o satélite, ~95 mil acessos inflariam os "provedores regionais", que concorrem com fibra, não com satélite.
- **Tecnologia:** o campo "Tecnologia" muda de nome entre anos ("Fibra" em 2019, "FTTH" depois). Usei o "Meio de Acesso", que é estável.
- **Acessos são estoque, não fluxo:** o total de um período é o do último mês, nunca a soma dos meses (medida semiaditiva no DAX).
- **Densidade:** o PDF de metadados da Anatel diz "por 100 domicílios", mas os valores batem com **acessos por 100 habitantes** (RO: 528 mil acessos com densidade 30 implica ~1,76 mi de pessoas, a população do estado, não o número de domicílios). Rotulei conforme os dados.

## Reproduzir

1. Baixe a base da Anatel: [acessos_banda_larga_fixa.zip](https://www.anatel.gov.br/dadosabertos/paineis_de_dados/acessos/acessos_banda_larga_fixa.zip) → `data/raw/`
2. `pip install pandas`
3. `python scripts/01_preparar_dados.py`  (≈5 min, pouca memória)
4. `python scripts/02_analise_exploratoria.py`
5. Abra `dashboard/banda_larga_ro_mt.pbix` (ou o projeto `banda_larga_ro_mt.pbip`), ajuste o parâmetro **PastaDados** (*Transformar dados → Editar parâmetros*) para a sua pasta `data/processed/` e clique em **Atualizar**.

O dashboard também está salvo como **Power BI Project (.pbip)**, com o modelo em TMDL e o relatório em PBIR, ou seja, em texto versionável no Git. As decisões de modelagem e as medidas DAX estão explicadas em [`docs/roteiro_dashboard.md`](docs/roteiro_dashboard.md).

## Estrutura

```
├── data/
│   ├── raw/           base original da Anatel (não versionada) + coordenadas dos municípios
│   └── processed/     tabelas prontas para o Power BI
├── scripts/           tratamento e análise em Python
├── dashboard/         .pbix, projeto .pbip (TMDL/PBIR), PDF e tema
├── docs/              roteiro de montagem do dashboard
└── img/               prints e GIF
```

## Fontes
- Anatel, Dados Abertos: [Acessos de banda larga fixa (SCM)](https://www.gov.br/anatel/pt-br/dados/dados-abertos), jan/2019 a jul/2026
- Coordenadas dos municípios: [kelvins/municipios-brasileiros](https://github.com/kelvins/municipios-brasileiros)

---
**Autor:** Jedaías Ismael da Costa · Analista de dados · Aberto a projetos freelance de análise de dados e dashboards em Power BI.
