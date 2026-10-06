import pandas as pd

files = [
    "Syn-training.parquet",
    "UDP-training.parquet",
    "NetBIOS-training.parquet",
    "MSSQL-training.parquet",
    "LDAP-training.parquet",
]

train_dfs = []
test_dfs = []

for f in files:
    df = pd.read_parquet(f"/home/hadiya/fyp/data/{f}")
    split_point = int(len(df) * 0.8)
    train_dfs.append(df.iloc[:split_point])   # first 80% = train
    test_dfs.append(df.iloc[split_point:])    # last 20% = test
    print(f, "train:", split_point, "test:", len(df) - split_point)

train_df = pd.concat(train_dfs, ignore_index=True)
test_df = pd.concat(test_dfs, ignore_index=True)

# Clean both (same steps as before)
import numpy as np
for d in [train_df, test_df]:
    d.drop_duplicates(inplace=True)
    d.replace([np.inf, -np.inf], np.nan, inplace=True)
train_df.dropna(inplace=True)
test_df.dropna(inplace=True)

print("\nFinal train shape:", train_df.shape)
print("Final test shape:", test_df.shape)
print("\nTrain label distribution:")
print(train_df["Label"].value_counts())
print("\nTest label distribution:")
print(test_df["Label"].value_counts())

X_train = train_df.drop(columns=["Label"])
y_train = train_df["Label"]
X_test = test_df.drop(columns=["Label"])
y_test = test_df["Label"]

X_train.to_parquet("/home/hadiya/fyp/data/X_train_timebased.parquet")
X_test.to_parquet("/home/hadiya/fyp/data/X_test_timebased.parquet")
y_train.to_frame().to_parquet("/home/hadiya/fyp/data/y_train_timebased.parquet")
y_test.to_frame().to_parquet("/home/hadiya/fyp/data/y_test_timebased.parquet")
print("\nSaved time-based split files!")
