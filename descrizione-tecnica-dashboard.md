# Descrizione tecnica — `dashboard.html`

## Cos'è

`dashboard.html` è la **versione statica "buildata" della dashboard interattiva**
`app.py`. Mentre `app.py` è un'applicazione [Streamlit](https://streamlit.io) che
richiede un server Python in esecuzione, questo file è un **singolo HTML
autosufficiente**: si apre con un doppio clic in qualunque browser, **anche senza
connessione internet e senza installare nulla**, e i grafici restano interattivi
(zoom, hover con i valori, legenda cliccabile).

## Stack tecnologico

```
yfinance ──► core.py ──► Plotly ──► build_html.py ──► dashboard.html
 (dati)     (calcoli)   (grafici)    (export)        (artefatto finale)
```

| Livello | Tecnologia | Ruolo |
|---|---|---|
| Dati | **yfinance** (Yahoo Finance) | Scarica prezzi, azioni in circolazione storiche e tassi |
| Calcolo | **Python / pandas / numpy / scipy** (`core.py`) | Ricostruisce market cap storici, indici, metriche, t-test |
| Grafici | **Plotly** | Genera 5 grafici interattivi |
| Build | **`build_html.py`** | Incorpora i grafici e Plotly.js in un unico `.html` |
| Output | **HTML5 + CSS + JavaScript** | File statico ~5 MB, offline-ready |

## Fonti dati

Tutti i dati sono pubblici e gratuiti, scaricati via `yfinance`:
**SPY** (S&P500 cap-weight), **RSP** (S&P500 equal-weight), **^IRX** (T-bill USA
13 settimane, risk-free), i **50 maggiori titoli** dell'indice e le loro **azioni
in circolazione storiche** (`get_shares_full`). I market cap non sono pesi statici
ma ricostruiti = prezzo × azioni a ciascuna data.

## Contenuto della pagina

1. **4 KPI** in evidenza: rendimento SPY, rendimento RSP (con gap), concentrazione
   Mag7, quota del rendimento spiegata dai Mag7.
2. **Banner del test t** (SPY vs RSP): significatività statistica.
3. **5 grafici interattivi**:
   - Performance cumulata (SPY vs RSP vs senza Mag7)
   - Attribuzione annuale per titolo
   - Concentrazione nel tempo
   - Matrice di correlazione
   - Sharpe ratio rolling a 12 mesi
4. **Tabella delle metriche** dettagliate + sezione metodologia/limiti.

## Caratteristiche tecniche

- **Design editoriale** ("dossier di equity research"): palette calda carta-avorio /
  nero inchiostro con accento ruggine, titoli serif (**Fraunces**), numeri in
  monospazio tabulare (**IBM Plex Mono**), filetti tipografici, grana sottile e
  animazioni d'ingresso scaglionate. I 5 grafici sono in **tab** cliccabili come in `app.py`.
- **Tema chiaro / scuro**: interruttore in alto a destra; i grafici Plotly cambiano
  tema al volo. La scelta viene ricordata (`localStorage`) e all'apertura segue il
  tema di sistema.
- **Tipografia**: font caricati da Google Fonts con fallback di sistema (se offline,
  ripiega su serif/sans/mono di sistema mantenendo l'impianto grafico).
- **Autosufficiente**: la libreria Plotly.js (~3 MB) è **incorporata inline**, non
  caricata da CDN → funziona offline.
- **Interattivo**: ogni grafico supporta zoom, pan, hover e toggle della legenda.
- **Responsive** (si adatta a desktop e mobile).
- **Identico ai numeri del paper**: usa lo stesso modulo di calcolo `core.py`, quindi
  i valori mostrati coincidono con quelli del PDF (validazione: l'indice ricostruito
  correla 0,98 con SPY reale).

## Come rigenerarlo

Dalla cartella `sp500-concentration`:

```bash
python build_html.py        # riscarica i dati e ricostruisce dashboard.html
```

Per la versione interattiva completa (con filtri e selezione titoli):

```bash
streamlit run app.py
```
