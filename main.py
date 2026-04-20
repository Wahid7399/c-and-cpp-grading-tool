from config import load_file, settings
from core import checker
from tools.report import dict_to_csv
from tools.utils import transpose_dict, collect_input_folders
from tools.partial import child_key, read_existing
import argparse
import time
import os
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Set up command line args
parser = argparse.ArgumentParser(description="Process some files.")
parser.add_argument("--input", type=str, required=True, help="Input dir path")
parser.add_argument("--output", type=str, required=True, help="Output dir path")
parser.add_argument("--tests", type=str, required=False, help="Tests file path")
parser.add_argument("--config", type=str, help="Config file path")
parser.add_argument("--threads", type=int, default=1, help="Number of threads to use for processing")
parser.add_argument("--check-zips", type=str, default="true", help="Check and extract zip files in multifolder mode")
parser.add_argument("--multifolder", action="store_true", help="Multifolder analysis for multiple projects at once, extracts")
parser.add_argument("--grading", type=str, default="relative", choices=["absolute", "relative"], help="Grading type for the results")

args = parser.parse_args()

# Custom config provided
if args.config:
    config = load_file(args.config)
    settings.load(config)

start_time = time.perf_counter()

checker.init()
default_tests_paths = None
if settings.plugins.doctest.enabled:
    def _resolve_test_path(p):
        if os.path.isabs(p):
            return p
        config_dir = os.path.dirname(args.config) if args.config else os.getcwd()
        return os.path.abspath(os.path.join(config_dir, p))

    if hasattr(settings.plugins.doctest, 'tests_files') and settings.plugins.doctest.tests_files is not None:
        default_tests_paths = [_resolve_test_path(p) for p in settings.plugins.doctest.tests_files]
    elif settings.plugins.doctest.tests_file is not None:
        default_tests_paths = [_resolve_test_path(settings.plugins.doctest.tests_file)]
checker.setup_tests(args.tests or default_tests_paths)

if args.multifolder:
    csv_path = os.path.join(args.output, "raw_scores.csv")
    existing = read_existing(csv_path)
    done = set(existing.keys())
    folders = [p for p in collect_input_folders(args.input) if child_key(p) not in done]

    results, partial = checker.multifolder_run(folders, args.output, args.threads, args.check_zips != "false")
    if partial:
        print("⚠️ Some folders could not be processed due to errors.")
    if existing:
        results.update(existing)
else:
    results = {args.input: checker.run_single(args.input, args.output)}

with open(os.path.join(args.output, "raw.json"), "w", encoding='utf-8') as f:
    f.write(json.dumps(results, indent=2))
dict_to_csv(transpose_dict(results), os.path.join(args.output, "raw_scores.csv"))

if args.grading == "absolute" or (args.multifolder and args.grading == "relative"):
    checker.grade(results, args.output, args.grading)
else:
    print("Warning: Relative grading is only supported in multifolder mode, skipping grading.")

end_time = time.perf_counter()
print(f"Total processing time: {end_time - start_time:.2f} seconds")