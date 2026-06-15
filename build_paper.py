"""
build_paper.py — Genera figure e numeri REALI per il paper, usando core.py
come unica fonte di calcolo (gli stessi numeri della dashboard app.py).

Output:
  paper/figures/*.png   (5 grafici ad alta risoluzione)
  paper/results.json    (tutti i numeri citati nel testo / tabella)
"""
import json
from pathlib import Path

import plotly.express as px
import plotly.graph_objects as go

import core

FIGDIR = Path(__file__).parent / "paper" / "figures"
FIGDIR.mkdir(parents=True, exist_ok=True)


def save(fig, name):
    fig.update_layout(template="plotly_white", font=dict(size=14),
                      margin=dict(l=60, r=30, t=60, b=50))
    fig.write_image(str(FIGDIR / name), width=1100, height=620, scale=2)
    print(f"   figura -> {name}")


print(">> Scarico dati reali (prezzi, azioni in circolazione, tassi)...")
data = core.load_raw_data()
print(">> Eseguo analisi (esclusione: Magnificent 7)...")
a = core.analyze(data, excluded=core.MAG7)
td = a.trading_days

print(">> Genero figure...")
# 1. Performance
fig = go.Figure()
fig.add_scatter(x=td, y=a.spy_cum, name="S&P500 (SPY, cap-weight)", line=dict(width=2.5))
fig.add_scatter(x=td, y=a.rsp_cum, name="S&P500 Equal-Weight (RSP)", line=dict(width=2.5))
fig.add_scatter(x=td, y=a.ex_cum, name="Top-50 senza Magnificent 7", line=dict(width=2.5, dash="dash"))
fig.update_layout(title="Performance cumulata (base = 100)",
                  yaxis_title="Indice (base 100)", legend=dict(x=0.02, y=0.98))
save(fig, "performance_chart.png")

# 2. Attribution
fig = px.bar(a.attribution, x="Anno", y="Contributo", color="Titolo",
             title="Contributo annuo al rendimento dell'indice per titolo Mag7 (punti %)")
fig.update_layout(yaxis_title="Contributo (punti percentuali)")
save(fig, "attribution_chart.png")

# 3. Concentrazione
fig = go.Figure()
fig.add_scatter(x=td, y=a.conc_excluded, name="Magnificent 7", fill="tozeroy", line=dict(width=2.5))
fig.add_scatter(x=td, y=a.conc_top5, name="Top 5", line=dict(width=2, dash="dot"))
fig.update_layout(title="Concentrazione: quota di capitalizzazione nell'universo top-50",
                  yaxis_title="Quota del market cap (%)")
save(fig, "concentration_chart.png")

# 4. Correlazione
fig = px.imshow(a.corr, text_auto=".2f", color_continuous_scale="RdBu_r", zmin=0, zmax=1,
                title="Matrice di correlazione dei rendimenti giornalieri")
save(fig, "heatmap_chart.png")

# 5. Rolling Sharpe
fig = go.Figure()
fig.add_scatter(x=td, y=core.rolling_sharpe(a.spy_ret, data["irx"]), name="S&P500 (SPY)", line=dict(width=2.5))
fig.add_scatter(x=td, y=core.rolling_sharpe(a.rsp_ret, data["irx"]), name="Equal-Weight (RSP)", line=dict(width=2.5))
fig.add_hline(y=0, line_dash="dot", line_color="gray")
fig.update_layout(title="Sharpe ratio rolling a 12 mesi (risk-free reale, ^IRX)",
                  yaxis_title="Sharpe ratio")
save(fig, "sharpe_chart.png")

# ============================ NUMERI ============================
results = {
    "period": {"start": core.DEFAULT_START, "end": core.DEFAULT_END, "n_days": len(td)},
    "universe_top_n": core.TOP_N,
    "mag7_used": a.mag7_in,
    "metrics": a.metrics,
    "spy_vs_rsp_gap_pp": a.summary["spy_vs_rsp_gap_pp"],
    "ttest_spy_vs_rsp": a.ttest,
    "concentration": {
        "mag7_start_pct": a.summary["conc_start_pct"],
        "mag7_end_pct": a.summary["conc_end_pct"],
        "mag7_peak_pct": a.summary["conc_peak_pct"],
        "top5_end_pct": float(a.conc_top5.iloc[-1]),
    },
    "reconstructed_index": {
        "full_cum_pct": float(a.full_cum.iloc[-1] - 100),
        "ex_mag7_cum_pct": float(a.ex_cum.iloc[-1] - 100),
        "mag7_share_of_total_return_pct": a.summary["excluded_share_of_return_pct"],
        "corr_full_vs_spy": a.summary["corr_full_vs_spy"],
    },
    "correlation": {
        "mean_mag7_spy": float(a.corr.loc[[core.NAMES[t] for t in a.mag7_in], "S&P500"].mean()),
    },
    "attribution_2023_2024": a.attribution[a.attribution["Anno"].isin([2023, 2024])]
        .groupby("Titolo")["Contributo"].sum().round(2).to_dict(),
}
(Path(__file__).parent / "paper" / "results.json").write_text(json.dumps(results, indent=2))
print("\n================ RISULTATI ================")
print(json.dumps(results, indent=2))
print(f"\nValidazione: corr indice ricostruito vs SPY = {results['reconstructed_index']['corr_full_vs_spy']:.4f}")
