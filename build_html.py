"""
build_html.py - Report web statico (The Concentration Report): stessi numeri
e stessi grafici del paper (core.py + charts.py).

- Solo tema chiaro (carta avorio, inchiostro nero, accento ruggine), stile in report.css.
- Link ai PDF del paper sul sito; Plotly.js da CDN.
- Output: dashboard.html, da copiare in portfolio/public/concentration-report.html.
"""
from pathlib import Path

import pandas as pd
import plotly.offline

import charts
import core

HERE = Path(__file__).parent
OUT = HERE / "dashboard.html"
PLOT_CFG = {"displayModeBar": False, "responsive": True}
REPO = "https://github.com/giulioparrinello/sp500-concentration"
PLOTLY_JS = f"https://cdn.plot.ly/plotly-{plotly.offline.get_plotlyjs_version()}.min.js"


def it(x: float, d: int = 1) -> str:
    """Numero in formato italiano (virgola decimale, punto per le migliaia)."""
    s = f"{x:,.{d}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def frag(fig, div_id):
    fig.update_layout(height=480)
    return fig.to_html(full_html=False, div_id=div_id, include_plotlyjs=False, config=PLOT_CFG)


print(">> Calcolo (core.py)...")
data = core.load_raw_data()
a = core.analyze(data, excluded=core.MAG7)
issues = core.validate(data, a)
if issues:
    raise SystemExit("Controlli non superati:\n  " + "\n  ".join(issues))
td = a.trading_days
v1 = pd.read_csv(HERE / "data" / "v1_concentrazione.csv", index_col=0, parse_dates=True)["mag7_pct_v1"]

TABS = [
    ("Performance", "chart-perf", "SPY, RSP e top 50 senza Mag7, base 100.",
     charts.performance(a, web=True)),
    ("Attribuzione", "chart-attr",
     "Contributo annuo di ogni titolo Mag7 al rendimento del top 50 (punti %). Il trattino nero è il totale.",
     charts.attribution(a, web=True)),
    ("Concentrazione", "chart-conc",
     "Quota di capitalizzazione dei Mag7 e dei primi 5 nel top 50, ricomposto ogni anno.",
     charts.concentration(a, web=True)),
    ("Correlazione", "chart-corr", "Correlazione dei rendimenti giornalieri tra Mag7 e S&amp;P500.",
     charts.heatmap(a, web=True)),
    ("Sharpe", "chart-sharpe", "Sharpe ratio mobile a 12 mesi, con risk-free reale (^IRX).",
     charts.sharpe(a, data["irx"], web=True)),
    ("Revisione", "chart-rev", "Quota dei Mag7 nel top 50: versione 1 (errata) e versione 2 (corretta).",
     charts.revision(a, v1, web=True)),
]
tabbtn_html = "".join(
    f'<button class="tab{" active" if i == 0 else ""}" onclick="showTab({i})">'
    f'<span class="tab-n">{i + 1:02d}</span>{name}</button>'
    for i, (name, _, _, _) in enumerate(TABS))
panels_html = "".join(
    f'<div class="panel{" active" if i == 0 else ""}" id="panel-{i}">'
    f'<p class="desc">{desc}</p>{frag(fig, div_id)}</div>'
    for i, (name, div_id, desc, fig) in enumerate(TABS))

# ── KPI ───────────────────────────────────────────────────────────────────────
m, s = a.metrics, a.summary
kpis = [
    ("S&amp;P500 · SPY", it(m["SPY"]["cum"], 0), "%", "rendimento 2019–2024", ""),
    ("Equal-weight · RSP", it(m["RSP"]["cum"], 0), "%", f"{it(s['spy_vs_rsp_gap_pp'], 0)} pp sotto SPY", "down"),
    ("Concentrazione Mag7", it(s["conc_end_pct"], 0), "%", f"da {it(s['conc_start_pct'], 0)}% a inizio 2019", "up"),
    ("Quota del rendimento", it(s["excluded_share_of_return_pct"], 0), "%", "del top 50, dovuta ai Mag7", ""),
]
kpi_html = "".join(
    f'<div class="kpi" style="animation-delay:{0.05 * i + 0.1:.2f}s"><div class="kpi-label">{l}</div>'
    f'<div class="kpi-value">{v}<span class="unit">{u}</span></div><div class="kpi-sub {c}">{sub}</div></div>'
    for i, (l, v, u, sub, c) in enumerate(kpis))

attr = a.attribution.pivot(index="Anno", columns="Titolo", values="Contributo")
mean_corr = a.corr.loc[[core.NAMES[t] for t in a.mag7_in], "S&P500"].mean()
facts = [
    (f"+{it(m['Mag7']['cum'], 0)}%", "Rendimento dei soli Mag7"),
    (f"+{it(attr.loc[[2023, 2024], 'NVIDIA'].sum())} pp", "Contributo NVIDIA 2023–24"),
    (it(mean_corr, 2), "Correlazione media Mag7–S&amp;P500"),
    (f"{it(s['conc_peak_pct'], 0)}%", "Quota Mag7 massima"),
    (f"{it(a.conc_top5.iloc[-1], 0)}%", "Quota dei primi 5 a fine 2024"),
    (it(len(td), 0), "Giorni di borsa analizzati"),
]
facts_html = "".join(f'<div class="fact"><div class="fact-v">{v}</div><div class="fact-l">{l}</div></div>'
                     for v, l in facts)

# ── Tabella metriche ──────────────────────────────────────────────────────────
labels = {"SPY": "S&amp;P500 (SPY)", "RSP": "Equal-weight (RSP)", "ExMag7": "Top 50 senza Mag7", "Mag7": "Solo Mag7"}
rowfmt = [("Rendimento cumulato", "cum", "%", 1), ("Rendimento annualizzato", "ann", "%", 1),
          ("Volatilità annua", "vol", "%", 1), ("Sharpe ratio", "sharpe", "", 2), ("Max drawdown", "mdd", "%", 1)]
head = "".join(f"<th>{labels[k]}</th>" for k in m)
tbody = "".join(f"<tr><th>{lab}</th>" + "".join(f"<td>{it(m[k][key], d)}{u}</td>" for k in m) + "</tr>"
                for lab, key, u, d in rowfmt)
table_html = f"<div class='table-wrap'><table class='metrics'><thead><tr><th></th>{head}</tr></thead><tbody>{tbody}</tbody></table></div>"

tt = a.ttest
ttest_html = (f"Test t sulla differenza giornaliera tra SPY e RSP ({it(tt['n_obs'], 0)} giorni): media "
              f"<b>+{it(tt['mean_ann_excess_pp'], 2)} pp</b> l'anno, t = {it(tt['t_stat'], 2)}, p = {it(tt['p_value'], 2)}. "
              f"Con errori standard di Newey-West: t = {it(tt['t_stat_nw'], 2)}, p = {it(tt['p_value_nw'], 2)}. "
              f"<b>Non significativo</b> al 5%: un vantaggio giornaliero piccolo e rumoroso, composto su sei anni, "
              f"produce comunque un divario cumulato ampio.")

revision_html = (f"Rileggendo il lavoro ho trovato un errore nella versione 1 (giugno 2026): il prezzo di Yahoo "
                 f"Finance è corretto per gli split azionari, il numero di azioni no, quindi le capitalizzazioni "
                 f"prima di ogni split risultavano molto più basse (Amazon a fine 2018: 38 miliardi di dollari "
                 f"invece di 734). La quota iniziale dei Mag7 era {it(v1.iloc[0], 0)}% invece di "
                 f"{it(s['conc_start_pct'], 0)}%: la concentrazione è quasi raddoppiata, non triplicata. "
                 f"La versione 2 usa le azioni dichiarate alla SEC e ricompone ogni anno il gruppo dei 50 titoli "
                 f"più grandi. I numeri basati sugli ETF cambiano di poco. Dettagli nella sezione 2 del paper, "
                 f"nella scheda Revisione e nel <a href=\"{REPO}\" target=\"_blank\" rel=\"noopener\">repository su GitHub</a>.")

methodology_html = f"""<ul>
<li><b>Capitalizzazioni storiche</b>: prezzo × azioni in circolazione dichiarate alla SEC (dati XBRL), sulla stessa base split. Fusioni dalla data di chiusura, spin-off dal giorno dello stacco. Visa e Berkshire: azioni equivalenti da Yahoo Finance.</li>
<li><b>Universo</b>: ogni anno i 50 titoli più grandi a fine anno precedente, solo tra i membri dell'S&amp;P500 (Tesla dal 21/12/2020). Correlazione con SPY {it(s['corr_full_vs_spy'], 3)}, tracking error {it(s['tracking_error_pp'])} pp.</li>
<li><b>Attribuzione esatta</b>: i contributi dei singoli titoli sommano al rendimento del top 50. Le quote si riferiscono al top 50, non all'intero S&amp;P500.</li>
<li><b>Equal-weight reale</b>: ETF RSP. <b>Risk-free reale</b>: T-bill a 13 settimane (^IRX), variabile.</li>
<li>I Mag7 sono scelti con il senno di poi: per questo il confronto principale è SPY contro RSP.</li>
<li><b>Codice e dati</b>: <a href="{REPO}" target="_blank" rel="noopener">github.com/giulioparrinello/sp500-concentration</a>, con le istruzioni per replicare i risultati.</li>
</ul>"""

ids_js = "[" + ",".join(f'"{d}"' for _, d, _, _ in TABS) + "]"

NOISE = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E"
         "%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='2' "
         "stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")

print(">> Assemblo HTML...")

TEMPLATE = r"""<!DOCTYPE html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Concentration Report · S&P500 2019–2024</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Hanken+Grotesk:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
%%CSS%%
</style><script src="%%PLOTLY%%"></script>
</head><body>

<header class="rise">
  <div class="kicker">Equity Research · Indici · 2019–2024 · Versione 2</div>
  <div class="masthead">
    <h1>The Concentration <em>Report</em></h1>
    <div class="byline">S&amp;P500 vs Magnificent 7<br>Giulio Parrinello<br>Univ. di Palermo</div>
  </div>
  <p class="sub">Quanto della performance dell'indice dipende da un pugno di titoli? Capitalizzazioni
  storiche dai dati SEC, ETF equal-weight (RSP) e risk-free reale (^IRX): gli stessi numeri del paper.</p>
  <div class="papers">
    <a class="paper-btn" href="https://giulioparrinello.it/paper1/it" target="_blank" rel="noopener"><span class="ic">↗</span>Leggi il paper completo (IT)</a>
    <a class="paper-btn alt" href="https://giulioparrinello.it/paper1/en" target="_blank" rel="noopener"><span class="ic">↗</span>EN</a>
  </div>
  <p class="papers-note">La versione inglese è stata tradotta dall'italiano con Claude (versione 1: Claude 3.5 Sonnet; versione 2: Claude Opus 5.5).</p>
</header>

<div class="banner revision rise" style="animation-delay:.03s">
  <div class="tag">Versione 2 · 14/10/2026</div>
  <div>%%REVISION%%</div>
</div>

<section class="research rise" style="animation-delay:.05s">
  <p class="lead">La domanda di partenza è semplice: <b>quanta parte della performance dell'S&amp;P500
  dal 2019 al 2024 dipende da un pugno di titoli?</b> L'indice è considerato il termometro
  diversificato del mercato statunitense, ma è ponderato per capitalizzazione: le aziende più grandi
  pesano di più. Dal 2019 sette mega-cap tecnologiche, i <em>Magnificent 7</em>, hanno raggiunto un
  peso senza precedenti.</p>
  <p>Per misurarlo ricostruiamo le <b>capitalizzazioni storiche</b> (prezzo × azioni dichiarate alla SEC),
  confrontiamo l'indice con la sua versione equiponderata (ETF RSP) e isoliamo il contributo dei sette titoli
  nel gruppo dei 50 più grandi. Il risultato: i Magnificent 7 spiegano <b>%%SHARE%%%</b> del rendimento di
  questo gruppo e la loro quota è quasi raddoppiata. La concentrazione non è un'anomalia passeggera ma una
  <b>caratteristica strutturale</b> dell'indicizzazione moderna. Amplifica i rendimenti quanto i rischi, e
  mette in dubbio l'idea stessa di diversificazione passiva.</p>
</section>

<section class="kpis rise" style="animation-delay:.1s">%%KPIS%%</section>
<section class="facts rise" style="animation-delay:.14s">%%FACTS%%</section>

<div class="banner rise" style="animation-delay:.2s">
  <div class="tag">Nota statistica</div>
  <div>%%BANNER%%</div>
</div>

<div class="sec-head"><span class="no">§</span><h2>Grafici</h2><span class="rule"></span></div>
<div class="tabs">%%TABS%%</div>
%%PANELS%%

<div class="sec-head" style="margin-top:38px"><span class="no">§</span><h2>Metriche</h2><span class="rule"></span></div>
%%TABLE%%
<details><summary>Metodologia &amp; limiti</summary>%%METHOD%%</details>

<footer><a href="https://giulioparrinello.it">giulioparrinello.it</a></footer>

<script>
const CHART_IDS = %%IDS%%;
function showTab(i){
  document.querySelectorAll(".tab").forEach((b,j)=>b.classList.toggle("active",i===j));
  document.querySelectorAll(".panel").forEach((p,j)=>p.classList.toggle("active",i===j));
  try{Plotly.Plots.resize(CHART_IDS[i]);}catch(e){}
}
</script>
</body></html>"""

html = (TEMPLATE
        .replace("%%CSS%%", (HERE / "report.css").read_text(encoding="utf-8").replace("%%NOISE%%", NOISE))
        .replace("%%PLOTLY%%", PLOTLY_JS)
        .replace("%%REVISION%%", revision_html)
        .replace("%%SHARE%%", it(s["excluded_share_of_return_pct"], 0))
        .replace("%%KPIS%%", kpi_html)
        .replace("%%FACTS%%", facts_html)
        .replace("%%BANNER%%", ttest_html)
        .replace("%%TABS%%", tabbtn_html)
        .replace("%%PANELS%%", panels_html)
        .replace("%%TABLE%%", table_html)
        .replace("%%METHOD%%", methodology_html)
        .replace("%%IDS%%", ids_js))

assert "—" not in html, "trattino lungo nel report"
OUT.write_text(html, encoding="utf-8")
print(f">> Scritto {OUT.name} ({OUT.stat().st_size / 1e6:.1f} MB)")
