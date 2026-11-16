"""Print detailed column-level profile from dataset_metadata.json."""
import json

with open("reports/dataset_metadata.json", encoding="utf-8") as f:
    meta = json.load(f)

for fname, p in meta["profiles"].items():
    print(f"=== {fname} ===")
    rows = p["rows"]
    cols = p["columns"]
    dups = p["duplicate_rows"]
    mem = p["memory_mb"]
    print(f"  Rows: {rows:,}  |  Cols: {cols}  |  Dups: {dups:,}  |  Memory: {mem} MB")
    print(f"  Columns & Types:")
    for col, dt in p["dtypes"].items():
        miss = p["missing_values"][col]
        uniq = p["unique_counts"][col]
        mc = miss["count"]
        mp = miss["pct"]
        print(f"    {col:<45s}  {dt:<10s}  uniq={uniq:>8,d}  miss={mc:>6,d} ({mp}%)")
    if p.get("date_ranges"):
        print("  Date Ranges:")
        for col, dr in p["date_ranges"].items():
            if dr.get("min"):
                print(f"    {col}: {dr['min']} → {dr['max']}  (nulls: {dr['null_count']}, parse_failures: {dr.get('parse_failures', 0)})")
    print()

