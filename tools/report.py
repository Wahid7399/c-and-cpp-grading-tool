import csv

def dict_to_csv(data: dict, out_path: str, key_col: str = "key", fill=""):
    # Union of all nested keys (columns)
    all_cols = sorted({k for v in data.values() if isinstance(v, dict) for k in v})
    fieldnames = [key_col] + all_cols

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for key, attrs in data.items():
            attrs = attrs if isinstance(attrs, dict) else {}
            row = {key_col: key, **{col: attrs.get(col, fill) for col in all_cols}}
            writer.writerow(row)