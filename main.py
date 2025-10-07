import time
from config import load_file, settings
from core import checker
from tools.report import dict_to_csv
from tools.utils import transpose_dict
import argparse
import os

# Set up command line args
parser = argparse.ArgumentParser(description="Process some files.")
parser.add_argument("--input", type=str, required=True, help="Input dir path")
parser.add_argument("--output", type=str, required=True, help="Output dir path")
parser.add_argument("--tests", type=str, required=False, help="Tests file path")
parser.add_argument("--config", type=str, help="Config file path")
parser.add_argument("--threads", type=int, default=1, help="Number of threads to use for processing")
parser.add_argument("--multifolder", action="store_true", help="Multifolder analysis for multiple projects at once, extracts")
parser.add_argument("--grading", type=str, default="absolute", choices=["absolute", "relative"], help="Grading type for the results")

args = parser.parse_args()

# Custom config provided
if args.config:
    config = load_file(args.config)
    settings.load(config)

start_time = time.perf_counter()

checker.init()
checker.setup_tests(args.tests)

if args.multifolder:
    results = checker.multifolder_run(args.input, args.output, args.threads)
else:
    results = {args.input: checker.run_single(args.input, args.output)}

dict_to_csv(transpose_dict(results), os.path.join(args.output, "raw_scores.csv"))

if args.grading == "absolute" or (args.multifolder and args.grading == "relative"):
    checker.grade(results, args.output, args.grading)
else:
    print("Warning: Relative grading is only supported in multifolder mode, skipping grading.")

end_time = time.perf_counter()
print(f"Total processing time: {end_time - start_time:.2f} seconds")