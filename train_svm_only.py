import pandas as pd
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, accuracy_score
import joblib

X_train = pd.read_parquet("/home/hadiya/fyp/data/X_train.parquet")
X_test = pd.read_parquet("/home/hadiya/fyp/data/X_test.parquet")
y_train = pd.read_parquet("/home/hadiya/fyp/data/y_train.parquet")["Label"]
y_test = pd.read_parquet("/home/hadiya/fyp/data/y_test.parquet")["Label"]

sample_size = 10000
X_train_sample = X_train.sample(n=sample_size, random_state=42)
y_train_sample = y_train.loc[X_train_sample.index]

# Scale features - critical for SVM
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train_sample)
X_test_scaled = scaler.transform(X_test)

print("Training SVM on scaled, sampled data:", X_train_scaled.shape)

model = SVC(kernel="rbf", class_weight="balanced")
model.fit(X_train_scaled, y_train_sample)
preds = model.predict(X_test_scaled)

acc = accuracy_score(y_test, preds)
print(f"SVM Accuracy: {acc:.4f}")
print(classification_report(y_test, preds))

joblib.dump(model, "/home/hadiya/fyp/SVM_model.pkl")
joblib.dump(scaler, "/home/hadiya/fyp/scaler.pkl")
print("Saved SVM_model.pkl and scaler.pkl")
