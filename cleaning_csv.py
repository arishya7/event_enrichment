"""
Clean and format CSV files for database upload.

Usage:
    python cleaning_csv.py <input_csv> [output_csv]

Examples:
    python cleaning_csv.py data/events_output/14Nov.csv
    python cleaning_csv.py data/events_output/14Nov.csv data/14Nov_clean.csv
"""

import pandas as pd
import csv
import json
import sys
from pathlib import Path


def clean_csv(input_path: str, output_path: str = None) -> None:
    """
    Clean and reorder CSV columns for database upload.
    
    Args:
        input_path: Path to input CSV file
        output_path: Path to output CSV file (default: adds '_clean' suffix)
    """
    input_file = Path(input_path)
    
    if not input_file.exists():
        print(f"❌ Input file not found: {input_path}")
        sys.exit(1)
    
    # Default output path: same name with _clean suffix
    if output_path is None:
        output_path = input_file.parent / f"{input_file.stem}_clean.csv"
    
    print(f"📄 Input:  {input_path}")
    print(f"📄 Output: {output_path}")
    
    # Load everything as string
    df = pd.read_csv(input_path, dtype=str).fillna("")
    print(f"📊 Loaded {len(df)} rows")

    # Desired column order (matching database schema)
    COL_ORDER = [
        "id", "title", "organiser", "blurb", "description", "guid",
        "activity_or_event", "url", "is_free", "price_display_teaser",
        "price_display", "price", "min_price", "max_price",
        "age_group_display", "min_age", "max_age",
        "datetime_display_teaser", "datetime_display",
        "start_datetime", "end_datetime",
        "venue_name", "address_display", "categories", "images",
        "longitude", "latitude", "checked", "source_file",
        "region", "planning_area", "label_tag", "keyword_tag"
    ]

    # -----------------------
    # Fix JSON Columns
    # -----------------------
    JSON_COLS = ["images", "categories"]

    for col in JSON_COLS:
        if col not in df.columns:
            continue
            
        def fix_json(s):
            if not s or s.strip() == "":
                return "[]"
            try:
                obj = json.loads(s)
                return json.dumps(obj, ensure_ascii=False)
            except:
                return s  # leave unchanged

        df[col] = df[col].apply(fix_json)
        print(f"✓ Fixed JSON in column: {col}")

    # -----------------------
    # Replace newlines
    # -----------------------
    df = df.replace({"\n": "\\n", "\r": "\\n"}, regex=True)
    print("✓ Replaced newline characters")

    # -----------------------
    # Force column order
    # -----------------------
    # Missing columns will be created as blank
    for col in COL_ORDER:
        if col not in df.columns:
            df[col] = ""
            print(f"⚠ Added missing column: {col}")

    # Keep only columns in COL_ORDER (drop extras)
    extra_cols = [c for c in df.columns if c not in COL_ORDER]
    if extra_cols:
        print(f"⚠ Dropping extra columns: {extra_cols}")
    
    df = df[COL_ORDER]

    # -----------------------
    # Save cleaned CSV
    # -----------------------
    df.to_csv(
        output_path,
        index=False,
        quoting=csv.QUOTE_ALL,
        escapechar='\\'
    )

    print(f"\n✅ Cleaned & Reordered CSV saved to: {output_path}")
    print(f"📊 Total rows: {len(df)}")
    print(f"📊 Total columns: {len(df.columns)}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nAvailable CSV files in data/events_output/:")
        events_dir = Path("data/events_output")
        if events_dir.exists():
            csv_files = list(events_dir.glob("**/*.csv"))
            for f in csv_files[:10]:
                print(f"  - {f}")
            if len(csv_files) > 10:
                print(f"  ... and {len(csv_files) - 10} more")
        sys.exit(1)
    
    input_csv = sys.argv[1]
    output_csv = sys.argv[2] if len(sys.argv) > 2 else None
    
    clean_csv(input_csv, output_csv)


if __name__ == "__main__":
    main()
