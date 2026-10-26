import glob, os
import pandas as pd
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, confusion_matrix

FEAT = ["pkts_per_s", "bytes_per_s", "avg_pkt_size"]
PROTECTED = {"00:00:00:00:00:05"}
CONSEC = 3
home = os.path.expanduser("~/fyp/")
main = sorted(glob.glob(home + "ds2_flow_stats_*.csv"))
held_B = sorted(glob.glob(home + "heldout/ds2_flow_stats_*.csv"))
held_D = sorted(glob.glob(home + "heldout_D/ds2_flow_stats_*.csv"))
assert held_D, "heldout_D mein file nahi"
day = lambda f: os.path.basename(f).split("_")[3]
old = [f for f in main if day(f) < "20261026"]
new_c = [f for f in main if day(f) >= "20261026"]
rd = lambda fs: pd.concat([pd.read_csv(f) for f in fs])
test = rd(held_D).copy()
test["y"] = (test["label"] == "attack").astype(int)
print("test D rows:", len(test), "| old:", len(old), "| C:", len(new_c), "| B:", len(held_B))


def decisions(t):
    d = t[~t["eth_src"].isin(PROTECTED)].copy()
    d["poll"] = d["time"].rank(method="dense").astype(int)
    out = []
    for (ph, src), g in d.groupby(["phase", "eth_src"]):
        s = g.groupby("poll")["pred"].max().sort_index()
        run = best = 0
        last = None
        for poll, v in s.items():
            if v == 1:
                run = run + 1 if (last is not None and poll - last == 1) else 1
                last = poll
                best = max(best, run)
            else:
                run, last = 0, None
        is_att = bool((g["label"] == "attack").any())
        if is_att != (best >= CONSEC):
            out.append("  %s %s -> lagatar %d (%s)" % (
                ph, src, best, "FALSE BLOCK" if best >= CONSEC else "MISS"))
    return out


sets = {"M1": old, "M2": old + held_B + new_c}
summ = test.groupby("phase").agg(rows=("y", "size"), attack_rows=("y", "sum"))
for name, fs in sets.items():
    tr = rd(fs)
    m = XGBClassifier(n_estimators=100, max_depth=3, eval_metric="logloss")
    m.fit(tr[FEAT], (tr["label"] == "attack").astype(int))
    t = test.copy()
    t["pred"] = m.predict(t[FEAT])
    cm = confusion_matrix(t["y"], t["pred"], labels=[0, 1])
    print("\n===", name, "| train rows", len(tr), "===")
    print("D accuracy", round(accuracy_score(t["y"], t["pred"]), 4))
    print("normal sahi %d | normal galat flag %d | attack miss %d | attack pakda %d"
          % (cm[0, 0], cm[0, 1], cm[1, 0], cm[1, 1]))
    summ[name + "_flagged"] = t.groupby("phase")["pred"].sum()
    bad = decisions(t)
    print("galat block decisions:", len(bad))
    for b in bad:
        print(b)
    if name == "M2":
        m.save_model(home + "xgb_mininet4.json")
print()
print(summ)
print("\nsaved xgb_mininet4.json (M2; D pe test hua, D pe train nahi)")
