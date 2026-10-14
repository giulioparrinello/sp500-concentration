# S&P500 Concentration Analysis

Quanto della performance dell'S&P500 (2019–2024) dipende dai "Magnificent Seven"
(Apple, Microsoft, NVIDIA, Amazon, Alphabet, Meta, Tesla), e che cosa implica per
l'Ipotesi dei Mercati Efficienti.

**Versione 2, 14 ottobre 2026.** Corregge un errore della versione 1 (giugno 2026):
il prezzo di Yahoo Finance è aggiustato per gli split, il numero di azioni no, quindi
le capitalizzazioni prima di ogni split erano sottostimate (Amazon a fine 2018:
38 miliardi di dollari invece di 734). La versione 1 è il primo commit del repository;
la sezione 2 del paper descrive la revisione.

## Metodologia

- **Capitalizzazioni storiche**: prezzo di chiusura × azioni in circolazione dichiarate
  alla SEC (dati XBRL, `data.sec.gov`), sulla stessa base split. Fusioni dalla data di
  chiusura, spin-off dal giorno dello stacco. Visa e Berkshire Hathaway: azioni
  equivalenti da Yahoo Finance.
- **Universo point-in-time**: ogni anno i 50 titoli più grandi a fine anno precedente,
  tra i membri dell'S&P500 (111 candidati).
- **Benchmark equal-weight**: ETF RSP. Il divario SPY/RSP misura l'effetto concentrazione.
- **Risk-free**: T-bill USA a 13 settimane (`^IRX`), variabile.
- **Attribuzione esatta**: i contributi dei titoli sommano al rendimento dell'indice.
- **Significatività**: t-test sulla differenza giornaliera SPY meno RSP, anche con
  errori standard di Newey-West.
- **Controlli automatici** (`core.validate`): salti anomali nelle capitalizzazioni,
  copertura dei dati, correlazione con SPY. `build_paper.py` e `build_html.py` si
  fermano se un controllo fallisce.

## Replicare i risultati (per sviluppatori)

### Requisiti

- Python 3.11 o successivo (la versione 2 è stata prodotta con Python 3.13.7).
- Connessione a internet solo se si riscaricano i dati.
- Google Chrome o Chromium installato: `kaleido` 1.x lo usa per esportare i grafici PNG.
- [Tectonic](https://tectonic-typesetting.github.io) (o pdflatex/Overleaf) solo per compilare i PDF.
- Circa 500 MB liberi se si riscaricano i filing SEC.

### 1. Ambiente

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.lock.txt # versioni esatte della v2
```

`requirements.txt` contiene solo le versioni minime; per riprodurre i numeri usare
`requirements.lock.txt`.

### 2. Verificare i numeri del paper

```bash
python verify.py
```

Ricalcola l'analisi a partire da `data/snapshot.pkl` (prezzi, split, azioni e tassi
scaricati il 14/10/2026) e confronta dieci numeri chiave con `paper/results.json`.
Con lo snapshot il risultato deve coincidere esattamente:

```
SPY rendimento cumulato %            157.4620     157.4620  ok
...
Replica riuscita: i numeri coincidono con quelli del paper.
```

Lo snapshot è un file pickle di pandas: si legge con la stessa versione indicata in
`requirements.lock.txt`. Come ogni pickle, va aperto solo se proviene da questo repository.

### 3. Rigenerare figure, report e PDF

```bash
python build_paper.py                # paper/figures/{it,en}, paper/results.json, data/*.csv
python build_html.py                 # dashboard.html (il report web)
tectonic paper/main_it.tex           # paper italiano (originale)
tectonic paper/main.tex              # paper inglese
streamlit run app.py                 # dashboard interattiva, facoltativa
```

`build_paper.py` e `build_html.py` si fermano con l'elenco dei problemi se
`core.validate()` trova dati incoerenti. I numeri nei file `.tex` sono scritti a mano a
partire da `paper/results.json`: se cambiano i dati, vanno aggiornati anche i testi.

### 4. Ripartire dai dati originali

```bash
export SEC_USER_AGENT="Nome Cognome nome@dominio.it"   # Windows: set SEC_USER_AGENT=...
python verify.py --fresh
```

`--fresh` riscarica tutto senza toccare lo snapshot: prezzi da Yahoo Finance e filing
XBRL dalla SEC (`data.sec.gov`, salvati in `data/sec/`, uno per società). La SEC chiede
un User-Agent che identifichi chi scarica; senza `SEC_USER_AGENT` viene usato quello
del progetto. I filing scaricati restano in cache: le esecuzioni successive non li
riscaricano.

Prova del 14/10/2026 su un clone pulito, senza cache: download completo in circa
3 minuti, numeri uguali a quelli del paper al terzo decimale (RSP differisce di 0,0001
punti). Con dati scaricati in futuro sono possibili piccole differenze, e `verify.py --fresh` le tollera
(0,5 punti percentuali): Yahoo Finance a volte rivede i prezzi storici, mentre dalla SEC
si usa sempre il primo valore pubblicato per ogni data, quindi quella parte non cambia.
Per rendere i nuovi dati la base di calcolo, cancellare `data/snapshot.pkl` e lanciare
`python build_paper.py`.

### Come scorrono i dati

1. `core.load_raw_data()` scarica prezzi (Yahoo Finance), split, azioni (SEC) e tasso
   privo di rischio, e salva lo snapshot.
2. `core.market_caps()` calcola prezzo × azioni sulla stessa base split, con fusioni e
   spin-off alla data reale (`CORPORATE_EVENTS`, fattori di spin-off di Yahoo).
3. `core.analyze()` sceglie ogni anno i 50 titoli più grandi (`INDEX_ENTRY` esclude chi
   non era ancora nell'indice), costruisce gli indici, l'attribuzione e i test.
4. `core.validate()` controlla salti anomali, copertura dei dati e correlazione con SPY.
5. `charts.py` disegna i grafici; `build_paper.py` e `build_html.py` producono gli output.

### Cambiare i parametri

- **Periodo**: `DEFAULT_START` e `DEFAULT_END` in `core.py`. Fuori dal 2019–2024 vanno
  ricontrollati `UNIVERSE`/`CIK` (i candidati), `INDEX_ENTRY` e `CORPORATE_EVENTS`.
- **Ampiezza dell'universo**: `TOP_N` (default 50).
- **Titoli esclusi**: parametro `excluded` di `core.analyze()` (default i Magnificent Seven).
- **Nuova società candidata**: aggiungerla a `CIK` con il suo identificativo SEC (lo si
  trova su EDGAR); se ha più classi di azioni, controllare in `data/azioni_usate.csv`
  che il totale sia corretto.

### Problemi frequenti

- **`HTTP Error 403` dalla SEC**: impostare `SEC_USER_AGENT` con nome ed email reali.
- **Download Yahoo Finance vuoti o interrotti**: limiti di richieste; riprovare dopo
  qualche minuto. I ticker cambiati nel tempo sono già aggiornati (per esempio Marsh
  McLennan è `MRSH`, Fiserv è `FISV`).
- **`Controlli non superati`**: `validate()` ha trovato un salto della capitalizzazione
  non spiegato dal prezzo. Di solito è una fusione o uno spin-off da aggiungere a
  `CORPORATE_EVENTS`, oppure un dato SEC dichiarato su una base split diversa.
- **Errore di `kaleido` sull'export PNG**: manca Chrome/Chromium.

## Struttura

```
sp500-concentration/
├── core.py            # Unica fonte di calcolo (dati, analisi, controlli)
├── charts.py          # Grafici condivisi da paper e report
├── build_paper.py     # Figure PNG IT/EN, results.json, dati esportati
├── build_html.py      # Report web (stile in report.css)
├── app.py             # Dashboard Streamlit
├── verify.py          # Confronto dei numeri ricalcolati con quelli del paper
├── requirements.lock.txt  # Versioni esatte usate per la v2
├── data/              # snapshot.pkl (dati del 14/10/2026), azioni usate,
│                      # top 50 per anno, serie della v1; sec/ = cache SEC (non versionata)
└── paper/             # main_it.tex (originale), main.tex (EN), figure, results.json
```

## Limiti

- Quote e contributi si riferiscono al gruppo dei 50 titoli più grandi, non all'intero S&P500.
- Capitalizzazione totale, non flottante; azioni aggiornate una volta per trimestre.
- I "Magnificent Seven" sono scelti con il senno di poi: per questo il confronto
  principale è SPY contro RSP.
- Il periodo include eventi eccezionali (crollo del 2020, ripresa, rialzo dei tassi del 2022).
