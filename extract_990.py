"""
IRS Form 990 XML Extraction Pipeline
=====================================
Reads index CSVs, selectively extracts 990/990PF/990T XMLs from zip archives,
and parses key financial fields into a structured CSV dataset.

Usage:
    python extract_990.py --data-dir "D:\\Aggie Hackathon\\irs_990_raw" --output "D:\\Aggie Hackathon\\990_parsed.csv"

    # Process only specific years:
    python extract_990.py --data-dir "D:\\Aggie Hackathon\\irs_990_raw" --years 2019 2020 2021 2022 2023 2024 2025

    # Limit filings per year (for quick testing):
    python extract_990.py --data-dir "D:\\Aggie Hackathon\\irs_990_raw" --limit 1000
"""

import os, sys, csv, zipfile, argparse, time
from pathlib import Path
from xml.etree import ElementTree as ET
from collections import defaultdict

# Enable deflate64 compression support (handles 2020/2025 zips)
try:
    import zipfile_deflate64  # noqa: F401 — patches zipfile on import
except ImportError:
    pass


def strip_ns(tag):
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag

def find_elem(root, *tag_names):
    for elem in root.iter():
        if strip_ns(elem.tag) in tag_names:
            return elem
    return None

def find_text(root, *tag_names):
    elem = find_elem(root, *tag_names)
    if elem is not None and elem.text:
        return elem.text.strip()
    return None

def find_number(root, *tag_names):
    txt = find_text(root, *tag_names)
    if txt:
        try:
            return float(txt.replace(",", ""))
        except ValueError:
            return None
    return None

def find_bool(root, *tag_names):
    txt = find_text(root, *tag_names)
    if txt:
        return txt.lower() in ("1", "true", "x", "yes")
    return None


def parse_990(root, return_type):
    """Extract key financial fields from a Form 990 XML return."""
    ret_data = find_elem(root, "ReturnData")
    if ret_data is None:
        ret_data = root

    irs990 = find_elem(ret_data, "IRS990", "IRS990PF", "IRS990T")
    if irs990 is None:
        irs990 = ret_data

    header = find_elem(root, "ReturnHeader")
    # Use header if found, otherwise fall back to root (avoids deprecation warning)
    hdr = header if header is not None else root

    record = {}

    # --- HEADER INFO ---
    record["ein"] = find_text(hdr, "EIN") or find_text(root, "EIN")
    record["tax_year"] = find_text(hdr, "TaxYr", "TaxYear", "TaxPeriodEndDt")
    record["tax_period_begin"] = find_text(hdr, "TaxPeriodBeginDt", "TaxPrdBeginDt")
    record["tax_period_end"] = find_text(hdr, "TaxPeriodEndDt", "TaxPrdEndDt")
    record["return_type"] = return_type

    name_elem = find_elem(hdr, "BusinessNameLine1Txt", "BusinessNameLine1", "Name")
    record["org_name"] = name_elem.text.strip() if name_elem is not None and name_elem.text else None

    record["state"] = find_text(hdr, "StateAbbreviationCd", "State")
    if record["state"] is None:
        addr = find_elem(hdr, "USAddress", "FilerUSAddress")
        if addr is not None:
            record["state"] = find_text(addr, "StateAbbreviationCd", "State")

    # --- MISSION / NTEE ---
    record["activity_or_mission"] = find_text(irs990, "ActivityOrMissionDesc", "ActivityOrMissionDescription", "PrimaryExemptPurposeTxt")
    record["ntee_code"] = find_text(root, "NTEECode")

    # --- PART I: SUMMARY ---
    record["num_voting_members"] = find_number(irs990, "VotingMembersGoverningBodyCnt", "NbrVotingMembersGoverningBody")
    record["num_independent_members"] = find_number(irs990, "VotingMembersIndependentCnt", "NbrIndependentVotingMembers")
    record["num_employees"] = find_number(irs990, "TotalEmployeeCnt", "TotalNbrEmployees")
    record["num_volunteers"] = find_number(irs990, "TotalVolunteersCnt", "TotalNbrVolunteers")

    # --- PART VIII: REVENUE ---
    record["contributions_grants"] = find_number(irs990,
        "CYContributionsGrantsAmt", "ContributionsGrantsCurrentYear",
        "FedCampaignContriAmt", "CYTotalContributionsAmt", "TotalContributionsAmt")
    record["program_service_revenue"] = find_number(irs990,
        "CYProgramServiceRevenueAmt", "ProgramServiceRevCurrentYear",
        "ProgramServiceRevenueAmt", "TotalProgramServiceRevenueAmt")
    record["investment_income"] = find_number(irs990,
        "CYInvestmentIncomeAmt", "InvestmentIncomeCurrentYear",
        "InvestmentIncomeAmt", "NetInvestmentIncomeAmt")
    record["other_revenue"] = find_number(irs990,
        "CYOtherRevenueAmt", "OtherRevenueCurrentYear", "OtherRevenueAmt")
    record["total_revenue"] = find_number(irs990,
        "CYTotalRevenueAmt", "TotalRevenueCurrentYear",
        "TotalRevenueAmt", "TotalRevenue")
    record["govt_grants"] = find_number(irs990,
        "GovernmentGrantsAmt", "GovtGrantsAmt", "GovernmentContributionsAmt")

    # --- PART IX: EXPENSES ---
    record["total_functional_expenses"] = find_number(irs990,
        "CYTotalExpensesAmt", "TotalExpensesCurrentYear",
        "TotalFunctionalExpensesAmt", "TotalExpenses", "TotalExpensesAmt")
    record["grants_and_similar"] = find_number(irs990,
        "GrantsAndSimilarAmtAmt", "TotalGrantsAmt",
        "CYGrantsAndSimilarPaidAmt", "GrantsAndSimilarAmountsPaid")
    record["salaries_compensation"] = find_number(irs990,
        "SalariesEtcCurrentYearAmt", "SalariesAndWages",
        "CYSalariesCompEmpBnftPaidAmt", "CompCurrentOfcrDirectorsGrp")
    record["program_expenses"] = find_number(irs990,
        "TotalProgramServExpenseAmt", "TotalProgramServiceExpense")
    record["management_expenses"] = find_number(irs990,
        "TotalMgmtAndGeneralExpnssAmt", "ManagementAndGeneralAmt")
    record["fundraising_expenses"] = find_number(irs990,
        "TotalFundrsngExpenseAmt", "FundraisingAmt",
        "CYTotalFundraisingExpenseAmt", "FundraisingExpenses")

    # --- PART X: BALANCE SHEET ---
    record["total_assets_boy"] = find_number(irs990,
        "TotalAssetsBOYAmt", "TotalAssetsBeginOfYear", "TotalAssetsBOY")
    record["total_assets_eoy"] = find_number(irs990,
        "TotalAssetsEOYAmt", "TotalAssetsEndOfYear", "TotalAssetsEOY", "TotalAssets")
    record["total_liabilities_boy"] = find_number(irs990,
        "TotalLiabilitiesBOYAmt", "TotalLiabilitiesBeginOfYear")
    record["total_liabilities_eoy"] = find_number(irs990,
        "TotalLiabilitiesEOYAmt", "TotalLiabilitiesEndOfYear", "TotalLiabilities")
    record["net_assets_boy"] = find_number(irs990,
        "NetAssetsOrFundBalancesBOYAmt", "TotNetAstOrFundBalancesBOY", "NetAssetsBeginOfYear")
    record["net_assets_eoy"] = find_number(irs990,
        "NetAssetsOrFundBalancesEOYAmt", "TotNetAstOrFundBalancesEOY",
        "NetAssetsEndOfYear", "NetAssetsOrFundBalances")
    record["cash_savings"] = find_number(irs990,
        "CashNonInterestBearingGrp", "SavingsAndTempCashInvstAmt", "CashSavingsAndInvestments")

    # --- PART XI: RECONCILIATION ---
    record["revenue_less_expenses"] = find_number(irs990,
        "RevenuesLessExpensesAmt", "RevenuesLessExpenses", "ExcessOrDeficitForYearAmt")

    # --- GOVERNANCE ---
    record["independent_audit"] = find_bool(irs990,
        "IndependentAuditFinclStmtInd", "AuditedFinancialStmtAttInd")
    record["conflict_of_interest_policy"] = find_bool(irs990,
        "ConflictOfInterestPolicyInd", "ConflictOfInterestPolicy")
    record["whistleblower_policy"] = find_bool(irs990,
        "WhistleblowerPolicyInd", "WhistleblowerPolicy")
    record["document_retention_policy"] = find_bool(irs990,
        "DocumentRetentionPolicyInd", "DocumentRetentionPolicy")

    # --- 990PF SPECIFIC ---
    if return_type in ("990PF", "990-PF"):
        record["fair_market_value_assets"] = find_number(irs990, "FMVAssetsEOYAmt", "FairMarketValueOfAllAssets")
        record["distributable_amount"] = find_number(irs990, "DistributableAmountAmt", "DistributableAmount")
        record["qualifying_distributions"] = find_number(irs990, "QualifyingDistriAmt", "QualifyingDistributions")

    # --- 990T SPECIFIC ---
    if return_type in ("990T", "990-T"):
        record["unrelated_business_income"] = find_number(irs990, "TotalUBTIAmt", "TotalUnrelatedBusinessIncome", "TotalUBTIComputedAmt")
        record["total_deductions"] = find_number(irs990, "TotalDeductionAmt", "TotalDeductions")
        record["taxable_income"] = find_number(irs990, "TaxableIncomeAmt", "TaxableIncome")

    return record


def load_index(index_path, allowed_types=None):
    if allowed_types is None:
        allowed_types = {"990", "990PF", "990T"}
    filings = []
    with open(index_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("RETURN_TYPE", "").strip() in allowed_types:
                filings.append(row)
    return filings


def process_year(year_dir, year, allowed_types, limit=None):
    index_path = year_dir / f"index_{year}.csv"
    if not index_path.exists():
        print(f"  [WARN] No index file for {year}, skipping")
        return []

    print(f"  Loading index for {year}...")
    filings = load_index(index_path, allowed_types)
    total = len(filings)
    print(f"  Found {total:,} filings of types {allowed_types}")

    if limit:
        filings = filings[:limit]
        print(f"  Limited to {len(filings)} filings")

    filing_by_oid = {}
    for f in filings:
        oid = f.get("OBJECT_ID", "").strip()
        if oid:
            filing_by_oid[oid] = f

    # Check if index has batch IDs (2024+)
    has_batch_id = False
    batch_to_oids = defaultdict(list)
    with open(index_path, "r", encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh)
        first = next(reader, None)
        if first and "XML_BATCH_ID" in first:
            has_batch_id = True
            # Re-read to build batch mapping
            fh.seek(0)
            reader = csv.DictReader(fh)
            for row in reader:
                oid = row.get("OBJECT_ID", "").strip()
                batch = row.get("XML_BATCH_ID", "").strip()
                if oid in filing_by_oid and batch:
                    batch_to_oids[batch].append(oid)

    zip_files = sorted(year_dir.glob("*.zip"))
    if not zip_files:
        print(f"  [WARN] No zip files in {year_dir}")
        return []

    results = []
    processed = 0
    errors = 0
    skipped = 0

    for zf_path in zip_files:
        zip_name = zf_path.stem

        if has_batch_id:
            relevant_oids = set(batch_to_oids.get(zip_name, []))
            if not relevant_oids:
                continue
        else:
            relevant_oids = set(filing_by_oid.keys())

        print(f"  Scanning {zf_path.name} ({len(relevant_oids):,} target filings)...")

        try:
            with zipfile.ZipFile(zf_path, "r") as zf:
                for xml_name in zf.namelist():
                    if not xml_name.endswith(".xml"):
                        continue

                    base = xml_name.replace("_public.xml", "").replace(".xml", "").split("/")[-1]

                    if base not in relevant_oids and base not in filing_by_oid:
                        skipped += 1
                        continue

                    filing_meta = filing_by_oid.get(base, {})

                    try:
                        with zf.open(xml_name) as xml_file:
                            root = ET.parse(xml_file).getroot()

                        record = parse_990(root, filing_meta.get("RETURN_TYPE", "990"))
                        record["object_id"] = base
                        record["filing_year"] = year
                        record["taxpayer_name_index"] = filing_meta.get("TAXPAYER_NAME", "")
                        record["tax_period_index"] = filing_meta.get("TAX_PERIOD", "")
                        if not record.get("org_name"):
                            record["org_name"] = filing_meta.get("TAXPAYER_NAME", "")

                        results.append(record)
                        processed += 1

                        if processed % 5000 == 0:
                            print(f"    Processed {processed:,}/{len(filing_by_oid):,} ({errors} errors)...")

                        if limit and processed >= limit:
                            break

                    except ET.ParseError:
                        errors += 1
                    except Exception as e:
                        errors += 1
                        if errors <= 5:
                            print(f"    [ERROR] {xml_name}: {e}")

        except zipfile.BadZipFile:
            print(f"  [ERROR] Bad zip: {zf_path.name}")
            continue

        if limit and processed >= limit:
            break

    print(f"  Year {year}: {processed:,} parsed, {errors} errors, {skipped:,} skipped")
    return results


def main():
    parser = argparse.ArgumentParser(description="Parse IRS 990 XML bulk data")
    parser.add_argument("--data-dir", required=True, help="Path to irs_990_raw directory")
    parser.add_argument("--output", default=None, help="Output CSV path")
    parser.add_argument("--years", nargs="+", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None, help="Max filings per year (for testing)")
    parser.add_argument("--types", nargs="+", default=["990", "990PF", "990T"])
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"ERROR: Data directory not found: {data_dir}")
        sys.exit(1)

    output_path = Path(args.output) if args.output else data_dir.parent / "990_parsed.csv"

    available_years = sorted(int(d.name) for d in data_dir.iterdir() if d.is_dir() and d.name.isdigit())
    years = [y for y in args.years if y in available_years] if args.years else available_years

    print("=" * 60)
    print("IRS Form 990 XML Extraction Pipeline")
    print("=" * 60)
    print(f"Data dir:     {data_dir}")
    print(f"Output:       {output_path}")
    print(f"Years:        {years}")
    print(f"Return types: {args.types}")
    print(f"Limit/year:   {args.limit or 'none'}")
    print("=" * 60)

    allowed_types = set(args.types)
    all_results = []
    start_time = time.time()

    for year in years:
        year_dir = data_dir / str(year)
        print(f"\n--- Processing {year} ---")
        t0 = time.time()
        results = process_year(year_dir, year, allowed_types, args.limit)
        all_results.extend(results)
        print(f"  Completed {year} in {time.time()-t0:.1f}s ({len(results):,} records)")

    if all_results:
        priority_fields = [
            "ein", "org_name", "state", "return_type", "filing_year",
            "tax_year", "tax_period_begin", "tax_period_end", "tax_period_index",
            "object_id", "taxpayer_name_index",
            "ntee_code", "activity_or_mission",
            "num_voting_members", "num_independent_members", "num_employees", "num_volunteers",
            "contributions_grants", "program_service_revenue", "investment_income",
            "other_revenue", "total_revenue", "govt_grants",
            "total_functional_expenses", "grants_and_similar", "salaries_compensation",
            "program_expenses", "management_expenses", "fundraising_expenses",
            "total_assets_boy", "total_assets_eoy",
            "total_liabilities_boy", "total_liabilities_eoy",
            "net_assets_boy", "net_assets_eoy", "cash_savings",
            "revenue_less_expenses",
            "independent_audit", "conflict_of_interest_policy",
            "whistleblower_policy", "document_retention_policy",
            "fair_market_value_assets", "distributable_amount", "qualifying_distributions",
            "unrelated_business_income", "total_deductions", "taxable_income",
        ]
        seen = set(priority_fields)
        all_fields = list(priority_fields)
        for rec in all_results:
            for k in rec:
                if k not in seen:
                    all_fields.append(k)
                    seen.add(k)

        print(f"\nWriting {len(all_results):,} records to {output_path}...")
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=all_fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(all_results)

        total_time = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"DONE!")
        print(f"Total records: {len(all_results):,}")
        print(f"Total time:    {total_time:.1f}s ({total_time/60:.1f}m)")
        print(f"Output file:   {output_path}")
        print(f"File size:     {output_path.stat().st_size / 1e6:.1f} MB")
        print(f"{'='*60}")
    else:
        print("\n[WARN] No records extracted!")


if __name__ == "__main__":
    main()
