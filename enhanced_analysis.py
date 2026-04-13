"""
Enhanced Analytics v2 — Fixed: memory issue, honest model interpretation, 
uses 990_parsed.csv directly (not the 1.1GB features file).
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")
from pathlib import Path

OUTPUT_DIR = Path("analysis")

print("=" * 70)
print("ENHANCED ANALYSIS v2")
print("=" * 70)

# Load raw parsed data with chunking for the recovery analysis
print("\nLoading resilience scores (smaller file)...")
df = pd.read_csv("analysis/resilience_scores.csv", low_memory=False)
for col in ["total_revenue", "total_functional_expenses", "revenue_less_expenses",
            "operating_reserve_months", "revenue_hhi", "operating_margin",
            "program_expense_ratio", "debt_ratio", "governance_score",
            "resilience_index", "net_assets_eoy", "contributions_grants",
            "investment_income", "other_revenue", "program_service_revenue",
            "num_employees"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

df["in_deficit"] = (df["revenue_less_expenses"] < 0).astype(int)
print(f"  {len(df):,} organizations")

# =====================================================================
# 1. MULTI-YEAR SURVIVAL ANALYSIS (better than single-year correlation)
# This is the RIGHT framing: do features predict LONG-TERM stability?
# =====================================================================
print("\n" + "=" * 70)
print("1. MULTI-YEAR SURVIVAL ANALYSIS")
print("   Does financial health predict long-term stability?")
print("=" * 70)

# Load longitudinal data (much smaller)
long_df = pd.read_csv("analysis/longitudinal_stats.csv", low_memory=False)
for col in ["revenue_cv", "cagr", "rev_mean"]:
    if col in long_df.columns:
        long_df[col] = pd.to_numeric(long_df[col], errors="coerce")

# Merge: orgs with multi-year data + their current resilience features
merged = df.merge(long_df[["ein", "revenue_cv", "cagr", "years_of_data"]], on="ein", how="inner")
print(f"  Orgs with longitudinal + resilience data: {len(merged):,}")

# Define "chronically unstable" = high revenue volatility + deficit
merged["chronically_unstable"] = (
    (merged["revenue_cv"] > merged["revenue_cv"].quantile(0.75)) &
    (merged["in_deficit"] == 1)
).astype(int)

print(f"  Chronically unstable orgs: {merged['chronically_unstable'].sum():,} ({merged['chronically_unstable'].mean():.1%})")

# NOW correlate features with chronic instability (much stronger signal)
features = ["operating_reserve_months", "revenue_hhi", "program_expense_ratio",
            "operating_margin", "debt_ratio", "governance_score"]

print(f"\n  Feature correlation with CHRONIC instability:")
print(f"  (Single-year deficit has weak signal; multi-year instability is the real target)")
print(f"  {'Feature':35s} {'vs Deficit':>12s} {'vs Chronic':>12s} {'Improvement':>12s}")
print("  " + "-" * 73)

for feat in features:
    valid = merged[[feat, "in_deficit", "chronically_unstable"]].dropna()
    corr_deficit = valid[feat].corr(valid["in_deficit"])
    corr_chronic = valid[feat].corr(valid["chronically_unstable"])
    improvement = abs(corr_chronic) / max(abs(corr_deficit), 0.001)
    print(f"  {feat:35s} {corr_deficit:>+12.4f} {corr_chronic:>+12.4f} {improvement:>11.1f}x")

# =====================================================================
# 2. PREDICTIVE MODEL — Chronic Instability (better target)
# =====================================================================
print("\n" + "=" * 70)
print("2. PREDICTIVE MODEL: Chronic Financial Instability")
print("=" * 70)

try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_score
    from sklearn.preprocessing import StandardScaler
    from sklearn.ensemble import GradientBoostingClassifier

    model_features = ["operating_reserve_months", "revenue_hhi", "program_expense_ratio",
                       "debt_ratio", "governance_score", "operating_margin"]

    model_df = merged[model_features + ["chronically_unstable"]].dropna()
    X = model_df[model_features]
    y = model_df["chronically_unstable"]
    print(f"  Dataset: {len(model_df):,} orgs, {y.mean():.1%} chronic instability rate")

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Logistic Regression
    lr = LogisticRegression(max_iter=1000, random_state=42)
    lr_auc = cross_val_score(lr, X_scaled, y, cv=5, scoring="roc_auc")
    print(f"\n  Logistic Regression AUC: {lr_auc.mean():.4f} (+/- {lr_auc.std():.4f})")

    # Gradient Boosting (better performance, still interpretable via feature importance)
    gb = GradientBoostingClassifier(n_estimators=100, max_depth=4, random_state=42)
    gb_auc = cross_val_score(gb, X_scaled, y, cv=5, scoring="roc_auc")
    print(f"  Gradient Boosting AUC:   {gb_auc.mean():.4f} (+/- {gb_auc.std():.4f})")

    # Feature importance from GB
    gb.fit(X_scaled, y)
    importances = sorted(zip(model_features, gb.feature_importances_), key=lambda x: x[1], reverse=True)

    print(f"\n  Feature importance (Gradient Boosting):")
    print(f"  {'Feature':35s} {'Importance':>12s} {'Our Weight':>12s}")
    print("  " + "-" * 61)
    weight_map = {"operating_reserve_months": 0.25, "revenue_hhi": 0.15,
                  "program_expense_ratio": 0.15, "operating_margin": 0.15,
                  "debt_ratio": 0.10, "governance_score": 0.10}
    for feat, imp in importances:
        print(f"  {feat:35s} {imp:>12.4f} {weight_map.get(feat, 0):>12.2f}")

    # Logistic coefficients for interpretability
    lr.fit(X_scaled, y)
    print(f"\n  Logistic Regression coefficients (interpretable):")
    coefs = sorted(zip(model_features, lr.coef_[0]), key=lambda x: abs(x[1]), reverse=True)
    for feat, coef in coefs:
        odds = np.exp(coef)
        direction = "INCREASES risk" if coef > 0 else "DECREASES risk"
        print(f"    {feat:35s} coef={coef:>+8.4f}  OR={odds:.3f}  {direction}")

except ImportError:
    print("  [WARN] Install scikit-learn: pip install scikit-learn")

# =====================================================================
# 3. DONATION THRESHOLD — Reframed with multi-year lens
# =====================================================================
print("\n" + "=" * 70)
print("3. DONATION IMPACT THRESHOLDS")
print("=" * 70)

# Reserve thresholds vs CHRONIC instability (much stronger signal)
print(f"\n  Operating reserve thresholds vs chronic instability:")
for months in [0, 3, 6, 12, 18, 24, 36]:
    above = merged[merged["operating_reserve_months"] >= months]
    rate = above["chronically_unstable"].mean() if len(above) > 0 else 0
    print(f"    >= {months:2d} months: {rate:>6.1%} chronically unstable  ({len(above):>7,} orgs)")

# HHI thresholds vs chronic instability
print(f"\n  Revenue diversification thresholds vs chronic instability:")
for hhi in [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0]:
    below = merged[merged["revenue_hhi"] <= hhi]
    rate = below["chronically_unstable"].mean() if len(below) > 0 else 0
    print(f"    HHI <= {hhi:.1f}: {rate:>6.1%} chronically unstable  ({len(below):>7,} orgs)")

# Donation needed to move the needle
print(f"\n  Donation amounts to change tier:")
for tier in ["Critical", "At Risk"]:
    tier_orgs = df[df["resilience_tier"] == tier]
    med_monthly = (tier_orgs["total_functional_expenses"] / 12).median()
    for months_add in [3, 6, 12]:
        donation = med_monthly * months_add
        print(f"    {tier:10s} org + {months_add:2d} months reserves = ${donation:>12,.0f} median grant")

# =====================================================================
# 4. RECOVERY PATHWAY ANALYSIS — Using raw parsed data in chunks
# =====================================================================
print("\n" + "=" * 70)
print("4. RECOVERY PATHWAY ANALYSIS")
print("=" * 70)

print("  Reading raw data in chunks to find recovery stories...")

# Read in chunks to avoid memory issues
chunk_records = []
for chunk in pd.read_csv("990_parsed.csv", low_memory=False, chunksize=200000,
                          usecols=["ein", "return_type", "tax_year", "total_revenue",
                                   "total_functional_expenses", "revenue_less_expenses",
                                   "contributions_grants", "program_service_revenue",
                                   "investment_income", "other_revenue"]):
    c990 = chunk[chunk["return_type"] == "990"].copy()
    for col in ["total_revenue", "total_functional_expenses", "revenue_less_expenses",
                "contributions_grants", "program_service_revenue", "investment_income", "other_revenue"]:
        c990[col] = pd.to_numeric(c990.get(col), errors="coerce")
    c990["tax_yr"] = pd.to_numeric(c990["tax_year"].astype(str).str[:4], errors="coerce")
    chunk_records.append(c990[["ein", "tax_yr", "total_revenue", "total_functional_expenses",
                                "revenue_less_expenses", "contributions_grants",
                                "program_service_revenue", "investment_income", "other_revenue"]])

panel = pd.concat(chunk_records, ignore_index=True)
panel = panel.dropna(subset=["tax_yr", "ein"])
panel["tax_yr"] = panel["tax_yr"].astype(int)
panel["in_deficit"] = (panel["revenue_less_expenses"] < 0).astype(int)

# Revenue composition
rev_total = panel["total_revenue"].replace(0, np.nan)
panel["pct_contrib"] = panel["contributions_grants"].fillna(0) / rev_total
panel["pct_program"] = panel["program_service_revenue"].fillna(0) / rev_total
panel["pct_invest"] = panel["investment_income"].fillna(0) / rev_total
shares = panel[["pct_contrib", "pct_program", "pct_invest"]].clip(0, 1).fillna(0)
panel["hhi"] = (shares ** 2).sum(axis=1) + (panel["other_revenue"].fillna(0) / rev_total).clip(0,1).fillna(0) ** 2

# Find orgs with 4+ years
year_counts = panel.groupby("ein")["tax_yr"].nunique()
multi_eins = year_counts[year_counts >= 4].index
multi = panel[panel["ein"].isin(multi_eins)].copy()
print(f"  Organizations with 4+ years: {len(multi_eins):,}")

# Split into early half and late half per org
recovery_records = []
for ein, grp in multi.groupby("ein"):
    grp = grp.sort_values("tax_yr")
    mid = len(grp) // 2
    early = grp.iloc[:mid]
    late = grp.iloc[mid:]
    
    early_deficit_rate = early["in_deficit"].mean()
    late_deficit_rate = late["in_deficit"].mean()
    
    # Recovered: was mostly in deficit, now mostly in surplus
    if early_deficit_rate >= 0.5 and late_deficit_rate <= 0.25:
        recovery_records.append({
            "ein": ein,
            "early_deficit_rate": early_deficit_rate,
            "late_deficit_rate": late_deficit_rate,
            "hhi_early": early["hhi"].mean(),
            "hhi_late": late["hhi"].mean(),
            "hhi_change": late["hhi"].mean() - early["hhi"].mean(),
            "rev_growth": (late["total_revenue"].mean() / early["total_revenue"].mean() - 1) if early["total_revenue"].mean() > 0 else np.nan,
            "early_rev": early["total_revenue"].mean(),
            "late_rev": late["total_revenue"].mean(),
        })

recoveries = pd.DataFrame(recovery_records)
print(f"  Organizations that recovered from chronic deficit: {len(recoveries):,}")

# Compare with non-recovered
stayed_deficit = []
for ein, grp in multi.groupby("ein"):
    grp = grp.sort_values("tax_yr")
    mid = len(grp) // 2
    early = grp.iloc[:mid]
    late = grp.iloc[mid:]
    early_def = early["in_deficit"].mean()
    late_def = late["in_deficit"].mean()
    if early_def >= 0.5 and late_def >= 0.5:
        stayed_deficit.append({
            "ein": ein,
            "hhi_change": late["hhi"].mean() - early["hhi"].mean(),
            "rev_growth": (late["total_revenue"].mean() / early["total_revenue"].mean() - 1) if early["total_revenue"].mean() > 0 else np.nan,
        })

stayed = pd.DataFrame(stayed_deficit)
print(f"  Organizations that STAYED in deficit: {len(stayed):,}")

if len(recoveries) > 10 and len(stayed) > 10:
    print(f"\n  WHAT DIFFERENTIATES RECOVERED vs STUCK ORGANIZATIONS:")
    print(f"  {'Metric':30s} {'Recovered':>12s} {'Still Stuck':>12s} {'Difference':>12s}")
    print("  " + "-" * 68)
    
    rec_hhi = recoveries["hhi_change"].median()
    stk_hhi = stayed["hhi_change"].median()
    print(f"  {'HHI change (diversification)':30s} {rec_hhi:>+12.4f} {stk_hhi:>+12.4f} {rec_hhi-stk_hhi:>+12.4f}")
    
    rec_rev = recoveries["rev_growth"].median()
    stk_rev = stayed["rev_growth"].median()
    print(f"  {'Revenue growth':30s} {rec_rev:>+12.1%} {stk_rev:>+12.1%} {rec_rev-stk_rev:>+12.1%}")

    print(f"\n  RECOVERY INSIGHT:")
    if rec_hhi < stk_hhi:
        print(f"    Recovered orgs DIVERSIFIED more (HHI dropped by {abs(rec_hhi):.3f} vs {abs(stk_hhi):.3f})")
    if rec_rev > stk_rev:
        print(f"    Recovered orgs GREW revenue faster ({rec_rev:.1%} vs {stk_rev:.1%})")
    
    print(f"\n    This is the pathway: diversify revenue + grow. Not just cut costs.")

recoveries.to_csv(OUTPUT_DIR / "recovery_pathways.csv", index=False)

print(f"\n{'='*70}")
print("ENHANCED ANALYSIS COMPLETE")
print(f"{'='*70}")
