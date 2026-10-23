import glob, os
import pandas as pd
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

feat = ["pkts_per_s", "bytes_per_s", "avg_pkt_size"]
files = sorted(glob.glob(os.path.expanduser("~/fyp/ds_flow_stats_*.csv")))
runs = [pd.read_csv(f) for f in files]
for f, r in zip(files, runs):
    print(os.path.basename(f), len(r))

def xy(d):
    return d[feat], (d["label"] == "attack").astype(int)

def make():
    return XGBClassifier(n_estimators=100, max_depth=3, eval_metric="logloss")

def fit_eval(tr, te, name):
    Xtr, ytr = xy(tr)
    Xte, yte = xy(te)
    m = make().fit(Xtr, ytr)
    p = m.predict(Xte)
    print("\n", name, "accuracy", round(accuracy_score(yte, p), 4))
    print(confusion_matrix(yte, p))
    print(classification_report(yte, p, target_names=["normal", "attack"], zero_division=0))

fit_eval(runs[0], runs[1], "train run1 -> test run2")
fit_eval(runs[1], runs[0], "train run2 -> test run1")

X, y = xy(pd.concat(runs))
make().fit(X, y).save_model(os.path.expanduser("~/fyp/xgb_mininet.json"))
print("saved xgb_mininet.json, features:", feat)
