"""
verify.py - Ricalcola l'analisi e confronta i numeri principali con paper/results.json.

  python verify.py           usa lo snapshot dei dati (data/snapshot.pkl): deve coincidere esattamente
  python verify.py --fresh   riscarica prezzi e filing: tollera piccole differenze dovute
                             a revisioni dei dati di Yahoo Finance

Esce con codice 1 se un numero e' fuori tolleranza.
"""
import json
import sys
from pathlib import Path

import core

HERE = Path(__file__).parent
fresh = "--fresh" in sys.argv
tol_pp, tol_ratio = (0.5, 0.01) if fresh else (1e-6, 1e-9)

ref = json.loads((HERE / "paper" / "results.json").read_text(encoding="utf-8"))
data = core.load_raw_data(use_snapshot=not fresh, save_snapshot=False)
a = core.analyze(data)

issues = core.validate(data, a)
for i in issues:
    print("CONTROLLO DATI:", i)

checks = [  # (nome, valore di riferimento, valore ricalcolato, tolleranza)
    ("SPY rendimento cumulato %", ref["metrics"]["SPY"]["cum"], a.metrics["SPY"]["cum"], tol_pp),
    ("RSP rendimento cumulato %", ref["metrics"]["RSP"]["cum"], a.metrics["RSP"]["cum"], tol_pp),
    ("Top 50 senza Mag7 %", ref["metrics"]["ExMag7"]["cum"], a.metrics["ExMag7"]["cum"], tol_pp),
    ("Solo Mag7 %", ref["metrics"]["Mag7"]["cum"], a.metrics["Mag7"]["cum"], tol_pp * 4),
    ("Quota Mag7 inizio %", ref["concentration"]["mag7_start_pct"], a.summary["conc_start_pct"], tol_pp),
    ("Quota Mag7 fine %", ref["concentration"]["mag7_end_pct"], a.summary["conc_end_pct"], tol_pp),
    ("Quota del rendimento Mag7 %", ref["reconstructed_index"]["mag7_share_of_return_pct"],
     a.summary["excluded_share_of_return_pct"], tol_pp),
    ("Correlazione top 50 vs SPY", ref["reconstructed_index"]["corr_full_vs_spy"],
     a.summary["corr_full_vs_spy"], tol_ratio),
    ("t-test p-value", ref["ttest_spy_vs_rsp"]["p_value"], a.ttest["p_value"], tol_ratio * 2),
    ("Giorni di borsa", ref["period"]["n_days"], len(a.trading_days), 0),
]
failed = 0
print(f"\n{'misura':32s} {'paper':>12s} {'ricalcolo':>12s}  esito")
for name, r, v, tol in checks:
    ok = abs(r - v) <= tol
    failed += not ok
    print(f"{name:32s} {r:12.4f} {v:12.4f}  {'ok' if ok else 'DIVERSO'}")
print(f"\nModalita': {'download nuovo' if fresh else 'snapshot'}; dati scaricati il {data.get('downloaded')}")
if failed or issues:
    print(f"{failed} misure fuori tolleranza, {len(issues)} problemi nei dati")
    sys.exit(1)
print("Replica riuscita: i numeri coincidono con quelli del paper.")
