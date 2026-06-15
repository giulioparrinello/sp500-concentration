"""
core.py — Single source of truth per l'analisi.

Logica condivisa tra la dashboard (app.py) e la generazione del paper
(build_paper.py), cosi' i numeri mostrati a schermo e quelli nel PDF coincidono
sempre. Nessuna dipendenza da Streamlit: solo pandas / numpy / yfinance / scipy.

Metodologia (dati REALI, niente pesi statici):
  - Market cap storici  = prezzo NON aggiustato x azioni in circolazione nel tempo
                          (yfinance get_shares_full).
  - Benchmark equal-weight reale = ETF RSP.
  - Risk-free reale e variabile  = ^IRX (T-bill 13 settimane).
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats

warnings.filterwarnings("ignore")

MAG7 = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA"]
NAMES = {
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "NVIDIA", "AMZN": "Amazon",
    "GOOGL": "Alphabet", "META": "Meta", "TSLA": "Tesla",
}
# Superset dei ~50 maggiori costituenti S&P500 nel periodo 2019-2024.
UNIVERSE = MAG7 + [
    "BRK-B", "JPM", "V", "UNH", "XOM", "JNJ", "WMT", "MA", "PG", "HD",
    "LLY", "CVX", "ABBV", "MRK", "PEP", "KO", "COST", "BAC", "AVGO", "ADBE",
    "CRM", "TMO", "MCD", "CSCO", "ACN", "ABT", "DHR", "NFLX", "INTC", "WFC",
    "TXN", "DIS", "VZ", "PM", "CMCSA", "QCOM", "NKE", "AMD", "ORCL", "HON",
    "UPS", "T", "IBM", "CAT", "GS", "BA", "PFE", "LOW", "UNP", "RTX",
]
DEFAULT_START, DEFAULT_END = "2019-01-01", "2024-12-31"
TOP_N = 50


# --------------------------------------------------------------------------- #
# Download dati grezzi (separato dal calcolo cosi' la cache della UI e' facile)
# --------------------------------------------------------------------------- #
def _close(tickers, start, end, auto_adjust):
    df = yf.download(tickers, start=start, end=end, auto_adjust=auto_adjust,
                     progress=False)["Close"]
    if isinstance(df, pd.Series):
        df = df.to_frame(tickers[0] if isinstance(tickers, list) else tickers)
    return df.dropna(how="all")


def load_raw_data(start: str = DEFAULT_START, end: str = DEFAULT_END,
                  universe: list[str] | None = None) -> dict:
    """Scarica tutto il necessario. Ritorna un dict di DataFrame/Series grezzi."""
    universe = universe or UNIVERSE
    etf = _close(["SPY", "RSP", "^IRX"], start, end, auto_adjust=True)
    spy, rsp, irx = etf["SPY"].dropna(), etf["RSP"].dropna(), etf["^IRX"].dropna()
    trading_days = spy.index

    adj = _close(universe, start, end, auto_adjust=True).reindex(trading_days).ffill()
    raw = _close(universe, start, end, auto_adjust=False).reindex(trading_days).ffill()

    shares = {}
    for t in universe:
        try:
            s = yf.Ticker(t).get_shares_full(start=start, end=end)
            if s is not None and len(s):
                s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
                s = s[~s.index.duplicated(keep="last")]
                shares[t] = s.reindex(trading_days, method="ffill").bfill()
        except Exception:
            pass
    shares = pd.DataFrame(shares).reindex(trading_days).ffill().bfill()

    return {"spy": spy, "rsp": rsp, "irx": irx, "adj": adj, "raw": raw,
            "shares": shares, "trading_days": trading_days}


# --------------------------------------------------------------------------- #
# Risultato dell'analisi
# --------------------------------------------------------------------------- #
@dataclass
class Analysis:
    trading_days: pd.DatetimeIndex
    top: list[str]
    mag7_in: list[str]
    excluded: list[str]
    # serie cumulate (base 100)
    spy_cum: pd.Series
    rsp_cum: pd.Series
    ex_cum: pd.Series
    mag7_cum: pd.Series
    full_cum: pd.Series
    # rendimenti
    spy_ret: pd.Series
    rsp_ret: pd.Series
    # concentrazione
    conc_excluded: pd.Series        # quota dei titoli esclusi nell'universo top-N
    conc_top5: pd.Series
    # tabelle
    attribution: pd.DataFrame       # Anno / Titolo / Contributo
    corr: pd.DataFrame
    metrics: dict
    ttest: dict
    summary: dict = field(default_factory=dict)


def _metrics(r: pd.Series, irx: pd.Series) -> dict:
    r = r.dropna()
    c = (1 + r).cumprod()
    tot = (c.iloc[-1] - 1) * 100
    yrs = len(r) / 252
    ann = (c.iloc[-1] ** (1 / yrs) - 1) * 100
    vol = r.std() * np.sqrt(252) * 100
    rf_d = (irx.reindex(r.index).ffill().bfill() / 100) / 252
    ex = r - rf_d
    sharpe = ex.mean() / ex.std() * np.sqrt(252) if ex.std() > 0 else 0.0
    mdd = ((c - c.cummax()) / c.cummax()).min() * 100
    return {"cum": tot, "ann": ann, "vol": vol, "sharpe": sharpe, "mdd": mdd}


def analyze(data: dict, excluded: list[str] | None = None,
            top_n: int = TOP_N, sharpe_window_days: int = 252) -> Analysis:
    """Esegue l'intera analisi sui dati grezzi, escludendo `excluded` (default Mag7)."""
    excluded = MAG7 if excluded is None else excluded
    td = data["trading_days"]
    spy, rsp, irx = data["spy"], data["rsp"], data["irx"]

    # Market cap storici reali
    raw, shares = data["raw"], data["shares"]
    common = [c for c in raw.columns if c in shares.columns]
    mktcap = (raw[common] * shares[common]).dropna(axis=1, how="all")
    top = mktcap.mean().sort_values(ascending=False).head(top_n).index.tolist()
    mktcap = mktcap[top]
    excl_in = [t for t in excluded if t in top]

    adj = data["adj"][top].reindex(td).ffill()
    ret = adj.pct_change().fillna(0)
    spy_ret, rsp_ret = spy.pct_change().fillna(0), rsp.pct_change().fillna(0)

    # Pesi cap-weighted storici, indice full e senza esclusi
    w = mktcap.div(mktcap.sum(axis=1), axis=0)
    full_ret = (w.shift(1) * ret).sum(axis=1)
    keep = [t for t in top if t not in excl_in]
    w_ex = mktcap[keep].div(mktcap[keep].sum(axis=1), axis=0)
    ex_ret = (w_ex.shift(1) * ret[keep]).sum(axis=1)
    # Portafoglio dei soli titoli esclusi (cap-weighted tra loro)
    if excl_in:
        mce = mktcap[excl_in]
        we = mce.div(mce.sum(axis=1), axis=0)
        excl_ret = (we.shift(1) * ret[excl_in]).sum(axis=1)
    else:
        excl_ret = pd.Series(0.0, index=td)

    cum = lambda r: (1 + r).cumprod() * 100

    # Concentrazione
    conc_excluded = (mktcap[excl_in].sum(axis=1) / mktcap.sum(axis=1) * 100) if excl_in \
        else pd.Series(0.0, index=td)
    conc_top5 = mktcap.apply(lambda r: r.nlargest(5).sum(), axis=1) / mktcap.sum(axis=1) * 100

    # Attribution annuale (peso reale x rendimento)
    rows = []
    if excl_in:
        prices_y = adj[excl_in].resample("YE").last()
        ann_ret = prices_y.pct_change().dropna()
        w_year = w[excl_in].resample("YE").mean()
        for d in ann_ret.index:
            for t in excl_in:
                rows.append({"Anno": d.year, "Titolo": NAMES.get(t, t),
                             "Contributo": w_year.loc[d, t] * ann_ret.loc[d, t] * 100})
    attribution = pd.DataFrame(rows)

    # Correlazione
    corr = pd.concat([ret[excl_in].rename(columns=NAMES) if excl_in else pd.DataFrame(index=td),
                      spy_ret.rename("S&P500")], axis=1).corr()

    # Metriche + t-test SPY vs RSP
    metrics = {
        "SPY": _metrics(spy_ret, irx), "RSP": _metrics(rsp_ret, irx),
        "ExMag7": _metrics(ex_ret, irx), "Mag7": _metrics(excl_ret, irx),
    }
    diff = (spy_ret - rsp_ret).reindex(td).dropna()
    t_stat, p_val = stats.ttest_1samp(diff, 0.0)
    ttest = {"mean_ann_excess_pp": float(diff.mean() * 252 * 100),
             "t_stat": float(t_stat), "p_value": float(p_val),
             "n_obs": int(len(diff)), "significant_5pct": bool(p_val < 0.05)}

    tot_full = cum(full_ret).iloc[-1] - 100
    tot_ex = cum(ex_ret).iloc[-1] - 100
    summary = {
        "spy_vs_rsp_gap_pp": metrics["SPY"]["cum"] - metrics["RSP"]["cum"],
        "excluded_share_of_return_pct": (tot_full - tot_ex) / tot_full * 100 if tot_full else 0,
        "corr_full_vs_spy": float(pd.concat([full_ret, spy_ret], axis=1).corr().iloc[0, 1]),
        "conc_start_pct": float(conc_excluded.iloc[0]),
        "conc_end_pct": float(conc_excluded.iloc[-1]),
        "conc_peak_pct": float(conc_excluded.max()),
    }

    return Analysis(
        trading_days=td, top=top, mag7_in=excl_in, excluded=excluded,
        spy_cum=cum(spy_ret), rsp_cum=cum(rsp_ret), ex_cum=cum(ex_ret),
        mag7_cum=cum(excl_ret), full_cum=cum(full_ret),
        spy_ret=spy_ret, rsp_ret=rsp_ret,
        conc_excluded=conc_excluded, conc_top5=conc_top5,
        attribution=attribution, corr=corr,
        metrics=metrics, ttest=ttest, summary=summary,
    )


def rolling_sharpe(r: pd.Series, irx: pd.Series, window: int = 252) -> pd.Series:
    rf_d = (irx.reindex(r.index).ffill().bfill() / 100) / 252
    ex = r - rf_d
    return (ex.rolling(window).mean() / ex.rolling(window).std()) * np.sqrt(252)
