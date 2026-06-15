"""
build_html.py — "Builda" la dashboard app.py in un singolo file HTML statico,
autosufficiente e dal design editoriale (dossier di equity research).

- Solo tema chiaro (carta avorio / nero inchiostro, accento ruggine).
- Il paper (PDF, IT ed EN) e' INCORPORATO nell'HTML: scaricabile anche spostando
  il solo file .html.
- Plotly.js incorporato inline -> apribile offline, grafici interattivi.
"""
from pathlib import Path

import plotly.graph_objects as go
import plotly.express as px

import core

HERE = Path(__file__).parent
OUT = HERE / "dashboard.html"
PAPER = HERE / "paper"
PLOT_CFG = {"displayModeBar": False, "responsive": True}
GRID = "rgba(120,110,95,0.18)"
INK = "#3A332B"
COLORWAY = ["#B5482A", "#2F6E8F", "#C99A3B", "#1F7A5A", "#7D5BA6", "#467487", "#A8553A"]
CORR_SCALE = [[0.0, "#F0E9DA"], [0.45, "#E0A96D"], [0.75, "#B5482A"], [1.0, "#6E2417"]]


def styled(fig):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Hanken Grotesk, -apple-system, sans-serif", size=13, color=INK),
        height=480, margin=dict(l=55, r=25, t=18, b=40),
        legend=dict(orientation="h", y=-0.17, font=dict(size=12.5)),
        colorway=COLORWAY,
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID, color=INK)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID, color=INK)
    return fig


def frag(fig, div_id, first=False):
    return styled(fig).to_html(full_html=False, div_id=div_id,
                               include_plotlyjs=("inline" if first else False),
                               config=PLOT_CFG)


print(">> Calcolo (core.py)...")
data = core.load_raw_data()
a = core.analyze(data, excluded=core.MAG7)
td = a.trading_days

# ── Figure ────────────────────────────────────────────────────────────────────
f_perf = go.Figure()
f_perf.add_scatter(x=td, y=a.spy_cum, name="S&P500 (SPY, cap-weight)", line=dict(width=2.6))
f_perf.add_scatter(x=td, y=a.rsp_cum, name="Equal-Weight (RSP)", line=dict(width=2.6))
f_perf.add_scatter(x=td, y=a.ex_cum, name="Senza Mag7", line=dict(width=2.4, dash="dash"))
f_perf.update_yaxes(title="Indice (base 100)")

f_attr = px.bar(a.attribution, x="Anno", y="Contributo", color="Titolo")
f_attr.update_yaxes(title="Contributo (punti %)")

f_conc = go.Figure()
f_conc.add_scatter(x=td, y=a.conc_excluded, name="Magnificent 7", fill="tozeroy",
                   line=dict(width=2.6, color="#B5482A"), fillcolor="rgba(181,72,42,0.12)")
f_conc.add_scatter(x=td, y=a.conc_top5, name="Top 5", line=dict(width=2, dash="dot", color="#2F6E8F"))
f_conc.update_yaxes(title="Quota market cap top-50 (%)")

f_corr = px.imshow(a.corr, text_auto=".2f", color_continuous_scale=CORR_SCALE, zmin=0, zmax=1)

f_sharpe = go.Figure()
f_sharpe.add_scatter(x=td, y=core.rolling_sharpe(a.spy_ret, data["irx"]), name="S&P500 (SPY)", line=dict(width=2.6))
f_sharpe.add_scatter(x=td, y=core.rolling_sharpe(a.rsp_ret, data["irx"]), name="Equal-Weight (RSP)", line=dict(width=2.6))
f_sharpe.add_hline(y=0, line_dash="dot", line_color="rgba(120,110,95,0.5)")
f_sharpe.update_yaxes(title="Sharpe ratio")

TABS = [
    ("Performance", "chart-perf", "Cap-weight (SPY) vs equal-weight (RSP) vs indice senza Mag7 — base 100.", f_perf),
    ("Attribuzione", "chart-attr", "Contributo annuo al rendimento dell'indice per titolo Mag7 (pesi storici).", f_attr),
    ("Concentrazione", "chart-conc", "Quota di capitalizzazione dei Mag7 e dei top-5 nell'universo dei 50 maggiori titoli.", f_conc),
    ("Correlazione", "chart-corr", "Correlazione dei rendimenti giornalieri tra Mag7 e indice.", f_corr),
    ("Sharpe", "chart-sharpe", "Sharpe ratio rolling a 12 mesi — risk-free reale (^IRX).", f_sharpe),
]

tabbtn_html = "".join(
    f'<button class="tab{" active" if i == 0 else ""}" onclick="showTab({i})">'
    f'<span class="tab-n">{i + 1:02d}</span>{name}</button>'
    for i, (name, _, _, _) in enumerate(TABS))

panels_html = ""
for i, (name, div_id, desc, fig) in enumerate(TABS):
    panels_html += (f'<div class="panel{" active" if i == 0 else ""}" id="panel-{i}">'
                    f'<p class="desc">{desc}</p>{frag(fig, div_id, first=(i == 0))}</div>')

# ── KPI ───────────────────────────────────────────────────────────────────────
m = a.metrics
kpis = [
    ("S&P500 — SPY", f"{m['SPY']['cum']:.0f}", "%", "rendimento 2019–2024", ""),
    ("Equal-Weight — RSP", f"{m['RSP']['cum']:.0f}", "%", f"{a.summary['spy_vs_rsp_gap_pp']:+.0f} pp vs SPY", "down"),
    ("Concentrazione Mag7", f"{a.summary['conc_end_pct']:.0f}", "%", f"da {a.summary['conc_start_pct']:.0f}% nel 2019", "up"),
    ("Quota del rendimento", f"{a.summary['excluded_share_of_return_pct']:.0f}", "%", "spiegata dai Mag7", ""),
]
kpi_html = ""
for i, (l, v, u, s, c) in enumerate(kpis):
    kpi_html += (f'<div class="kpi" style="animation-delay:{0.05 * i + 0.1:.2f}s">'
                 f'<div class="kpi-label">{l}</div>'
                 f'<div class="kpi-value">{v}<span class="unit">{u}</span></div>'
                 f'<div class="kpi-sub {c}">{s}</div></div>')

# ── Dati in sintesi (facts) ───────────────────────────────────────────────────
nvidia_2324 = a.attribution[(a.attribution["Titolo"] == "NVIDIA") &
                            (a.attribution["Anno"].isin([2023, 2024]))]["Contributo"].sum()
mean_corr = a.corr.loc[[core.NAMES[t] for t in a.mag7_in], "S&P500"].mean()
facts = [
    (f"+{m['Mag7']['cum']:.0f}%", "Rendimento dei soli Mag7"),
    (f"+{nvidia_2324:.1f} pp", "Contributo NVIDIA 2023–24"),
    (f"{mean_corr:.2f}", "Correlazione media Mag7–S&P500"),
    (f"{a.summary['conc_peak_pct']:.0f}%", "Concentrazione Mag7 di picco"),
    (f"{a.conc_top5.iloc[-1]:.0f}%", "Quota dei Top-5 a fine 2024"),
    (f"{len(td):,}".replace(",", "."), "Giorni di borsa analizzati"),
]
facts_html = "".join(
    f'<div class="fact"><div class="fact-v">{v}</div><div class="fact-l">{l}</div></div>'
    for v, l in facts)

# ── Tabella metriche ──────────────────────────────────────────────────────────
labels = {"SPY": "S&P500 (SPY)", "RSP": "Equal-Weight (RSP)", "ExMag7": "Senza Mag7", "Mag7": "Solo Mag7"}
rowfmt = [("Rendimento cumulato", "cum", "%"), ("Rendimento annualizzato", "ann", "%"),
          ("Volatilità annua", "vol", "%"), ("Sharpe ratio", "sharpe", ""), ("Max drawdown", "mdd", "%")]
head = "".join(f"<th>{labels[k]}</th>" for k in m)
tbody = ""
for lab, key, unit in rowfmt:
    cells = "".join(f"<td>{m[k][key]:.2f}{unit}</td>" for k in m)
    tbody += f"<tr><th>{lab}</th>{cells}</tr>"
table_html = f"<table class='metrics'><thead><tr><th></th>{head}</tr></thead><tbody>{tbody}</tbody></table>"

tt = a.ttest
sig = "significativo" if tt["significant_5pct"] else "<b>non significativo</b>"
ttest_html = (f"Test t (SPY vs RSP, {tt['n_obs']} giorni): differenza media annualizzata "
              f"<b>{tt['mean_ann_excess_pp']:+.1f} pp</b>, t = {tt['t_stat']:.2f}, "
              f"p = {tt['p_value']:.3f} → {sig} al 5%. Un divario cumulato ampio può nascere "
              f"da un vantaggio giornaliero piccolo e rumoroso, composto su sei anni.")

methodology_html = f"""<ul>
<li><b>Market cap storici reali</b> — prezzo non aggiustato × azioni in circolazione nel tempo (yfinance <code>get_shares_full</code>): niente look-ahead bias.</li>
<li><b>Equal-weight reale</b> — ETF RSP. <b>Risk-free reale</b> — T-bill 13 settimane (^IRX), variabile.</li>
<li>Universo = 50 maggiori costituenti; replicano l'indice al ~98% (corr <b>{a.summary['corr_full_vs_spy']:.3f}</b> con SPY).</li>
<li>I Mag7 sono scelti col senno di poi (selection bias): per questo il confronto principale è SPY vs RSP.</li>
</ul>"""

ids_js = "[" + ",".join(f'"{d}"' for _, d, _, _ in TABS) + "]"

NOISE = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E"
         "%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='2' "
         "stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")

print(">> Assemblo HTML...")

TEMPLATE = r"""<!DOCTYPE html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Concentration Report — S&P500 2019–2024</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Hanken+Grotesk:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root{
    --bg:#F4F0E7; --surface:#FBF8F1; --ink:#1C1916; --muted:#6E665A; --faint:#9A9080;
    --line:#E1D8C7; --line2:#D2C7B2; --accent:#B5482A; --up:#2F7D58; --down:#B5482A;
    --shadow:rgba(60,45,25,0.10);
    --serif:"Fraunces",Georgia,serif; --sans:"Hanken Grotesk",-apple-system,Segoe UI,sans-serif;
    --mono:"IBM Plex Mono",ui-monospace,Menlo,Consolas,monospace;
  }
  *{box-sizing:border-box;}
  html{scroll-behavior:smooth;}
  body{font-family:var(--sans); background:var(--bg); color:var(--ink);
       max-width:1080px; margin:0 auto; padding:0 26px 64px; line-height:1.55;
       position:relative; overflow-x:hidden;}
  body::before{content:""; position:fixed; inset:0; z-index:0; pointer-events:none;
       background-image:url("%%NOISE%%"); opacity:0.04; mix-blend-mode:multiply;}
  body>*{position:relative; z-index:1;}
  ::selection{background:var(--accent); color:#fff;}

  @keyframes rise{from{opacity:0; transform:translateY(14px);} to{opacity:1; transform:none;}}
  .rise{animation:rise .7s cubic-bezier(.2,.7,.2,1) both;}

  header{padding:30px 0 16px; border-bottom:2px solid var(--ink); margin-bottom:2px;}
  .kicker{font-family:var(--mono); font-size:11px; letter-spacing:.22em; text-transform:uppercase;
       color:var(--accent); display:flex; gap:14px; align-items:center; margin-bottom:14px;}
  .kicker::after{content:""; flex:1; height:1px; background:var(--line2);}
  .masthead{display:flex; justify-content:space-between; align-items:flex-end; gap:20px; flex-wrap:wrap;}
  h1{font-family:var(--serif); font-weight:600; font-size:clamp(30px,5vw,52px); line-height:1.02;
       letter-spacing:-.015em; margin:0; max-width:14ch;}
  h1 em{font-style:italic; color:var(--accent);}
  .byline{font-family:var(--mono); font-size:11.5px; color:var(--muted); text-align:right; line-height:1.9;}
  .sub{color:var(--muted); font-size:15px; max-width:62ch; margin:18px 0 0; border-top:1px solid var(--line);
       padding-top:14px;}

  .papers{display:flex; gap:10px; flex-wrap:wrap; margin-top:18px;}
  .paper-btn{font-family:var(--mono); font-size:12px; letter-spacing:.04em; text-decoration:none;
       display:inline-flex; align-items:center; gap:8px; padding:9px 16px; border-radius:2px;
       border:1px solid var(--ink); color:var(--bg); background:var(--ink); transition:.2s;}
  .paper-btn:hover{background:var(--accent); border-color:var(--accent);}
  .paper-btn.alt{background:transparent; color:var(--ink);}
  .paper-btn.alt:hover{color:var(--accent); border-color:var(--accent); background:transparent;}
  .paper-btn .ic{font-size:13px;}

  .research{max-width:72ch; margin:30px 0 6px; font-size:16px; line-height:1.72; color:var(--ink);}
  .research p{margin:0 0 14px;}
  .research .lead::first-letter{font-family:var(--serif); font-weight:600; float:left; font-size:62px;
       line-height:.78; padding:6px 12px 0 0; color:var(--accent);}
  .research b{font-weight:600;}

  .kpis{display:grid; grid-template-columns:repeat(4,1fr); margin:32px 0 8px;
       border:1px solid var(--line); background:var(--surface); border-radius:3px; overflow:hidden;}
  .kpi{padding:20px 22px; border-right:1px solid var(--line);}
  .kpi:last-child{border-right:none;}
  .kpi-label{font-family:var(--mono); font-size:10.5px; letter-spacing:.1em; text-transform:uppercase; color:var(--muted);}
  .kpi-value{font-family:var(--serif); font-weight:600; font-size:46px; line-height:1.05; margin:8px 0 4px;
       font-variant-numeric:tabular-nums;}
  .kpi-value .unit{font-size:24px; color:var(--faint); margin-left:2px;}
  .kpi-sub{font-family:var(--mono); font-size:11px; color:var(--muted);}
  .kpi-sub.up{color:var(--up);} .kpi-sub.down{color:var(--down);}
  .kpi-sub.up::before{content:"▲ ";} .kpi-sub.down::before{content:"▼ ";}

  .facts{display:grid; grid-template-columns:repeat(6,1fr); gap:0; margin:18px 0 8px;
       border:1px solid var(--line); border-radius:3px; background:var(--surface); overflow:hidden;}
  .fact{padding:16px 14px; border-right:1px solid var(--line); text-align:center;}
  .fact:last-child{border-right:none;}
  .fact-v{font-family:var(--serif); font-weight:600; font-size:26px; color:var(--accent); font-variant-numeric:tabular-nums;}
  .fact-l{font-family:var(--mono); font-size:9.5px; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); margin-top:4px; line-height:1.4;}

  .banner{display:grid; grid-template-columns:auto 1fr; gap:18px; align-items:start;
       background:var(--surface); border:1px solid var(--line); border-left:3px solid var(--accent);
       border-radius:3px; padding:16px 20px; margin:24px 0 36px; font-size:14px;}
  .banner .tag{font-family:var(--mono); font-size:10px; letter-spacing:.16em; text-transform:uppercase;
       color:var(--accent); writing-mode:vertical-rl; transform:rotate(180deg); align-self:stretch;}

  .sec-head{display:flex; align-items:baseline; gap:14px; margin:8px 0 16px;}
  .sec-head .no{font-family:var(--mono); font-size:12px; color:var(--accent); letter-spacing:.1em;}
  .sec-head h2{font-family:var(--serif); font-weight:600; font-size:24px; margin:0; letter-spacing:-.01em;}
  .sec-head .rule{flex:1; height:1px; background:var(--line); align-self:center;}

  .tabs{display:flex; gap:0; border-bottom:1px solid var(--line2); flex-wrap:wrap;}
  .tab{font-family:var(--sans); background:none; border:none; border-bottom:2px solid transparent;
       color:var(--muted); font-size:14.5px; font-weight:600; padding:11px 18px 12px; cursor:pointer;
       margin-bottom:-1px; display:flex; align-items:center; gap:8px; transition:color .2s;}
  .tab .tab-n{font-family:var(--mono); font-size:10px; color:var(--faint); font-weight:500;}
  .tab:hover{color:var(--ink);}
  .tab.active{color:var(--accent); border-bottom-color:var(--accent);}
  .tab.active .tab-n{color:var(--accent);}
  .panel{display:none; background:var(--surface); border:1px solid var(--line); border-top:none;
       border-radius:0 0 3px 3px; padding:18px 20px 8px;}
  .panel.active{display:block; animation:rise .5s ease both;}
  .desc{font-family:var(--mono); font-size:12px; color:var(--muted); margin:2px 2px 10px;}

  table.metrics{width:100%; border-collapse:collapse; font-family:var(--mono); font-size:13px;
       font-variant-numeric:tabular-nums; background:var(--surface); border:1px solid var(--line); border-radius:3px; overflow:hidden;}
  table.metrics th,table.metrics td{text-align:right; padding:11px 16px; border-bottom:1px solid var(--line);}
  table.metrics tr:last-child td,table.metrics tr:last-child th{border-bottom:none;}
  table.metrics thead th{color:var(--accent); font-weight:600; font-size:11px; letter-spacing:.04em; text-transform:uppercase;}
  table.metrics tbody th{text-align:left; color:var(--ink); font-family:var(--sans); font-weight:600;}
  table.metrics tbody tr:hover{background:color-mix(in srgb,var(--accent) 6%,transparent);}

  details{font-size:13.5px; color:var(--muted); margin-top:18px; background:var(--surface);
       border:1px solid var(--line); border-radius:3px; padding:14px 20px;}
  summary{cursor:pointer; font-family:var(--mono); font-size:12px; letter-spacing:.1em; text-transform:uppercase;
       color:var(--ink); font-weight:600;}
  details ul{margin:12px 0 2px; padding-left:18px;} details li{margin:5px 0;}
  code{font-family:var(--mono); font-size:.9em; background:color-mix(in srgb,var(--accent) 10%,transparent);
       padding:1px 5px; border-radius:3px;}

  footer{margin-top:48px; padding-top:18px; border-top:2px solid var(--ink); text-align:center;}
  footer a{font-family:var(--mono); font-size:12px; letter-spacing:.2em; text-transform:uppercase;
       color:var(--muted); text-decoration:none; transition:color .2s;}
  footer a:hover{color:var(--accent);}

  @media (max-width:860px){ .facts{grid-template-columns:repeat(3,1fr);} .fact:nth-child(3){border-right:none;} }
  @media (max-width:760px){
    .kpis{grid-template-columns:repeat(2,1fr);}
    .kpi:nth-child(2){border-right:none;}
    .kpi:nth-child(-n+2){border-bottom:1px solid var(--line);}
  }
</style></head><body>

<header class="rise">
  <div class="kicker">Equity Research · Indici · 2019—2024</div>
  <div class="masthead">
    <h1>The Concentration <em>Report</em></h1>
    <div class="byline">S&amp;P500 vs Magnificent 7<br>Giulio Parrinello<br>Univ. di Palermo</div>
  </div>
  <p class="sub">Quanto della performance dell'indice dipende da un pugno di titoli? Analisi con
  market cap storici reali, ETF equal-weight (RSP) e risk-free reale (^IRX) — gli stessi numeri del paper.</p>
  <div class="papers">
    <a class="paper-btn" href="https://giulioparrinello.it/paper1/it" target="_blank" rel="noopener"><span class="ic">↗</span>Leggi il paper completo (IT)</a>
    <a class="paper-btn alt" href="https://giulioparrinello.it/paper1/en" target="_blank" rel="noopener"><span class="ic">↗</span>EN</a>
  </div>
</header>

<section class="research rise" style="animation-delay:.05s">
  <p class="lead">La domanda di partenza è semplice: <b>quanta parte della performance dell'S&amp;P500
  negli ultimi sei anni dipende davvero da un pugno di titoli?</b> L'indice è considerato il termometro
  diversificato del mercato statunitense, ma è ponderato per capitalizzazione: le aziende più grandi
  pesano di più, e dal 2019 sette mega-cap tecnologiche — i <em>Magnificent 7</em> — hanno acquisito un
  peso senza precedenti.</p>
  <p>Per misurarlo senza distorsioni ricostruiamo i <b>pesi storici reali</b> (prezzo × azioni in
  circolazione nel tempo), confrontiamo l'indice con la sua versione equiponderata (ETF RSP) e isoliamo
  il contributo dei sette titoli. Il risultato: i Magnificent 7 spiegano circa <b>un terzo</b> del
  rendimento cumulato e il loro peso è più che triplicato. La concentrazione non è un'anomalia
  passeggera ma una <b>caratteristica strutturale</b> dell'indicizzazione moderna — che amplifica tanto
  i rendimenti quanto i rischi, e mette in discussione l'idea stessa di diversificazione passiva.</p>
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
        .replace("%%NOISE%%", NOISE)
        .replace("%%KPIS%%", kpi_html)
        .replace("%%FACTS%%", facts_html)
        .replace("%%BANNER%%", ttest_html)
        .replace("%%TABS%%", tabbtn_html)
        .replace("%%PANELS%%", panels_html)
        .replace("%%TABLE%%", table_html)
        .replace("%%METHOD%%", methodology_html)
        .replace("%%IDS%%", ids_js))

OUT.write_text(html, encoding="utf-8")
print(f">> Scritto {OUT.name} ({OUT.stat().st_size/1e6:.1f} MB, solo tema chiaro)")
