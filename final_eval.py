import glob, os
import pandas as pd
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, confusion_matrix

FEAT = ["pkts_per_s", "bytes_per_s", "avg_pkt_size"]
PROTECTED = {"00:00:00:00:00:05"}
CONSEC = 3
tr = sorted(glob.glob(os.path.expanduser("~/fyp/ds2_flow_stats_*.csv")))
te = sorted(glob.glob(os.path.expanduser("~/fyp/heldout/ds2_flow_stats_*.csv")))
assert te, "heldout mein file nahi mili"
train = pd.concat([pd.read_csv(f) for f in tr])
test = pd.concat([pd.read_csv(f) for f in te]).copy()
print("train files:", len(tr), "rows:", len(train), "| test files:", len(te), "rows:", len(test))

ytr = (train["label"] == "attack").astype(int)
yte = (test["label"] == "attack").astype(int)
m = XGBClassifier(n_estimators=100, max_depth=3, eval_metric="logloss")
m.fit(train[FEAT], ytr)
test["pred"] = m.predict(test[FEAT])
test["y"] = yte

cm = confusion_matrix(yte, test["pred"], labels=[0, 1])
print("\nHELD-OUT accuracy", round(accuracy_score(yte, test["pred"]), 4))
print("normal sahi %d | normal galat flag %d | attack miss %d | attack pakda %d"
      % (cm[0, 0], cm[0, 1], cm[1, 0], cm[1, 1]))

print("\nPer-phase:")
print(test.groupby("phase").agg(rows=("y", "size"), attack_rows=("y", "sum"),
                                flagged=("pred", "sum")))

d = test[~test["eth_src"].isin(PROTECTED)].copy()
d["poll"] = d["time"].rank(method="dense").astype(int)
print("\nBlock decision (3 lagatar polls):")
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
    blocked = best >= CONSEC
    if is_att != blocked:
        print("  %s %s -> lagatar flag %d  (%s)" % (
            ph, src, best, "FALSE BLOCK" if blocked else "MISS"))
print("(sirf galat decisions print hue; kuch na ho to sab sahi)")

m.save_model(os.path.expanduser("~/fyp/xgb_mininet3.json"))
print("\nsaved xgb_mininet3.json (sirf train files pe, heldout nahi)")
