import os
import sys

# Get the absolute path to the project root (one level up from scripts/)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

# Put the project root on sys.path if it's not already there
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import load_file, settings
from core import checker
from tools.report import dict_to_csv, csv_to_dict
from tools.utils import transpose_dict, collect_input_folders
from tools.partial import child_key, list_children, read_existing
import argparse
import time
import os
import json

parser = argparse.ArgumentParser(description="Process some files.")
parser.add_argument("--output", type=str, required=True, help="Output dir path")
parser.add_argument("--config", type=str, help="Config file path")
parser.add_argument("--multifolder", action="store_true", help="Multifolder analysis for multiple projects at once, extracts")
parser.add_argument("--grading", type=str, default="relative", choices=["absolute", "relative"], help="Grading type for the results")

args = parser.parse_args()

if args.config:
    config = load_file(args.config)
    settings.load(config)

results = transpose_dict(csv_to_dict(os.path.join(args.output, "raw_scores.csv")))

checker.init()

# with open(os.path.join(args.output, "raw.json"), "w") as f:
#     f.write(json.dumps(results, indent=2))

if args.grading == "absolute" or (args.multifolder and args.grading == "relative"):
    checker.grade(results, args.output, args.grading)
else:
    print("Warning: Relative grading is only supported in multifolder mode, skipping grading.")
