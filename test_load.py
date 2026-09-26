import pandas as pd

df = pd.read_parquet("/home/hadiya/fyp/data/Syn-training.parquet")
print(df.shape)
print(df.columns.tolist())
print(df.head())
