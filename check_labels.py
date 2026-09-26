import pandas as pd

df = pd.read_parquet("/home/hadiya/fyp/data/Syn-training.parquet")
print(df["Label"].value_counts())
