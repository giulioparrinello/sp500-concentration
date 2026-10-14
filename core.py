"""
core.py - Unica fonte di calcolo per dashboard (app.py), paper (build_paper.py)
e report web (build_html.py): i numeri mostrati ovunque coincidono.

Versione 2 (14 ottobre 2026). Rispetto alla versione 1 (giugno 2026):
  - Azioni in circolazione dai filing ufficiali SEC (XBRL), riportate sulla
    stessa base split del prezzo. La v1 moltiplicava un prezzo aggiustato per
    gli split per azioni NON aggiustate e sottostimava le capitalizzazioni
    pre-split (es. Amazon a gennaio 2019: 38 miliardi di dollari invece di ~740).
  - Universo point-in-time: ogni anno i 50 titoli piu' grandi a fine anno
    precedente, solo tra i membri dell'S&P500 (Tesla dal 21/12/2020).
  - Nessun riempimento all'indietro (bfill) dei dati.
  - Attribuzione esatta: i contributi sommano al rendimento dell'indice.
  - t-test con errori standard di Newey-West.
  - Controlli automatici sui dati (validate()).
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats

warnings.filterwarnings("ignore")

HERE = Path(__file__).parent
SEC_DIR = HERE / "data" / "sec"
SNAPSHOT = HERE / "data" / "snapshot.pkl"
# La SEC chiede un User-Agent che identifichi chi scarica: impostare SEC_USER_AGENT
# (es. "Nome Cognome nome@dominio.it") per usare il proprio.
SEC_UA = os.environ.get("SEC_USER_AGENT", "sp500-concentration academic research script (University of Palermo)")

MAG7 = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA"]
NAMES = {
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "NVIDIA", "AMZN": "Amazon",
    "GOOGL": "Alphabet", "META": "Meta", "TSLA": "Tesla",
}

# Candidati: tutte le societa' che tra fine 2018 e fine 2023 potevano stare tra
# le 50 piu' grandi dell'S&P500. La selezione vera e' fatta ogni anno sui dati.
# CIK = identificativo SEC del filer (per Exxon e BlackRock il filer storico,
# prima delle riorganizzazioni in holding del 2024-2025).
CIK = {
    "AAPL": 320193, "ABBV": 1551152, "ABT": 1800, "ACN": 1467373, "ADBE": 796343, "ADI": 6281,
    "ADP": 8670, "AMAT": 6951, "AMD": 2488, "AMGN": 318154, "AMZN": 1018724, "ANET": 1596532,
    "AVGO": 1730168, "AXP": 4962, "BA": 12927, "BAC": 70858, "BKNG": 1075531, "BLK": 1364742,
    "BMY": 14272, "BRK-B": 1067983, "BSX": 885725, "BX": 1393818, "C": 831001, "CAT": 18230,
    "CB": 896159, "CHTR": 1091667, "CI": 1739940, "CMCSA": 1166691, "CME": 1156375, "COST": 909832,
    "CRM": 1108524, "CSCO": 858877, "CVS": 64803, "CVX": 93410, "DE": 315189, "DHR": 313616,
    "DIS": 1744489, "DUK": 1326160, "ELV": 1156039, "ETN": 1551182, "FISV": 798354, "GE": 40545,
    "GILD": 882095, "GOOGL": 1652044, "GS": 886982, "HD": 354950, "HON": 773840, "IBM": 51143,
    "INTC": 50863, "INTU": 896878, "ISRG": 1035267, "JNJ": 200406, "JPM": 19617, "KLAC": 319201,
    "KO": 21344, "LIN": 1707925, "LLY": 59478, "LMT": 936468, "LOW": 60667, "LRCX": 707549,
    "MA": 1141391, "MCD": 63908, "MDLZ": 1103982, "MDT": 1613103, "META": 1326801, "MMM": 66740,
    "MO": 764180, "MRK": 310158, "MRSH": 62709, "MS": 895421, "MSFT": 789019, "MU": 723125,
    "NEE": 753308, "NFLX": 1065280, "NKE": 320187, "NOW": 1373715, "NVDA": 1045810, "ORCL": 1341439,
    "PANW": 1327567, "PEP": 77476, "PFE": 78003, "PG": 80424, "PGR": 80661, "PLD": 1045609,
    "PM": 1413329, "PYPL": 1633917, "QCOM": 804328, "REGN": 872589, "RTX": 101829, "SBUX": 829224,
    "SCHW": 316709, "SNPS": 883241, "SO": 92122, "SPGI": 64040, "SYK": 310764, "T": 732717,
    "TJX": 109198, "TMO": 97745, "TMUS": 1283699, "TSLA": 1318605, "TXN": 97476, "UBER": 1543151,
    "UNH": 731766, "UNP": 100885, "UPS": 1090727, "V": 1403161, "VRTX": 875320, "VZ": 732712,
    "WFC": 72971, "WMT": 104169, "XOM": 34088,
}
EXTRA_CIK = {"DIS": [1001039],          # Disney prima della holding del marzo 2019
             "CI": [701221]}            # Cigna prima della fusione con Express Scripts (dic. 2018)
UNIVERSE = list(CIK)

# Societa' con piu' classi di azioni per cui la SEC non espone un totale non
# dimensionale: azioni "as-converted" da Yahoo Finance (mediana trimestrale).
YF_SHARES = ["V", "BRK-B"]

# Ingresso nell'S&P500 dopo il 31/12/2018 (prima: fuori dall'universo).
INDEX_ENTRY = {
    "TSLA": "2020-12-21", "UBER": "2023-12-18", "PANW": "2023-06-20", "BX": "2023-09-18",
    "TMUS": "2019-07-15", "NOW": "2019-11-21",
}

# Data di chiusura delle fusioni che cambiano molto il numero di azioni.
CORPORATE_EVENTS = {
    "CVS": ["2018-11-28"],   # Aetna
    "LIN": ["2018-10-31"],   # Praxair + Linde AG
    "CI": ["2018-12-20"],    # Express Scripts
    "DIS": ["2019-03-20"],   # 21st Century Fox
    "FISV": ["2019-07-29"],  # First Data
    "BMY": ["2019-11-20"],   # Celgene
    "PLD": ["2020-02-04", "2022-10-03"],  # Liberty Property, Duke Realty
    "TMUS": ["2020-04-01"],  # Sprint
    "RTX": ["2020-04-03"],   # United Technologies + Raytheon
    "ABBV": ["2020-05-08"],  # Allergan
    "ADI": ["2021-08-26"],   # Maxim Integrated
    "AMD": ["2022-02-14"],   # Xilinx
    "SPGI": ["2022-02-28"],  # IHS Markit
    "AVGO": ["2023-11-22"],  # VMware
}

DEFAULT_START, DEFAULT_END = "2019-01-01", "2024-12-31"
TOP_N = 50


# --------------------------------------------------------------------------- #
# Azioni in circolazione (SEC XBRL)
# --------------------------------------------------------------------------- #
def _sec_facts(cik: int) -> dict:
    path = SEC_DIR / f"CIK{cik:010d}.json"
    if not path.exists():
        SEC_DIR.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(
            f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json",
            headers={"User-Agent": SEC_UA})
        path.write_bytes(urllib.request.urlopen(req, timeout=60).read())
        time.sleep(0.15)
    return json.loads(path.read_text())


def _sec_series(facts: dict, tax: str, concept: str, quarterly: bool = False) -> pd.Series:
    """Valori come pubblicati la prima volta (point-in-time), indicizzati per data di riferimento."""
    try:
        units = facts["facts"][tax][concept]["units"]["shares"]
    except KeyError:
        return pd.Series(dtype=float, index=pd.DatetimeIndex([]))
    rows = []
    for x in units:
        if quarterly:
            if "start" not in x:
                continue
            days = (pd.Timestamp(x["end"]) - pd.Timestamp(x["start"])).days
            if not 80 <= days <= 100:
                continue
        rows.append((pd.Timestamp(x["end"]), float(x["val"]), x["filed"]))
    if not rows:
        return pd.Series(dtype=float, index=pd.DatetimeIndex([]))
    df = pd.DataFrame(rows, columns=["end", "val", "filed"]).sort_values(["end", "filed"])
    s = df.groupby("end")["val"].first()
    return s[s > 0]


def sec_shares(ticker: str) -> tuple[pd.Series, str]:
    """Azioni dichiarate alla SEC. Priorita': copertina del filing (dei),
    poi media trimestrale (basic), poi stato patrimoniale."""
    facts = [_sec_facts(CIK[ticker])] + [_sec_facts(c) for c in EXTRA_CIK.get(ticker, [])]
    for tax, concept, q in [("dei", "EntityCommonStockSharesOutstanding", False),
                            ("us-gaap", "WeightedAverageNumberOfSharesOutstandingBasic", True),
                            ("us-gaap", "CommonStockSharesOutstanding", False)]:
        parts = [_sec_series(f, tax, concept, q) for f in facts]
        s = pd.concat(parts).sort_index()
        s = s[~s.index.duplicated(keep="last")]
        s = s[(s.index >= "2017-01-01") & (s.index <= "2025-06-30")]
        if len(s) >= 12 and s.index.min() <= pd.Timestamp("2018-12-31"):
            return _drop_spikes(s), f"SEC {concept}"
    # Ultima risorsa: la serie piu' lunga disponibile
    s = pd.concat([_sec_series(f, "dei", "EntityCommonStockSharesOutstanding") for f in facts])
    s = s[~s.index.duplicated(keep="last")]
    return _drop_spikes(s.sort_index()), "SEC EntityCommonStockSharesOutstanding (parziale)"


def yf_shares(ticker: str) -> pd.Series:
    s = yf.Ticker(ticker).get_shares_full(start="2017-01-01", end="2025-06-30")
    s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
    return s.sort_index().resample("QE").median().dropna()


def _drop_spikes(s: pd.Series, tol: float = 0.25) -> pd.Series:
    """Toglie valori isolati che si scostano di oltre il 25% sia dal dato
    precedente sia dal successivo (errori di inserimento, non eventi societari)."""
    v = s.values
    bad = [i for i in range(1, len(v) - 1)
           if abs(v[i] / v[i - 1] - 1) > tol and abs(v[i] / v[i + 1] - 1) > tol
           and abs(v[i + 1] / v[i - 1] - 1) < tol]
    return s.drop(s.index[bad])


def is_real_split(r: float) -> bool:
    """Split veri (2:1, 20:1, 1:8...). Gli altri fattori di Yahoo sono spin-off
    (es. AT&T 1,324 per WarnerMedia): cambiano il prezzo, non il numero di azioni."""
    return any(x >= 1.9 and abs(x - round(x)) < 0.01 for x in (r, 1 / r)) or abs(r - 1.5) < 1e-3


def fix_basis(s: pd.Series, real: pd.Series, window_days: int = 200) -> pd.Series:
    """Corregge i dati gia' dichiarati post-split ma datati prima dello split
    (es. Alphabet al 30/06/2022, depositato dopo lo split del 18/07/2022)."""
    s = s.copy()
    for d in s.index:
        near = s[(s.index != d) & (abs(s.index - d) <= pd.Timedelta(days=window_days))]
        if len(near) < 2:
            continue
        ratio = s[d] / near.median()
        for sd, r in real.items():
            if abs(sd - d) > pd.Timedelta(days=window_days):
                continue
            if abs(ratio / r - 1) < 0.05:
                s[d] /= r
                break
            if abs(ratio * r - 1) < 0.05:
                s[d] *= r
                break
    return s


def anchor_events(s: pd.Series, ticker: str) -> pd.Series:
    """Fusioni: il primo dato SEC dopo la chiusura vale dalla data di chiusura,
    non dalla data del filing successivo (fino a un trimestre dopo)."""
    for d in CORPORATE_EVENTS.get(ticker, []):
        d = pd.Timestamp(d)
        after = s[s.index >= d]
        if len(after) and d not in s.index:
            s = pd.concat([s, pd.Series([after.iloc[0]], index=[d])]).sort_index()
    return s


def split_factor_after(splits: pd.Series, dates: pd.DatetimeIndex) -> pd.Series:
    """Per ogni data, prodotto dei fattori di split successivi (base di oggi)."""
    f = pd.Series(1.0, index=dates)
    for d, r in splits.items():
        f[f.index < d] *= r
    return f


# --------------------------------------------------------------------------- #
# Download dati grezzi
# --------------------------------------------------------------------------- #
def _close(tickers, start, end, auto_adjust):
    df = yf.download(tickers, start=start, end=end, auto_adjust=auto_adjust,
                     progress=False)["Close"]
    if isinstance(df, pd.Series):
        df = df.to_frame(tickers[0] if isinstance(tickers, list) else tickers)
    return df.dropna(how="all")


def load_raw_data(start: str = DEFAULT_START, end: str = DEFAULT_END,
                  universe: list[str] | None = None, use_snapshot: bool = True,
                  save_snapshot: bool = True) -> dict:
    """Scarica (o rilegge dallo snapshot) prezzi, split, azioni e tassi.
    save_snapshot=False lascia intatto lo snapshot esistente (usato da verify.py)."""
    default = universe is None and (start, end) == (DEFAULT_START, DEFAULT_END)
    if use_snapshot and default and SNAPSHOT.exists():
        return pd.read_pickle(SNAPSHOT)

    universe = universe or UNIVERSE
    # Qualche settimana prima dell'inizio: serve la capitalizzazione di fine 2018.
    pre = (pd.Timestamp(start) - pd.Timedelta(days=40)).strftime("%Y-%m-%d")
    end = (pd.Timestamp(end) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")   # yfinance: fine esclusa
    etf = _close(["SPY", "RSP", "^IRX"], pre, end, auto_adjust=True)
    days_all = etf["SPY"].dropna().index
    trading_days = days_all[days_all >= start]
    spy = etf["SPY"].reindex(trading_days)
    rsp = etf["RSP"].reindex(trading_days)
    irx = etf["^IRX"].reindex(trading_days).ffill()

    adj = _close(universe, pre, end, auto_adjust=True).reindex(days_all)
    close = _close(universe, pre, end, auto_adjust=False).reindex(days_all)

    shares, source, splits, pseudo = {}, {}, {}, {}
    for t in universe:
        sp = yf.Ticker(t).splits
        sp.index = pd.to_datetime(sp.index).tz_localize(None).normalize()
        splits[t] = sp
        if t in YF_SHARES:
            s, src = yf_shares(t), "Yahoo Finance get_shares_full (mediana trimestrale)"
        else:
            s, src = sec_shares(t)
        real = sp[sp.map(is_real_split)] if len(sp) else sp
        # split veri: per data del dato (azioni sulla base split del prezzo)
        s = fix_basis(s * split_factor_after(real, s.index), real)
        shares[t] = anchor_events(s, t)
        pseudo[t] = sp[~sp.index.isin(real.index)]
        source[t] = src

    data = {"spy": spy, "rsp": rsp, "irx": irx, "adj": adj, "close": close,
            "shares_obs": shares, "shares_source": source, "splits": splits, "pseudo_splits": pseudo,
            "trading_days": trading_days, "days_all": days_all,
            "downloaded": pd.Timestamp.now().strftime("%Y-%m-%d")}
    if default and save_snapshot:
        SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        pd.to_pickle(data, SNAPSHOT)
    return data


def market_caps(data: dict) -> pd.DataFrame:
    """Capitalizzazione giornaliera = prezzo (base split corrente) x azioni (stessa base).
    Le azioni restano costanti fino al dato SEC successivo; prima del primo dato: vuoto.
    I fattori degli spin-off si applicano per giorno, perche' Yahoo li toglie dal prezzo."""
    days = data["days_all"]
    sh = pd.DataFrame({t: s.reindex(days.union(s.index)).ffill().reindex(days)
                       * split_factor_after(data["pseudo_splits"][t], days)
                       for t, s in data["shares_obs"].items()})
    cols = [c for c in data["close"].columns if c in sh.columns]
    return data["close"][cols] * sh[cols]


def membership(index: pd.DatetimeIndex, tickers) -> pd.DataFrame:
    m = pd.DataFrame(True, index=index, columns=list(tickers))
    for t, d in INDEX_ENTRY.items():
        if t in m.columns:
            m.loc[m.index < pd.Timestamp(d), t] = False
    return m


# --------------------------------------------------------------------------- #
# Risultato dell'analisi
# --------------------------------------------------------------------------- #
@dataclass
class Analysis:
    trading_days: pd.DatetimeIndex
    top: list[str]                  # titoli entrati almeno un anno nel top-N
    top_by_year: dict               # anno -> top-N scelti a fine anno precedente
    mag7_in: list[str]
    excluded: list[str]
    spy_cum: pd.Series
    rsp_cum: pd.Series
    ex_cum: pd.Series
    mag7_cum: pd.Series
    full_cum: pd.Series
    spy_ret: pd.Series
    rsp_ret: pd.Series
    conc_excluded: pd.Series        # quota dei titoli esclusi nell'universo top-N
    conc_top5: pd.Series
    attribution: pd.DataFrame       # Anno / Titolo / Contributo (punti % del rendimento annuo)
    contrib_total: pd.Series        # contributo al rendimento cumulato (punti %)
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
    rf_d = (irx.reindex(r.index).ffill() / 100) / 252
    ex = r - rf_d
    sharpe = ex.mean() / ex.std() * np.sqrt(252) if ex.std() > 0 else 0.0
    mdd = ((c - c.cummax()) / c.cummax()).min() * 100
    return {"cum": tot, "ann": ann, "vol": vol, "sharpe": sharpe, "mdd": mdd}


def newey_west_t(x: pd.Series, lags: int | None = None) -> dict:
    """t-test sulla media con errore standard di Newey-West (kernel di Bartlett)."""
    x = np.asarray(x.dropna(), dtype=float)
    n = len(x)
    lags = lags if lags is not None else int(np.floor(4 * (n / 100) ** (2 / 9)))
    e = x - x.mean()
    s = e @ e / n
    for k in range(1, lags + 1):
        s += 2 * (1 - k / (lags + 1)) * (e[k:] @ e[:-k]) / n
    t = x.mean() / np.sqrt(s / n)
    p = 2 * (1 - stats.t.cdf(abs(t), n - 1))
    return {"t_stat": float(t), "p_value": float(p), "lags": lags}


def analyze(data: dict, excluded: list[str] | None = None,
            top_n: int = TOP_N, sharpe_window_days: int = 252) -> Analysis:
    excluded = MAG7 if excluded is None else excluded
    td = data["trading_days"]
    days_all = data["days_all"]
    spy, rsp, irx = data["spy"], data["rsp"], data["irx"]

    mc_all = market_caps(data)
    mc_all = mc_all.where(membership(days_all, mc_all.columns))

    # Universo point-in-time: top-N a fine anno precedente, tenuto per tutto l'anno
    years = sorted(set(td.year))
    prev_day = {y: days_all[days_all < pd.Timestamp(f"{y}-01-01")][-1] for y in years}
    top_by_year = {y: mc_all.loc[prev_day[y]].dropna().nlargest(top_n).index.tolist() for y in years}
    top = sorted(set().union(*top_by_year.values()))
    in_set = pd.DataFrame(False, index=days_all, columns=top)
    for y in years:
        in_set.loc[days_all.year == y, top_by_year[y]] = True
    in_set.loc[prev_day[years[0]], top_by_year[years[0]]] = True
    mc = mc_all[top].where(in_set)
    ret = data["adj"][top].pct_change().reindex(td)

    def cap_weighted(cols):
        """Pesi di chiusura del giorno prima; il primo giorno dell'anno usa i pesi
        di fine anno precedente calcolati sul nuovo insieme."""
        m = mc[cols]
        w = m.div(m.sum(axis=1), axis=0).shift(1).reindex(td)
        for y in years[1:]:
            d0 = td[td.year == y][0]
            row = mc_all.loc[prev_day[y], [c for c in cols if c in top_by_year[y]]]
            w.loc[d0] = 0.0
            w.loc[d0, row.index] = (row / row.sum()).values
        w = w.fillna(0.0)
        return w, (w * ret[cols].fillna(0.0)).sum(axis=1)

    w_full, full_ret = cap_weighted(top)
    excl_in = [t for t in excluded if t in top]
    keep = [t for t in top if t not in excl_in]
    _, ex_ret = cap_weighted(keep)
    excl_ret = cap_weighted(excl_in)[1] if excl_in else pd.Series(0.0, index=td)

    spy_ret, rsp_ret = spy.pct_change().fillna(0.0), rsp.pct_change().fillna(0.0)
    cum = lambda r: (1 + r).cumprod() * 100

    # Concentrazione nell'universo top-N
    mc_td = mc.reindex(td)
    tot = mc_td.sum(axis=1)
    conc_excluded = (mc_td[excl_in].sum(axis=1) / tot * 100) if excl_in else pd.Series(0.0, index=td)
    conc_top5 = mc_td.apply(lambda r: r.nlargest(5).sum(), axis=1) / tot * 100

    # Attribuzione esatta: w_i,t-1 x r_i,t x livello dell'indice a t-1 (base = inizio periodo)
    contrib = w_full * ret[top].fillna(0.0)
    level = (1 + full_ret).cumprod().shift(1).fillna(1.0)
    rows = []
    for y in years:
        mask = td.year == y
        lvl_y = level[mask] / level[mask].iloc[0]
        cy = contrib[mask].mul(lvl_y, axis=0).sum() * 100     # somma = rendimento dell'anno
        for t in excl_in:
            rows.append({"Anno": y, "Titolo": NAMES.get(t, t), "Contributo": float(cy[t])})
    attribution = pd.DataFrame(rows)
    contrib_total = contrib.mul(level, axis=0).sum() * 100     # somma = rendimento cumulato

    corr = pd.concat([ret[excl_in].rename(columns=NAMES) if excl_in else pd.DataFrame(index=td),
                      spy_ret.rename("S&P500")], axis=1).iloc[1:].corr()

    metrics = {"SPY": _metrics(spy_ret, irx), "RSP": _metrics(rsp_ret, irx),
               "ExMag7": _metrics(ex_ret, irx), "Mag7": _metrics(excl_ret, irx)}
    diff = (spy_ret - rsp_ret).iloc[1:]
    t_stat, p_val = stats.ttest_1samp(diff, 0.0)
    nw = newey_west_t(diff)
    ttest = {"mean_ann_excess_pp": float(diff.mean() * 252 * 100),
             "t_stat": float(t_stat), "p_value": float(p_val),
             "t_stat_nw": nw["t_stat"], "p_value_nw": nw["p_value"], "nw_lags": nw["lags"],
             "n_obs": int(len(diff)), "significant_5pct": bool(max(p_val, nw["p_value"]) < 0.05)}

    tot_full = cum(full_ret).iloc[-1] - 100
    tot_ex = cum(ex_ret).iloc[-1] - 100
    summary = {
        "spy_vs_rsp_gap_pp": metrics["SPY"]["cum"] - metrics["RSP"]["cum"],
        "excluded_share_of_return_pct": float(contrib_total[excl_in].sum() / tot_full * 100) if excl_in else 0.0,
        "counterfactual_gap_pp": float(tot_full - tot_ex),
        "corr_full_vs_spy": float(pd.concat([full_ret, spy_ret], axis=1).iloc[1:].corr().iloc[0, 1]),
        "tracking_error_pp": float((full_ret - spy_ret).iloc[1:].std() * np.sqrt(252) * 100),
        "conc_start_pct": float(conc_excluded.iloc[0]),
        "conc_end_pct": float(conc_excluded.iloc[-1]),
        "conc_peak_pct": float(conc_excluded.max()),
    }

    return Analysis(
        trading_days=td, top=top, top_by_year=top_by_year, mag7_in=excl_in, excluded=excluded,
        spy_cum=cum(spy_ret), rsp_cum=cum(rsp_ret), ex_cum=cum(ex_ret),
        mag7_cum=cum(excl_ret), full_cum=cum(full_ret),
        spy_ret=spy_ret, rsp_ret=rsp_ret,
        conc_excluded=conc_excluded, conc_top5=conc_top5,
        attribution=attribution, contrib_total=contrib_total, corr=corr,
        metrics=metrics, ttest=ttest, summary=summary,
    )


def rolling_sharpe(r: pd.Series, irx: pd.Series, window: int = 252) -> pd.Series:
    rf_d = (irx.reindex(r.index).ffill() / 100) / 252
    ex = r - rf_d
    return (ex.rolling(window).mean() / ex.rolling(window).std()) * np.sqrt(252)


# --------------------------------------------------------------------------- #
# Controlli automatici
# --------------------------------------------------------------------------- #
def validate(data: dict, a: Analysis | None = None) -> list[str]:
    """Elenco dei problemi trovati (vuoto = dati coerenti)."""
    issues = []
    mc = market_caps(data)
    close = data["close"]
    for t in mc.columns:
        # 1. La capitalizzazione non deve saltare piu' del prezzo (split non allineati)
        resid = (np.log(mc[t]).diff() - np.log(close[t]).diff()).abs()
        expected = {pd.Timestamp(d) for d in CORPORATE_EVENTS.get(t, [])}
        expected |= set(data["pseudo_splits"][t].index)
        entry = pd.Timestamp(INDEX_ENTRY.get(t, "1900-01-01"))
        for d, v in resid[resid > 0.15].items():
            if d not in expected and d >= entry:
                issues.append(f"{t}: salto azioni {np.exp(v) - 1:+.0%} il {d.date()}")
        # 2. Dato sulle azioni disponibile a fine 2018
        s = data["shares_obs"][t]
        if t not in INDEX_ENTRY and (len(s) == 0 or s.index.min() > pd.Timestamp("2018-12-31")):
            issues.append(f"{t}: primo dato azioni {s.index.min().date() if len(s) else 'nessuno'}")
    if a is not None and a.summary["corr_full_vs_spy"] < 0.97:
        issues.append(f"indice ricostruito vs SPY: correlazione {a.summary['corr_full_vs_spy']:.3f}")
    return issues
