"""
charts.py - Grafici condivisi da paper (PNG, IT ed EN) e report web (HTML).

Colori: ogni serie ha sempre lo stesso colore in tutti i grafici.
Palette validata per daltonismo (dataviz validate_palette.js, sfondo #F4F0E7).
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

import core

SERIES = ["#B5482A", "#2a78d6", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7"]
MAG7_COLOR = {core.NAMES[t]: SERIES[i] for i, t in enumerate(core.MAG7)}
INK, MUTED, GRID = "#1C1916", "#6E665A", "rgba(110,102,90,0.20)"
OLD = "#9A9080"          # versione 1, superata

TXT = {
    "it": {
        "spy": "S&P500 (SPY)", "rsp": "Equal-weight (RSP)", "ex": "Top 50 senza Mag7",
        "full": "Top 50 ricostruito", "base100": "Indice (base 100)",
        "contrib": "Contributo (punti %)", "year": "Anno", "share": "Quota della capitalizzazione (%)",
        "mag7": "Magnificent 7", "top5": "Primi 5", "sharpe": "Sharpe ratio (12 mesi)",
        "v1": "Versione 1 (errata)", "v2": "Versione 2 (corretta)", "total": "Totale Mag7",
    },
    "en": {
        "spy": "S&P500 (SPY)", "rsp": "Equal-weight (RSP)", "ex": "Top 50 excluding Mag7",
        "full": "Reconstructed top 50", "base100": "Index (base 100)",
        "contrib": "Contribution (pp)", "year": "Year", "share": "Share of market cap (%)",
        "mag7": "Magnificent 7", "top5": "Top 5", "sharpe": "Sharpe ratio (12 months)",
        "v1": "Version 1 (incorrect)", "v2": "Version 2 (corrected)", "total": "Mag7 total",
    },
}
NAMES_EN = {"Apple": "Apple", "Microsoft": "Microsoft", "NVIDIA": "NVIDIA", "Amazon": "Amazon",
            "Alphabet": "Alphabet", "Meta": "Meta", "Tesla": "Tesla", "S&P500": "S&P500"}


def style(fig: go.Figure, web: bool = False) -> go.Figure:
    fig.update_layout(
        template="none",
        paper_bgcolor="rgba(0,0,0,0)" if web else "white",
        plot_bgcolor="rgba(0,0,0,0)" if web else "white",
        font=dict(family="Hanken Grotesk, Helvetica, Arial, sans-serif", size=13 if web else 15, color=INK),
        margin=dict(l=60, r=30 if web else 130, t=20, b=50),
        legend=dict(orientation="h", y=-0.14, x=0, font=dict(size=12.5 if web else 14)),
        hovermode="x unified" if web else False,
    )
    fig.update_xaxes(gridcolor=GRID, linecolor=GRID, zerolinecolor=GRID, color=MUTED, showgrid=False)
    fig.update_yaxes(gridcolor=GRID, linecolor=GRID, zerolinecolor=GRID, color=MUTED)
    return fig


def _end_label(fig, x, y, text, color, web):
    if web:
        return
    fig.add_annotation(x=str(x), y=float(y), text=text, showarrow=False, xanchor="left", xshift=6,
                       font=dict(color=INK, size=13))


def performance(a: core.Analysis, lang="it", web=False) -> go.Figure:
    T = TXT[lang]
    td = a.trading_days
    fig = go.Figure()
    for y, name, color, dash in [(a.spy_cum, T["spy"], SERIES[0], None),
                                 (a.rsp_cum, T["rsp"], SERIES[1], None),
                                 (a.ex_cum, T["ex"], SERIES[2], "dash")]:
        fig.add_scatter(x=td, y=y, name=name, line=dict(width=2, color=color, dash=dash),
                        hovertemplate="%{y:.0f}")
        _end_label(fig, td[-1], y.iloc[-1], f"{y.iloc[-1] - 100:+.0f}%", color, web)
    fig.update_yaxes(title=T["base100"])
    return style(fig, web)


def attribution(a: core.Analysis, lang="it", web=False) -> go.Figure:
    """Barre impilate per anno: contributo di ogni titolo Mag7 al rendimento
    dell'indice top 50 (tutti i contributi di un anno hanno lo stesso segno)."""
    T = TXT[lang]
    df = a.attribution.pivot(index="Anno", columns="Titolo", values="Contributo")
    fig = go.Figure()
    for t in core.MAG7:
        n = core.NAMES[t]
        if n in df.columns:
            fig.add_bar(x=df.index, y=df[n], name=n, marker=dict(color=MAG7_COLOR[n], line=dict(width=1, color="white")),
                        hovertemplate=f"{n}: " + "%{y:.1f} pp<extra></extra>")
    tot = df.sum(axis=1)
    fig.add_scatter(x=df.index, y=tot, mode="markers+text", name=T["total"],
                    marker=dict(symbol="line-ew", size=26, line=dict(width=2.5, color=INK)),
                    text=[f"{v:+.1f}" for v in tot], textposition=["top center" if v >= 0 else "bottom center" for v in tot],
                    textfont=dict(size=13, color=INK), hovertemplate="%{y:.1f} pp<extra></extra>")
    fig.update_layout(barmode="relative", bargap=0.35)
    fig.update_yaxes(title=T["contrib"], zeroline=True, zerolinecolor=MUTED)
    fig.update_xaxes(title=T["year"], dtick=1)
    fig = style(fig, web)
    fig.update_layout(margin=dict(r=30))
    return fig


def concentration(a: core.Analysis, lang="it", web=False) -> go.Figure:
    T = TXT[lang]
    td = a.trading_days
    fig = go.Figure()
    fig.add_scatter(x=td, y=a.conc_excluded, name=T["mag7"], line=dict(width=2, color=SERIES[0]),
                    hovertemplate="%{y:.1f}%")
    fig.add_scatter(x=td, y=a.conc_top5, name=T["top5"], line=dict(width=2, color=SERIES[1], dash="dot"),
                    hovertemplate="%{y:.1f}%")
    _end_label(fig, td[-1], a.conc_excluded.iloc[-1], f"{a.conc_excluded.iloc[-1]:.0f}%", SERIES[0], web)
    _end_label(fig, td[-1], a.conc_top5.iloc[-1], f"{a.conc_top5.iloc[-1]:.0f}%", SERIES[1], web)
    fig.update_yaxes(title=T["share"], rangemode="tozero")
    return style(fig, web)


def heatmap(a: core.Analysis, lang="it", web=False) -> go.Figure:
    c = a.corr.copy()
    if lang == "en":
        c = c.rename(index=NAMES_EN, columns=NAMES_EN)
    fig = go.Figure(go.Heatmap(
        z=c.values, x=list(c.columns), y=list(c.index), zmin=0, zmax=1,
        colorscale=[[0.0, "#F7F2E8"], [0.5, "#E0A27E"], [1.0, "#8A2E16"]],
        text=[[f"{v:.2f}" for v in row] for row in c.values], texttemplate="%{text}",
        textfont=dict(size=13), hovertemplate="%{y} / %{x}: %{z:.2f}<extra></extra>",
        colorbar=dict(thickness=12, outlinewidth=0)))
    fig.update_yaxes(autorange="reversed")
    fig = style(fig, web)
    fig.update_layout(margin=dict(l=90, r=30, t=20, b=60))
    fig.update_yaxes(showgrid=False)
    return fig


def sharpe(a: core.Analysis, irx: pd.Series, lang="it", web=False) -> go.Figure:
    T = TXT[lang]
    td = a.trading_days
    fig = go.Figure()
    for r, name, color in [(a.spy_ret, T["spy"], SERIES[0]), (a.rsp_ret, T["rsp"], SERIES[1])]:
        fig.add_scatter(x=td, y=core.rolling_sharpe(r, irx), name=name, line=dict(width=2, color=color),
                        hovertemplate="%{y:.2f}")
    fig.add_hline(y=0, line_width=1, line_color=MUTED)
    fig.update_yaxes(title=T["sharpe"])
    return style(fig, web)


def revision(a: core.Analysis, v1: pd.Series, lang="it", web=False) -> go.Figure:
    """Concentrazione Mag7: versione 1 (errata) contro versione 2 (corretta)."""
    T = TXT[lang]
    fig = go.Figure()
    fig.add_scatter(x=v1.index, y=v1.values, name=T["v1"], line=dict(width=2, color=OLD, dash="dash"),
                    hovertemplate="%{y:.1f}%")
    fig.add_scatter(x=a.trading_days, y=a.conc_excluded, name=T["v2"], line=dict(width=2, color=SERIES[0]),
                    hovertemplate="%{y:.1f}%")
    if not web:
        for x, y, color in [(v1.index[0], v1.iloc[0], MUTED),
                            (a.trading_days[0], a.conc_excluded.iloc[0], INK)]:
            fig.add_annotation(x=str(x), y=float(y), text=f"{y:.0f}%", showarrow=False, xanchor="right",
                               xshift=-6, font=dict(color=color, size=13))
    fig.update_yaxes(title=T["share"], rangemode="tozero")
    fig = style(fig, web)
    fig.update_layout(margin=dict(l=90))
    return fig
