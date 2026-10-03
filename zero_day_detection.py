import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix
import joblib

X_train = pd.read_parquet("/home/hadiya/fyp/data/X_train.parquet")
y_train = pd.read_parquet("/home/hadiya/fyp/data/y_train.parquet")["Label"]

benign_train = X_train[y_train == "Benign"]
print("Benign training samples:", benign_train.shape)

# Scale features - critical for Isolation Forest too
scaler = StandardScaler()
benign_train_scaled = scaler.fit_transform(benign_train)

iso = IsolationForest(contamination=0.1, random_state=42, n_estimators=200)
iso.fit(benign_train_scaled)
print("Isolation Forest trained on scaled benign-only data.")

udplag = pd.read_parquet("/home/hadiya/fyp/data/UDPLag-training.parquet")
udplag_attack_only = udplag[udplag["Label"] != "Benign"]
udplag_benign = udplag[udplag["Label"] == "Benign"]

X_udplag_attack = udplag_attack_only.drop(columns=["Label"])[benign_train.columns]
X_udplag_benign = udplag_benign.drop(columns=["Label"])[benign_train.columns]

X_zero_day_test = pd.concat([X_udplag_attack, X_udplag_benign])
y_zero_day_test = ["Attack"] * len(X_udplag_attack) + ["Benign"] * len(X_udplag_benign)

# Apply the SAME scaler (fit on benign train) to test data
X_zero_day_test_scaled = scaler.transform(X_zero_day_test)

preds = iso.predict(X_zero_day_test_scaled)
preds_labeled = ["Attack" if p == -1 else "Benign" for p in preds]

print("\n=== Zero-Day Detection Results (UDPLag held-out) ===")
print(classification_report(y_zero_day_test, preds_labeled))
print("Confusion Matrix:")
print(confusion_matrix(y_zero_day_test, preds_labeled, labels=["Benign", "Attack"]))

joblib.dump(iso, "/home/hadiya/fyp/IsolationForest_zeroday_model.pkl")
joblib.dump(scaler, "/home/hadiya/fyp/zeroday_scaler.pkl")
print("\nSaved IsolationForest_zeroday_model.pkl and zeroday_scaler.pkl")
