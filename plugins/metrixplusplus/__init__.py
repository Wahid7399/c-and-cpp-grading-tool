import glob
from pathlib import Path
from config import settings
from plugins import BasePlugin
from collections import defaultdict
import subprocess
import re
import os
import json
import requests
import zipfile
import io
import shutil

class MetrixPlusPlusPlugin(BasePlugin):
    """
    Metrix++ Plugin for Code Quality Scorer
    """
    PATH = str(Path(__file__).parent.resolve() / "implementation" / "metrix++.py")

    def __init__(self):
        super(MetrixPlusPlusPlugin, self).__init__(
            name="Metrix++",
            description="Integrate Metrix++ metrics into Code Quality Scorer",
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
        cpp_files = glob.glob(os.path.join(input_path, "**", "*.cpp"), recursive=True)

        if not cpp_files:
            print(f"❌ No .cpp files found in {input_path}")
            return {}

        self.__collect(pwd, input_path)

        data = self.__view(pwd)

        raw = self.__parse_metrics(data)

        metrices = {}
        if "std.code.complexity:cyclomatic" in raw:
            metrices["cyclomatic"] = raw["std.code.complexity:cyclomatic"]["stats"]["Total"]
        if "std.code.lines:code" in raw:
            metrices["lines_of_code"] = raw["std.code.lines:code"]["stats"]["Total"]
        if "std.code.lines:comments" in raw:
            metrices["lines_of_comments"] = raw["std.code.lines:comments"]["stats"]["Total"]
        if "std.code.ratio:comments" in raw:
            metrices["comment_ratio"] = raw["std.code.ratio:comments"]["stats"]["Total"]
        if "std.code.halstead_base:_n1" in raw:
            metrices["halstead_n1"] = raw["std.code.halstead_base:_n1"]["stats"]["Total"]
        if "std.code.halstead_base:_n2" in raw:
            metrices["halstead_n2"] = raw["std.code.halstead_base:_n2"]["stats"]["Total"]
        if "std.code.halstead_base:N1" in raw:
            metrices["halstead_N1"] = raw["std.code.halstead_base:N1"]["stats"]["Total"]
        if "std.code.halstead_base:N2" in raw:
            metrices["halstead_N2"] = raw["std.code.halstead_base:N2"]["stats"]["Total"]
        if "std.code.halstead_adv:H_Volume" in raw:
            metrices["halstead_volume"] = raw["std.code.halstead_adv:H_Volume"]["stats"]["Total"]
        if "std.code.halstead_adv:H_Difficulty" in raw:
            metrices["halstead_difficulty"] = raw["std.code.halstead_adv:H_Difficulty"]["stats"]["Total"]
        if "std.code.halstead_adv:H_Effort" in raw:
            metrices["halstead_effort"] = raw["std.code.halstead_adv:H_Effort"]["stats"]["Total"]
        if "std.code.mi:simple" in raw:
            metrices["maintainability_index"] = raw["std.code.mi:simple"]["stats"]["Total"]
        results = {
            "metrices": metrices,
            "raw_metrices": raw
        }
        with open(os.path.join(pwd, "results.json"), "w") as metrics_file:
            json.dump(results, metrics_file, indent=4)
        return metrices

    def __collect(self, pwd: str, input_path: str):
        """
        Run Metrix++ collect with the specified metrics and input path
        """
        command = [
            settings.python_slug,
            MetrixPlusPlusPlugin.PATH,
            "collect",
            *[f"--{metric}" for metric in settings.plugins.metrixplusplus.metrices],
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

    def __view(self, pwd: str):
        # Run Metrix++ view, store return value in output_path, process it regex
        command = [
            settings.python_slug,
            MetrixPlusPlusPlugin.PATH,
            "view",
            "--db-file",
            f"{pwd}/metrixpp.db",
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