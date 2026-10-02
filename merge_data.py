import pandas as pd

files = [
    "Syn-training.parquet",
    "UDP-training.parquet",
    "NetBIOS-training.parquet",
    "MSSQL-training.parquet",
    "LDAP-training.parquet",
]

dfs = []
for f in files:
    path = f"/home/hadiya/fyp/data/{f}"
    df = pd.read_parquet(path)
    dfs.append(df)
    print(f, df.shape)

merged = pd.concat(dfs, ignore_index=True)
print("Merged shape:", merged.shape)
print(merged["Label"].value_counts())

merged.to_parquet("/home/hadiya/fyp/data/merged_training.parquet")
print("Saved merged_training.parquet")
