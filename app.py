import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import core
from core import MAG7, NAMES

st.set_page_config(layout="wide", page_title="S&P500 Concentration Analysis")
st.title("S&P500 Concentration Analysis")
st.caption("Quanto della performance dell'indice dipende da pochi titoli? "
           "Dati reali: market cap storici, ETF equal-weight (RSP), risk-free reale (^IRX).")

# ── Cache dei dati grezzi (download una sola volta) ───────────────────────────
@st.cache_data(ttl=3600, show_spinner="Scarico prezzi, azioni in circolazione e tassi...")
def get_data(start, end):
    return core.load_raw_data(start, end)


@st.cache_data(ttl=3600, show_spinner="Calcolo...")
def get_analysis(start, end, excluded, window):
    data = get_data(start, end)
    return core.analyze(data, excluded=list(excluded), sharpe_window_days=window), data


# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.header("Controlli")
excluded = st.sidebar.multiselect(
    "Titoli da escludere dall'indice:", options=MAG7, default=MAG7,
    format_func=lambda t: f"{NAMES.get(t, t)} ({t})",
)
c0, c1 = st.sidebar.columns(2)
start_date = c0.date_input("Inizio", value=pd.Timestamp(core.DEFAULT_START))
end_date = c1.date_input("Fine", value=pd.Timestamp(core.DEFAULT_END))
sharpe_window = st.sidebar.slider("Finestra Sharpe rolling (mesi)", 3, 24, 12)

a, data = get_analysis(start_date.strftime("%Y-%m-%d"),
                       end_date.strftime("%Y-%m-%d"),
                       tuple(excluded), sharpe_window * 21)
td = a.trading_days

# ── KPI ───────────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("S&P500 (SPY)", f"{a.metrics['SPY']['cum']:.0f}%")
k2.metric("Equal-Weight (RSP)", f"{a.metrics['RSP']['cum']:.0f}%",
          f"{a.summary['spy_vs_rsp_gap_pp']:+.0f} pp vs SPY")
k3.metric("Concentrazione esclusi", f"{a.summary['conc_end_pct']:.0f}%",
          f"da {a.summary['conc_start_pct']:.0f}%")
k4.metric("Quota del rendimento", f"{a.summary['excluded_share_of_return_pct']:.0f}%")

# ── Tabs ──────────────────────────────────────────────────────────────────────
t1, t2, t3, t4, t5 = st.tabs(
    ["Performance", "Attribution", "Concentrazione", "Correlazione", "Sharpe"])

with t1:
    fig = go.Figure()
    fig.add_scatter(x=td, y=a.spy_cum, name="S&P500 (SPY, cap-weight)", line=dict(width=2.5))
    fig.add_scatter(x=td, y=a.rsp_cum, name="Equal-Weight (RSP)", line=dict(width=2.5))
    fig.add_scatter(x=td, y=a.ex_cum, name="Senza esclusi", line=dict(width=2.5, dash="dash"))
    fig.update_layout(template="plotly_white", yaxis_title="Indice (base 100)",
                      legend=dict(x=0.02, y=0.98))
    st.plotly_chart(fig, use_container_width=True)

with t2:
    if not a.attribution.empty:
        fig = px.bar(a.attribution, x="Anno", y="Contributo", color="Titolo",
                     template="plotly_white",
                     title="Contributo annuo al rendimento per titolo (punti %)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nessun titolo escluso selezionato.")

with t3:
    fig = go.Figure()
    fig.add_scatter(x=td, y=a.conc_excluded, name="Titoli esclusi", fill="tozeroy",
                    line=dict(width=2.5))
    fig.add_scatter(x=td, y=a.conc_top5, name="Top 5", line=dict(width=2, dash="dot"))
    fig.update_layout(template="plotly_white",
                      yaxis_title="Quota del market cap top-50 (%)")
    st.plotly_chart(fig, use_container_width=True)

with t4:
    fig = px.imshow(a.corr, text_auto=".2f", color_continuous_scale="RdBu_r",
                    zmin=0, zmax=1, template="plotly_white",
                    title="Correlazione dei rendimenti giornalieri")
    st.plotly_chart(fig, use_container_width=True)

with t5:
    fig = go.Figure()
    fig.add_scatter(x=td, y=core.rolling_sharpe(a.spy_ret, data["irx"], sharpe_window * 21),
                    name="S&P500 (SPY)", line=dict(width=2.5))
    fig.add_scatter(x=td, y=core.rolling_sharpe(a.rsp_ret, data["irx"], sharpe_window * 21),
                    name="Equal-Weight (RSP)", line=dict(width=2.5))
    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    fig.update_layout(template="plotly_white", yaxis_title="Sharpe ratio")
    st.plotly_chart(fig, use_container_width=True)

# ── Significativita' statistica ───────────────────────────────────────────────
tt = a.ttest
sig = "**significativo**" if tt["significant_5pct"] else "**non significativo**"
st.info(f"Test t (SPY vs RSP, {tt['n_obs']} giorni): differenza media annualizzata "
        f"{tt['mean_ann_excess_pp']:+.1f} pp, t = {tt['t_stat']:.2f}, "
        f"p = {tt['p_value']:.3f} → {sig} al 5%.")

# ── Metriche dettagliate ──────────────────────────────────────────────────────
with st.expander("Metriche dettagliate"):
    labels = {"SPY": "S&P500 (SPY)", "RSP": "Equal-Weight (RSP)",
              "ExMag7": "Senza esclusi", "Mag7": "Solo esclusi"}
    fmt = {"cum": "Rend. cumulato", "ann": "Rend. annualizzato",
           "vol": "Volatilita' annua", "sharpe": "Sharpe ratio", "mdd": "Max drawdown"}
    rows = {}
    for key, m in a.metrics.items():
        rows[labels[key]] = {
            fmt[k]: (f"{v:.2f}" if k == "sharpe" else f"{v:.1f}%") for k, v in m.items()}
    st.dataframe(pd.DataFrame(rows).T, use_container_width=True)
    st.caption(f"Validazione: l'indice ricostruito correla "
               f"{a.summary['corr_full_vs_spy']:.3f} con SPY.")

with st.expander("Metodologia e limiti"):
    st.markdown("""
- **Market cap storici reali**: prezzo non aggiustato × azioni in circolazione nel tempo
  (`yfinance get_shares_full`). Niente look-ahead bias da pesi statici attuali.
- **Equal-weight reale**: ETF RSP (Invesco S&P500 Equal Weight).
- **Risk-free reale**: rendimento T-bill 13 settimane (`^IRX`), variabile nel tempo.
- Universo = 50 maggiori costituenti per capitalizzazione media (replicano l'indice al ~98%).
- I "Magnificent 7" sono scelti col senno di poi (selection bias): per questo il confronto
  principale è SPY vs RSP, che non seleziona alcun titolo.
""")
