"""Check what columns actually have data in the parsed CSV."""
import pandas as pd

df = pd.read_csv(r"D:\Aggie Hackathon\990_parsed.csv", nrows=5000, low_memory=False)
df990 = df[df["return_type"] == "990"]

print(f"Sample: {len(df990)} Form 990 records\n")

# Check all columns for non-null rates
print("Columns with data:")
for col in sorted(df990.columns):
    non_null = df990[col].notna().sum()
    pct = non_null / len(df990) * 100
    if pct > 0:
        sample_val = df990[col].dropna().iloc[0] if non_null > 0 else ""
        print(f"  {col:40s}: {pct:5.1f}% filled  (e.g. {str(sample_val)[:50]})")

print("\n\nColumns that are EMPTY (0% filled):")
for col in sorted(df990.columns):
    if df990[col].notna().sum() == 0:
        print(f"  {col}")
