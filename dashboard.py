"""
Nonprofit Resilience Dashboard v5 - Polished UI
================================================
streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

import base64
from pathlib import Path

st.set_page_config(page_title="PACEA by Fairlight", layout="wide", page_icon="\U0001F3C3")

# Load runner image as base64 for background
runner_bg = ""
try:
    runner_path = Path("runner.png")
    if runner_path.exists():
        runner_bg = base64.b64encode(runner_path.read_bytes()).decode()
except:
    pass

# ---- CUSTOM CSS ----
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Space+Grotesk:wght@500;700&display=swap');
    
    .stApp { background: #ffffff; font-family: 'DM Sans', sans-serif; }
    
    /* Sidebar */
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); }
    section[data-testid="stSidebar"] * { color: #cbd5e1 !important; }
    section[data-testid="stSidebar"] .stRadio label:hover { color: #38bdf8 !important; }
    
    /* Headers */
    h1 { font-family: 'Space Grotesk', sans-serif !important; color: #0f172a !important; font-weight: 700 !important; letter-spacing: -0.5px; }
    h2, h3 { font-family: 'Space Grotesk', sans-serif !important; color: #1e293b !important; }
    h4 { color: #334155 !important; }
    
    /* Metric cards */
    [data-testid="stMetric"] {
        background: white; padding: 18px 16px; border-radius: 14px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06); border: 1px solid #e2e8f0;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    [data-testid="stMetric"]:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,0.1); }
    [data-testid="stMetricValue"] { font-family: 'Space Grotesk', sans-serif !important; font-size: 1.5rem !important; color: #0f172a !important; font-weight: 700 !important; }
    [data-testid="stMetricLabel"] { font-size: 0.8rem !important; color: #64748b !important; text-transform: uppercase; letter-spacing: 0.5px; }
    
    /* Expanders */
    .streamlit-expanderHeader { background: white !important; border-radius: 10px !important; font-family: 'DM Sans', sans-serif !important; }
    
    /* DataFrames */
    .stDataFrame { border-radius: 10px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
    
    /* Progress bars */
    .stProgress > div > div { background: linear-gradient(90deg, #0d9488, #06b6d4) !important; border-radius: 8px; }
    
    /* Inputs */
    .stTextInput input { border-radius: 10px !important; border: 2px solid #e2e8f0 !important; padding: 12px !important; font-size: 1rem !important; }
    .stTextInput input:focus { border-color: #0d9488 !important; box-shadow: 0 0 0 3px rgba(13,148,136,0.15) !important; }
    
    hr { border: none; height: 1px; background: linear-gradient(90deg, transparent, #cbd5e1, transparent); margin: 24px 0; }
    
    /* Hide Streamlit toolbar */
    .stDeployButton, #MainMenu, header[data-testid="stHeader"] { display: none !important; visibility: hidden !important; }
    header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# Runner background image (separate so we can use the base64 variable)
if runner_bg:
    st.markdown(f"""
    <style>
    .stApp::before {{
        content: '';
        position: fixed;
        top: 50%;
        left: calc(50% + 130px);
        transform: translate(-50%, -50%);
        width: 60vw;
        height: 80vh;
        opacity: 0.13;
        background-image: url("data:image/png;base64,{runner_bg}");
        background-size: contain;
        background-repeat: no-repeat;
        background-position: center;
        pointer-events: none;
        z-index: 0;
    }}
    </style>
    """, unsafe_allow_html=True)

SEG_COLORS = {"Elite Performers":"#059669", "Diversified Growers":"#F59E0B", "Steady Operators":"#2563EB",
              "Emerging Organizations":"#94A3B8", "Struggling Missions":"#DC2626"}

@st.cache_data
def load_segments():
    df = pd.read_csv("analysis/nonprofit_segments.csv.gz", low_memory=False)
    for c in ["surplus_ratio","financial_cushion","revenue_diversification","revenue_stability",
              "asset_liability_ratio","total_revenue","total_functional_expenses","net_assets_eoy","hhi"]:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce")
    if "hhi" not in df.columns and "revenue_diversification" in df.columns:
        df["hhi"] = 1 - df["revenue_diversification"]
    return df

@st.cache_data
def load_readiness():
    df = pd.read_csv("analysis/client_readiness_scores.csv.gz", low_memory=False)
    for c in ["total_revenue","surplus_ratio","financial_cushion","revenue_diversification",
              "revenue_stability","asset_liability_ratio","client_readiness_score",
              "s1_surplus","s2_cushion","s3_diversification","s4_stability","s5_solvency"]:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

@st.cache_data
def load_other():
    shock = pd.read_csv("analysis/shock_simulation_results.csv")
    try: playbooks = pd.read_csv("analysis/persona_playbooks.csv")
    except: playbooks = pd.DataFrame()
    try: benchmarks = pd.read_csv("analysis/research_benchmarks.csv")
    except: benchmarks = pd.DataFrame()
    try: factors = pd.read_csv("analysis/factor_influence.csv")
    except: factors = pd.DataFrame()
    return shock, playbooks, benchmarks, factors

try:
    seg = load_segments()
    rd = load_readiness()
    shock, playbooks, benchmarks, factors = load_other()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# Sidebar
st.sidebar.markdown('<div style="text-align:center; padding-bottom:8px;"><p style="font-size:1.6rem; font-weight:700; margin:0; letter-spacing:4px;">PACEA</p><p style="font-size:0.7rem; margin:6px 0 0 0; opacity:0.6;">by Fairlight Advisors</p></div>', unsafe_allow_html=True)
st.sidebar.markdown("---")
page = st.sidebar.radio("", [
    "Overview",
    "Organization Lookup",
    "Client Readiness",
    "Nonprofit Segments",
    "Shock Simulator",
    "Thresholds & Recovery",
    "Advisory ROI",
    "Research Validation",
])
st.sidebar.markdown("---")
st.sidebar.markdown(f"**{len(rd):,} orgs scored**")
st.sidebar.markdown("Model AUC: 0.86")
st.sidebar.markdown("""\n<div style="text-align:center; padding-top:12px; border-top:1px solid rgba(255,255,255,0.1);">\n    <p style="font-size:0.65rem; opacity:0.4; margin:8px 0 0 0;">Built by</p>\n    <p style="font-size:0.85rem; font-weight:600; margin:2px 0 0 0;">The Data Gamblers</p>\n    <p style="font-size:0.6rem; opacity:0.35; margin:4px 0 0 0;">Aggie Hackathon 2026</p>\n</div>\n""", unsafe_allow_html=True)

# ==================================================================
# OVERVIEW
# ==================================================================
if page == "Overview":
    st.markdown('<h1 style="text-align:center; font-size:3.5rem; letter-spacing:6px; margin-bottom:0;">PACEA</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align:center; font-style:italic; color:#64748b;">Don\'t tell me I\'m the only one who loves marathons. Because 387,000 American nonprofits are running one right now.</p>', unsafe_allow_html=True)
    st.markdown('<p style="text-align:center; color:#94a3b8;">Helping Fairlight Advisors decide which nonprofits to take on as clients.</p>', unsafe_allow_html=True)

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Organizations", "387,917")
    c2.metric("Filings Parsed", "2.34M")
    c3.metric("In Deficit", "37.6%")
    c4.metric("Median Revenue", "$476K")
    c5.metric("Model Accuracy", "AUC 0.86")

    st.markdown("---")
    st.subheader("What this tool does")
    st.markdown(
        "We analyzed **2.34 million IRS Form 990 filings** (2019 to 2025) for **387,917 active nonprofits**. "
        "Every organization is scored on 5 financial health indicators and placed into one of 3 readiness tiers."
    )

    st.subheader("The course")
    st.markdown(
        "Running a nonprofit is like running a 100-mile ultramarathon. The terrain is unpredictable: "
        "funding disruptions, donor fatigue, economic shocks. Some organizations are elite athletes with "
        "deep reserves and diversified fuel. Others are on fumes, one bad quarter from collapse. "
        "**Fairlight Advisors is the elite coaching team.** This dashboard is the performance lab "
        "that tells you which organizations to coach, what to improve, and where to place the aid stations. "
        "We don't just tell you who looks good today. We tell you who will still be standing at mile 100."
    )

    st.subheader("5 health indicators")
    st.dataframe(pd.DataFrame({
        "Indicator": ["Surplus Ratio", "Financial Cushion", "Revenue Diversification", "Revenue Stability", "Asset/Liability Ratio"],
        "What It Tells You": [
            "Is this org making more than it spends? (Energy output)",
            "How many years could they survive on savings? (Fuel in the tank)",
            "Do they rely on one funder or many? (One bottle or a full belt?) HHI = Herfindahl-Hirschman Index. 1.0 = single source, lower = more diversified.",
            "Is their revenue steady or volatile? (Steady stride or erratic sprints?)",
            "Do their assets cover their debts? (Hill strength)"
        ],
        "Formula": ["(Revenue - Expenses) / Revenue", "Net Assets / Annual Expenses",
                    "1 minus concentration across 4 revenue types",
                    "1 minus year-to-year variation (needs 3+ years)", "Total Assets / Total Liabilities"],
        "Weight": ["20%","20%","20%","20%","20%"],
    }), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("3 readiness tiers")
    st.markdown("Every nonprofit is ranked by percentile (top 30% / middle 40% / bottom 30%):")
    t1,t2,t3 = st.columns(3)
    with t1:
        st.markdown("#### Tier 1: Strong (Frontrunners)")
        st.metric("Count", "116,375 (30%)")
        st.markdown("Ready for advisory. Surplus: +20%. Cushion: 3.4 years. Leading the pack.")
    with t2:
        st.markdown("#### Tier 2: Potential (Mid-Pack)")
        st.metric("Count", "155,167 (40%)")
        st.markdown("Good candidates. Surplus: +4%. Cushion: 1.0 year. Solid pace, room to improve.")
    with t3:
        st.markdown("#### Tier 3: At Risk (Back of Pack)")
        st.metric("Count", "116,375 (30%)")
        st.markdown("Needs help first. Surplus: -5%. Cushion: 2.6 months. Running on fumes.")

    st.markdown("---")
    st.subheader("Predictive model")
    st.markdown(
        "Our Gradient Boosting model predicts chronic financial instability with **86% accuracy** (AUC 0.86). "
        "Operating margin drives **89.5%** of the prediction. Revenue diversification is #2 at **6.9%**."
    )
    u1,u2,u3 = st.columns(3)
    with u1:
        st.markdown("**Screen new clients**")
        st.markdown("Check any nonprofit before engagement.")
    with u2:
        st.markdown("**Monitor portfolio**")
        st.markdown("Get early warnings when clients decline.")
    with u3:
        st.markdown("**Target what to fix**")
        st.markdown("Operating margin is the #1 lever.")

    st.markdown("---")
    st.subheader("5 nonprofit segments")
    st.dataframe(pd.DataFrame({
        "Segment": ["Emerging Organizations (New Entrants)", "Diversified Growers (Trail Blazers)", "Struggling Missions (Hitting the Wall)", "Steady Operators (Consistent Pacers)", "Elite Performers (Frontrunners)"],
        "Count": ["115,949", "81,329", "4,099", "2,492", "1,697"],
        "Profile": [
            "Biggest group. Stable but 96% rely on one funder. Fragile stability.",
            "Multiple revenue sources. Most resilient when the course gets tough.",
            "100% distressed. Hit the wall. Need an aid station before coaching.",
            "96.9% thriving. Reliable pace. Best candidates for Fairlight.",
            "Strong financials but 9.9% are quietly burning out (Starvation Cycle)."
        ],
    }), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("3 key findings")
    k1,k2,k3 = st.columns(3)
    with k1:
        st.metric("HHI = 0.5", "The Wall")
        st.markdown("HHI (Herfindahl-Hirschman Index) measures how concentrated revenue is. HHI = 1.0 means all revenue from one source. Diversify past 0.5 and distress drops from 39% to 11%.")
    with k2:
        st.metric("$62K", "The Aid Station")
        st.markdown("Gives an at-risk org 3 months of reserves. The difference between DNF and finish.")
    with k3:
        st.metric("3.4x", "The Comeback")
        st.markdown("Recovered orgs grew revenue 3.4x faster. The formula: grow and diversify.")

    col1, col2 = st.columns(2)
    with col1:
        td = rd["client_tier"].value_counts().reindex(["Tier 1: Strong/Ready","Tier 2: High-Potential","Tier 3: At Risk"])
        fig = px.bar(x=["Strong","Potential","At Risk"], y=td.values,
                     color=["Strong","Potential","At Risk"],
                     color_discrete_map={"Strong":"#059669","Potential":"#2563EB","At Risk":"#DC2626"},
                     labels={"x":"","y":"Organizations"})
        fig.update_layout(showlegend=False, height=300, margin=dict(t=10,b=10),
                         plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Number of nonprofits in each readiness tier. The 30/40/30 split is by design (percentile-based).")
    with col2:
        tier_med = rd.groupby("client_tier")[["surplus_ratio","financial_cushion","revenue_diversification"]].median()
        tier_med = tier_med.reindex(["Tier 1: Strong/Ready","Tier 2: High-Potential","Tier 3: At Risk"])
        tier_med.columns = ["Surplus","Cushion (yrs)","Diversification"]
        tier_med.index = ["Strong","Potential","At Risk"]
        st.dataframe(tier_med.round(3).style.format({"Cushion (yrs)":"{:.2f}"}), use_container_width=True)
        st.caption("Median financial values per tier. Tier 1 orgs have 3x the surplus and 17x the cushion of Tier 3.")

# ==================================================================
# ORGANIZATION LOOKUP (with Playbook + Peer Benchmarking)
# ==================================================================
elif page == "Organization Lookup":
    st.title("Organization Lookup")
    st.info("Search any nonprofit to get a complete due diligence report: financial profile, peer benchmarking, 90-day engagement playbook, and investment readiness ladder. One search. Full picture.")

    search = st.text_input("Type a name or EIN", placeholder="Try: YMCA, UNITED WAY, GOODWILL, HABITAT, WIPFLI")

    if search:
        search = search.strip()
        if search.isdigit():
            matches = rd[rd["ein"].astype(str) == search]
            if len(matches) == 0:
                matches = rd[rd["ein"].astype(str).str.contains(search, na=False)]
        else:
            terms = search.upper().split()
            mask = pd.Series(True, index=rd.index)
            for term in terms:
                mask = mask & rd["org_name"].astype(str).str.upper().str.contains(term, na=False)
            matches = rd[mask]

        if len(matches) == 0:
            st.warning(f"No results for '{search}'. IRS filing names may differ. Try shorter terms.")
        else:
            st.success(f"Found {len(matches):,} organizations")
            for _, org in matches.head(20).iterrows():
                name = str(org.get("org_name","Unknown"))
                state = str(org.get("state",""))
                score = org.get("client_readiness_score", 0)
                if pd.isna(score): score = 0
                tier = str(org.get("client_tier",""))
                tier_short = tier.split(": ")[-1] if ": " in tier else tier

                with st.expander(f"{name}  |  {state}  |  Score: {score:.1f}  |  {tier_short}"):
                    # ---- SECTION 1: FINANCIAL PROFILE ----
                    st.markdown("### Financial Profile")
                    m1,m2,m3 = st.columns(3)
                    m1.metric("Readiness Score", f"{score:.1f} / 100")
                    m2.metric("Tier", tier_short)
                    rev = org.get("total_revenue", 0)
                    m3.metric("Revenue", f"${rev:,.0f}" if pd.notna(rev) else "N/A")

                    st.markdown("**Financial health indicators:**")
                    v1,v2,v3,v4,v5 = st.columns(5)
                    sr = org.get("surplus_ratio", 0)
                    v1.metric("Surplus", f"{sr:.1%}" if pd.notna(sr) else "N/A")
                    fc = org.get("financial_cushion", 0)
                    v2.metric("Cushion", f"{fc:.2f} yrs" if pd.notna(fc) else "N/A")
                    rd_val = org.get("revenue_diversification", 0)
                    v3.metric("Diversification", f"{rd_val:.3f}" if pd.notna(rd_val) else "N/A")
                    rs = org.get("revenue_stability", None)
                    v4.metric("Stability", f"{rs:.3f}" if pd.notna(rs) else "N/A")
                    alr = org.get("asset_liability_ratio", 0)
                    v5.metric("Solvency", f"{alr:.1f}x" if pd.notna(alr) else "N/A")

                    st.markdown("**Percentile ranking vs 387K nonprofits:**")
                    for col, label in [("s1_surplus","Surplus"),("s2_cushion","Cushion"),
                                       ("s3_diversification","Diversification"),("s4_stability","Stability"),
                                       ("s5_solvency","Solvency")]:
                        raw = org.get(col, None)
                        if pd.notna(raw):
                            val = max(0, min(100, int(raw)))
                            st.progress(val, text=f"{label}: {val}th percentile")
                        else:
                            st.progress(50, text=f"{label}: data not available")

                    # ---- SECTION 2: PEER BENCHMARKING ----
                    st.markdown("---")
                    st.markdown("### Peer Benchmarking")
                    st.caption("Comparing against organizations in the same state with similar revenue (±50%), not the full national dataset.")

                    org_rev = org.get("total_revenue", 0)
                    org_state = org.get("state", "")
                    if pd.notna(org_rev) and org_rev > 0 and pd.notna(org_state) and org_state != "":
                        rev_low = org_rev * 0.5
                        rev_high = org_rev * 1.5
                        peers = rd[
                            (rd["state"] == org_state) &
                            (rd["total_revenue"] >= rev_low) &
                            (rd["total_revenue"] <= rev_high) &
                            (rd["ein"].astype(str) != str(org.get("ein", "")))
                        ]
                        peer_count = len(peers)

                        if peer_count >= 5:
                            st.markdown(f"**Peer group:** {peer_count} organizations in **{org_state}** with revenue between **${rev_low:,.0f}** and **${rev_high:,.0f}**")

                            # Calculate peer percentiles for this org
                            peer_metrics = []
                            for feat, label in [("surplus_ratio","Surplus"),("financial_cushion","Cushion"),
                                                ("revenue_diversification","Diversification"),("revenue_stability","Stability"),
                                                ("asset_liability_ratio","Solvency")]:
                                org_val = org.get(feat, None)
                                if pd.notna(org_val) and feat in peers.columns:
                                    peer_vals = peers[feat].dropna()
                                    if len(peer_vals) > 0:
                                        peer_pctl = (peer_vals < org_val).mean() * 100
                                        natl_pctl = org.get(f"s{['surplus_ratio','financial_cushion','revenue_diversification','revenue_stability','asset_liability_ratio'].index(feat)+1}_{'surplus' if feat=='surplus_ratio' else 'cushion' if feat=='financial_cushion' else 'diversification' if feat=='revenue_diversification' else 'stability' if feat=='revenue_stability' else 'solvency'}", 50)
                                        peer_metrics.append({"Indicator": label, "This Org": org_val,
                                                             "Peer Median": peer_vals.median(),
                                                             "Peer Pctl": peer_pctl,
                                                             "National Pctl": natl_pctl if pd.notna(natl_pctl) else 50})

                            if peer_metrics:
                                # Radar chart: org vs peer median
                                pm_df = pd.DataFrame(peer_metrics)
                                cats_p = pm_df["Indicator"].tolist()
                                org_pctls = pm_df["Peer Pctl"].tolist()
                                natl_pctls = [m["National Pctl"] for m in peer_metrics]

                                fig_peer = go.Figure()
                                fig_peer.add_trace(go.Scatterpolar(
                                    r=org_pctls, theta=cats_p, fill="toself", name="vs Peers (state+size)",
                                    line_color="#0D9488", fillcolor="rgba(13,148,136,0.2)"))
                                fig_peer.add_trace(go.Scatterpolar(
                                    r=natl_pctls, theta=cats_p, fill="toself", name="vs National (387K)",
                                    line_color="#94A3B8", fillcolor="rgba(148,163,184,0.1)"))
                                fig_peer.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,100])),
                                    height=300, margin=dict(t=30,b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                                st.plotly_chart(fig_peer, use_container_width=True)
                                st.caption("**Teal** = rank among local peers (same state, similar revenue). **Gray** = rank among all 387K orgs nationally. Gaps reveal whether this org's strengths/weaknesses are local or national patterns.")

                                # Comparison table
                                for pm in peer_metrics:
                                    delta = pm["Peer Pctl"] - pm["National Pctl"]
                                    direction = "↑" if delta > 5 else "↓" if delta < -5 else "→"
                                    st.markdown(f"**{pm['Indicator']}:** Peer rank **{pm['Peer Pctl']:.0f}th** vs National **{pm['National Pctl']:.0f}th** {direction}")
                        else:
                            st.markdown(f"_Only {peer_count} peers found in {org_state} at this revenue level. Showing national benchmarks only._")
                    else:
                        st.markdown("_Peer benchmarking requires valid state and revenue data._")

                    # ---- SECTION 3: 90-DAY ENGAGEMENT PLAYBOOK ----
                    st.markdown("---")
                    st.markdown("### 90-Day Engagement Playbook")

                    ein_str = str(org.get("ein", ""))
                    seg_match = seg[seg["ein"].astype(str) == ein_str] if "ein" in seg.columns else pd.DataFrame()
                    persona = seg_match.iloc[0]["persona"] if len(seg_match) > 0 and "persona" in seg_match.columns else "Emerging Organizations"
                    marathon_map = {"Elite Performers":"Frontrunners", "Diversified Growers":"Trail Blazers",
                                    "Steady Operators":"Consistent Pacers", "Emerging Organizations":"New Entrants",
                                    "Struggling Missions":"Hitting the Wall"}

                    s1p = org.get("s1_surplus", 50); s2p = org.get("s2_cushion", 50); s3p = org.get("s3_diversification", 50)
                    s4p = org.get("s4_stability", 50); s5p = org.get("s5_solvency", 50)
                    pscores = {"Surplus": s1p, "Cushion": s2p, "Diversification": s3p, "Stability": s4p, "Solvency": s5p}
                    valid_ps = {k: v for k, v in pscores.items() if pd.notna(v)}
                    sorted_ps = sorted(valid_ps.items(), key=lambda x: x[1])
                    weak1 = sorted_ps[0] if sorted_ps else ("Unknown", 50)
                    weak2 = sorted_ps[1] if len(sorted_ps) > 1 else ("Unknown", 50)
                    org_hhi = 1 - org.get("revenue_diversification", 0) if pd.notna(org.get("revenue_diversification", None)) else None

                    st.markdown(f"**Segment:** {persona} ({marathon_map.get(persona, '')})")
                    st.markdown(f"**Priority lever:** {weak1[0]} ({int(weak1[1])}th percentile)" if pd.notna(weak1[1]) else "")
                    st.markdown(f"**Secondary lever:** {weak2[0]} ({int(weak2[1])}th percentile)" if pd.notna(weak2[1]) else "")

                    playbook_templates = {
                        "Elite Performers": {
                            "risk": "Starvation Cycle — strong financials masking infrastructure decay",
                            "m1": "**Diagnose: Audit program capacity.** Review 3-year trend in program expenses vs total expenses. Flag if program ratio is declining while surplus grows. Interview leadership about overhead cuts made under donor pressure. Compare overhead ratio against Charity Navigator 65/35 benchmark. Deliverable: Starvation Cycle risk assessment report.",
                            "m2": "**Strategize: Benchmark against Trail Blazers.** Compare revenue mix against Diversified Growers segment (HHI 0.456). Identify which of the 4 revenue streams (contributions, program revenue, investment income, other) are underdeveloped. Develop board-ready presentation on why the Starvation Cycle threatens long-term mission delivery. Deliverable: Revenue diversification strategy deck.",
                            "m3": "**Execute: Stress-test and protect.** Run PACEA Shock Simulator with Donor Fatigue scenario on this specific org. Build a 12-month contingency plan covering 3 funding disruption scenarios. Establish quarterly financial monitoring cadence with Fairlight. If reserves exceed 12 months, introduce investment policy review and endowment planning. Deliverable: Contingency plan + monitoring schedule.",
                        },
                        "Diversified Growers": {
                            "risk": "Strong diversification but may lack investment strategy for growing reserves",
                            "m1": "**Diagnose: Validate diversification quality.** Confirm revenue streams are truly independent (not all from one geography or one grant type). Assess whether program revenue is earned vs grant-dependent. Review revenue stability trend over 5 years. Deliverable: Revenue stream independence audit.",
                            "m2": "**Strategize: Build the investment framework.** This org is a prime candidate for board-designated fund or endowment creation. Assess whether reserves exceed 6 months (investment-ready threshold). Develop draft liquidity policy and Investment Policy Statement (IPS) aligned with Fairlight's socially responsible investing approach. Deliverable: Draft IPS and liquidity policy.",
                            "m3": "**Execute: Launch investment management.** Document this org's diversification model as a case study template for other Fairlight clients. Run stress test to confirm shock resilience. Onboard to Fairlight's investment management platform. Set up quarterly rebalancing cadence for invested assets. Deliverable: Investment onboarding complete + case study.",
                        },
                        "Steady Operators": {
                            "risk": "Strong performance creates complacency — missed growth and endowment opportunities",
                            "m1": "**Diagnose: Confirm true stability.** Validate that all 5 indicators are genuinely strong (not masking one weak area). Review board governance structure and succession planning. Confirm reserve policy is documented and board-approved. Check if there's an existing investment policy. Deliverable: Governance and financial policy gap analysis.",
                            "m2": "**Strategize: Endowment readiness assessment.** With 96.9% thriving rate, the focus shifts from survival to growth. Assess endowment readiness: reserves > 12 months, diversified revenue, multi-year surplus trend. Develop investment policy if not already in place. Explore alignment with socially responsible investing (Fairlight's specialty). Deliverable: Endowment readiness scorecard.",
                            "m3": "**Execute: Activate Fairlight's investment services.** Introduce full investment management. Set up quarterly reporting cadence with board-ready updates. This is a retain-and-grow client — low advisory intensity, high AUM potential. Position for long-term endowment management relationship. Deliverable: Investment management agreement + quarterly calendar.",
                        },
                        "Emerging Organizations": {
                            "risk": "Single-Funder Trap — 96% of revenue from one source creates illusory stability",
                            "m1": "**Diagnose: Expose the trap.** Present HHI analysis showing near-total revenue concentration. Calculate the specific risk: if the primary funder reduces by 20%, quantify the exact dollar gap and timeline to deficit. Identify the specific funder dependency type (individual donor, government grant, foundation). Deliverable: Funder dependency risk report with dollar scenarios.",
                            "m2": "**Strategize: Build the diversification roadmap.** Use Trail Blazer segment data as a benchmark template. Calculate exact dollar targets: how much program revenue, investment income, or government grants are needed to reach HHI 0.5. Develop a 12-month revenue development plan with quarterly milestones. Identify 3-5 specific new funding opportunities. Deliverable: Revenue diversification roadmap with quarterly targets.",
                            "m3": "**Execute: Launch first new revenue stream.** Help launch one new revenue initiative (fee-for-service, earned revenue program, grant application to a new funder type). Set up PACEA monitoring to track HHI improvement quarterly. Begin reserve-building: target $62K = 3 months reserves (NORI minimum). Schedule 90-day review checkpoint. Deliverable: First new stream launched + monitoring dashboard.",
                        },
                        "Struggling Missions": {
                            "risk": "100% distress rate — needs emergency stabilization before any advisory engagement",
                            "m1": "**Triage: Assess viability.** Calculate months to insolvency (net assets ÷ monthly burn rate). If < 3 months, this org needs emergency intervention, not standard advisory. Determine whether the deficit is structural (expenses permanently exceed revenue capacity) or cyclical (temporary funding gap from a specific lost grant or event). Deliverable: Viability assessment with insolvency timeline.",
                            "m2": "**Stabilize: Stop the bleeding.** If structural: develop cost restructuring plan targeting break-even within 6 months, identify which programs to scale back. If cyclical: identify bridge funding options, prepare emergency grant applications, explore fiscal sponsorship. Target: reach $62K reserve threshold (3 months NORI minimum). Deliverable: Stabilization plan with monthly cash flow targets.",
                            "m3": "**Transition: Move to growth mode.** Once stabilized (positive monthly cash flow for 2+ consecutive months), transition to the Emerging Organizations (New Entrants) playbook. Begin diversification planning. This org is NOT ready for investment management — Fairlight's role here is pure advisory and capacity building. Deliverable: Transition plan to New Entrants playbook.",
                        },
                    }
                    tpl = playbook_templates.get(persona, playbook_templates["Emerging Organizations"])

                    # Custom flags
                    if pd.notna(weak1[1]) and weak1[1] < 30:
                        st.error(f"**Critical flag:** {weak1[0]} is at the {int(weak1[1])}th percentile — bottom third nationally. This must be the #1 priority in Month 1.")
                    if org_hhi is not None and org_hhi > 0.5:
                        st.warning(f"**HHI is {org_hhi:.2f}** (above the 0.5 wall). Revenue diversification should be a core objective across all 3 months.")
                    if pd.notna(org.get("financial_cushion")) and org["financial_cushion"] < 0.25:
                        st.error("**Less than 3 months of reserves.** Emergency reserve-building should precede any other initiative.")

                    st.info(f"**Primary risk:** {tpl['risk']}")

                    pb1, pb2, pb3 = st.columns(3)
                    with pb1:
                        st.markdown("#### Month 1")
                        st.markdown("*Diagnose & Assess*")
                        st.markdown(tpl["m1"])
                    with pb2:
                        st.markdown("#### Month 2")
                        st.markdown("*Strategy & Plan*")
                        st.markdown(tpl["m2"])
                    with pb3:
                        st.markdown("#### Month 3")
                        st.markdown("*Execute & Monitor*")
                        st.markdown(tpl["m3"])

                    # ---- SECTION 4: INVESTMENT READINESS LADDER ----
                    st.markdown("---")
                    st.markdown("### Investment Readiness Ladder")
                    st.caption("Where is this org on the path to becoming a Fairlight AUM client?")

                    cush = org.get("financial_cushion", 0) if pd.notna(org.get("financial_cushion")) else 0
                    div_val = org.get("revenue_diversification", 0) if pd.notna(org.get("revenue_diversification")) else 0

                    if cush < 0.25:
                        rung = 1; rung_label = "Building Reserves"
                        rung_action = "Needs to build 3 months of operating reserves ($62K median). Not ready for investment management. Fairlight's role: X-Ray Assessment© and reserve policy development."
                        next_step = "Build to 3 months reserves. Target: consistent monthly surplus for 6+ consecutive months."
                    elif cush < 0.5:
                        rung = 2; rung_label = "Reserve Complete"
                        rung_action = "Has 3-6 months reserves. Ready for liquidity policy and short-term investment strategy. Fairlight's role: Consulting engagement + liquidity management."
                        next_step = "Grow reserves to 6 months. Begin diversifying revenue past HHI 0.5. Draft liquidity policy."
                    elif cush < 1.0 or div_val < 0.4:
                        rung = 3; rung_label = "Investment Ready"
                        rung_action = "6+ months reserves with growing surplus. Ready for board-designated fund and Investment Policy Statement (IPS). Fairlight's role: Investment management client."
                        next_step = "Sustain 12+ months reserves. Achieve HHI < 0.5. Establish board-designated fund. Draft IPS."
                    else:
                        rung = 4; rung_label = "Endowment Ready"
                        rung_action = "12+ months reserves, diversified revenue, multi-year surplus. Ready for permanent endowment. Fairlight's role: Full AUM client — the ideal long-term relationship."
                        next_step = None

                    for i in range(4, 0, -1):
                        lm = {1: "Building Reserves", 2: "Reserve Complete", 3: "Investment Ready", 4: "Endowment Ready"}
                        cm = {1: "#DC2626", 2: "#F59E0B", 3: "#2563EB", 4: "#059669"}
                        ic = (i == rung)
                        marker = " ◀ THIS ORG" if ic else ""
                        bg = cm[i] if ic else "#f1f5f9"
                        tc = "white" if ic else "#64748b"
                        st.markdown(f'<div style="background:{bg}; padding:10px 16px; border-radius:8px; margin:4px 0; color:{tc}; font-weight:{"700" if ic else "400"};">' \
                                    f'Rung {i}: {lm[i]}{marker}</div>', unsafe_allow_html=True)

                    st.markdown(f"**Current: Rung {rung} — {rung_label}**")
                    st.markdown(rung_action)
                    if next_step:
                        st.info(f"**To reach the next rung:** {next_step}")

# ==================================================================
# CLIENT READINESS
# ==================================================================
elif page == "Client Readiness":
    st.title("Client Readiness")
    st.info("Browse and filter all 387,917 scored nonprofits by readiness tier, state, and minimum revenue. Use this to build targeted client lists for Fairlight. Sort by readiness score to find the strongest candidates in any region.")
    st.markdown("Filter and explore all 387K nonprofits by tier, state, and size.")

    fc1,fc2,fc3 = st.columns(3)
    ft = fc1.selectbox("Tier", ["All","Tier 1: Strong/Ready","Tier 2: High-Potential","Tier 3: At Risk"])
    fs = fc2.selectbox("State", ["All"] + sorted(rd["state"].dropna().unique().tolist()))
    fmin = fc3.number_input("Min Revenue ($)", value=0, step=100000)
    filt = rd.copy()
    if ft != "All": filt = filt[filt["client_tier"]==ft]
    if fs != "All": filt = filt[filt["state"]==fs]
    filt = filt[filt["total_revenue"]>=fmin]
    st.markdown(f"**{len(filt):,} organizations match**")
    show = ["org_name","state","ein","total_revenue","client_readiness_score","client_tier",
            "surplus_ratio","financial_cushion","revenue_diversification"]
    avail = [c for c in show if c in filt.columns]
    st.dataframe(filt[avail].sort_values("client_readiness_score",ascending=False).head(200).style.format({
        "total_revenue":"${:,.0f}","client_readiness_score":"{:.1f}","surplus_ratio":"{:.3f}",
        "financial_cushion":"{:.2f}","revenue_diversification":"{:.3f}",
    }), use_container_width=True, height=500)

# ==================================================================
# NONPROFIT SEGMENTS
# ==================================================================
elif page == "Nonprofit Segments":
    st.title("Nonprofit Segments")
    st.info("K-Means clustering found 5 natural archetypes. Each segment has a distinct financial fingerprint, a different outcome distribution, and requires a different Fairlight advisory strategy. Names are based on the dominant characteristic that defines each cluster.")

    st.markdown("---")
    st.subheader("Why these 5 segments?")
    st.markdown(
        "We ran K-Means clustering on the 5 health indicators (surplus, cushion, diversification, stability, solvency) "
        "for 205,566 organizations with complete data. The algorithm discovered 5 natural groupings, not pre-defined categories. "
        "We then named each cluster based on its **dominant defining characteristic** from the data."
    )

    # Consistent segment reference cards
    seg_definitions = [
        {
            "name": "Steady Operators", "marathon": "Consistent Pacers", "color": "#2563EB",
            "count": "2,492", "thriving": "96.9%", "distressed": "1.5%",
            "surplus": "88.7%", "cushion": "117 yrs", "diversification": "0.075 (very low)",
            "defining": "Massive reserves and endowments. These are established institutions (universities, hospitals, large foundations) that have accumulated decades of net assets. Their cushion is so deep that revenue concentration doesn't threaten them.",
            "paradox": "Low diversification + high thriving rate. This seems to contradict our HHI 0.5 finding. The explanation: their enormous reserves (117 years of cushion) make them immune to short-term funding shocks. Diversification matters most for orgs with thin reserves.",
            "fairlight": "Dream AUM clients. Already investment-ready. Focus on endowment optimization and socially responsible investing.",
        },
        {
            "name": "Diversified Growers", "marathon": "Trail Blazers", "color": "#F59E0B",
            "count": "81,329", "thriving": "28.4%", "distressed": "27.4%",
            "surplus": "5.5%", "cushion": "1.70 yrs", "diversification": "0.456 (high)",
            "defining": "Highest revenue diversification of any segment (HHI 0.456, close to the 0.5 tipping point). Multiple funding sources across contributions, program revenue, investment income, and government grants.",
            "paradox": "High diversification but only 28.4% thriving. Diversification protects against shocks but doesn't guarantee surplus. Many are mid-size orgs still growing. Their mixed outcome distribution shows they're in transition.",
            "fairlight": "Template for other clients. Use their revenue mix as a benchmark. Help them convert diversification into surplus and reserves.",
        },
        {
            "name": "Elite Performers", "marathon": "Frontrunners", "color": "#059669",
            "count": "1,697", "thriving": "28.6%", "distressed": "19.7%",
            "surplus": "6.1%", "cushion": "1.67 yrs", "diversification": "0.214 (moderate)",
            "defining": "Named 'Elite' by the algorithm based on strong solvency ratios and moderate surplus. But our deeper analysis reveals a critical hidden risk: 29.4% show DECLINING outcomes despite healthy-looking financials.",
            "paradox": "This is the Starvation Cycle in action (Gregory & Howard, SSIR 2009). Donors pressure these orgs to minimize overhead. They cut infrastructure, staff, and capacity to show 'efficient' financials. The numbers look good. The organization is hollowing out.",
            "fairlight": "Screen every one for declining program capacity. Healthy balance sheet ≠ healthy organization. This is Fairlight's highest-value diagnostic opportunity.",
        },
        {
            "name": "Emerging Organizations", "marathon": "New Entrants", "color": "#94A3B8",
            "count": "115,949", "thriving": "19.1%", "distressed": "27.4%",
            "surplus": "2.7%", "cushion": "0.84 yrs", "diversification": "0.042 (extremely low)",
            "defining": "The largest segment. Nearly complete revenue concentration (HHI 0.96). 96% of revenue from a single source. The stability score (0.76) looks fine but it's an illusion — it only appears stable because one funder has been consistent. When that funder leaves, everything collapses.",
            "paradox": "This is the Single-Funder Trap. High apparent stability masking extreme fragility. Our shock simulator shows these orgs are devastated by even moderate funding disruptions.",
            "fairlight": "Fairlight's largest addressable market (115K orgs). Capacity building to diversify before the crisis. This is where advisory has the most outsized impact.",
        },
        {
            "name": "Struggling Missions", "marathon": "Hitting the Wall", "color": "#DC2626",
            "count": "4,099", "thriving": "0.0%", "distressed": "100%",
            "surplus": "-219.7%", "cushion": "1.22 yrs", "diversification": "0.081 (very low)",
            "defining": "Every single organization in this cluster is in financial distress. Deep structural deficits with expenses far exceeding revenue. The paradox of 1.2 years cushion comes from historical reserves that are being rapidly depleted.",
            "paradox": "Cushion > 1 year but 100% distressed. The reserves are a legacy — they're burning through accumulated assets at an unsustainable rate. Without intervention, the cushion disappears within 1-2 years.",
            "fairlight": "Not advisory clients without emergency stabilization first. Triage: stop the bleeding, build to $62K reserves (3 months NORI minimum), then transition to the New Entrants playbook.",
        },
    ]

    for sd in seg_definitions:
        st.markdown(f'<div style="border-left: 4px solid {sd["color"]}; padding-left: 12px; margin-bottom: 8px;"><h3 style="margin:0;">{sd["name"]} <span style="color:#94a3b8; font-weight:400;">({sd["marathon"]})</span></h3></div>', unsafe_allow_html=True)
        mc = st.columns(6)
        mc[0].metric("Count", sd["count"])
        mc[1].metric("Thriving", sd["thriving"])
        mc[2].metric("Distressed", sd["distressed"])
        mc[3].metric("Surplus", sd["surplus"])
        mc[4].metric("Cushion", sd["cushion"])
        mc[5].metric("Diversification", sd["diversification"])
        st.markdown(f"**What defines this segment:** {sd['defining']}")
        st.markdown(f"**Why the numbers might seem counterintuitive:** {sd['paradox']}")
        st.markdown(f"**Fairlight's play:** {sd['fairlight']}")
        st.markdown("---")

    # Radar chart
    st.subheader("Segment fingerprints")
    fig = go.Figure()
    cats = ["Surplus","Cushion","Diversification","Stability","Solvency"]
    for persona in ["Elite Performers","Steady Operators","Emerging Organizations","Struggling Missions","Diversified Growers"]:
        t = seg[seg["persona"]==persona]
        if len(t) == 0: continue
        vals = [max(min(t["surplus_ratio"].median()*200,100),0),
                min(t["financial_cushion"].median()*10,100),
                t["revenue_diversification"].median()*100,
                t["revenue_stability"].median()*100 if "revenue_stability" in t.columns else 50,
                min(t["asset_liability_ratio"].median()*2,100)]
        fig.add_trace(go.Scatterpolar(r=vals, theta=cats, fill="toself", name=persona,
                                        line_color=SEG_COLORS.get(persona,"#999")))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,100])), height=400, margin=dict(t=40),
                     paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("**How to read:** Each axis = one health indicator (0-100 scale). Larger area = healthier segment. "
               "Steady Operators (blue) dominate on surplus and cushion but are compressed on diversification. "
               "Diversified Growers (amber) show the opposite pattern. This is why different segments need different advisory strategies.")

    if "outcome" in seg.columns:
        st.subheader("Outcomes by segment")
        ct = pd.crosstab(seg["persona"], seg["outcome"], normalize="index").reindex(
            columns=["Thriving","Stable","Declining","Distressed"]).fillna(0)*100
        st.dataframe(ct.round(1).style.format("{:.1f}%").background_gradient(cmap="RdYlGn", axis=1), use_container_width=True)
        st.caption(
            "**Key insight:** Steady Operators thrive at 96.9% despite low diversification because their massive reserves insulate them. "
            "Emerging Organizations have 27.4% distress despite decent stability because their single-funder dependency is a hidden fragility. "
            "Elite Performers at 19.7% distressed despite healthy financials = the Starvation Cycle. "
            "**The takeaway:** each segment's risk is driven by a DIFFERENT factor, which is why one-size-fits-all advisory fails."
        )

# ==================================================================
# SHOCK SIMULATOR
# ==================================================================
elif page == "Shock Simulator":
    st.title("Funding Shock Simulator")
    st.info("See what happens to the nonprofit sector under different funding disruption scenarios (recessions, government cuts, donor fatigue, pandemic shocks). Use the custom sliders to model any scenario. Use this for portfolio risk assessment and contingency planning.")
    st.markdown("What happens when funding drops?")

    fig = go.Figure()
    fig.add_bar(x=shock["scenario"], y=shock["newly_in_deficit"],
                marker_color=["#F59E0B","#DC2626","#059669","#F59E0B","#2563EB"],
                text=shock["newly_in_deficit"].apply(lambda x: f"{x:,}"), textposition="outside")
    fig.update_layout(height=400, yaxis_title="Newly in deficit", margin=dict(t=10),
                     paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("**How to read this chart:** Each bar shows how many additional nonprofits would be pushed from surplus into deficit under that scenario. A severe recession is the worst case, pushing 112K new orgs into deficit. Donor fatigue (88K) is nearly as damaging and is already happening in the real world according to GivingUSA 2024 data.")

    st.markdown("---")
    st.subheader("Custom scenario")
    st.markdown("Drag the sliders to simulate your own funding shock. All metrics update in real time.")
    sc1,sc2,sc3 = st.columns(3)
    cd = sc1.slider("Donation drop %", 0, 50, 15) / 100
    id_ = sc2.slider("Investment drop %", 0, 50, 20) / 100
    gd = sc3.slider("Govt grant drop %", 0, 75, 5) / 100

    be = rd["total_functional_expenses"].fillna(0)
    br = rd["total_revenue"].fillna(0)
    na = rd["net_assets_eoy"].fillna(0) if "net_assets_eoy" in rd.columns else pd.Series(0, index=rd.index)
    was_surplus = (br - be) >= 0

    # Calculate shocked revenue
    rev_drop = cd*0.6 + id_*0.1 + gd*0.1
    shocked_rev = br * (1 - rev_drop)
    shocked_balance = shocked_rev - be
    now_deficit = shocked_balance < 0
    newly_deficit = was_surplus & now_deficit

    # Months to insolvency for newly deficit orgs
    monthly_burn = (-shocked_balance[newly_deficit]) / 12
    months_to_insolvency = na[newly_deficit] / monthly_burn.replace(0, np.nan)
    high_risk = (months_to_insolvency < 6).sum() if len(months_to_insolvency) > 0 else 0
    med_risk = ((months_to_insolvency >= 6) & (months_to_insolvency < 18)).sum() if len(months_to_insolvency) > 0 else 0

    # Display metrics
    r1,r2,r3,r4 = st.columns(4)
    r1.metric("Newly in deficit", f"{newly_deficit.sum():,}", help="Orgs that were in surplus but are now in deficit after the shock")
    r2.metric("Total in deficit", f"{now_deficit.sum():,} ({now_deficit.mean():.1%})", help="All orgs in deficit after the shock (including those already in deficit)")
    r3.metric("High risk (<6 mo)", f"{high_risk:,}", help="Newly deficit orgs with less than 6 months of reserves to cover the gap")
    r4.metric("Medium risk (6-18 mo)", f"{med_risk:,}", help="Newly deficit orgs with 6 to 18 months of reserves")

    r5,r6,r7,r8 = st.columns(4)
    r5.metric("Revenue drop", f"-{rev_drop:.1%}", help="Weighted average revenue impact across the sector")
    r6.metric("Revenue lost", f"${br.sum()*rev_drop/1e9:,.1f}B", help="Total dollars of revenue lost across all organizations")
    pct_affected = newly_deficit.mean()
    r7.metric("% affected", f"{pct_affected:.1%}", help="Share of previously-healthy orgs pushed to deficit")
    avg_deficit = -shocked_balance[newly_deficit].median() if newly_deficit.sum() > 0 else 0
    r8.metric("Median new deficit", f"${avg_deficit:,.0f}", help="Median size of the new deficit for affected orgs")

    # Dynamic charts that respond to sliders
    ch1, ch2 = st.columns(2)

    with ch1:
        st.subheader("Impact by tier")
        # Calculate impact per tier
        tier_impact = []
        for tier in ["Tier 1: Strong/Ready", "Tier 2: High-Potential", "Tier 3: At Risk"]:
            mask = rd["client_tier"] == tier
            tier_surplus = was_surplus & mask
            tier_newly = newly_deficit & mask
            tier_total = mask.sum()
            tier_impact.append({
                "Tier": tier.split(": ")[-1],
                "Previously healthy": tier_surplus.sum(),
                "Pushed to deficit": tier_newly.sum(),
                "Impact rate": tier_newly.sum() / tier_surplus.sum() * 100 if tier_surplus.sum() > 0 else 0
            })
        tid = pd.DataFrame(tier_impact)
        fig_tier = px.bar(tid, x="Tier", y=["Previously healthy", "Pushed to deficit"], barmode="group",
                          color_discrete_map={"Previously healthy":"#059669", "Pushed to deficit":"#DC2626"})
        fig_tier.update_layout(height=320, margin=dict(t=10,b=10), paper_bgcolor="rgba(0,0,0,0)",
                               plot_bgcolor="rgba(0,0,0,0)", legend_title_text="")
        st.plotly_chart(fig_tier, use_container_width=True)
        st.caption("**How to read:** Green = orgs that were in surplus. Red = orgs pushed to deficit by the shock. Tier 3 orgs are already mostly in deficit, so the shock hits Tier 2 hardest.")

    with ch2:
        st.subheader("Sector health gauge")
        pct_deficit_before = (~was_surplus).mean() * 100
        pct_deficit_after = now_deficit.mean() * 100
        fig_gauge = go.Figure()
        fig_gauge.add_trace(go.Indicator(
            mode="gauge+number+delta",
            value=pct_deficit_after,
            delta={"reference": pct_deficit_before, "increasing": {"color": "#DC2626"}, "suffix": "%"},
            number={"suffix": "%", "font": {"size": 40}},
            title={"text": "Sector in deficit (after shock)"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#DC2626" if pct_deficit_after > 50 else "#F59E0B"},
                "steps": [
                    {"range": [0, 30], "color": "#d1fae5"},
                    {"range": [30, 50], "color": "#fef3c7"},
                    {"range": [50, 100], "color": "#fee2e2"},
                ],
                "threshold": {"line": {"color": "#059669", "width": 3}, "thickness": 0.8, "value": pct_deficit_before}
            }
        ))
        fig_gauge.update_layout(height=320, margin=dict(t=60,b=10), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_gauge, use_container_width=True)
        st.caption(f"**How to read:** The green line marks the baseline ({pct_deficit_before:.1f}% in deficit before shock). The needle shows the post-shock level. Red zone = more than 50% of sector in deficit.")

    # Scenario comparison table
    st.subheader("Your scenario vs pre-built scenarios")
    custom_row = {"Scenario": "Your custom scenario", "Newly in deficit": newly_deficit.sum(),
                  "High risk (<6mo)": high_risk, "Revenue impact": f"-{rev_drop:.1%}"}
    compare_rows = []
    for _, row in shock.iterrows():
        compare_rows.append({"Scenario": row["scenario"], "Newly in deficit": int(row["newly_in_deficit"]),
                             "High risk (<6mo)": int(row["high_risk_lt6mo"]), "Revenue impact": f"{row['median_revenue_change_pct']:.1f}%"})
    compare_rows.append(custom_row)
    st.dataframe(pd.DataFrame(compare_rows), use_container_width=True, hide_index=True)
    st.caption("**Your scenario appears at the bottom.** Compare it against the 5 pre-built scenarios to see where it falls on the severity spectrum.")

    st.markdown("---")
    st.subheader("How the custom scenario is calculated")
    st.markdown(
        f"We estimate that **{cd*100:.0f}% of donations** make up ~60% of typical nonprofit revenue, "
        f"**{id_*100:.0f}% of investment losses** affect ~10%, and **{gd*100:.0f}% government cuts** affect ~10%. "
        f"The weighted average revenue impact is **-{rev_drop:.1%}**. We then recalculate each org's "
        f"balance (shocked revenue minus expenses) and count how many flip from surplus to deficit. "
        f"For those newly in deficit, we estimate months to insolvency by dividing their net assets "
        f"by their monthly burn rate.")

# ==================================================================
# THRESHOLDS & RECOVERY
# ==================================================================
elif page == "Thresholds & Recovery":
    st.title("Thresholds & Recovery")
    st.info("Three critical findings: (1) the exact diversification level where financial risk drops dramatically (HHI = 0.5), (2) how much grant money is needed to shift a nonprofit's resilience tier, and (3) what organizations that recovered from deficit actually did differently. Use this to set investment strategy and advisory recommendations.")

    st.subheader("The diversification tipping point")
    if "hhi" in seg.columns and "outcome" in seg.columns:
        thresh = []
        for hi in [0.3,0.4,0.5,0.6,0.7,0.8,1.0]:
            sub = seg[seg["hhi"]<=hi]
            if len(sub)>0:
                thresh.append({"Level":f"HHI < {hi}","Distressed %":(sub["outcome"]=="Distressed").mean()*100})
        if thresh:
            fig = px.bar(pd.DataFrame(thresh), x="Level", y="Distressed %", text="Distressed %",
                         color_discrete_sequence=["#059669"])
            fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            fig.update_layout(height=350, margin=dict(t=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
            st.caption("**How to read this chart:** Each bar shows the distress rate for nonprofits at or below that HHI level. Lower HHI means more diversified revenue. The sharp drop at HHI 0.5 is the key insight: organizations that diversify past this point are dramatically less likely to be financially distressed.")
    st.success("**HHI = 0.5 is the tipping point.** HHI (Herfindahl-Hirschman Index) measures revenue concentration. HHI = 1.0 means 100% from one source. HHI = 0.25 means perfectly spread across 4 sources. Below 0.5, distress drops from 39% to 11%.")

    st.markdown("---")
    st.subheader("How much money makes a difference?")
    st.dataframe(pd.DataFrame({
        "Tier":["At Risk","At Risk","Potential","Potential"],
        "Reserves":["+3 months","+6 months","+3 months","+6 months"],
        "Grant":["$62K","$123K","$75K","$149K"]
    }), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("What recovered orgs did differently")
    rc1,rc2 = st.columns(2)
    with rc1:
        st.markdown("#### Recovered (35K orgs)")
        st.metric("Revenue growth", "+38.5%")
        st.metric("Diversification", "Improved")
    with rc2:
        st.markdown("#### Still stuck (74K orgs)")
        st.metric("Revenue growth", "+11.2%")
        st.metric("Diversification", "No change")
    st.info("Recovered orgs grew **3.4x faster** and diversified. The formula: **grow and diversify**.")

# ==================================================================
# ADVISORY ROI CALCULATOR
# ==================================================================
elif page == "Advisory ROI":
    st.title("Advisory ROI Calculator")
    st.markdown("""
    <div style="background: linear-gradient(135deg, #fef3c7 0%, #fffbeb 100%); padding: 24px; border-radius: 14px; border-left: 4px solid #f59e0b; margin-bottom: 24px;">
    <h3 style="margin-top:0;">The Business Case for Each Engagement Type</h3>
    <p>PACEA tells you WHO to target. This calculator tells you <b>how much money Fairlight will make from each client type</b>.
    Backed by real recovery-pathway data showing that orgs receiving advisory-style intervention grow revenue 3.4× faster than those that don't.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Engagement Assumptions")
    c1, c2, c3 = st.columns(3)
    with c1:
        engagement_fee = st.number_input("Fairlight fee per engagement ($)",
                                         min_value=5000, max_value=100000, value=15000, step=1000)
    with c2:
        fee_pct = st.slider("Fairlight success fee (% of revenue uplift)",
                             min_value=0.5, max_value=5.0, value=1.5, step=0.25)
    with c3:
        success_rate_roi = st.slider("Expected success rate (%)", min_value=20, max_value=80, value=40, step=5)

    st.markdown("### Portfolio Size by Client Tier")
    c1, c2, c3 = st.columns(3)
    with c1:
        n_tier1 = st.number_input("Tier 1 clients (Elite)", min_value=0, max_value=200, value=10, step=1)
    with c2:
        n_tier2 = st.number_input("Tier 2 clients (High Potential)", min_value=0, max_value=500, value=50, step=5)
    with c3:
        n_tier3 = st.number_input("Tier 3 clients (At Risk)", min_value=0, max_value=500, value=20, step=5)

    # Recovery data-backed growth rates
    growth_rates = {
        "tier1_with": 0.12, "tier1_without": 0.06,
        "tier2_with": 0.28, "tier2_without": 0.11,
        "tier3_with": 0.385, "tier3_without": -0.05,
    }
    tier_revenues = {1: 3_000_000, 2: 1_200_000, 3: 450_000}

    def tier_roi(n, tier, rev_med, growth_with, growth_without):
        n_successes = n * (success_rate_roi / 100)
        total_fees_fixed = n * engagement_fee
        uplift_per_client = rev_med * (growth_with - growth_without) * 2  # 2-year horizon
        total_uplift = uplift_per_client * n_successes
        success_fees = total_uplift * (fee_pct / 100)
        total_fees = total_fees_fixed + success_fees
        return {
            "n": n, "expected_successes": n_successes, "fixed_fees": total_fees_fixed,
            "uplift_per_success": uplift_per_client, "total_uplift": total_uplift,
            "success_fees": success_fees, "total_revenue": total_fees,
            "roi_multiple": total_fees / total_fees_fixed if total_fees_fixed > 0 else 0,
        }

    r1 = tier_roi(n_tier1, 1, tier_revenues[1], growth_rates["tier1_with"], growth_rates["tier1_without"])
    r2 = tier_roi(n_tier2, 2, tier_revenues[2], growth_rates["tier2_with"], growth_rates["tier2_without"])
    r3 = tier_roi(n_tier3, 3, tier_revenues[3], growth_rates["tier3_with"], growth_rates["tier3_without"])

    total_investment = r1["fixed_fees"] + r2["fixed_fees"] + r3["fixed_fees"]
    total_client_uplift = r1["total_uplift"] + r2["total_uplift"] + r3["total_uplift"]
    total_fairlight_revenue = r1["total_revenue"] + r2["total_revenue"] + r3["total_revenue"]
    portfolio_roi = total_fairlight_revenue / total_investment if total_investment > 0 else 0

    st.markdown("## Portfolio ROI Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Fairlight Investment", f"${total_investment/1e6:.2f}M", f"{n_tier1+n_tier2+n_tier3} engagements")
    c2.metric("Client Revenue Uplift", f"${total_client_uplift/1e6:.1f}M", "across portfolio")
    c3.metric("Fairlight Revenue", f"${total_fairlight_revenue/1e6:.2f}M",
              f"${(total_fairlight_revenue-total_investment)/1e6:+.2f}M net")
    c4.metric("Portfolio ROI", f"{portfolio_roi:.1f}x", "multiple of investment")

    st.markdown("### ROI Breakdown by Tier")
    roi_df = pd.DataFrame([
        {"Tier": "Tier 1 (Elite)", "N": r1["n"], "Success %": success_rate_roi,
         "Uplift/Client": f"${r1['uplift_per_success']/1e3:,.0f}K",
         "Total Uplift": f"${r1['total_uplift']/1e6:.2f}M",
         "Fairlight Rev": f"${r1['total_revenue']/1e3:,.0f}K",
         "ROI": f"{r1['roi_multiple']:.1f}x"},
        {"Tier": "Tier 2 (High Pot.)", "N": r2["n"], "Success %": success_rate_roi,
         "Uplift/Client": f"${r2['uplift_per_success']/1e3:,.0f}K",
         "Total Uplift": f"${r2['total_uplift']/1e6:.2f}M",
         "Fairlight Rev": f"${r2['total_revenue']/1e3:,.0f}K",
         "ROI": f"{r2['roi_multiple']:.1f}x"},
        {"Tier": "Tier 3 (At Risk)", "N": r3["n"], "Success %": success_rate_roi,
         "Uplift/Client": f"${r3['uplift_per_success']/1e3:,.0f}K",
         "Total Uplift": f"${r3['total_uplift']/1e6:.2f}M",
         "Fairlight Rev": f"${r3['total_revenue']/1e3:,.0f}K",
         "ROI": f"{r3['roi_multiple']:.1f}x"},
    ])
    st.dataframe(roi_df, hide_index=True, use_container_width=True)

    st.markdown("### Visual Comparison")
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Investment", x=["Tier 1", "Tier 2", "Tier 3"],
                          y=[r1["fixed_fees"], r2["fixed_fees"], r3["fixed_fees"]],
                          marker_color="#94a3b8"))
    fig.add_trace(go.Bar(name="Fairlight Revenue", x=["Tier 1", "Tier 2", "Tier 3"],
                          y=[r1["total_revenue"], r2["total_revenue"], r3["total_revenue"]],
                          marker_color="#0d9488"))
    fig.update_layout(barmode="group", height=380,
                       yaxis_tickformat="$,.0f", yaxis_title="Dollars",
                       paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                       legend=dict(orientation="h", yanchor="bottom", y=1.02))
    st.plotly_chart(fig, use_container_width=True)

    total_successes = r1["expected_successes"] + r2["expected_successes"] + r3["expected_successes"]
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #fef3c7 0%, #fffbeb 100%); padding: 24px; border-radius: 14px; border-left: 4px solid #f59e0b;">
    <h3 style="margin-top:0;">Executive Summary</h3>
    If Fairlight engages <b>{n_tier1+n_tier2+n_tier3}</b> clients at current assumptions
    (${engagement_fee:,} per engagement, {fee_pct}% success fee, {success_rate_roi}% success rate),
    the expected portfolio outcome is:
    <ul>
      <li><b>${total_client_uplift/1e6:.1f}M</b> in client revenue uplift across {total_successes:.0f} successful engagements</li>
      <li><b>${total_fairlight_revenue/1e6:.2f}M</b> in Fairlight total revenue (fixed fees + success fees)</li>
      <li><b>{portfolio_roi:.1f}x ROI</b> on Fairlight's ${total_investment/1e6:.2f}M upfront investment</li>
    </ul>
    <p><small><i>Growth rate assumptions grounded in: (a) recovery pathway data showing 38.5% revenue growth for orgs that recover vs −5% for those that don't; (b) Hager (2001) research showing diversification-focused advisory can compound returns over 2–5 year horizons.</i></small></p>
    </div>
    """, unsafe_allow_html=True)

# ==================================================================
# RESEARCH VALIDATION
# ==================================================================
elif page == "Research Validation":
    st.title("Research Validation")
    st.info("Every major finding in our model is validated against published academic research and industry benchmarks. This page maps 6 key studies to our specific data findings. Also includes 3 surprising insights that go beyond intuition. Use this to defend the methodology to stakeholders.")
    st.markdown("Our findings match 30 years of academic research.")

    if len(benchmarks) > 0:
        for _, b in benchmarks.iterrows():
            with st.expander(b["benchmark"]):
                st.markdown(f"**Research says:** {b['finding']}")
                st.markdown(f"**Our data shows:** {b['our_result']}")
                st.markdown(f"**What it means:** {b['implication']}")
    else:
        for title, lit, ours in [
            ("Tuckman & Chang (1991)", "Margins and concentration predict vulnerability", "Our model: margin = 89.5%, HHI = 6.9%"),
            ("NORI", "3-6 months reserves minimum", "Tier 3 median: 2.6 months. $62K reaches it."),
            ("Hager (2001)", "Diversification predicts survival", "HHI = 0.5 tipping point: distress drops 39% to 11%"),
            ("Starvation Cycle (2009)", "Overhead cuts cause infrastructure decay", "9.9% of top performers are declining"),
            ("GivingUSA 2024", "Individual giving fell 2.1%", "Donor fatigue scenario pushes 88K orgs into deficit"),
        ]:
            with st.expander(title):
                st.markdown(f"**Research:** {lit}")
                st.markdown(f"**Our data:** {ours}")

    st.subheader("Surprising findings")
    ni1,ni2,ni3 = st.columns(3)
    with ni1:
        st.markdown("#### Starvation Cycle")
        st.markdown("9.9% of healthy orgs are shrinking. Donor pressure to cut overhead causes decay.")
    with ni2:
        st.markdown("#### Single-Funder Trap")
        st.markdown("115K orgs get 96% from one source. Looks stable until that source disappears.")
    with ni3:
        st.markdown("#### Sweet Spot")
        st.markdown("HHI 0.3 to 0.5 is optimal. Too diversified also increases risk.")
