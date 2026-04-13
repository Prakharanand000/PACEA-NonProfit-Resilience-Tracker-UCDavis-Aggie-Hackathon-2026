"""Quick diagnostic on the resilience scores to understand NaN patterns and fix hidden gems."""
import pandas as pd
import numpy as np

print("Loading resilience scores...")
df = pd.read_csv(r"D:\Aggie Hackathon\analysis\resilience_scores.csv", low_memory=False)
print(f"Records: {len(df):,}")

# Check NaN rates for key columns
key_cols = ["total_revenue", "total_functional_expenses", "program_expenses",
            "management_expenses", "fundraising_expenses",
            "operating_margin", "program_expense_ratio", "operating_reserve_months",
            "revenue_hhi", "debt_ratio", "governance_score", "resilience_index"]

print("\nNaN rates:")
for col in key_cols:
    if col in df.columns:
        pct_nan = df[col].isna().mean() * 100
        print(f"  {col:30s}: {pct_nan:5.1f}% NaN")

# Hidden gems: check how many pass each filter
print("\n\nHidden gems filter breakdown:")
print(f"  Total orgs:                      {len(df):,}")

f1 = df["total_revenue"].between(50_000, 2_000_000)
print(f"  Revenue $50K-$2M:                {f1.sum():,}")

f2 = df["program_expense_ratio"] > 0.65
print(f"  Program ratio > 65%%:             {f2.sum():,}")

f2b = (df["program_expense_ratio"] > 0.65) | df["program_expense_ratio"].isna()
print(f"  Program ratio > 65%% OR NaN:      {f2b.sum():,}")

f3 = df["operating_reserve_months"].between(0, 12)
print(f"  Reserves 0-12 months:            {f3.sum():,}")

f4 = df["operating_margin"] > -0.20
print(f"  Margin > -20%%:                   {f4.sum():,}")

f4b = (df["operating_margin"] > -0.20) | df["operating_margin"].isna()
print(f"  Margin > -20%% OR NaN:            {f4b.sum():,}")

ri_q40 = df["resilience_index"].quantile(0.40)
f5 = df["resilience_index"] > ri_q40
print(f"  Resilience > 40th pctile ({ri_q40:.1f}): {f5.sum():,}")

# Combined with NaN-tolerant filters
combined = f1 & f3 & f5
print(f"\n  Revenue + Reserves + Resilience:  {combined.sum():,}")

# What about using total_functional_expenses > 0 as a proxy for active orgs?
has_expenses = df["total_functional_expenses"] > 0
print(f"  Has expenses > 0:                {has_expenses.sum():,}")

# Alternative: use revenue_less_expenses as margin proxy
has_rle = df["revenue_less_expenses"].notna()
print(f"  Has revenue_less_expenses:       {has_rle.sum():,}")
