import itertools
from typing import Tuple
from config import settings
from plugins import BasePlugin
from tools.utils import shell_run
from glob import glob
from .reporting import generate_html_report
import os
import subprocess
import xml.etree.ElementTree as ET
import platform
import json

class CppcheckPlugin(BasePlugin):
    """
    Cppcheck Plugin for Code Quality Scorer
    """

    def __init__(self):
        super(CppcheckPlugin, self).__init__(
            name="Cppcheck",
            report_name="Style & Security Report",
            description="Static Analysis - Code style, Security, Correctness, Performance, and more",
            slug="cppcheck",
            version="20.1.0"
        )

    def initialize(self):
        if settings.plugins.cppcheck is None or settings.plugins.cppcheck.enabled is not True:
            return

        # Check if cppcheck is installed
        try:
            subprocess.run(
                [settings.plugins.cppcheck.command, "--version"],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            print("✅ Cppcheck is installed")
            return
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Cppcheck is not installed, attempting an auto-install.")

        if platform.system() == "Darwin":
            shell_run("brew install cppcheck")
            print("✅ Cppcheck has been installed via Homebrew")
        elif platform.system() == "Linux":
            shell_run("sudo apt-get install -y cppcheck")
            print("✅ Cppcheck has been installed via apt-get")
        elif platform.system() == "Windows":
            print("❌ Cppcheck auto-installation not supported on Windows. Please install it manually from https://cppcheck.sourceforge.io/")
        else:
            print("❌ Cppcheck is not installed and auto-install is not supported. Please install it using your system's package manager.")

    def __test_code(self, pwd: str, input_path: str, output_path: str):
        """
        Run Cppcheck on the given input path and store XML results in pwd.
        """
        command = [
            "cppcheck",
            "--enable=all",
            "--inconclusive",
            "--xml",
            f"--output-file={output_path}",
            "--suppress=missingIncludeSystem",
            "--suppress=shadowVariable",
            "--suppress=passedByValue",
            input_path,
        ]

        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True
            )
            # Log stdout+stderr for debugging
            with open(os.path.join(pwd, "data.log"), "w") as f:
                f.write((result.stdout or "") + "\n" + (result.stderr or ""))
            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, command)
        except subprocess.CalledProcessError as e:
            print(f"❌ Error running Cppcheck: {e}")


    def run(self, input_path, output_path) -> Tuple[dict, dict, str]:
        """
        Run the Cppcheck analysis.

        Args:
            input_path (str): Path to the input directory containing .cpp files.
            output_path (str): Path to the output directory where results will be stored.

        Returns:
            Tuple[dict, dict, str]: A tuple containing:
                - Simplified metrics result
                - Detailed output
                - Logs
        """
        if settings.plugins.cppcheck is None or settings.plugins.cppcheck.enabled is not True:
            return {}, {}, ""

        pwd = os.path.join(output_path, f".{self.slug}")
        os.makedirs(pwd, exist_ok=True)

        cpp_files = list(itertools.chain.from_iterable(
            glob.glob(os.path.join(input_path, "**", ext), recursive=True)
            for ext in ("*.c", "*.cpp")
        ))
        if not cpp_files:
            print(f"❌ No .cpp files found in {input_path}")
            return {}, {}, ""
        
        output = os.path.join(pwd, "cppcheck.xml")
        self.__test_code(pwd, input_path, output)

        issues = []
        try:
            tree = ET.parse(output)
            root = tree.getroot()
            for error in root.findall(".//error"):
                if error.attrib.get("severity", "") == "information":
                    continue
                issues.append({
                    "name": error.attrib.get("id", ""),
                    "severity": error.attrib.get("severity", ""),
                    "message": error.attrib.get("msg", ""),
                    "location": error.find("location").attrib if error.find("location") is not None else {},
                })
        except Exception as e:
            print(f"❌ Failed to parse cppcheck.xml: {e}")

        metrics = {
            "cppcheck_style_violations": 0,
            "cppcheck_performance_violations": 0,
            "cppcheck_error_violations": 0,
        }
        for issue in issues:
            sev = issue.get("severity", "unknown")
            # convert to snake_case from camelCase
            # sev = ''.join(['_' + c.lower() if c.isupper() else c for c in sev])
            sev = "cppcheck_" + sev + "_violations"
            metrics[sev] = metrics.get(sev, 0) + 1
        results = {"metrics": metrics, "raw": issues}

        with open(os.path.join(pwd, "results.json"), "w") as f:
            json.dump(results, f, indent=4)

        output_xml = ""
        try:
            with open(output, "r") as f:
                output_xml = f.read()
        except Exception as e:
            print(f"❌ Failed to read cppcheck.xml: {e}")

        return metrics, results, output_xml

    def generate_report(self, input_path: str, output_path: str, results: dict, log: str) -> bool:
        """
        Generate a report from the collected metrics.
        """
        if not results:
            return "No results to report."

        html = generate_html_report(results)

        pwd = os.path.join(output_path, f".{self.slug}")
        with open(os.path.join(pwd, "report.html"), "w") as metrics_file:
            metrics_file.write(html)
        return {"summary": "No Summary Available"}

    def get_weights(self) -> dict:
        return {
            "cppcheck_error_violations": {"direction": -1, "weight": 1.0, "normalized": False},
            "cppcheck_performance_violations": {"direction": -1, "weight": 1.0, "normalized": False},
            "cppcheck_style_violations": {"direction": -1, "weight": 1.0, "normalized": False},
        }