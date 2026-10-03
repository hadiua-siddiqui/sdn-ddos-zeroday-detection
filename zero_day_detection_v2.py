import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix
import joblib

X_train = pd.read_parquet("/home/hadiya/fyp/data/X_train.parquet")
y_train = pd.read_parquet("/home/hadiya/fyp/data/y_train.parquet")["Label"]

benign_train = X_train[y_train == "Benign"]
scaler = StandardScaler()
benign_train_scaled = scaler.fit_transform(benign_train)

iso = IsolationForest(random_state=42, n_estimators=200)
iso.fit(benign_train_scaled)

# Get anomaly scores on benign training data itself
benign_scores = iso.score_samples(benign_train_scaled)
# Set threshold at the 5th percentile of benign scores
threshold = np.percentile(benign_scores, 5)
print("Chosen threshold:", threshold)

udplag = pd.read_parquet("/home/hadiya/fyp/data/UDPLag-training.parquet")
udplag_attack_only = udplag[udplag["Label"] != "Benign"]
udplag_benign = udplag[udplag["Label"] == "Benign"]

X_udplag_attack = udplag_attack_only.drop(columns=["Label"])[benign_train.columns]
X_udplag_benign = udplag_benign.drop(columns=["Label"])[benign_train.columns]

X_zero_day_test = pd.concat([X_udplag_attack, X_udplag_benign])
y_zero_day_test = ["Attack"] * len(X_udplag_attack) + ["Benign"] * len(X_udplag_benign)
X_zero_day_test_scaled = scaler.transform(X_zero_day_test)

test_scores = iso.score_samples(X_zero_day_test_scaled)
preds_labeled = ["Attack" if s < threshold else "Benign" for s in test_scores]

print("\n=== Zero-Day Detection Results (threshold-based) ===")
print(classification_report(y_zero_day_test, preds_labeled))
print("Confusion Matrix:")
print(confusion_matrix(y_zero_day_test, preds_labeled, labels=["Benign", "Attack"]))

joblib.dump(iso, "/home/hadiya/fyp/IsolationForest_zeroday_model.pkl")
joblib.dump(scaler, "/home/hadiya/fyp/zeroday_scaler.pkl")
joblib.dump(threshold, "/home/hadiya/fyp/zeroday_threshold.pkl")
print("\nSaved model, scaler, and threshold")
