from pathlib import Path
from subprocess import TimeoutExpired
from tools import docker
from tools.utils import find_entry_point
from typing import Tuple
from config import settings
from plugins import BasePlugin
from .helpers import parse_valgrind_stdout
from .reporting import generate_html_report
import sys
import os
import shutil

class ValgrindPlugin(BasePlugin):
    """
    Valgrind Plugin for Code Quality Scorer
    """
    DOCKER_IMAGE = "lumsdocker/cs200env:x86_64"

    def __init__(self):
        super(ValgrindPlugin, self).__init__(
            name="Valgrind",
            report_name="Memory Issues Report",
            description="Report on memory leaks and memory management issues",
            slug="valgrind",
            version="20.1.0"
        )

    def initialize(self):
        if settings.plugins.valgrind is None or settings.plugins.valgrind.enabled is not True:
            return

        # Check if valgrind docker image is available
        try:
            docker.ensure_docker()
            if not docker.image_exists(ValgrindPlugin.DOCKER_IMAGE):
                print(f"❌ Docker image '{ValgrindPlugin.DOCKER_IMAGE}' not found. Pulling `{ValgrindPlugin.DOCKER_IMAGE}`")
                docker.pull_image(ValgrindPlugin.DOCKER_IMAGE)
            if not docker.image_exists(ValgrindPlugin.DOCKER_IMAGE):
                raise Exception("Docker image not found after pull, please check...")
        except Exception as e:
            print(f"❌ {e}")
            sys.exit(1)

        print("✅ Valgrind is installed")

    def run(self, input_path, output_path) -> Tuple[dict, dict, str]:
        """
        Run the Valgrind analysis.

        Args:
            input_path (str): Path to the input directory containing .cpp files.
            output_path (str): Path to the output directory where results will be stored.

        Returns:
            Tuple[dict, dict, str]: A tuple containing:
                - Simplified metrics result
                - Detailed output
                - Logs
        """
        if settings.plugins.valgrind is None or settings.plugins.valgrind.enabled is not True:
            return {}, {}, ""
        
        pwd = os.path.join(output_path, f".{self.slug}")
        os.makedirs(pwd, exist_ok=True)

        main_file_path = find_entry_point(input_path)
        if main_file_path is None:
            return {}, {}, "No main function found"
        main_file_path = os.path.relpath(main_file_path, input_path)

        compile_cmd = f"mkdir -p valgrind && g++ -std=c++11 {main_file_path} -o valgrind/a.out"
        try:
            comp = docker.run(ValgrindPlugin.DOCKER_IMAGE, input_path, compile_cmd, timeout=60)
        except TimeoutExpired as e:
            return {}, {}, f"Valgrind execution timed out: {e}"
        if comp.returncode != 0:
            return {}, {}, "Compilation failed."

        # prog_args = " ".join(shlex.quote(a) for a in (settings.plugins.valgrind.args or []))
        run_cmd = f"valgrind --leak-check=full --error-exitcode=1 valgrind/a.out"
        try:
            res = docker.run(ValgrindPlugin.DOCKER_IMAGE, input_path, run_cmd, timeout=60)
        except TimeoutExpired as e:
            return {}, {}, f"Valgrind execution timed out: {e}"

        with open(os.path.join(pwd, "data.log"), "w") as f:
            f.write(res.stdout)
            f.write(res.stderr)

        shutil.rmtree(Path(input_path) / "valgrind", ignore_errors=True)

        results = parse_valgrind_stdout(res.stderr)

        metrics = {
            "valgrind_errors": results.get("error_summary", {}).get("errors", 0),
            "valgrind_leaks": (results.get("leak_summary") or {}).get("definitely lost", 0),
        }

        detailed = {
            "metrics": metrics,
            "raw": results,
        }

        with open(os.path.join(pwd, "results.json"), "w") as f:
            import json
            json.dump(detailed, f, indent=4)

        return metrics, results, "Valgrind integration is not yet implemented."

    def generate_report(self, input_path: str, output_path: str, results: dict, log: str) -> None:
        """
        Generate a report from the collected metrics.
        """
        if not results:
            return "No results to report."

        html, summary = generate_html_report(results)

        pwd = os.path.join(output_path, f".{self.slug}")
        with open(os.path.join(pwd, "report.html"), "w") as metrics_file:
            metrics_file.write(html)
        return summary

    def get_weights(self) -> dict:
        return {
            "valgrind_errors": {"direction": -1, "weight": 1.0, "normalized": False},
            "valgrind_leaks": {"direction": -1, "weight": 1.0, "normalized": False},
        }