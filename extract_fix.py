"""
Fix extraction for zip files using unsupported compression methods.
Uses subprocess calls to 7-Zip or PowerShell to extract, then parses the XMLs.

Usage:
    python extract_fix.py
"""

import os, sys, csv, subprocess, time, shutil
from pathlib import Path
from xml.etree import ElementTree as ET

# Import the parser from extract_990.py
sys.path.insert(0, str(Path(__file__).parent))
from extract_990 import parse_990, load_index

DATA_DIR = Path(r"D:\Aggie Hackathon\irs_990_raw")
OUTPUT = Path(r"D:\Aggie Hackathon\990_parsed_fix2.csv")
TEMP_DIR = Path(r"D:\Aggie Hackathon\_temp_extract")

# The problematic zip files
PROBLEM_ZIPS = [
    (2020, "2020_TEOS_XML_CT1.zip"),
    (2025, "2025_TEOS_XML_05A.zip"),
    (2025, "2025_TEOS_XML_11B.zip"),
]

def find_7z():
    """Find 7-Zip executable."""
    candidates = [
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
        shutil.which("7z"),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None

def extract_with_7z(zip_path, dest_dir, exe_7z):
    """Extract zip using 7-Zip."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    cmd = [exe_7z, "x", str(zip_path), f"-o{dest_dir}", "-y", "-bso0", "-bsp1"]
    print(f"  Extracting {zip_path.name} with 7-Zip...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [ERROR] 7z failed: {result.stderr[:200]}")
        return False
    return True

def extract_with_powershell(zip_path, dest_dir):
    """Extract zip using PowerShell (handles most compression methods)."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    # Use .NET's ZipFile which supports more methods than Python
    ps_cmd = f"""
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::ExtractToDirectory('{zip_path}', '{dest_dir}')
    """
    print(f"  Extracting {zip_path.name} with PowerShell .NET...")
    result = subprocess.run(
        ["powershell", "-Command", ps_cmd],
        capture_output=True, text=True, timeout=1800
    )
    if result.returncode != 0:
        print(f"  [ERROR] PowerShell failed: {result.stderr[:300]}")
        return False
    return True

def parse_loose_xmls(xml_dir, year, allowed_types, filing_by_oid):
    """Parse XML files from an extracted directory."""
    results = []
    errors = 0
    processed = 0

    xml_files = list(xml_dir.rglob("*.xml"))
    print(f"  Found {len(xml_files):,} XML files in {xml_dir.name}")

    for xml_path in xml_files:
        base = xml_path.stem.replace("_public", "")

        if base not in filing_by_oid:
            continue

        filing_meta = filing_by_oid[base]

        try:
            tree = ET.parse(str(xml_path))
            root = tree.getroot()
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
                print(f"    Processed {processed:,} ({errors} errors)...")

        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f"    [ERROR] {xml_path.name}: {e}")

    print(f"  Parsed {processed:,} records, {errors} errors")
    return results


def main():
    # Find extraction tool
    exe_7z = find_7z()
    if exe_7z:
        print(f"Found 7-Zip: {exe_7z}")
        use_7z = True
    else:
        print("7-Zip not found, will use PowerShell .NET extraction")
        use_7z = False

    all_results = []
    start_time = time.time()

    for year, zip_name in PROBLEM_ZIPS:
        print(f"\n{'='*60}")
        print(f"Processing {zip_name} (year {year})")
        print(f"{'='*60}")

        zip_path = DATA_DIR / str(year) / zip_name
        if not zip_path.exists():
            print(f"  [WARN] Zip not found: {zip_path}")
            continue

        # Load index for this year
        index_path = DATA_DIR / str(year) / f"index_{year}.csv"
        allowed_types = {"990", "990PF", "990T"}
        filings = load_index(str(index_path), allowed_types)
        filing_by_oid = {f.get("OBJECT_ID", "").strip(): f for f in filings if f.get("OBJECT_ID", "").strip()}
        print(f"  Index has {len(filing_by_oid):,} target filings for {year}")

        # Extract to temp directory
        temp_dest = TEMP_DIR / f"{year}_{Path(zip_name).stem}"
        if temp_dest.exists():
            shutil.rmtree(temp_dest)

        if use_7z:
            success = extract_with_7z(zip_path, temp_dest, exe_7z)
        else:
            success = extract_with_powershell(zip_path, temp_dest)

        if not success:
            print(f"  Skipping {zip_name} due to extraction failure")
            continue

        # Parse the extracted XMLs
        results = parse_loose_xmls(temp_dest, year, allowed_types, filing_by_oid)
        all_results.extend(results)

        # Clean up temp files to save disk space
        print(f"  Cleaning up temp files...")
        shutil.rmtree(temp_dest, ignore_errors=True)

    # Write output
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

        print(f"\nWriting {len(all_results):,} records to {OUTPUT}...")
        with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=all_fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(all_results)

        total_time = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"DONE! {len(all_results):,} recovered records")
        print(f"Time: {total_time:.1f}s")
        print(f"Output: {OUTPUT}")
        print(f"{'='*60}")

        # Now merge with main file
        print(f"\nTo merge with your main dataset, run:")
        print(f'python -c "import pandas as pd; m=pd.read_csv(\'990_parsed.csv\',low_memory=False); f=pd.read_csv(\'990_parsed_fix2.csv\',low_memory=False); r=pd.concat([m,f]).drop_duplicates(subset=[\'object_id\'],keep=\'last\'); r.to_csv(\'990_parsed.csv\',index=False); print(f\'Merged: {{len(r):,}} (was {{len(m):,}}, added {{len(r)-len(m):,}}\')"')
    else:
        print("\nNo records recovered.")

    # Clean up temp dir
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR, ignore_errors=True)


if __name__ == "__main__":
    main()
