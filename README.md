# S&P500 Concentration Analysis

Analisi interattiva di quanto la performance dell'S&P500 (2019–2024) dipenda dai
"Magnificent Seven" (Apple, Microsoft, NVIDIA, Amazon, Alphabet, Meta, Tesla), e
di cosa questo implichi per l'Efficient Market Hypothesis.

## Domanda di ricerca

> "Quanto della performance dell'S&P500 è spiegabile da un pugno di titoli? E cosa
> ci dice questo sulla market efficiency?"

## Metodologia (dati reali, niente pesi statici)

- **Market cap storici reali**: prezzo non aggiustato × azioni in circolazione nel
  tempo (`yfinance get_shares_full`) → pesi cap-weighted che variano nel tempo,
  senza look-ahead bias.
- **Benchmark equal-weight reale**: ETF RSP (Invesco S&P500 Equal Weight). Il
  divario SPY vs RSP è la misura standard dell'effetto concentrazione.
- **Risk-free reale**: rendimento T-bill USA a 13 settimane (`^IRX`), variabile.
- **Significatività statistica**: paired t-test sulla differenza di rendimento
  giornaliero SPY − RSP.
- Validazione: l'indice ricostruito correla **0.98** con SPY reale.

## Fonti dati

Tutti i dati sono pubblici e gratuiti, scaricati via `yfinance` (Yahoo Finance):
SPY, RSP, ^IRX e i 50 maggiori costituenti dell'indice; azioni in circolazione
storiche via `get_shares_full`.

## Installazione

```bash
pip install -r requirements.txt
```

## Uso

Dashboard interattiva:
```bash
streamlit run app.py
```

Generazione figure + numeri per il paper (anche via `run_analysis.bat`):
```bash
python build_paper.py
```

## Struttura

```
sp500-concentration/
├── core.py            # Unica fonte di calcolo (dati + analisi)
├── app.py             # Dashboard Streamlit (UI su core.py)
├── build_paper.py     # Esporta figure PNG + paper/results.json
├── paper/
│   ├── main.tex       # Paper LaTeX
│   ├── references.bib # Bibliografia
│   ├── results.json   # Numeri generati da build_paper.py
│   └── figures/       # PNG esportati
├── README.md
└── requirements.txt
```

## Paper accademico

Compilazione (con `tectonic`, oppure pdflatex/Overleaf):

```bash
tectonic paper/main.tex
```

## Limiti

- Universo = 50 maggiori costituenti (replicano l'indice al ~98%).
- SPY/RSP come proxy dell'indice e della sua versione equal-weight.
- I "Magnificent Seven" sono scelti col senno di poi (selection bias): per questo
  il confronto principale è SPY vs RSP, che non seleziona alcun titolo.
- Il periodo include eventi eccezionali (crash Covid, rally post-Covid, shock tassi 2022).
```
