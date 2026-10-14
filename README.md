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

## Uso

```bash
pip install -r requirements.txt
python build_paper.py      # figure IT/EN, paper/results.json, data/*.csv
python build_html.py       # report web (dashboard.html)
streamlit run app.py       # dashboard interattiva
```

Il primo avvio scarica i dati (prezzi da Yahoo Finance, filing SEC in `data/sec/`)
e salva uno snapshot in `data/snapshot.pkl`; gli avvii successivi lo riusano.
Entrambi sono esclusi da git: `data/azioni_usate.csv` contiene le azioni effettivamente
usate, per titolo e data, con la fonte.

Compilazione dei paper (con `tectonic`, oppure pdflatex/Overleaf):

```bash
tectonic paper/main_it.tex   # originale italiano
tectonic paper/main.tex      # traduzione inglese
```

## Struttura

```
sp500-concentration/
├── core.py            # Unica fonte di calcolo (dati, analisi, controlli)
├── charts.py          # Grafici condivisi da paper e report
├── build_paper.py     # Figure PNG IT/EN, results.json, dati esportati
├── build_html.py      # Report web (stile in report.css)
├── app.py             # Dashboard Streamlit
├── data/              # Azioni usate, top 50 per anno, serie della v1
└── paper/             # main_it.tex (originale), main.tex (EN), figure, results.json
```

## Limiti

- Quote e contributi si riferiscono al gruppo dei 50 titoli più grandi, non all'intero S&P500.
- Capitalizzazione totale, non flottante; azioni aggiornate una volta per trimestre.
- I "Magnificent Seven" sono scelti con il senno di poi: per questo il confronto
  principale è SPY contro RSP.
- Il periodo include eventi eccezionali (crollo del 2020, ripresa, rialzo dei tassi del 2022).
