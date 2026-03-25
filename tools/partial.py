import os
from .report import dict_to_csv
from .utils import transpose_dict
import csv

def child_key(p): return os.path.basename(os.path.normpath(p))
def list_children(root): 
    return [os.path.join(root, n) for n in sorted(os.listdir(root)) if os.path.isdir(os.path.join(root, n))]

def read_existing(csv_path):
    if not os.path.isfile(csv_path): return {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        if not r.fieldnames: return {}
        return {row[r.fieldnames[0]]: {k: row[k] for k in r.fieldnames[1:]} for row in r}

def write_results(d, csv_path):
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    dict_to_csv(transpose_dict(d), csv_path)
