import os
from config import settings
from core import quality_scorer
from tools.report import dict_to_csv
import argparse

# Set up command line args
parser = argparse.ArgumentParser(description="Process some files.")
parser.add_argument("--input", type=str, required=True, help="Input dir path")
parser.add_argument("--output", type=str, required=True, help="Output dir path")
parser.add_argument("--config", type=str, help="Config file path")
parser.add_argument("--result-format", type=str, choices=["json", "csv"], default="csv", help="Output format for results")
parser.add_argument("--threads", type=int, default=1, help="Number of threads to use for processing")
parser.add_argument("--multifolder", action="store_true", help="Multifolder analysis for multiple projects at once, extracts")

args = parser.parse_args()

# Custom config provided
if args.config:
    settings.load_config(args.config)

quality_scorer.init()

if args.multifolder:
    results = quality_scorer.multifolder_run(args.input, args.output, args.threads)
else:
    results = {args.input: quality_scorer.run(args.input, args.output)}

if args.result_format == "csv":
    dict_to_csv(results, os.path.join(args.output, "results.csv"))