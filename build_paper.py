"""
build_paper.py - Figure (IT ed EN), numeri e dati esportati per il paper,
con core.py come unica fonte di calcolo.

Output:
  paper/figures/it/*.png, paper/figures/en/*.png
  paper/results.json            tutti i numeri citati nel testo
  data/azioni_usate.csv         azioni per titolo e data, con la fonte
  data/top50_per_anno.csv       composizione dell'universo anno per anno
Si ferma se validate() trova problemi nei dati.
"""
import json
import sys
from pathlib import Path

import pandas as pd

import charts
import core

HERE = Path(__file__).parent
FIG = HERE / "paper" / "figures"

print(">> Dati (snapshot se presente, altrimenti download)...")
data = core.load_raw_data()
a = core.analyze(data, excluded=core.MAG7)

issues = core.validate(data, a)
if issues:
    print("Controlli non superati:\n  " + "\n  ".join(issues))
    sys.exit(1)
print(">> Controlli sui dati superati")

v1 = pd.read_csv(HERE / "data" / "v1_concentrazione.csv", index_col=0, parse_dates=True)["mag7_pct_v1"]

for lang in ["it", "en"]:
    out = FIG / lang
    out.mkdir(parents=True, exist_ok=True)
    figs = {
        "performance_chart.png": charts.performance(a, lang),
        "attribution_chart.png": charts.attribution(a, lang),
        "concentration_chart.png": charts.concentration(a, lang),
        "heatmap_chart.png": charts.heatmap(a, lang),
        "sharpe_chart.png": charts.sharpe(a, data["irx"], lang),
        "revision_chart.png": charts.revision(a, v1, lang),
    }
    for name, fig in figs.items():
        h = 760 if name == "heatmap_chart.png" else 620
        fig.write_image(str(out / name), width=1100, height=h, scale=2)
    print(f"   figure {lang}: {len(figs)}")

# ============================ DATI ESPORTATI ============================
rows = []
for t, s in data["shares_obs"].items():
    for d, v in s.items():
        rows.append({"ticker": t, "data": d.date(), "azioni": int(round(v)), "fonte": data["shares_source"][t]})
pd.DataFrame(rows).to_csv(HERE / "data" / "azioni_usate.csv", index=False)
pd.DataFrame({y: l for y, l in a.top_by_year.items()}).to_csv(HERE / "data" / "top50_per_anno.csv", index=False)

# ============================ NUMERI ============================
mc = core.market_caps(data).where(core.membership(data["days_all"], core.market_caps(data).columns))
first, last = a.trading_days[0], a.trading_days[-1]
corr_m7 = a.corr.loc[[core.NAMES[t] for t in a.mag7_in], [core.NAMES[t] for t in a.mag7_in]]
pairs = [corr_m7.iloc[i, j] for i in range(len(corr_m7)) for j in range(i + 1, len(corr_m7))]
attr = a.attribution.pivot(index="Anno", columns="Titolo", values="Contributo")
full_y = (a.full_cum / 100).groupby(a.trading_days.year).last()
full_y = full_y / full_y.shift(1).fillna(1.0) - 1

results = {
    "version": 2,
    "date": "2026-10-14",
    "data_downloaded": data.get("downloaded"),
    "period": {"start": str(first.date()), "end": str(last.date()),
               "n_days": len(a.trading_days), "n_returns": a.ttest["n_obs"]},
    "universe_top_n": core.TOP_N,
    "n_candidates": len(core.UNIVERSE),
    "n_firms_ever_in_top": len(a.top),
    "top_cutoff_bn": {str(y): float(mc.loc[mc.index[mc.index < f"{y}-01-01"][-1]].dropna().nlargest(core.TOP_N).iloc[-1] / 1e9)
                      for y in a.top_by_year},
    "mag7_in_top_by_year": {str(y): [t for t in core.MAG7 if t in l] for y, l in a.top_by_year.items()},
    "share_sources": pd.Series(data["shares_source"]).value_counts().to_dict(),
    "mktcap_bn": {d: {t: float(mc.loc[d, t] / 1e9) for t in core.MAG7 + ["BRK-B"] if pd.notna(mc.loc[d, t])}
                  for d in [str(mc.index[mc.index < "2019-01-01"][-1].date()), str(last.date())]},
    "metrics": a.metrics,
    "spy_vs_rsp_gap_pp": a.summary["spy_vs_rsp_gap_pp"],
    "ttest_spy_vs_rsp": a.ttest,
    "concentration": {
        "mag7_start_pct": a.summary["conc_start_pct"],
        "mag7_end_pct": a.summary["conc_end_pct"],
        "mag7_peak_pct": a.summary["conc_peak_pct"],
        "mag7_peak_date": str(a.conc_excluded.idxmax().date()),
        "top5_start_pct": float(a.conc_top5.iloc[0]),
        "top5_end_pct": float(a.conc_top5.iloc[-1]),
    },
    "reconstructed_index": {
        "full_cum_pct": float(a.full_cum.iloc[-1] - 100),
        "ex_mag7_cum_pct": float(a.ex_cum.iloc[-1] - 100),
        "mag7_portfolio_cum_pct": float(a.mag7_cum.iloc[-1] - 100),
        "mag7_contribution_pp": float(a.contrib_total[a.mag7_in].sum()),
        "mag7_share_of_return_pct": a.summary["excluded_share_of_return_pct"],
        "counterfactual_gap_pp": a.summary["counterfactual_gap_pp"],
        "corr_full_vs_spy": a.summary["corr_full_vs_spy"],
        "tracking_error_pp": a.summary["tracking_error_pp"],
        "annual_return_pct": {str(y): float(v * 100) for y, v in full_y.items()},
    },
    "contribution_total_pp": {core.NAMES[t]: float(a.contrib_total[t]) for t in a.mag7_in},
    "attribution_by_year_pp": {str(y): {k: float(v) for k, v in r.items()} for y, r in attr.iterrows()},
    "attribution_2023_2024": attr.loc[[2023, 2024]].sum().round(2).to_dict(),
    "correlation": {
        "mean_mag7_spy": float(a.corr.loc[corr_m7.index, "S&P500"].mean()),
        "min_pair": float(min(pairs)), "max_pair": float(max(pairs)),
        "tesla_spy": float(a.corr.loc["Tesla", "S&P500"]),
    },
    "v1_comparison": {"mag7_start_pct_v1": float(v1.iloc[0]), "mag7_end_pct_v1": float(v1.iloc[-1])},
}
(HERE / "paper" / "results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False))
print(json.dumps(results, indent=2, ensure_ascii=False))
