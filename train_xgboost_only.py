import pandas as pd
from xgboost import XGBClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score
import joblib

X_train = pd.read_parquet("/home/hadiya/fyp/data/X_train.parquet")
X_test = pd.read_parquet("/home/hadiya/fyp/data/X_test.parquet")
y_train = pd.read_parquet("/home/hadiya/fyp/data/y_train.parquet")["Label"]
y_test = pd.read_parquet("/home/hadiya/fyp/data/y_test.parquet")["Label"]

# XGBoost needs numeric labels, not strings
le = LabelEncoder()
y_train_enc = le.fit_transform(y_train)
y_test_enc = le.transform(y_test)

print("Training XGBoost...")
model = XGBClassifier(eval_metric="mlogloss")
model.fit(X_train, y_train_enc)
preds = model.predict(X_test)

acc = accuracy_score(y_test_enc, preds)
print(f"XGBoost Accuracy: {acc:.4f}")
print(classification_report(y_test_enc, preds, target_names=le.classes_))

joblib.dump(model, "/home/hadiya/fyp/XGBoost_model.pkl")
joblib.dump(le, "/home/hadiya/fyp/label_encoder.pkl")
print("Saved XGBoost_model.pkl and label_encoder.pkl")
