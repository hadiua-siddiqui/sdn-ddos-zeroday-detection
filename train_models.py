import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.svm import SVC
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, accuracy_score
import joblib

# Load cleaned train/test data
X_train = pd.read_parquet("/home/hadiya/fyp/data/X_train.parquet")
X_test = pd.read_parquet("/home/hadiya/fyp/data/X_test.parquet")
y_train = pd.read_parquet("/home/hadiya/fyp/data/y_train.parquet")["Label"]
y_test = pd.read_parquet("/home/hadiya/fyp/data/y_test.parquet")["Label"]

print("Train:", X_train.shape, "Test:", X_test.shape)

models = {
    "RandomForest": RandomForestClassifier(n_estimators=100, random_state=42, class_weight="balanced"),
    "DecisionTree": DecisionTreeClassifier(random_state=42, class_weight="balanced"),
    "SVM": SVC(kernel="rbf", class_weight="balanced"),
    "XGBoost": XGBClassifier(eval_metric="mlogloss")
}

results = {}

for name, model in models.items():
    print(f"\n{'='*50}")
    print(f"Training {name}...")
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    results[name] = acc
    print(f"{name} Accuracy: {acc:.4f}")
    print(classification_report(y_test, preds))

    # Save the trained model
    joblib.dump(model, f"/home/hadiya/fyp/{name}_model.pkl")

print(f"\n{'='*50}")
print("Summary of all models:")
for name, acc in results.items():
    print(f"{name}: {acc:.4f}")
