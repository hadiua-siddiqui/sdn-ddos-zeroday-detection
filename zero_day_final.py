import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import joblib

X_train = pd.read_parquet("/home/hadiya/fyp/data/X_train.parquet")
y_train = pd.read_parquet("/home/hadiya/fyp/data/y_train.parquet")["Label"]
benign_train = X_train[y_train == "Benign"]

scaler = StandardScaler()
benign_train_scaled = scaler.fit_transform(benign_train)

iso = IsolationForest(random_state=42, n_estimators=200)
iso.fit(benign_train_scaled)

benign_train_scores = iso.score_samples(benign_train_scaled)
FINAL_THRESHOLD = np.percentile(benign_train_scores, 40)
print(f"Final threshold (40th percentile): {FINAL_THRESHOLD:.4f}")

udplag = pd.read_parquet("/home/hadiya/fyp/data/UDPLag-training.parquet")
udplag_attack = udplag[udplag["Label"] != "Benign"].drop(columns=["Label"])[benign_train.columns]
udplag_benign = udplag[udplag["Label"] == "Benign"].drop(columns=["Label"])[benign_train.columns]

X_test = pd.concat([udplag_attack, udplag_benign])
y_test = ["Attack"] * len(udplag_attack) + ["Benign"] * len(udplag_benign)
X_test_scaled = scaler.transform(X_test)
test_scores = iso.score_samples(X_test_scaled)

auc = roc_auc_score([1 if l == "Attack" else 0 for l in y_test], -test_scores)
preds = ["Attack" if s < FINAL_THRESHOLD else "Benign" for s in test_scores]

print(f"\nFinal ROC-AUC: {auc:.4f}")
print("\n=== Final Zero-Day Detection Results (UDPLag held-out) ===")
print(classification_report(y_test, preds))
print("Confusion Matrix:")
print(confusion_matrix(y_test, preds, labels=["Benign", "Attack"]))

joblib.dump(iso, "/home/hadiya/fyp/IsolationForest_zeroday_model.pkl")
joblib.dump(scaler, "/home/hadiya/fyp/zeroday_scaler.pkl")
joblib.dump(FINAL_THRESHOLD, "/home/hadiya/fyp/zeroday_threshold.pkl")
print("\nSaved final model, scaler, and threshold")
