# Sports Market Compass <a href="#"><img src="https://github.githubassets.com/images/icons/emoji/unicode/1f1ee-1f1f9.png?v8" width="28" alt="Versione italiana"/></a> <a href="../README.md"><img src="https://github.githubassets.com/images/icons/emoji/unicode/1f1ec-1f1e7.png?v8" width="28" alt="English version"/></a>

![CI](https://github.com/aleattene/sports-market-compass/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.13-blue)
![Pandas](https://img.shields.io/badge/Pandas-Data%20Analysis-blue)
![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-orange)
![Matplotlib](https://img.shields.io/badge/Matplotlib-Visualization-green)
![License](https://img.shields.io/badge/License-MIT-blue)
![Last Commit](https://img.shields.io/github/last-commit/aleattene/sports-market-compass)
<!-- [![Coverage](https://codecov.io/gh/aleattene/sports-market-compass/branch/main/graph/badge.svg)]-->
<!-- (https://codecov.io/gh/aleattene/sports-market-compass) -->

> La bussola indica la direzione: dove, cosa e quanto. Non la rotta.

---

Analisi del mercato sportivo italiano costruita su due fonti pubbliche:
- il registro ufficiale delle società sportive
- una piattaforma software per la gestione di società sportive.

Da qui la domanda fondamentale: di tutto il mercato sportivo italiano,
quanto è già servito dalla piattaforma e quanto è ancora da servire?

---

<br/>

## L'analisi, in tre atti

1. **Dimensione del mercato**: i totali del registro per provincia, cioè quanto
   è grande ogni mercato locale.
2. **Copertura**: presenza della piattaforma vs totali del registro, il gap
   di copertura provincia per provincia.
3. **Direzione**: matrice di priorità e ranking a livelli, dove puntano
   insieme la dimensione del mercato e l'ampiezza del gap.

Il notebook ([`01_coverage_gap_analysis.ipynb`](../notebooks/01_coverage_gap_analysis.ipynb))
percorre l'intero arco a profondità EDA. La roadmap approfondisce il terzo
atto: soglia di investibilità, attractiveness score (dimensione × gap ×
diversità sport × trend registrazioni), allocatore parametrico di budget
(l'importo non è un dato raccolto ma un parametro libero, ripartito tra le
province in proporzione allo score).

---

<br/>


## Le figure chiave

<!-- *Renderizzate in locale da una raccolta reale (vedi la sezione Dati e privacy).*-->

<br/>

![Copertura della piattaforma nelle province italiane](../reports/figures/it/italy_choropleth.png)

<br/>

![Gap di copertura per regione](../reports/figures/it/coverage_gap_by_region_stacked.png)

<br/>

![Matrice di priorità di espansione](../reports/figures/it/priority_matrix.png)

<br/>

Un'analisi più dettagliata è presente nel **report** e/o nella **dashboard interattiva**:

- [Executive Report](../reports/it/REPORT.md).
- [Dashboard interattiva (Looker Studio)](https://datastudio.google.com/s/tDAIpFPxjls)
*(in corso di allineamento allo snapshot corrente)*.

---

<br/>


## Dati e privacy

Questo repository **non contiene alcun dataset reale**:

- `reports/` (figure e report) è renderizzato da una
  pipeline privata di raccolta dati, rispettosa di robots.txt e rate
  limiting, con sanitizzazione alla fonte;
- `data_sample/` è **interamente sintetico**: geografia reale (nomi e sigle
  di provincia sono fatti pubblici), valori auto-generati in maniera
  deterministica ([`generate_data_sample.py`](../scripts/generate_data_sample.py), con seed fisso);
- a runtime il notebook carica `data/` (i tuoi dati, gitignored) se presente,
  altrimenti ripiega sul sample: un clone fresco gira end-to-end.

---

<br/>

### Porta i tuoi dati

Metti questi file in `data/` (schema identico al sample):

| File | Colonne / campi | Ruolo |
|------|-----------------|-------|
| `registry_entity_counts_by_province.csv` | `region_id, region_name, province_id, province_name, province_abbr, entities_total` | totali di mercato per provincia |
| `platform_entity_counts_by_province.csv` | `region_code, region_name, province_abbr, platform_entities` | copertura per provincia |
| `platform_entities.json` | `{dimension, retrieved_at, count, sport_areas[], items:[{sport[], registration_year, province_abbr, region_code}]}` | opzionale: abilita le sezioni aree sportive e trend |

Il campo `sport` contiene **valori a livello di area** (vedi la prima nota di metodo).

---

<br/>

## Note di metodo e limiti dichiarati

- **Dimensione sport a granularità di area**. La fonte descrive le società con etichette sportive puntuali e in continua
evoluzione; la pipeline di raccolta, nel rispetto della privacy dei dati, le raggruppa in 16 aree
ispirate alle federazioni sportive prima dell'export. Analisi, figure e contratto dati usano solo le aree, ovvero una tassonomia stabile e indipendente
dalla fonte, dichiarata dal payload stesso (`sport_areas`).

- **Armonizzazione province sarde**. La piattaforma conserva la sigla provincia vigente all'iscrizione di ogni società,
quindi le sigle abolite dalla riforma del 2016 (CI, OG, OT) convivono con quelle attuali.
Vengono rimappate sulle province subentranti (CI in SU, OG in NU, OT in SS), cioè sull'assetto del registro alla
data dello snapshot. Armonizzazione a senso unico, dalla piattaforma verso il registro.

- **Limite dichiarato**. Le sigle sopravvissute al 2016 (CA in primis) non sono verificabili sotto il livello
provinciale. La provincia è la granularità più fine raccolta, privacy by design.
La riforma in arrivo riassegnerà SU/VS/OG/OT a nuove province: la mappa è versionata e andrà rivista quando le fonti
la recepiranno (per questo oggi non esiste una voce VS).

- **Parsing robusto dei codici**. La sigla di Napoli è letteralmente `NA`: le letture CSV la proteggono esplicitamente
dall'essere interpretata come valore mancante (default di pandas), che la farebbe sparire in silenzio da merge ed
etichette.

---

<br/>

## Struttura del repository

```
sports-market-compass/
├── README.md                             # inglese (canonico); versione italiana in /it
├── notebooks/
│   └── 01_coverage_gap_analysis.ipynb    # EDA notebook
├── reports/
│   ├── REPORT.md                         # risultati commentati dell'analisi (IT in reports/it/)
│   └── figures/                          # render da raccolta reale (IT in figures/it/)
├── geo/                                  # confini di province e regioni (geodati pubblici)
├── data_sample/                          # sample sintetico (geografia reale, valori auto-generati)
├── scripts/
│   └── generate_data_sample.py           # generatore sample sintetico
├── tests/
│   └── test_data_contract.py             # test del contratto dati sul sample
├── data/                                 # dataset reale (gitignored, opzionale)
├── requirements.txt                      # dipendenze di progetto
├── .github/
│   └── workflows/ci.yml                  # CI: igiene, determinismo, test, notebook
└── .pre-commit-config.yaml               # nbstripout: mai output di notebook nella history
```

---

<br/>

## Riproducibilità

Il notebook gira end-to-end anche su un clone appena scaricato: senza `data/`
usa il sample sintetico, nessun dato reale richiesto. Prerequisiti: Git e
Python 3.13+.

**1. Clona il repository ed entra nella cartella**: scarica il progetto da
GitHub e sposta la shell al suo interno.

```bash
git clone https://github.com/aleattene/sports-market-compass.git
cd sports-market-compass
```

**2. Crea l'ambiente virtuale**: un'installazione Python isolata e dedicata
al progetto, così le dipendenze non toccano il sistema.

```bash
python3 -m venv .venv      # macOS / Linux
py -3 -m venv .venv        # Windows
```

**3. Attiva l'ambiente**: da qui in poi `python` e `pip` puntano all'ambiente
del progetto (il prompt mostra `(.venv)`).

```bash
source .venv/bin/activate      # macOS / Linux
.venv\Scripts\activate         # Windows (PowerShell: .venv\Scripts\Activate.ps1)
```

**4. Installa le dipendenze**: legge `requirements.txt` e installa le librerie
alle versioni indicate.

```bash
pip install -r requirements.txt
```

**5. Installa l'hook pre-commit**: attiva nbstripout, che ripulisce in
automatico gli output dei notebook a ogni commit.

```bash
pre-commit install
```

**6. Apri il notebook**: avvia Jupyter nel browser, direttamente sul notebook
dell'analisi.

```bash
jupyter lab notebooks/01_coverage_gap_analysis.ipynb
```

Il sample si rigenera con `python scripts/generate_data_sample.py`
(deterministico: stesso seed, stesso output).

---

<br/>

### Autore:
[Alessandro Attene](https://www.linkedin.com/in/aleattene)

#### Licenza: 
[MIT](../LICENSE)
