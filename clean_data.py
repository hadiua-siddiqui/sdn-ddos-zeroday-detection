import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split

# Load merged data
df = pd.read_parquet("/home/hadiya/fyp/data/merged_training.parquet")
print("Original shape:", df.shape)

# Step 1: Remove duplicates
df = df.drop_duplicates()
print("After removing duplicates:", df.shape)

# Step 2: Handle infinite values
df = df.replace([np.inf, -np.inf], np.nan)

# Step 3: Remove nulls (including the ones created from inf)
df = df.dropna()
print("After removing nulls/infinities:", df.shape)

# Step 4: Drop leakage-causing columns (only if they exist)
leak_cols = ["Flow ID", "Source IP", "Destination IP", "Timestamp",
             "Source Port", "Destination Port"]
df = df.drop(columns=[c for c in leak_cols if c in df.columns], errors="ignore")
print("After dropping leakage columns:", df.shape)
print("Remaining columns:", df.shape[1])

# Step 5: Check class balance after cleaning
print("\nClass distribution after cleaning:")
print(df["Label"].value_counts())

# Step 6: Separate features and label
X = df.drop(columns=["Label"])
y = df["Label"]

# Step 7: Train/test split (stratified to preserve class ratios)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)
print("\nTrain size:", X_train.shape, "Test size:", X_test.shape)

# Step 8: Save everything
X_train.to_parquet("/home/hadiya/fyp/data/X_train.parquet")
X_test.to_parquet("/home/hadiya/fyp/data/X_test.parquet")
y_train.to_frame().to_parquet("/home/hadiya/fyp/data/y_train.parquet")
y_test.to_frame().to_parquet("/home/hadiya/fyp/data/y_test.parquet")
print("\nAll files saved successfully!")
