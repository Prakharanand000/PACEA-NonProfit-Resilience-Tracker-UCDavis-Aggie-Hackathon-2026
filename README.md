# Nonprofit Resilience Analytics — Aggie Hackathon 2026

Predicting financial durability across **415,000+ U.S. public charities** using 7 years of IRS Form 990 data.

## Key Results

| Metric | Value |
|--------|-------|
| Total filings parsed | 2.34M |
| Unique organizations | 415,123 |
| Predictive model AUC | 0.86 (Gradient Boosting) |
| Chronic instability rate | 10.5% |
| Hidden gems identified | 49,162 |
| Recovery insight | Recovered orgs grew revenue 3.4× faster |

## Three Deliverables

### 1. Resilience Scoring Model
Weighted composite index across 7 financial dimensions. Gradient Boosting classifier predicts chronic financial instability with **AUC 0.86**. Operating margin is the #1 driver (89.5% of model importance).

### 2. Peer Benchmarking Framework
358 peer groups (State × Revenue Size) with percentile rankings across 10 financial metrics. Enables comparisons like: *"You're in the 23rd percentile for reserves among mid-size TX education nonprofits."*

### 3. Funding Shock Simulator
5 scenarios (mild recession, severe recession, govt funding cut, donor fatigue, pandemic shock) model the cascade of nonprofits newly pushed into deficit. A severe recession pushes **112K organizations (27%)** into deficit.

## Critical Threshold Findings

- **HHI = 0.5** is the tipping point — below this, chronic instability drops from 39% to 11%
- **$62K median grant** gives a Critical nonprofit 3 months of operating reserves
- **Recovery pathway**: grow revenue + diversify (not just cut costs) — recovered orgs grew 38.5% vs 11.2% for stuck orgs

## Project Structure

```
├── extract_990.py          # XML extraction pipeline (IRS bulk data → CSV)
├── extract_fix.py          # Fix for deflate64-compressed zips
├── patch_data.py           # Compute derived fields from raw data
├── analyze_990_v2.py       # Core analysis: resilience, benchmarks, shocks
├── enhanced_analysis.py    # Predictive model, thresholds, recovery paths
├── dashboard.py            # Streamlit interactive dashboard
├── irs_990_downloader.py   # IRS bulk XML download script
├── analysis/               # Output CSVs (generated)
│   ├── shock_simulation_results.csv
│   ├── peer_group_stats.csv
│   ├── summary_stats.csv
│   ├── threshold_analysis.csv
│   └── recovery_pathways.csv
└── Nonprofit_Resilience_Deck_v2.pptx  # Presentation deck
```

## How to Run

### Prerequisites
```bash
pip install pandas numpy scikit-learn streamlit plotly
```

### Step 1: Extract IRS Data
```bash
python irs_990_downloader.py          # Download IRS bulk XML zips
python extract_990.py --data-dir irs_990_raw --output 990_parsed.csv
python extract_fix.py                  # Recover deflate64 zips (needs 7-Zip)
python patch_data.py                   # Compute derived fields
```

### Step 2: Run Analysis
```bash
python analyze_990_v2.py --input 990_parsed.csv --output-dir analysis
python enhanced_analysis.py
```

### Step 3: Launch Dashboard
```bash
streamlit run dashboard.py
```

## Data Sources

- **IRS Form 990 bulk XML downloads** — [irs.gov](https://www.irs.gov/charities-non-profits/form-990-series-downloads)
- Forms: 990, 990PF, 990T (excluding 990EZ per competition rules)
- Years: 2019–2026 (7-year rolling panel)

## Tech Stack

- **Python** (pandas, NumPy, scikit-learn)
- **Streamlit + Plotly** (interactive dashboard)
- **Gradient Boosting** (predictive model)
- **PptxGenJS** (presentation deck)

## Team

Aggie Hackathon 2026 — UC Davis
