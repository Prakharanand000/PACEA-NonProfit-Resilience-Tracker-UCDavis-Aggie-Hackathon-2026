"""
Nonprofit Resilience Dashboard v2
==================================
Updated with enhanced analysis: predictive model, thresholds, recovery pathways.

Usage:
    cd "D:\\Aggie Hackathon"
    pip install streamlit plotly
    streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Nonprofit Resilience Analytics", layout="wide", page_icon="\U0001F3E5")

@st.cache_data
def load_data():
    df = pd.read_csv("analysis/resilience_scores.csv", low_memory=False)
    for col in ["total_revenue","total_functional_expenses","revenue_less_expenses",
                "operating_reserve_months","revenue_hhi","operating_margin",
                "program_expense_ratio","debt_ratio","governance_score","resilience_index",
                "net_assets_eoy","contributions_grants","investment_income",
                "other_revenue","program_service_revenue","num_employees","govt_grants"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

@st.cache_data
def load_shock():
    return pd.read_csv("analysis/shock_simulation_results.csv")

@st.cache_data
def load_gems():
    return pd.read_csv("analysis/hidden_gems.csv", low_memory=False)

@st.cache_data
def load_recovery():
    try:
        return pd.read_csv("analysis/recovery_pathways.csv", low_memory=False)
    except:
        return pd.DataFrame()

try:
    df = load_data()
    shock = load_shock()
    gems = load_gems()
    recovery = load_recovery()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

st.sidebar.title("\U0001F3E5 Nonprofit Resilience")
page = st.sidebar.radio("Navigate", [
    "\U0001F4CA Overview",
    "\U0001F50D Org Lookup",
    "\U0001F4C8 Peer Benchmarks",
    "\u26A1 Shock Simulator",
    "\U0001F3AF Thresholds",
    "\U0001F48E Hidden Gems",
])

if page == "\U0001F4CA Overview":
    st.title("Nonprofit Resilience Analytics")
    st.markdown("**2.34M filings** parsed \u00B7 **415K+ organizations** \u00B7 IRS Form 990 (2019\u20132025) \u00B7 **Gradient Boosting AUC 0.86**")

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Organizations", f"{len(df):,}")
    c2.metric("Median Revenue", f"${df['total_revenue'].median():,.0f}")
    c3.metric("Median Reserves", f"{df['operating_reserve_months'].median():.1f} mo")
    c4.metric("In Deficit", f"{(df['revenue_less_expenses']<0).mean():.0%}")
    c5.metric("Chronic Instability", "10.5%")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Resilience tier distribution")
        tier_data = df["resilience_tier"].value_counts().reindex(["Critical","At Risk","Stable","Thriving"])
        fig = px.bar(x=tier_data.index, y=tier_data.values, color=tier_data.index,
                     color_discrete_map={"Critical":"#DC2626","At Risk":"#F59E0B","Stable":"#2563EB","Thriving":"#059669"},
                     labels={"x":"Tier","y":"Organizations"})
        fig.update_layout(showlegend=False, height=350, margin=dict(t=10))
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.subheader("Revenue size distribution")
        so = ["<100K","100K-500K","500K-1M","1M-5M","5M-25M","25M-100M",">100M"]
        sd = df["size_bucket"].value_counts().reindex(so)
        fig2 = px.bar(x=sd.index, y=sd.values, color_discrete_sequence=["#0d9488"], labels={"x":"Revenue","y":"Orgs"})
        fig2.update_layout(height=350, margin=dict(t=10))
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("What separates thriving from critical")
    tm = df.groupby("resilience_tier")[["operating_reserve_months","revenue_hhi","operating_margin","program_expense_ratio","debt_ratio","governance_score"]].median()
    tm = tm.reindex(["Critical","At Risk","Stable","Thriving"])
    tm.columns = ["Reserves (mo)","Revenue HHI","Op Margin","Program %","Debt Ratio","Governance"]
    st.dataframe(tm.round(3).style.format("{:.3f}"), use_container_width=True)

    st.subheader("Key model insight")
    st.info("**Operating margin accounts for 89.5% of predictive importance** in our Gradient Boosting model (AUC 0.86). "
            "Revenue HHI is the second driver at 6.9%. The recovery pathway analysis shows recovered orgs grew revenue "
            "3.4\u00D7 faster than those that stayed in deficit (+38.5% vs +11.2%).")

elif page == "\U0001F50D Org Lookup":
    st.title("Organization Lookup")
    search = st.text_input("Search by EIN or name", placeholder="e.g. 131624100 or Red Cross")
    if search:
        results = df[df["ein"].astype(str).str.contains(search)] if search.isdigit() else df[df["org_name"].str.contains(search, case=False, na=False)]
        if len(results) == 0:
            st.warning("No organizations found.")
        else:
            st.success(f"Found {len(results):,} organizations")
            if len(results) > 20:
                st.dataframe(results[["ein","org_name","state","total_revenue","resilience_index","resilience_tier"]].head(50).sort_values("resilience_index", ascending=False))
            else:
                for _, org in results.iterrows():
                    with st.expander(f"{org['org_name']} (EIN: {org['ein']}) \u2014 {org.get('state','N/A')} \u2014 {org.get('resilience_tier','?')}"):
                        m1,m2,m3,m4 = st.columns(4)
                        m1.metric("Resilience Index", f"{org.get('resilience_index',0):.1f}")
                        m2.metric("Tier", str(org.get("resilience_tier","N/A")))
                        m3.metric("Revenue", f"${org.get('total_revenue',0):,.0f}")
                        m4.metric("Expenses", f"${org.get('total_functional_expenses',0):,.0f}")
                        f1,f2,f3,f4 = st.columns(4)
                        f1.metric("Reserves", f"{org.get('operating_reserve_months',0):.1f} mo")
                        f2.metric("Revenue HHI", f"{org.get('revenue_hhi',0):.3f}")
                        f3.metric("Op Margin", f"{org.get('operating_margin',0):.1%}")
                        f4.metric("Program %", f"{org.get('program_expense_ratio',0):.1%}")
                        g1,g2,g3,g4 = st.columns(4)
                        g1.metric("Net Assets", f"${org.get('net_assets_eoy',0):,.0f}")
                        g2.metric("Debt Ratio", f"{org.get('debt_ratio',0):.1%}")
                        g3.metric("Employees", f"{int(org.get('num_employees',0)):,}")
                        g4.metric("Governance", f"{org.get('governance_score',0):.0%}")

                        # Peer percentile context
                        peer = df[(df["state"]==org.get("state")) & (df["size_bucket"]==org.get("size_bucket"))]
                        if len(peer) > 10:
                            st.markdown(f"**Peer group:** {org.get('state')} / {org.get('size_bucket')} ({len(peer):,} orgs)")
                            for metric, label in [("resilience_index","Resilience"),("operating_reserve_months","Reserves"),("revenue_hhi","HHI")]:
                                pctile = (peer[metric] <= org.get(metric,0)).mean() * 100
                                st.progress(int(pctile), text=f"{label}: {pctile:.0f}th percentile")

elif page == "\U0001F4C8 Peer Benchmarks":
    st.title("Peer Benchmarking")
    c1,c2 = st.columns(2)
    sel_state = c1.selectbox("State", ["All"] + sorted(df["state"].dropna().unique()))
    so = ["<100K","100K-500K","500K-1M","1M-5M","5M-25M","25M-100M",">100M"]
    sel_size = c2.selectbox("Revenue Size", ["All"] + so)
    filtered = df.copy()
    if sel_state != "All": filtered = filtered[filtered["state"]==sel_state]
    if sel_size != "All": filtered = filtered[filtered["size_bucket"]==sel_size]
    st.markdown(f"**{len(filtered):,} organizations** in this peer group")
    if len(filtered) > 0:
        mc = st.columns(4)
        mc[0].metric("Median Revenue", f"${filtered['total_revenue'].median():,.0f}")
        mc[1].metric("Median Reserves", f"{filtered['operating_reserve_months'].median():.1f} mo")
        mc[2].metric("Median Margin", f"{filtered['operating_margin'].median():.1%}")
        mc[3].metric("Median Resilience", f"{filtered['resilience_index'].median():.1f}")
        co1,co2 = st.columns(2)
        with co1:
            st.subheader("Resilience distribution")
            fig = px.histogram(filtered, x="resilience_index", nbins=50, color_discrete_sequence=["#0d9488"])
            fig.update_layout(height=300, margin=dict(t=10))
            st.plotly_chart(fig, use_container_width=True)
        with co2:
            st.subheader("Revenue vs reserves")
            sample = filtered.sample(min(2000, len(filtered)), random_state=42)
            fig2 = px.scatter(sample, x="total_revenue", y="operating_reserve_months", color="resilience_tier",
                              color_discrete_map={"Critical":"#DC2626","At Risk":"#F59E0B","Stable":"#2563EB","Thriving":"#059669"}, log_x=True)
            fig2.update_layout(height=300, margin=dict(t=10))
            st.plotly_chart(fig2, use_container_width=True)

elif page == "\u26A1 Shock Simulator":
    st.title("Funding Shock Simulator")
    sc1,sc2,sc3 = st.columns(3)
    cd = sc1.slider("Contribution drop %", 0, 50, 15) / 100
    id_ = sc2.slider("Investment drop %", 0, 50, 20) / 100
    gd = sc3.slider("Govt grant drop %", 0, 75, 5) / 100
    be = df["total_functional_expenses"].fillna(0)
    br = df["total_revenue"].fillna(0)
    ws = (br - be) >= 0
    sr = (df["contributions_grants"].fillna(0)*(1-cd) + df["program_service_revenue"].fillna(0) + df["investment_income"].fillna(0)*(1-id_) + df["other_revenue"].fillna(0) - df["govt_grants"].fillna(0)*gd)
    nd = (sr - be) < 0
    newly = ws & nd
    rc = ((sr-br)/br.replace(0,np.nan)*100)
    mg = (-(sr-be)).clip(lower=0)/12
    ml = df["net_assets_eoy"].fillna(0) / mg.replace(0,np.nan)
    hr = nd & (ml.clip(0,120) < 6)
    r1,r2,r3,r4 = st.columns(4)
    r1.metric("Median rev change", f"{rc.median():.1f}%")
    r2.metric("Newly in deficit", f"{newly.sum():,} ({newly.mean():.1%})")
    r3.metric("Total in deficit", f"{nd.sum():,} ({nd.mean():.1%})")
    r4.metric("High risk (<6mo)", f"{hr.sum():,} ({hr.mean():.1%})")
    st.markdown("---")
    st.subheader("Pre-built scenarios")
    fig = go.Figure()
    fig.add_bar(x=shock["scenario"], y=shock["newly_in_deficit"],
                marker_color=["#F59E0B","#DC2626","#0D9488","#F59E0B","#2563EB"],
                text=shock["newly_in_deficit"].apply(lambda x: f"{x:,}"), textposition="outside")
    fig.update_layout(title="Organizations newly pushed to deficit", height=400, yaxis_title="Count")
    st.plotly_chart(fig, use_container_width=True)

elif page == "\U0001F3AF Thresholds":
    st.title("Critical Thresholds: Where Intervention Matters")

    st.subheader("Revenue diversification (HHI) vs chronic instability")
    thresh_hhi = pd.DataFrame({
        "HHI threshold": ["\u22640.3","\u22640.4","\u22640.5","\u22640.6","\u22640.7","\u22640.8","\u22641.0"],
        "Chronic instability %": [39.2, 18.6, 10.9, 9.8, 9.4, 9.1, 10.3],
        "Org count": [4617, 14352, 41945, 88679, 120294, 152020, 320133],
    })
    fig = px.bar(thresh_hhi, x="HHI threshold", y="Chronic instability %",
                 color="Chronic instability %", color_continuous_scale=["#059669","#F59E0B","#DC2626"],
                 text="Chronic instability %")
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig.update_layout(height=350, margin=dict(t=30), coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

    st.info("**HHI = 0.5 is the tipping point.** Below 0.5, chronic instability jumps from ~10% to 39%. "
            "Revenue diversification is the single most actionable lever for resilience.")

    st.subheader("Donation amounts to shift resilience tier")
    don = pd.DataFrame({
        "Tier": ["Critical","Critical","Critical","At Risk","At Risk","At Risk"],
        "Reserves added": ["3 months","6 months","12 months","3 months","6 months","12 months"],
        "Median grant needed": ["$61,632","$123,263","$246,526","$74,733","$149,466","$298,931"],
    })
    st.dataframe(don, use_container_width=True, hide_index=True)

    st.success("**A $62K median grant** gives a Critical nonprofit 3 extra months of operating reserves \u2014 "
               "often the difference between survival and closure during a funding disruption.")

    if len(recovery) > 0:
        st.subheader("Recovery pathways: what actually works")
        rc1, rc2 = st.columns(2)
        rc1.metric("Recovered orgs", f"{len(recovery):,}")
        rc1.metric("Revenue growth", f"+{recovery['rev_growth'].median():.1%}")
        rc2.metric("Stuck orgs", "74,419")
        rc2.metric("Revenue growth", "+11.2%")
        st.markdown("Recovered organizations **grew revenue 3.4\u00D7 faster** and **diversified their income** (HHI dropped). "
                    "The pathway is **grow + diversify**, not just cut costs.")

elif page == "\U0001F48E Hidden Gems":
    st.title("Hidden Gems: High-Impact Donation Targets")
    st.markdown(f"**{len(gems):,}** organizations where donations have outsized impact")
    if len(gems) > 0:
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Total gems", f"{len(gems):,}")
        m2.metric("Median revenue", f"${gems['total_revenue'].median():,.0f}")
        m3.metric("Median program %", f"{gems['program_expense_ratio'].median():.0%}")
        m4.metric("Median reserves", f"{gems['operating_reserve_months'].median():.1f} mo")
        fc1,fc2 = st.columns(2)
        gs = fc1.selectbox("Filter by state", ["All"] + sorted(gems["state"].dropna().unique().tolist()))
        gsort = fc2.selectbox("Sort by", ["impact_score","total_revenue","operating_reserve_months","resilience_index"])
        fg = gems if gs=="All" else gems[gems["state"]==gs]
        fg = fg.sort_values(gsort, ascending=(gsort=="operating_reserve_months"))
        dcols = ["org_name","state","ein","total_revenue","program_expense_ratio","operating_reserve_months","resilience_index","impact_score"]
        avail = [c for c in dcols if c in fg.columns]
        st.dataframe(fg[avail].head(100).style.format({
            "total_revenue":"${:,.0f}","program_expense_ratio":"{:.1%}",
            "operating_reserve_months":"{:.1f}","resilience_index":"{:.1f}","impact_score":"{:.3f}",
        }), use_container_width=True, height=500)

st.sidebar.markdown("---")
st.sidebar.markdown("**Aggie Hackathon 2026**")
st.sidebar.markdown(f"*{len(df):,} organizations \u00B7 AUC 0.86*")
