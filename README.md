# PACEA — Nonprofit Resilience Tracker

> 🥉 Bronze (3rd Place) + 🏆 Best Team Award — Aggie Hackathon 2026, UC Davis Graduate School of Management

**Don't tell me I'm the only one who loves marathons. Because 388,000 American nonprofits are running one right now.**

PACEA (Predictive Analytics for Client Engagement & Advisory) is a nonprofit resilience platform built for Fairlight Advisors to answer two questions: which nonprofits should we take on as clients, and what do we fix first?

**[🚀 Try the Live Dashboard](https://pacea-nonprofit-resilience-tracker.streamlit.app/)**

---

## What It Does

PACEA treats nonprofits like marathon runners. Some are Frontrunners with deep reserves and diversified funding. Others are Hitting the Wall — 100% distressed, burning through reserves that won't last another year. Each type needs a completely different coaching strategy.

The platform parses 2.34 million IRS Form 990 filings across 7 years (~388K active nonprofits), scores every organization on 5 financial vital signs, and classifies them into readiness tiers and behavioral segments with tailored advisory playbooks.

---

## Key Findings

| Finding | Detail |
|---|---|
| **The Wall** | When revenue diversification (HHI) drops below 0.5, financial distress falls from 39% to 11% |
| **The Aid Station** | $62K gives an at-risk nonprofit 3 months of operating reserves (NORI minimum) |
| **The Comeback** | Recovered organizations grew revenue 3.4x faster — by growing and diversifying, not cutting costs |

---

## The 5 Nonprofit Archetypes (K-Means, K=5, Silhouette 0.41)

| Marathon Name | Analytical Name | Count | Key Characteristic |
|---|---|---|---|
| Consistent Pacers | Steady Operators | 2,492 | 96.9% thriving. 117yr median cushion. Dream AUM clients. |
| Trail Blazers | Diversified Growers | 81,329 | Highest diversification (HHI 0.456). The template for all clients. |
| Frontrunners | Elite Performers | 1,697 | Strong financials but 29.4% quietly declining (Starvation Cycle). |
| New Entrants | Emerging Organizations | 115,949 | 96% single-funder. Largest addressable market. |
| Hitting the Wall | Struggling Missions | 4,099 | 100% distressed. Surplus -220%. Need triage, not advisory. |

---

## Technical Stack

- **Data**: 2.34M IRS Form 990 XML filings (2019-2026), parsed and engineered into 40+ financial features
- **Predictive Model**: Gradient Boosting (AUC 0.86) predicting chronic financial instability — operating margin drives 89.5% of prediction
- **Segmentation**: K-Means clustering (K=5) on 5 standardized health indicators
- **Dashboard**: Streamlit + Plotly, 8 interactive tabs
- **Deployment**: Streamlit Community Cloud

---

## Dashboard Tabs

| Tab | What It Does |
|---|---|
| Overview | Executive summary — 5 metrics, 3 tiers, key findings |
| Organization Lookup | Search any nonprofit by name or EIN — full diagnostic, peer benchmarking, 90-day playbook, investment readiness ladder |
| Client Readiness | Filter 388K nonprofits by tier, state, and revenue — Fairlight's sales pipeline |
| Nonprofit Segments | 5 archetypes with radar chart, outcomes table, advisory playbooks |
| Shock Simulator | 3 sliders to model any funding disruption across the full sector in real time |
| Thresholds & Recovery | HHI tipping point analysis and recovery pathway data |
| Advisory ROI | Business case calculator — expected return per engagement type |
| Research Validation | 6 academic studies mapped to PACEA findings |

---

## The 5 Financial Vital Signs (0–100 score, equal weight)

| Indicator | Formula | What It Measures |
|---|---|---|
| Surplus Ratio | (Revenue - Expenses) / Revenue | Is the org making more than it spends? |
| Financial Cushion | Net Assets / Annual Expenses | How long could it survive on reserves? |
| Revenue Diversification | 1 - HHI (4 revenue streams) | One bottle or a full hydration belt? |
| Revenue Stability | 1 - CV(revenue) over 3+ years | Steady stride or erratic sprints? |
| Asset/Liability Ratio | Total Assets / Total Liabilities | Can it carry the weight of its debt? |

---

## Run Locally

```bash
git clone https://github.com/Prakharanand000/PACEA-NonProfit-Resilience-Tracker-UCDavis-Aggie-Hackathon-2026.git
cd PACEA-NonProfit-Resilience-Tracker-UCDavis-Aggie-Hackathon-2026
pip install -r requirements.txt
streamlit run dashboard.py
```

---

## Team — The Data Gamblers

Built at Aggie Hackathon 2026, UC Davis Graduate School of Management

- Prakhar Anand
- Vaishali Hireraddi
- Aishwarya Srivastava
- Angelica Gamboa

---

*Grow. Diversify. Endure.*
