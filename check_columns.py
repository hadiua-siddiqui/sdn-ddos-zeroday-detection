import pandas as pd

df = pd.read_parquet("/home/hadiya/fyp/data/Syn-training.parquet")
print("All columns:")
for col in df.columns.tolist():
    print(col)
