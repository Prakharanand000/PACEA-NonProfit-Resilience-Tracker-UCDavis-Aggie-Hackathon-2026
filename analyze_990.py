"""
Nonprofit Resilience Analytics Pipeline
========================================
Takes parsed 990 data and produces:
1. Resilience Score Model
2. Peer Benchmarking Framework  
3. Funding Shock Simulator

Usage:
    python analyze_990.py --input "D:\Aggie Hackathon\990_parsed.csv" --output-dir "D:\Aggie Hackathon\analysis"
"""

import os
import sys
import argparse
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from pathlib import Path

# ---------------------------------------------------------------------------
# DATA LOADING & CLEANING
# ---------------------------------------------------------------------------

def load_and_clean(csv_path):
    """Load parsed 990 data and perform cleaning."""
    print("Loading data...")
    df = pd.read_csv(csv_path, low_memory=False)
    print(f"  Raw records: {len(df):,}")
    
    # Filter to Form 990 only for core analysis (990PF and 990T are supplementary)
    # Keep 990PF separate for foundation analysis
    df_990 = df[df["return_type"] == "990"].copy()
    df_990pf = df[df["return_type"] == "990PF"].copy()
    df_990t = df[df["return_type"] == "990T"].copy()
    
    print(f"  Form 990:   {len(df_990):,}")
    print(f"  Form 990PF: {len(df_990pf):,}")
    print(f"  Form 990T:  {len(df_990t):,}")
    
    # Clean numeric columns
    numeric_cols = [
        "contributions_grants", "program_service_revenue", "investment_income",
        "other_revenue", "total_revenue", "govt_grants",
        "total_functional_expenses", "grants_and_similar", "salaries_compensation",
        "program_expenses", "management_expenses", "fundraising_expenses",
        "total_assets_boy", "total_assets_eoy",
        "total_liabilities_boy", "total_liabilities_eoy",
        "net_assets_boy", "net_assets_eoy", "cash_savings",
        "revenue_less_expenses",
        "num_employees", "num_volunteers",
        "num_voting_members", "num_independent_members",
    ]
    
    for col in numeric_cols:
        if col in df_990.columns:
            df_990[col] = pd.to_numeric(df_990[col], errors="coerce")
    
    # Derive tax year as integer
    df_990["tax_yr"] = pd.to_numeric(df_990["tax_year"].astype(str).str[:4], errors="coerce")
    df_990 = df_990.dropna(subset=["tax_yr"])
    df_990["tax_yr"] = df_990["tax_yr"].astype(int)
    
    # Drop filings with no revenue AND no expense data (empty/placeholder filings)
    df_990 = df_990[
        df_990["total_revenue"].notna() | df_990["total_functional_expenses"].notna()
    ]
    
    print(f"  After cleaning: {len(df_990):,} Form 990 records")
    
    return df_990, df_990pf, df_990t


# ---------------------------------------------------------------------------
# FEATURE ENGINEERING
# ---------------------------------------------------------------------------

def engineer_features(df):
    """Create financial health features from raw 990 fields."""
    print("Engineering features...")
    
    # --- REVENUE COMPOSITION (for diversification) ---
    # Fill missing revenue components with 0 for ratio calculations
    for col in ["contributions_grants", "program_service_revenue", "investment_income", "other_revenue"]:
        df[col] = df[col].fillna(0)
    
    # Revenue total (recalculate if missing)
    df["total_revenue_calc"] = df[["contributions_grants", "program_service_revenue", 
                                    "investment_income", "other_revenue"]].sum(axis=1)
    df["total_revenue"] = df["total_revenue"].fillna(df["total_revenue_calc"])
    
    # Revenue shares
    rev = df["total_revenue"].replace(0, np.nan)
    df["pct_contributions"] = df["contributions_grants"] / rev
    df["pct_program_revenue"] = df["program_service_revenue"] / rev
    df["pct_investment_income"] = df["investment_income"] / rev
    df["pct_other_revenue"] = df["other_revenue"] / rev
    
    # --- REVENUE DIVERSIFICATION (Herfindahl-Hirschman Index) ---
    # HHI ranges 0 to 1; lower = more diversified
    shares = df[["pct_contributions", "pct_program_revenue", 
                  "pct_investment_income", "pct_other_revenue"]].clip(0, 1)
    df["revenue_hhi"] = (shares ** 2).sum(axis=1)
    
    # --- OPERATING METRICS ---
    expenses = df["total_functional_expenses"].replace(0, np.nan)
    
    # Operating margin
    df["operating_margin"] = df["revenue_less_expenses"] / rev
    
    # Operating reserve ratio (months of expenses covered by net assets)
    df["operating_reserve_months"] = (df["net_assets_eoy"] / (expenses / 12))
    
    # Program expense ratio (higher = more mission-focused)
    df["program_expense_ratio"] = df["program_expenses"] / expenses
    
    # Management expense ratio
    df["mgmt_expense_ratio"] = df["management_expenses"] / expenses
    
    # Fundraising efficiency
    df["fundraising_ratio"] = df["fundraising_expenses"] / expenses
    
    # --- BALANCE SHEET HEALTH ---
    assets = df["total_assets_eoy"].replace(0, np.nan)
    
    # Debt ratio
    df["debt_ratio"] = df["total_liabilities_eoy"] / assets
    
    # Asset growth
    df["asset_growth"] = (df["total_assets_eoy"] - df["total_assets_boy"]) / df["total_assets_boy"].replace(0, np.nan)
    
    # Net asset growth
    df["net_asset_growth"] = (df["net_assets_eoy"] - df["net_assets_boy"]) / df["net_assets_boy"].replace(0, np.nan).abs()
    
    # --- SIZE CLASSIFICATION ---
    df["size_bucket"] = pd.cut(
        df["total_revenue"],
        bins=[-np.inf, 100_000, 500_000, 1_000_000, 5_000_000, 25_000_000, 100_000_000, np.inf],
        labels=["<100K", "100K-500K", "500K-1M", "1M-5M", "5M-25M", "25M-100M", ">100M"]
    )
    
    # --- GOVERNANCE SCORE ---
    gov_cols = ["independent_audit", "conflict_of_interest_policy", 
                "whistleblower_policy", "document_retention_policy"]
    for col in gov_cols:
        if col in df.columns:
            df[col] = df[col].map({True: 1, False: 0, "True": 1, "False": 0}).fillna(0)
    
    available_gov = [c for c in gov_cols if c in df.columns]
    if available_gov:
        df["governance_score"] = df[available_gov].sum(axis=1) / len(available_gov)
    
    print(f"  Engineered {len([c for c in df.columns if c not in ['ein']])} features")
    return df


# ---------------------------------------------------------------------------
# 1. RESILIENCE SCORING MODEL
# ---------------------------------------------------------------------------

def compute_resilience_scores(df):
    """
    Build a composite Resilience Index from financial health indicators.
    Uses a normalized scoring approach across key dimensions.
    """
    print("\n" + "="*60)
    print("1. COMPUTING RESILIENCE SCORES")
    print("="*60)
    
    # Work with latest filing per EIN
    latest = df.sort_values("tax_yr").groupby("ein").last().reset_index()
    print(f"  Unique organizations: {len(latest):,}")
    
    # Define resilience components and their ideal direction
    components = {
        # (column, weight, higher_is_better)
        "operating_reserve_months": (0.25, True),   # Liquidity buffer
        "revenue_hhi":             (0.15, False),   # Diversification (lower HHI = better)
        "program_expense_ratio":   (0.15, True),    # Mission focus
        "operating_margin":        (0.15, True),    # Surplus generation
        "debt_ratio":              (0.10, False),   # Leverage (lower = better)
        "governance_score":        (0.10, True),    # Governance quality
        "asset_growth":            (0.10, True),    # Growth trajectory
    }
    
    scored = latest.copy()
    
    for col, (weight, higher_better) in components.items():
        if col not in scored.columns:
            continue
        
        vals = scored[col].copy()
        
        # Winsorize at 1st and 99th percentile to handle outliers
        lo, hi = vals.quantile(0.01), vals.quantile(0.99)
        vals = vals.clip(lo, hi)
        
        # Min-max normalize to 0-100
        vmin, vmax = vals.min(), vals.max()
        if vmax > vmin:
            normalized = (vals - vmin) / (vmax - vmin) * 100
        else:
            normalized = 50.0
        
        # Flip if lower is better
        if not higher_better:
            normalized = 100 - normalized
        
        scored[f"score_{col}"] = normalized
    
    # Composite weighted score
    score_cols = [c for c in scored.columns if c.startswith("score_")]
    weights = []
    for col in score_cols:
        base = col.replace("score_", "")
        if base in components:
            weights.append(components[base][0])
        else:
            weights.append(1.0 / len(score_cols))
    
    # Normalize weights
    total_w = sum(weights)
    weights = [w / total_w for w in weights]
    
    scored["resilience_index"] = sum(
        scored[col].fillna(50) * w for col, w in zip(score_cols, weights)
    )
    
    # Classify into tiers
    scored["resilience_tier"] = pd.cut(
        scored["resilience_index"],
        bins=[0, 30, 50, 70, 100],
        labels=["Critical", "At Risk", "Stable", "Thriving"]
    )
    
    # Summary stats
    print("\n  Resilience Tier Distribution:")
    tier_counts = scored["resilience_tier"].value_counts().sort_index()
    for tier, count in tier_counts.items():
        pct = count / len(scored) * 100
        print(f"    {tier:12s}: {count:>8,} ({pct:5.1f}%)")
    
    print(f"\n  Mean Resilience Index: {scored['resilience_index'].mean():.1f}")
    print(f"  Median:               {scored['resilience_index'].median():.1f}")
    
    return scored


# ---------------------------------------------------------------------------
# 2. PEER BENCHMARKING
# ---------------------------------------------------------------------------

def build_peer_benchmarks(df):
    """
    Create peer group benchmarks by state x size bucket.
    Returns percentile rankings within peer groups.
    """
    print("\n" + "="*60)
    print("2. BUILDING PEER BENCHMARKS")
    print("="*60)
    
    # Use latest filing per EIN
    latest = df.sort_values("tax_yr").groupby("ein").last().reset_index()
    
    # Define peer groups: state x size bucket
    latest["peer_group"] = latest["state"].astype(str) + "_" + latest["size_bucket"].astype(str)
    
    # Metrics to benchmark
    benchmark_metrics = [
        "total_revenue", "total_functional_expenses",
        "operating_margin", "program_expense_ratio",
        "fundraising_ratio", "operating_reserve_months",
        "revenue_hhi", "debt_ratio", "net_assets_eoy",
        "num_employees"
    ]
    
    available_metrics = [m for m in benchmark_metrics if m in latest.columns]
    
    # Compute percentile within peer group
    for metric in available_metrics:
        latest[f"pctile_{metric}"] = latest.groupby("peer_group")[metric].rank(pct=True) * 100
    
    # Peer group summary stats
    peer_stats = latest.groupby("peer_group").agg(
        count=("ein", "count"),
        median_revenue=("total_revenue", "median"),
        median_expenses=("total_functional_expenses", "median"),
        median_operating_margin=("operating_margin", "median"),
        median_program_ratio=("program_expense_ratio", "median"),
        median_reserve_months=("operating_reserve_months", "median"),
    ).reset_index()
    
    # Filter to meaningful peer groups (at least 10 members)
    peer_stats_valid = peer_stats[peer_stats["count"] >= 10]
    
    print(f"  Total peer groups: {len(peer_stats):,}")
    print(f"  With 10+ members: {len(peer_stats_valid):,}")
    print(f"  Benchmarked metrics: {len(available_metrics)}")
    
    # Size bucket distribution
    print("\n  Size Bucket Distribution:")
    size_dist = latest["size_bucket"].value_counts().sort_index()
    for bucket, count in size_dist.items():
        print(f"    {str(bucket):12s}: {count:>8,}")
    
    return latest, peer_stats


# ---------------------------------------------------------------------------
# 3. FUNDING SHOCK SIMULATION
# ---------------------------------------------------------------------------

def simulate_funding_shock(df, shock_scenarios=None):
    """
    Simulate the impact of funding shocks on nonprofit financial health.
    Models: what happens if contributions drop X%? If govt grants disappear?
    """
    print("\n" + "="*60)
    print("3. FUNDING SHOCK SIMULATION")
    print("="*60)
    
    if shock_scenarios is None:
        shock_scenarios = [
            {"name": "Mild Recession", "contributions_drop": 0.15, "investment_drop": 0.20, "govt_drop": 0.05},
            {"name": "Severe Recession", "contributions_drop": 0.30, "investment_drop": 0.40, "govt_drop": 0.10},
            {"name": "Govt Funding Cut", "contributions_drop": 0.00, "investment_drop": 0.00, "govt_drop": 0.50},
            {"name": "Donor Fatigue", "contributions_drop": 0.25, "investment_drop": 0.05, "govt_drop": 0.00},
            {"name": "Pandemic Shock", "contributions_drop": 0.10, "investment_drop": 0.35, "govt_drop": -0.20},
        ]
    
    # Use latest filing per EIN
    latest = df.sort_values("tax_yr").groupby("ein").last().reset_index()
    
    results = []
    
    for scenario in shock_scenarios:
        print(f"\n  Scenario: {scenario['name']}")
        
        sim = latest.copy()
        
        # Apply shocks to revenue components
        sim["shocked_contributions"] = sim["contributions_grants"] * (1 - scenario["contributions_drop"])
        sim["shocked_investment"] = sim["investment_income"] * (1 - scenario["investment_drop"])
        
        # Government grants shock
        if "govt_grants" in sim.columns and sim["govt_grants"].notna().any():
            sim["shocked_govt"] = sim["govt_grants"].fillna(0) * (1 - scenario["govt_drop"])
            # Adjust contributions by the govt grant change
            govt_change = sim["govt_grants"].fillna(0) * scenario["govt_drop"]
            sim["shocked_contributions"] = sim["shocked_contributions"] - govt_change.clip(lower=0)
        
        # New total revenue
        sim["shocked_revenue"] = (
            sim["shocked_contributions"] + 
            sim["program_service_revenue"].fillna(0) + 
            sim["shocked_investment"] + 
            sim["other_revenue"].fillna(0)
        )
        
        # Revenue change
        sim["revenue_change_pct"] = (
            (sim["shocked_revenue"] - sim["total_revenue"]) / 
            sim["total_revenue"].replace(0, np.nan) * 100
        )
        
        # Can they still cover expenses?
        sim["shocked_surplus"] = sim["shocked_revenue"] - sim["total_functional_expenses"].fillna(0)
        sim["was_surplus"] = sim["revenue_less_expenses"].fillna(0) > 0
        sim["now_deficit"] = sim["shocked_surplus"] < 0
        sim["newly_in_deficit"] = sim["was_surplus"] & sim["now_deficit"]
        
        # Months of reserves to cover the gap
        monthly_gap = (-sim["shocked_surplus"]).clip(lower=0) / 12
        sim["months_until_insolvent"] = sim["net_assets_eoy"].fillna(0) / monthly_gap.replace(0, np.nan)
        sim["months_until_insolvent"] = sim["months_until_insolvent"].clip(0, 120)  # Cap at 10 years
        
        # At-risk: in deficit with < 6 months reserves
        sim["high_risk"] = sim["now_deficit"] & (sim["months_until_insolvent"] < 6)
        sim["medium_risk"] = sim["now_deficit"] & (sim["months_until_insolvent"].between(6, 18))
        
        # Summary
        total = len(sim)
        in_deficit = sim["now_deficit"].sum()
        newly_deficit = sim["newly_in_deficit"].sum()
        high_risk = sim["high_risk"].sum()
        
        print(f"    Organizations in deficit:     {in_deficit:>8,} ({in_deficit/total*100:.1f}%)")
        print(f"    Newly pushed to deficit:      {newly_deficit:>8,} ({newly_deficit/total*100:.1f}%)")
        print(f"    High risk (<6mo reserves):    {high_risk:>8,} ({high_risk/total*100:.1f}%)")
        print(f"    Median revenue change:        {sim['revenue_change_pct'].median():.1f}%")
        
        results.append({
            "scenario": scenario["name"],
            "total_orgs": total,
            "in_deficit": int(in_deficit),
            "newly_in_deficit": int(newly_deficit),
            "high_risk": int(high_risk),
            "median_revenue_change_pct": sim["revenue_change_pct"].median(),
            "mean_months_to_insolvent": sim.loc[sim["now_deficit"], "months_until_insolvent"].mean(),
        })
        
        sim["scenario"] = scenario["name"]
    
    return pd.DataFrame(results), latest


# ---------------------------------------------------------------------------
# 4. LONGITUDINAL / PANEL ANALYSIS
# ---------------------------------------------------------------------------

def longitudinal_analysis(df):
    """Analyze trends over time per organization for resilience prediction."""
    print("\n" + "="*60)
    print("4. LONGITUDINAL ANALYSIS")
    print("="*60)
    
    # Organizations with multiple years of data
    year_counts = df.groupby("ein")["tax_yr"].nunique()
    multi_year = year_counts[year_counts >= 3].index
    panel = df[df["ein"].isin(multi_year)].copy()
    
    print(f"  Organizations with 3+ years of data: {len(multi_year):,}")
    print(f"  Total panel observations: {len(panel):,}")
    
    # Revenue volatility (coefficient of variation over time)
    rev_stats = panel.groupby("ein").agg(
        rev_mean=("total_revenue", "mean"),
        rev_std=("total_revenue", "std"),
        rev_min=("total_revenue", "min"),
        rev_max=("total_revenue", "max"),
        years_of_data=("tax_yr", "nunique"),
        first_year=("tax_yr", "min"),
        last_year=("tax_yr", "max"),
    ).reset_index()
    
    rev_stats["revenue_cv"] = rev_stats["rev_std"] / rev_stats["rev_mean"].replace(0, np.nan)
    
    # Revenue CAGR
    first_last = panel.sort_values("tax_yr").groupby("ein").agg(
        first_rev=("total_revenue", "first"),
        last_rev=("total_revenue", "last"),
        n_years=("tax_yr", lambda x: x.max() - x.min())
    ).reset_index()
    
    first_last["cagr"] = np.where(
        (first_last["first_rev"] > 0) & (first_last["n_years"] > 0),
        (first_last["last_rev"] / first_last["first_rev"]) ** (1 / first_last["n_years"]) - 1,
        np.nan
    )
    
    rev_stats = rev_stats.merge(first_last[["ein", "cagr"]], on="ein", how="left")
    
    print(f"\n  Revenue Volatility Distribution:")
    print(f"    Median CV:  {rev_stats['revenue_cv'].median():.3f}")
    print(f"    Mean CAGR:  {rev_stats['cagr'].mean():.1%}")
    
    return rev_stats


# ---------------------------------------------------------------------------
# HIDDEN GEMS ANALYSIS
# ---------------------------------------------------------------------------

def find_hidden_gems(scored_df, percentile_threshold=75):
    """
    Identify 'hidden gems' -- small nonprofits with high resilience and 
    strong program ratios where donations could have outsized impact.
    """
    print("\n" + "="*60)
    print("5. HIDDEN GEMS ANALYSIS")
    print("="*60)
    
    gems = scored_df[
        (scored_df["total_revenue"] < 1_000_000) &  # Small
        (scored_df["resilience_index"] > scored_df["resilience_index"].quantile(0.60)) &  # Decent resilience
        (scored_df["program_expense_ratio"] > 0.70) &  # Mission-focused
        (scored_df["operating_reserve_months"] < 6) &  # Could use help
        (scored_df["operating_margin"] > -0.10)  # Not deeply in the red
    ].copy()
    
    gems["impact_score"] = (
        gems["program_expense_ratio"].fillna(0) * 0.3 +
        (1 - gems["revenue_hhi"].fillna(0.5)) * 0.2 +
        gems["governance_score"].fillna(0) * 0.2 +
        (1 - gems["debt_ratio"].fillna(0.5).clip(0, 1)) * 0.15 +
        gems["resilience_index"].fillna(50) / 100 * 0.15
    )
    
    gems = gems.sort_values("impact_score", ascending=False)
    
    print(f"  Hidden gems found: {len(gems):,}")
    if len(gems) > 0:
        print(f"  Median revenue:    ${gems['total_revenue'].median():,.0f}")
        print(f"  Median program %:  {gems['program_expense_ratio'].median():.1%}")
        print(f"  Median reserves:   {gems['operating_reserve_months'].median():.1f} months")
    
    return gems


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Nonprofit Resilience Analytics")
    parser.add_argument("--input", required=True, help="Path to parsed 990 CSV")
    parser.add_argument("--output-dir", default=None, help="Output directory")
    args = parser.parse_args()
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        sys.exit(1)
    
    output_dir = Path(args.output_dir) if args.output_dir else input_path.parent / "analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load & clean
    df_990, df_990pf, df_990t = load_and_clean(str(input_path))
    
    # Feature engineering
    df_990 = engineer_features(df_990)
    
    # Save engineered features
    df_990.to_csv(output_dir / "990_features.csv", index=False)
    print(f"\nSaved features to {output_dir / '990_features.csv'}")
    
    # 1. Resilience scores
    scored = compute_resilience_scores(df_990)
    scored.to_csv(output_dir / "resilience_scores.csv", index=False)
    
    # 2. Peer benchmarks
    benchmarked, peer_stats = build_peer_benchmarks(df_990)
    benchmarked.to_csv(output_dir / "peer_benchmarks.csv", index=False)
    peer_stats.to_csv(output_dir / "peer_group_stats.csv", index=False)
    
    # 3. Funding shock simulation
    shock_results, _ = simulate_funding_shock(df_990)
    shock_results.to_csv(output_dir / "shock_simulation_results.csv", index=False)
    
    # 4. Longitudinal analysis
    rev_stats = longitudinal_analysis(df_990)
    rev_stats.to_csv(output_dir / "longitudinal_stats.csv", index=False)
    
    # 5. Hidden gems
    gems = find_hidden_gems(scored)
    gems.to_csv(output_dir / "hidden_gems.csv", index=False)
    
    print(f"\n{'='*60}")
    print(f"ALL ANALYSIS COMPLETE")
    print(f"{'='*60}")
    print(f"Output directory: {output_dir}")
    print(f"Files created:")
    for f in sorted(output_dir.glob("*.csv")):
        size_mb = f.stat().st_size / 1e6
        print(f"  {f.name:40s} {size_mb:>8.1f} MB")


if __name__ == "__main__":
    main()
