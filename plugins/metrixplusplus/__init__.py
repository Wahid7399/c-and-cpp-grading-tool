import glob
import itertools
from pathlib import Path
from config import settings
from plugins import BasePlugin
from collections import defaultdict
from .reporting import generate_html_report
import subprocess
import re
import os
import json
import requests
import zipfile
import io
import shutil
import math

class MetrixPlusPlusPlugin(BasePlugin):
    """
    Metrix++ Plugin for Code Quality Scorer
    """
    PATH = str(Path(__file__).parent.resolve() / "implementation" / "metrix++.py")

    def __init__(self):
        super(MetrixPlusPlusPlugin, self).__init__(
            name="Metrix++",
            report_name="Software Quality Report",
            description="Software Metrics - Cyclomatic Complexity, Halstead Metrics, Maintainability Index, and more",
            slug="metrixplusplus",
            version="1.8.1"
        )

    def initialize(self):
        if settings.plugins.metrixplusplus is None or settings.plugins.metrixplusplus.enabled is not True:
            return

        if os.path.exists(MetrixPlusPlusPlugin.PATH):
            print(f"✅ Metrix++ is installed")
            return

        url = "https://github.com/metrixplusplus/metrixplusplus/archive/refs/tags/1.8.1.zip"
        print(f"⌛ Metrix++ not found, downloading v1.8.1 it from {url}")
        response = requests.get(url)
        if response.status_code == 200:
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                z.extractall(path=str(Path(__file__).parent.resolve()))
            shutil.move(
                str(Path(__file__).parent.resolve() / "metrixplusplus-1.8.1"),
                str(Path(__file__).parent.resolve() / "implementation")
            )
            # Copy/replace missing files from modified_implementation
            print(f"⌛ Updating Metrix++ with custom modifications/plugins")
            implementation_folder = str(Path(__file__).parent.resolve() / "implementation")
            modified_path = str(Path(__file__).parent.resolve() / "modified_implementation")
            for root, dirs, files in os.walk(modified_path):
                for file in files:
                    src_file = os.path.join(root, file)
                    rel_path = os.path.relpath(src_file, modified_path)
                    dest_file = os.path.join(implementation_folder, rel_path)
                    dest_dir = os.path.dirname(dest_file)
                    if not os.path.exists(dest_dir):
                        os.makedirs(dest_dir, exist_ok=True)
                    shutil.copy2(src_file, dest_file)
        print(f"✅ Metrix++ is ready")
    
    def run(self, input_path, output_path):
        """
        Run the Metrix++ tool with the specified input and output paths.
        """
        if settings.plugins.metrixplusplus is None or settings.plugins.metrixplusplus.enabled is not True:
            return
        
        pwd = os.path.join(output_path, f".{self.slug}")
        if not os.path.exists(pwd):
            os.makedirs(pwd, exist_ok=True)

        # Collect .cpp files
        cpp_files = list(itertools.chain.from_iterable(
            glob.glob(os.path.join(input_path, "**", ext), recursive=True)
            for ext in ("*.c", "*.cpp")
        ))

        if not cpp_files:
            print(f"❌ No .cpp files found in {input_path}")
            return {}, {}, ""

        self.__collect(pwd, input_path)

        data = self.__view(pwd, input_path)

        raw = self.__parse_metrics(data)

        metrics = {}
        if "std.code.complexity:cyclomatic" in raw:
            metrics["cyclomatic"] = raw.get("std.code.complexity:cyclomatic", {}).get("stats", {}).get("Total", 0)
        if "std.code.lines:code" in raw:
            metrics["lines_of_code"] = raw.get("std.code.lines:code", {}).get("stats", {}).get("Total", 0)
        if "std.code.lines:comments" in raw:
            metrics["lines_of_comments"] = raw.get("std.code.lines:comments", {}).get("stats", {}).get("Total", 0)
        if "std.code.ratio:comments" in raw:
            metrics["comment_ratio"] = raw.get("std.code.ratio:comments", {}).get("stats", {}).get("Total", 0)
        if "std.code.halstead_base:_n1" in raw:
            metrics["halstead_n1"] = raw.get("std.code.halstead_base:_n1", {}).get("stats", {}).get("Total", 0)
        if "std.code.halstead_base:_n2" in raw:
            metrics["halstead_n2"] = raw.get("std.code.halstead_base:_n2", {}).get("stats", {}).get("Total", 0)
        if "std.code.halstead_base:N1" in raw:
            metrics["halstead_N1"] = raw.get("std.code.halstead_base:N1", {}).get("stats", {}).get("Total", 0)
        if "std.code.halstead_base:N2" in raw:
            metrics["halstead_N2"] = raw.get("std.code.halstead_base:N2", {}).get("stats", {}).get("Total", 0)
        if "std.code.halstead_adv:H_Volume" in raw:
            metrics["halstead_volume"] = raw.get("std.code.halstead_adv:H_Volume", {}).get("stats", {}).get("Total", 0)
        if "std.code.halstead_adv:H_Difficulty" in raw:
            metrics["halstead_difficulty"] = raw.get("std.code.halstead_adv:H_Difficulty", {}).get("stats", {}).get("Total", 0)
        if "std.code.halstead_adv:H_Effort" in raw:
            metrics["halstead_effort"] = raw.get("std.code.halstead_adv:H_Effort", {}).get("stats", {}).get("Total", 0)
        # if "std.code.mi:simple" in raw:
        #     metrics["maintainability_index"] = raw.get("std.code.mi:simple", {}).get("stats", {}).get("Total", 0)
        # Maintainability Index = MAX(0,(171 - 5.2 * ln(Halstead Volume) - 0.23 * (Cyclomatic Complexity) - 16.2 * ln(Lines of Code))*100 / 171)
        # Calculate manually
        if "halstead_volume" in metrics and "cyclomatic" in metrics and "lines_of_code" in metrics:
            V = metrics["halstead_volume"]
            C = metrics["cyclomatic"]
            L = metrics["lines_of_code"]
            if V > 0 and L > 0:
                MI = max(0, (171 - 5.2 * math.log(V) - 0.23 * C - 16.2 * math.log(L)) * 100 / 171)
                metrics["maintainability_index"] = MI
            else:
                metrics["maintainability_index"] = 0
        else:
            metrics["maintainability_index"] = 0

        results = {
            "metrics": metrics,
            "raw": raw
        }

        with open(os.path.join(pwd, "results.json"), "w") as metrics_file:
            json.dump(results, metrics_file, indent=4)
        return metrics, results, data

    def __collect(self, pwd: str, input_path: str):
        """
        Run Metrix++ collect with the specified metrics and input path
        """
        command = [
            settings.python_slug,
            MetrixPlusPlusPlugin.PATH,
            "collect",
            *[f"--{metric}" for metric in settings.plugins.metrixplusplus.metrics],
            f"--db-file={pwd}/metrixpp.db",
            "--",
            input_path,
        ]

        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True
            )
            combined = (result.stdout or "") + "\n" + (result.stderr or "")
            with open(os.path.join(pwd, "data.log"), "w") as f:
                f.write(combined)
            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, command)
        except subprocess.CalledProcessError as e:
            print(f"❌ Error running Metrix++: {e}")

    def __view(self, pwd: str, input_path: str):
        # Run Metrix++ view, store return value in output_path, process it regex
        command = [
            settings.python_slug,
            MetrixPlusPlusPlugin.PATH,
            "view",
            "--db-file",
            f"{pwd}/metrixpp.db",
            "--",
            input_path,
        ]
        try:
            # Run the command and capture the output
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True
            )
            combined = (result.stdout or "") + "\n" + (result.stderr or "")
            with open(os.path.join(pwd, f"data.log"), "a") as log_file:
                log_file.write(combined)
            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, command)
            return combined            
        except subprocess.CalledProcessError as e:
            print(f"❌ Error running Metrix++: {e}")

    def __parse_metrics(self, log_text: str):
        metrics = defaultdict(dict)
        current_metric = None
        
        # Regex patterns
        metric_header = re.compile(r"Overall metrics for '(.+?)' metric")
        kv_pattern = re.compile(r"\t(\w+)\s*:\s*([0-9.]+)")
        distribution_pattern = re.compile(
            r"([\d.]+)\s*:\s*([\d.]+)\s*:\s*([\d.]+)\s*:\s*(\d+)"
        )

        if not log_text:
            return {}

        for line in log_text.splitlines():
            # Match metric header
            header_match = metric_header.search(line)
            if header_match:
                current_metric = header_match.group(1)
                metrics[current_metric]["stats"] = {}
                metrics[current_metric]["distribution"] = []
                continue
            
            # Match key-value stats
            if current_metric:
                kv_match = kv_pattern.match(line)
                if kv_match:
                    key, value = kv_match.groups()
                    metrics[current_metric]["stats"][key] = float(value)
                    continue

                # Match distribution rows
                dist_match = distribution_pattern.search(line)
                if dist_match:
                    val, ratio, rsum, n_regions = dist_match.groups()
                    metrics[current_metric]["distribution"].append({
                        "Metric value": float(val),
                        "Ratio": float(ratio),
                        "R-sum": float(rsum),
                        "Regions": int(n_regions)
                    })

        return dict(metrics)

    def generate_report(self, input_path: str, output_path: str, results: dict, log: str) -> bool:
        """
        Generate a report from the collected metrics.
        """
        if not results:
            return "No results to report."

        html, summary = generate_html_report(results["metrics"])

        pwd = os.path.join(output_path, f".{self.slug}")
        with open(os.path.join(pwd, "report.html"), "w") as metrics_file:
            metrics_file.write(html)
        return summary

    def to_absolute(self, key, value, normalizer=None) -> float:
        if not normalizer or normalizer == 0:
            raise ValueError("Normalizer must be a non-zero value.")
        if key == "cyclomatic":
            return 100 - ((value / normalizer) * 100.0)
        elif key == "halstead_difficulty":
            return None
            # Guidance: D ≲ 10 easy, ~20 moderate, ≥30 hard.
            # 1/(1+exp(-(D-m)/s)) scaled to 0-100 where s is 6 and m is 20
            # m, s = 20, 6
            # return 100 - ((1 / (1 + math.exp(-(value - m) / s))) * 100.0)
        elif key == "halstead_effort":
            # Halstead effort is time in seconds E / 18 (seconds per mental discriminations)
            # Assuming 8h work day, 8*60*60*18 = 518400            
            # Poisson
            return 100 - ((1 - math.exp(-value / 518400.0)) * 100.0)
        elif key == "halstead_volume":
            # Halstead volume is size of implementation
            # Halstead’s defect estimate: bugs ≈ V / 3000.
            # Map to risk via a Poisson “at least one defect” probability
            return 100 - ((1 - math.exp(-value / 3000.0)) * 100.0)
        elif key == "lines_of_comments":
            return (value / normalizer) * 100.0
        else:
            return value

    def get_weights(self) -> dict:
        return {
            "cyclomatic": {"direction": -1, "weight": 1.0},
            "halstead_difficulty": {"direction": -1, "weight": 1.0},
            "halstead_effort": {"direction": -1, "weight": 1.0},
            "halstead_volume": {"direction": -1, "weight": 1.0},
            "maintainability_index": {"direction": +1, "weight": 1.0},
            "comment_ratio": {"direction": +1, "weight": 0},
            "halstead_n1": {"direction": -1, "weight": 0},
            "halstead_n2": {"direction": -1, "weight": 0},
            "halstead_N1": {"direction": -1, "weight": 0},
            "halstead_N2": {"direction": -1, "weight": 0},
            "lines_of_comments": {"direction": +1, "weight": 1.0},
            "lines_of_code": {"direction": +1, "weight": 0},
        }
