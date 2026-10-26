import glob, os
import pandas as pd
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, confusion_matrix

FEAT = ["pkts_per_s", "bytes_per_s", "avg_pkt_size"]
PROTECTED = {"00:00:00:00:00:05"}
CONSEC = 3

files = sorted(glob.glob(os.path.expanduser("~/fyp/ds2_flow_stats_*.csv")))
runs = []
for i, f in enumerate(files):
    d = pd.read_csv(f)
    runs.append(d)
    print("run", i + 1, os.path.basename(f), len(d), "rows")


def make():
    return XGBClassifier(n_estimators=100, max_depth=3, eval_metric="logloss")


def xy(d):
    return d[FEAT], (d["label"] == "attack").astype(int)


def would_block(d):
    d = d.copy()
    d["poll"] = d["time"].rank(method="dense").astype(int)
    d = d[~d["eth_src"].isin(PROTECTED)]
    res = []
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
        res.append((ph, src, best, bool((g["label"] == "attack").any())))
    return res


for k, test in enumerate(runs):
    train = pd.concat([r for j, r in enumerate(runs) if j != k])
    Xtr, ytr = xy(train)
    Xte, yte = xy(test)
    m = make().fit(Xtr, ytr)
    test = test.copy()
    test["pred"] = m.predict(Xte)
    cm = confusion_matrix(yte, test["pred"], labels=[0, 1])
    print("\n=== test run", k + 1, "===")
    print("accuracy", round(accuracy_score(yte, test["pred"]), 4))
    print("normal sahi %d | normal galat flag %d | attack miss %d | attack pakda %d"
          % (cm[0, 0], cm[0, 1], cm[1, 0], cm[1, 1]))
    wb = would_block(test)
    att = [r for r in wb if r[3]]
    non = [r for r in wb if not r[3]]
    print("attack phases jahan block lagta:", sum(r[2] >= CONSEC for r in att), "/", len(att))
    for r in att:
        if r[2] < CONSEC:
            print("  MISS:", r[0], r[1], "lagatar flag", r[2])
    bad = [r for r in non if r[2] >= CONSEC]
    print("normal sources ka galat block:", len(bad), "/", len(non))
    for r in bad:
        print("  FALSE BLOCK:", r[0], r[1], "lagatar flag", r[2])

Xall, yall = xy(pd.concat(runs))
make().fit(Xall, yall).save_model(os.path.expanduser("~/fyp/xgb_mininet2.json"))
print("\nsaved xgb_mininet2.json")
