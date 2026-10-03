import pandas as pd
import numpy as np
from sklearn.metrics import classification_report, roc_auc_score
import joblib

X_train = pd.read_parquet("/home/hadiya/fyp/data/X_train.parquet")
y_train = pd.read_parquet("/home/hadiya/fyp/data/y_train.parquet")["Label"]
benign_train = X_train[y_train == "Benign"]

scaler = joblib.load("/home/hadiya/fyp/zeroday_scaler.pkl")
iso = joblib.load("/home/hadiya/fyp/IsolationForest_zeroday_model.pkl")

udplag = pd.read_parquet("/home/hadiya/fyp/data/UDPLag-training.parquet")
udplag_attack = udplag[udplag["Label"] != "Benign"].drop(columns=["Label"])[benign_train.columns]
udplag_benign = udplag[udplag["Label"] == "Benign"].drop(columns=["Label"])[benign_train.columns]

X_test = pd.concat([udplag_attack, udplag_benign])
y_test = ["Attack"] * len(udplag_attack) + ["Benign"] * len(udplag_benign)
X_test_scaled = scaler.transform(X_test)
test_scores = iso.score_samples(X_test_scaled)

# AUC tells us overall separability regardless of threshold choice
auc = roc_auc_score([1 if l == "Attack" else 0 for l in y_test], -test_scores)
print(f"ROC-AUC Score: {auc:.4f}  (0.5 = random, 1.0 = perfect)\n")

benign_train_scores = iso.score_samples(scaler.transform(benign_train))

# Try several less-strict thresholds
for pct in [50, 40, 30, 20, 10]:
    threshold = np.percentile(benign_train_scores, pct)
    preds = ["Attack" if s < threshold else "Benign" for s in test_scores]
    print(f"--- Threshold at {pct}th percentile ({threshold:.4f}) ---")
    print(classification_report(y_test, preds, zero_division=0))
