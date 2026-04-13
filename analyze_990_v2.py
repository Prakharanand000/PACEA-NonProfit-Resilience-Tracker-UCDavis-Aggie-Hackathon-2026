"""
Nonprofit Resilience Analytics Pipeline v2
===========================================
Fixed: percentile-based resilience tiers, shock simulation deficit logic,
       relaxed hidden gems criteria.

Usage:
    python analyze_990_v2.py --input "D:\\Aggie Hackathon\\990_parsed.csv" --output-dir "D:\\Aggie Hackathon\\analysis"
"""

import os, sys, argparse, warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from pathlib import Path


def load_and_clean(csv_path):
    print("Loading data...")
    df = pd.read_csv(csv_path, low_memory=False)
    print(f"  Raw records: {len(df):,}")

    df_990 = df[df["return_type"] == "990"].copy()
    df_990pf = df[df["return_type"] == "990PF"].copy()
    df_990t = df[df["return_type"] == "990T"].copy()

    print(f"  Form 990:   {len(df_990):,}")
    print(f"  Form 990PF: {len(df_990pf):,}")
    print(f"  Form 990T:  {len(df_990t):,}")

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

    df_990["tax_yr"] = pd.to_numeric(df_990["tax_year"].astype(str).str[:4], errors="coerce")
    df_990 = df_990.dropna(subset=["tax_yr"])
    df_990["tax_yr"] = df_990["tax_yr"].astype(int)

    df_990 = df_990[
        df_990["total_revenue"].notna() | df_990["total_functional_expenses"].notna()
    ]

    print(f"  After cleaning: {len(df_990):,} Form 990 records")
    return df_990, df_990pf, df_990t


def engineer_features(df):
    print("Engineering features...")

    for col in ["contributions_grants", "program_service_revenue", "investment_income", "other_revenue"]:
        df[col] = df[col].fillna(0)

    df["total_revenue_calc"] = df[["contributions_grants", "program_service_revenue",
                                    "investment_income", "other_revenue"]].sum(axis=1)
    df["total_revenue"] = df["total_revenue"].fillna(df["total_revenue_calc"])

    rev = df["total_revenue"].replace(0, np.nan)
    df["pct_contributions"] = df["contributions_grants"] / rev
    df["pct_program_revenue"] = df["program_service_revenue"] / rev
    df["pct_investment_income"] = df["investment_income"] / rev
    df["pct_other_revenue"] = df["other_revenue"] / rev

    shares = df[["pct_contributions", "pct_program_revenue",
                  "pct_investment_income", "pct_other_revenue"]].clip(0, 1).fillna(0)
    df["revenue_hhi"] = (shares ** 2).sum(axis=1)

    expenses = df["total_functional_expenses"].replace(0, np.nan)
    df["operating_margin"] = df["revenue_less_expenses"] / rev
    df["operating_reserve_months"] = (df["net_assets_eoy"] / (expenses / 12))
    df["program_expense_ratio"] = df["program_expenses"] / expenses
    df["mgmt_expense_ratio"] = df["management_expenses"] / expenses
    df["fundraising_ratio"] = df["fundraising_expenses"] / expenses

    assets = df["total_assets_eoy"].replace(0, np.nan)
    df["debt_ratio"] = df["total_liabilities_eoy"] / assets
    df["asset_growth"] = (df["total_assets_eoy"] - df["total_assets_boy"]) / df["total_assets_boy"].replace(0, np.nan)
    df["net_asset_growth"] = (df["net_assets_eoy"] - df["net_assets_boy"]) / df["net_assets_boy"].replace(0, np.nan).abs()

    df["size_bucket"] = pd.cut(
        df["total_revenue"],
        bins=[-np.inf, 100_000, 500_000, 1_000_000, 5_000_000, 25_000_000, 100_000_000, np.inf],
        labels=["<100K", "100K-500K", "500K-1M", "1M-5M", "5M-25M", "25M-100M", ">100M"]
    )

    gov_cols = ["independent_audit", "conflict_of_interest_policy",
                "whistleblower_policy", "document_retention_policy"]
    for col in gov_cols:
        if col in df.columns:
            df[col] = df[col].map({True: 1, False: 0, "True": 1, "False": 0}).fillna(0)
    available_gov = [c for c in gov_cols if c in df.columns]
    if available_gov:
        df["governance_score"] = df[available_gov].sum(axis=1) / len(available_gov)

    print(f"  Engineered {len(df.columns)} columns")
    return df


def compute_resilience_scores(df):
    print("\n" + "=" * 60)
    print("1. COMPUTING RESILIENCE SCORES")
    print("=" * 60)

    latest = df.sort_values("tax_yr").groupby("ein").last().reset_index()
    print(f"  Unique organizations: {len(latest):,}")

    # Components: (weight, higher_is_better)
    components = {
        "operating_reserve_months": (0.25, True),
        "revenue_hhi":             (0.15, False),
        "program_expense_ratio":   (0.15, True),
        "operating_margin":        (0.15, True),
        "debt_ratio":              (0.10, False),
        "governance_score":        (0.10, True),
        "asset_growth":            (0.10, True),
    }

    scored = latest.copy()

    for col, (weight, higher_better) in components.items():
        if col not in scored.columns:
            continue
        vals = scored[col].copy()

        # Winsorize at 1st and 99th percentile
        lo, hi = vals.quantile(0.01), vals.quantile(0.99)
        if pd.notna(lo) and pd.notna(hi) and hi > lo:
            vals = vals.clip(lo, hi)
            normalized = (vals - lo) / (hi - lo) * 100
        else:
            normalized = pd.Series(50.0, index=scored.index)

        if not higher_better:
            normalized = 100 - normalized

        scored[f"score_{col}"] = normalized

    score_cols = [c for c in scored.columns if c.startswith("score_")]
    weights = []
    for col in score_cols:
        base = col.replace("score_", "")
        weights.append(components.get(base, (1.0 / len(score_cols), True))[0])
    total_w = sum(weights)
    weights = [w / total_w for w in weights]

    scored["resilience_index"] = sum(
        scored[col].fillna(50) * w for col, w in zip(score_cols, weights)
    )

    # Use PERCENTILE-BASED tiers (quintiles) instead of fixed thresholds
    scored["resilience_tier"] = pd.qcut(
        scored["resilience_index"],
        q=[0, 0.15, 0.40, 0.75, 1.0],
        labels=["Critical", "At Risk", "Stable", "Thriving"]
    )

    print("\n  Resilience Tier Distribution:")
    tier_counts = scored["resilience_tier"].value_counts().sort_index()
    for tier, count in tier_counts.items():
        pct = count / len(scored) * 100
        print(f"    {tier:12s}: {count:>8,} ({pct:5.1f}%)")

    print(f"\n  Mean Resilience Index: {scored['resilience_index'].mean():.1f}")
    print(f"  Median:               {scored['resilience_index'].median():.1f}")

    # Key thresholds for the presentation
    print("\n  Key Threshold Values:")
    for q, label in [(0.15, "Critical/At Risk"), (0.40, "At Risk/Stable"), (0.75, "Stable/Thriving")]:
        val = scored["resilience_index"].quantile(q)
        print(f"    {label:20s} boundary: {val:.1f}")

    # Show what drives resilience
    print("\n  Median Values by Tier:")
    tier_medians = scored.groupby("resilience_tier")[
        ["operating_reserve_months", "revenue_hhi", "program_expense_ratio",
         "operating_margin", "debt_ratio", "governance_score"]
    ].median()
    print(tier_medians.round(3).to_string())

    return scored


def build_peer_benchmarks(df):
    print("\n" + "=" * 60)
    print("2. BUILDING PEER BENCHMARKS")
    print("=" * 60)

    latest = df.sort_values("tax_yr").groupby("ein").last().reset_index()
    latest["peer_group"] = latest["state"].astype(str) + "_" + latest["size_bucket"].astype(str)

    benchmark_metrics = [
        "total_revenue", "total_functional_expenses",
        "operating_margin", "program_expense_ratio",
        "fundraising_ratio", "operating_reserve_months",
        "revenue_hhi", "debt_ratio", "net_assets_eoy", "num_employees"
    ]
    available_metrics = [m for m in benchmark_metrics if m in latest.columns]

    for metric in available_metrics:
        latest[f"pctile_{metric}"] = latest.groupby("peer_group")[metric].rank(pct=True) * 100

    peer_stats = latest.groupby("peer_group").agg(
        count=("ein", "count"),
        median_revenue=("total_revenue", "median"),
        median_expenses=("total_functional_expenses", "median"),
        median_operating_margin=("operating_margin", "median"),
        median_program_ratio=("program_expense_ratio", "median"),
        median_reserve_months=("operating_reserve_months", "median"),
    ).reset_index()

    peer_stats_valid = peer_stats[peer_stats["count"] >= 10]
    print(f"  Total peer groups: {len(peer_stats):,}")
    print(f"  With 10+ members: {len(peer_stats_valid):,}")
    print(f"  Benchmarked metrics: {len(available_metrics)}")

    print("\n  Size Bucket Distribution:")
    for bucket, count in latest["size_bucket"].value_counts().sort_index().items():
        print(f"    {str(bucket):12s}: {count:>8,}")

    # Top/bottom states by median resilience
    if "resilience_index" not in latest.columns:
        # Merge resilience scores
        pass

    return latest, peer_stats


def simulate_funding_shock(df, shock_scenarios=None):
    print("\n" + "=" * 60)
    print("3. FUNDING SHOCK SIMULATION")
    print("=" * 60)

    if shock_scenarios is None:
        shock_scenarios = [
            {"name": "Mild Recession", "contributions_drop": 0.15, "investment_drop": 0.20, "govt_drop": 0.05},
            {"name": "Severe Recession", "contributions_drop": 0.30, "investment_drop": 0.40, "govt_drop": 0.10},
            {"name": "Govt Funding Cut 50%", "contributions_drop": 0.00, "investment_drop": 0.00, "govt_drop": 0.50},
            {"name": "Donor Fatigue", "contributions_drop": 0.25, "investment_drop": 0.05, "govt_drop": 0.00},
            {"name": "Pandemic Shock", "contributions_drop": 0.10, "investment_drop": 0.35, "govt_drop": -0.20},
        ]

    latest = df.sort_values("tax_yr").groupby("ein").last().reset_index()

    # Pre-compute baseline status
    baseline_expenses = latest["total_functional_expenses"].fillna(0)
    baseline_revenue = latest["total_revenue"].fillna(0)
    baseline_surplus = baseline_revenue - baseline_expenses
    was_in_surplus = baseline_surplus >= 0

    all_scenario_details = []
    results = []

    for scenario in shock_scenarios:
        print(f"\n  Scenario: {scenario['name']}")

        sim = latest.copy()

        # Apply shocks
        shocked_contrib = sim["contributions_grants"].fillna(0) * (1 - scenario["contributions_drop"])
        shocked_invest = sim["investment_income"].fillna(0) * (1 - scenario["investment_drop"])
        shocked_program = sim["program_service_revenue"].fillna(0)  # program revenue unaffected
        shocked_other = sim["other_revenue"].fillna(0)

        # Govt grants: reduce from contributions if govt_grants field is sparse
        govt = sim["govt_grants"].fillna(0)
        govt_reduction = govt * scenario["govt_drop"]
        shocked_contrib = shocked_contrib - govt_reduction.clip(lower=0)

        shocked_revenue = shocked_contrib + shocked_program + shocked_invest + shocked_other

        rev_change_pct = ((shocked_revenue - baseline_revenue) / baseline_revenue.replace(0, np.nan) * 100)

        shocked_surplus = shocked_revenue - baseline_expenses
        now_in_deficit = shocked_surplus < 0
        newly_in_deficit = was_in_surplus & now_in_deficit

        # Months until insolvent
        monthly_gap = (-shocked_surplus).clip(lower=0) / 12
        net_assets = sim["net_assets_eoy"].fillna(0)
        months_to_insolvency = net_assets / monthly_gap.replace(0, np.nan)
        months_to_insolvency = months_to_insolvency.clip(0, 120)

        high_risk = now_in_deficit & (months_to_insolvency < 6)
        medium_risk = now_in_deficit & months_to_insolvency.between(6, 18)

        total = len(sim)
        n_deficit = int(now_in_deficit.sum())
        n_newly = int(newly_in_deficit.sum())
        n_high = int(high_risk.sum())
        n_medium = int(medium_risk.sum())

        print(f"    Total organizations:          {total:>8,}")
        print(f"    Baseline already in deficit:   {int((~was_in_surplus).sum()):>8,} ({(~was_in_surplus).mean()*100:.1f}%)")
        print(f"    Post-shock in deficit:         {n_deficit:>8,} ({n_deficit/total*100:.1f}%)")
        print(f"    NEWLY pushed to deficit:       {n_newly:>8,} ({n_newly/total*100:.1f}%)")
        print(f"    High risk (<6mo reserves):     {n_high:>8,} ({n_high/total*100:.1f}%)")
        print(f"    Medium risk (6-18mo reserves): {n_medium:>8,} ({n_medium/total*100:.1f}%)")
        print(f"    Median revenue change:         {rev_change_pct.median():.1f}%")

        results.append({
            "scenario": scenario["name"],
            "total_orgs": total,
            "baseline_in_deficit": int((~was_in_surplus).sum()),
            "post_shock_in_deficit": n_deficit,
            "newly_in_deficit": n_newly,
            "high_risk_lt6mo": n_high,
            "medium_risk_6to18mo": n_medium,
            "median_revenue_change_pct": round(rev_change_pct.median(), 2),
            "mean_months_to_insolvent": round(months_to_insolvency[now_in_deficit].mean(), 1) if now_in_deficit.any() else None,
        })

        # Save per-org detail for this scenario
        sim["scenario"] = scenario["name"]
        sim["shocked_revenue"] = shocked_revenue
        sim["revenue_change_pct"] = rev_change_pct
        sim["shocked_surplus"] = shocked_surplus
        sim["now_in_deficit"] = now_in_deficit
        sim["newly_in_deficit"] = newly_in_deficit
        sim["months_to_insolvency"] = months_to_insolvency
        sim["high_risk"] = high_risk
        all_scenario_details.append(sim)

    return pd.DataFrame(results), latest, all_scenario_details


def longitudinal_analysis(df):
    print("\n" + "=" * 60)
    print("4. LONGITUDINAL ANALYSIS")
    print("=" * 60)

    year_counts = df.groupby("ein")["tax_yr"].nunique()
    multi_year = year_counts[year_counts >= 3].index
    panel = df[df["ein"].isin(multi_year)].copy()

    print(f"  Organizations with 3+ years of data: {len(multi_year):,}")
    print(f"  Total panel observations: {len(panel):,}")

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
    print(f"    Median CV:    {rev_stats['revenue_cv'].median():.3f}")
    print(f"    Mean CAGR:    {rev_stats['cagr'].mean():.1%}")
    print(f"    Median CAGR:  {rev_stats['cagr'].median():.1%}")

    # Categorize volatility
    rev_stats["volatility_tier"] = pd.qcut(
        rev_stats["revenue_cv"].clip(0, 10),
        q=[0, 0.25, 0.50, 0.75, 1.0],
        labels=["Low", "Moderate", "High", "Very High"]
    )

    print(f"\n  Volatility Tier Distribution:")
    for tier, count in rev_stats["volatility_tier"].value_counts().sort_index().items():
        print(f"    {tier:12s}: {count:>8,}")

    return rev_stats


def find_hidden_gems(scored_df):
    print("\n" + "=" * 60)
    print("5. HIDDEN GEMS ANALYSIS")
    print("=" * 60)

    # More relaxed criteria to find actionable hidden gems
    small = scored_df["total_revenue"].between(50_000, 2_000_000)
    decent_program = scored_df["program_expense_ratio"] > 0.65
    low_reserves = scored_df["operating_reserve_months"].between(0, 12)
    not_deeply_red = scored_df["operating_margin"] > -0.20
    above_median_resilience = scored_df["resilience_index"] > scored_df["resilience_index"].quantile(0.40)

    gems = scored_df[small & decent_program & low_reserves & not_deeply_red & above_median_resilience].copy()

    # Impact score: how much would a donation help?
    gems["impact_score"] = (
        gems["program_expense_ratio"].fillna(0) * 0.25 +
        (1 - gems["revenue_hhi"].fillna(0.5).clip(0, 1)) * 0.15 +
        gems["governance_score"].fillna(0) * 0.20 +
        (1 - gems["debt_ratio"].fillna(0.5).clip(0, 1)) * 0.15 +
        gems["resilience_index"].fillna(50) / 100 * 0.15 +
        (1 - gems["operating_reserve_months"].fillna(6) / 12).clip(0, 1) * 0.10  # lower reserves = more impact
    )

    gems = gems.sort_values("impact_score", ascending=False)

    print(f"  Hidden gems found: {len(gems):,}")
    if len(gems) > 0:
        print(f"  Median revenue:       ${gems['total_revenue'].median():,.0f}")
        print(f"  Median program ratio: {gems['program_expense_ratio'].median():.1%}")
        print(f"  Median reserves:      {gems['operating_reserve_months'].median():.1f} months")
        print(f"  Median resilience:    {gems['resilience_index'].median():.1f}")

        # Show top 10
        print(f"\n  Top 10 Hidden Gems:")
        top10 = gems.head(10)[["org_name", "state", "total_revenue", "program_expense_ratio",
                                 "operating_reserve_months", "impact_score", "resilience_index"]]
        for _, row in top10.iterrows():
            name = str(row["org_name"])[:40]
            print(f"    {name:40s} {row['state']:>3s}  Rev ${row['total_revenue']:>12,.0f}  "
                  f"Prog {row['program_expense_ratio']:.0%}  Rsv {row['operating_reserve_months']:.1f}mo  "
                  f"Impact {row['impact_score']:.3f}")

    return gems


def generate_summary_stats(df, scored, shock_results, rev_stats):
    """Generate high-level summary stats for the dashboard."""
    print("\n" + "=" * 60)
    print("6. SUMMARY STATISTICS")
    print("=" * 60)

    latest = scored.copy()
    summary = {
        "total_orgs_analyzed": len(latest),
        "total_filings_parsed": len(df),
        "years_covered": f"{int(df['tax_yr'].min())}-{int(df['tax_yr'].max())}",
        "orgs_with_3plus_years": len(rev_stats),
        "median_revenue": latest["total_revenue"].median(),
        "median_expenses": latest["total_functional_expenses"].median(),
        "median_net_assets": latest["net_assets_eoy"].median(),
        "median_operating_margin": latest["operating_margin"].median(),
        "median_program_ratio": latest["program_expense_ratio"].median(),
        "median_reserve_months": latest["operating_reserve_months"].median(),
        "median_revenue_hhi": latest["revenue_hhi"].median(),
        "pct_with_audit": latest["independent_audit"].mean() * 100 if "independent_audit" in latest.columns else None,
        "pct_with_conflict_policy": latest["conflict_of_interest_policy"].mean() * 100 if "conflict_of_interest_policy" in latest.columns else None,
        "median_revenue_cv": rev_stats["revenue_cv"].median(),
        "median_cagr": rev_stats["cagr"].median(),
    }

    for k, v in summary.items():
        if isinstance(v, float):
            print(f"  {k:35s}: {v:>12,.2f}")
        else:
            print(f"  {k:35s}: {v}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Nonprofit Resilience Analytics v2")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: {input_path} not found")
        sys.exit(1)

    output_dir = Path(args.output_dir) if args.output_dir else input_path.parent / "analysis"
    output_dir.mkdir(parents=True, exist_ok=True)

    df_990, df_990pf, df_990t = load_and_clean(str(input_path))
    df_990 = engineer_features(df_990)
    df_990.to_csv(output_dir / "990_features.csv", index=False)

    scored = compute_resilience_scores(df_990)
    scored.to_csv(output_dir / "resilience_scores.csv", index=False)

    benchmarked, peer_stats = build_peer_benchmarks(df_990)
    benchmarked.to_csv(output_dir / "peer_benchmarks.csv", index=False)
    peer_stats.to_csv(output_dir / "peer_group_stats.csv", index=False)

    shock_results, _, scenario_details = simulate_funding_shock(df_990)
    shock_results.to_csv(output_dir / "shock_simulation_results.csv", index=False)

    rev_stats = longitudinal_analysis(df_990)
    rev_stats.to_csv(output_dir / "longitudinal_stats.csv", index=False)

    gems = find_hidden_gems(scored)
    gems.to_csv(output_dir / "hidden_gems.csv", index=False)

    summary = generate_summary_stats(df_990, scored, shock_results, rev_stats)
    pd.DataFrame([summary]).to_csv(output_dir / "summary_stats.csv", index=False)

    print(f"\n{'='*60}")
    print(f"ALL ANALYSIS COMPLETE")
    print(f"{'='*60}")
    print(f"Output: {output_dir}")
    for f in sorted(output_dir.glob("*.csv")):
        print(f"  {f.name:40s} {f.stat().st_size/1e6:>8.1f} MB")


if __name__ == "__main__":
    main()
