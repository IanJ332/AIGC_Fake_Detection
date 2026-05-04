import pandas as pd
from pathlib import Path

p = Path("Data_V2/extracted/numeric_claims.csv")
df = pd.read_csv(p)
print("numeric_claims rows:", len(df))
print(df["claim_type"].value_counts(dropna=False))
print("\nSample rows:")
print(df.head(10).to_string())
