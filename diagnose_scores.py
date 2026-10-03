import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib

X_train = pd.read_parquet("/home/hadiya/fyp/data/X_train.parquet")
y_train = pd.read_parquet("/home/hadiya/fyp/data/y_train.parquet")["Label"]
benign_train = X_train[y_train == "Benign"]

scaler = joblib.load("/home/hadiya/fyp/zeroday_scaler.pkl")
iso = joblib.load("/home/hadiya/fyp/IsolationForest_zeroday_model.pkl")

udplag = pd.read_parquet("/home/hadiya/fyp/data/UDPLag-training.parquet")
udplag_attack = udplag[udplag["Label"] != "Benign"].drop(columns=["Label"])[benign_train.columns]
udplag_benign = udplag[udplag["Label"] == "Benign"].drop(columns=["Label"])[benign_train.columns]

attack_scaled = scaler.transform(udplag_attack)
benign_scaled = scaler.transform(udplag_benign)

attack_scores = iso.score_samples(attack_scaled)
benign_scores = iso.score_samples(benign_scaled)

print("Benign (training) score range: mean =", iso.score_samples(scaler.transform(benign_train)).mean())
print("UDPLag Attack scores -> mean:", attack_scores.mean(), "std:", attack_scores.std())
print("UDPLag Benign scores -> mean:", benign_scores.mean(), "std:", benign_scores.std())
print("\nOverlap check - min/max of each:")
print("Attack range:", attack_scores.min(), "to", attack_scores.max())
print("Benign range:", benign_scores.min(), "to", benign_scores.max())
