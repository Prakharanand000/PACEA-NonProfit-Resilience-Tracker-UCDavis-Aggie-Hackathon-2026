"""
Patch the parsed CSV: compute missing fields from existing data.
Much faster than re-parsing 2.3M XML files.

- program_expenses = total_functional_expenses - management_expenses - fundraising_expenses
- revenue_less_expenses = total_revenue - total_functional_expenses
- operating_margin = revenue_less_expenses / total_revenue
- program_expense_ratio = program_expenses / total_functional_expenses
"""
import pandas as pd
import numpy as np

INPUT = r"D:\Aggie Hackathon\990_parsed.csv"
OUTPUT = INPUT  # overwrite in place

print("Loading data...")
df = pd.read_csv(INPUT, low_memory=False)
print(f"  Records: {len(df):,}")

# Convert to numeric
for col in ["total_revenue", "total_functional_expenses", "management_expenses",
            "fundraising_expenses", "contributions_grants", "program_service_revenue",
            "investment_income", "other_revenue", "grants_and_similar",
            "net_assets_eoy", "net_assets_boy", "total_assets_eoy", "total_liabilities_eoy"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# --- COMPUTE MISSING FIELDS ---

# revenue_less_expenses = total_revenue - total_functional_expenses
df["revenue_less_expenses"] = df["total_revenue"] - df["total_functional_expenses"]
filled = df["revenue_less_expenses"].notna().sum()
print(f"  Computed revenue_less_expenses: {filled:,} values")

# program_expenses = total_expenses - management - fundraising
df["program_expenses"] = (
    df["total_functional_expenses"] 
    - df["management_expenses"].fillna(0) 
    - df["fundraising_expenses"].fillna(0)
)
# Only valid where we have total expenses
df.loc[df["total_functional_expenses"].isna(), "program_expenses"] = np.nan
filled = df["program_expenses"].notna().sum()
print(f"  Computed program_expenses:      {filled:,} values")

# Sanity check: program expenses should be >= 0
neg_count = (df["program_expenses"] < 0).sum()
if neg_count > 0:
    print(f"  [WARN] {neg_count:,} records with negative program_expenses (clamping to 0)")
    df["program_expenses"] = df["program_expenses"].clip(lower=0)

print(f"\nSaving patched data to {OUTPUT}...")
df.to_csv(OUTPUT, index=False)
print(f"  File size: {pd.io.common.file_exists(OUTPUT) and round(os.path.getsize(OUTPUT)/1e6, 1)} MB")

# Quick verification
print("\nVerification (Form 990 only):")
d990 = df[df["return_type"] == "990"]
for col in ["revenue_less_expenses", "program_expenses"]:
    pct = d990[col].notna().mean() * 100
    med = d990[col].median()
    print(f"  {col:30s}: {pct:.1f}% filled, median = ${med:,.0f}")

import os
print(f"\nDone! File size: {os.path.getsize(OUTPUT)/1e6:.1f} MB")
print("Now re-run: python analyze_990_v2.py --input 990_parsed.csv --output-dir analysis")
