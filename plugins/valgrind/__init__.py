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

        # Determine source file to compile
        explicit_main = getattr(settings.plugins.valgrind, "main_file", None)
        if explicit_main:
            # Copy provided driver into student dir so relative includes resolve
            driver_dst = os.path.join(input_path, "_valgrind_main_driver.c")
            shutil.copy(explicit_main, driver_dst)
            compile_src = "_valgrind_main_driver.c"
        else:
            found = find_entry_point(input_path)
            if found is None:
                return {}, {}, "No main function found and no main_file configured."
            compile_src = os.path.relpath(found, input_path)
            driver_dst = None

        extra = " ".join(settings.plugins.valgrind.extra_args or [])
        include_flags = " ".join(
            f"-I{d}" for d in (settings.plugins.valgrind.include_dirs or [])
        )
        compiler = getattr(settings.plugins.valgrind, "compiler", None) or "gcc"
        compile_cmd = f"mkdir -p valgrind && {compiler} {extra} {include_flags} {compile_src} -o valgrind/a.out"
        try:
            comp = docker.run(ValgrindPlugin.DOCKER_IMAGE, input_path, compile_cmd, timeout=60)
        except TimeoutExpired as e:
            if driver_dst:
                os.remove(driver_dst)
            return {}, {}, f"Valgrind compilation timed out: {e}"
        finally:
            if driver_dst and os.path.exists(driver_dst):
                os.remove(driver_dst)
        if comp.returncode != 0:
            compile_out = (comp.stdout or "") + "\n" + (comp.stderr or "")
            with open(os.path.join(pwd, "data.log"), "w", encoding="utf-8") as f:
                f.write("COMPILATION FAILED:\n" + compile_out)
            return {}, {}, f"Compilation failed:\n{compile_out}"

        # prog_args = " ".join(shlex.quote(a) for a in (settings.plugins.valgrind.args or []))
        run_cmd = f"valgrind --leak-check=full --error-exitcode=1 ./valgrind/a.out"
        try:
            res = docker.run(ValgrindPlugin.DOCKER_IMAGE, input_path, run_cmd, timeout=60)
        except TimeoutExpired as e:
            return {}, {}, f"Valgrind execution timed out: {e}"

        with open(os.path.join(pwd, "data.log"), "w", encoding='utf-8') as f:
            f.write(res.stdout or "")
            f.write(res.stderr or "")

        shutil.rmtree(Path(input_path) / "valgrind", ignore_errors=True)

        results = parse_valgrind_stdout(res.stderr or "")

        metrics = {
            "valgrind_errors": results.get("error_summary", {}).get("errors", 0),
            "valgrind_leaks": (results.get("leak_summary") or {}).get("definitely lost", 0),
        }

        detailed = {
            "metrics": metrics,
            "raw": results,
        }

        with open(os.path.join(pwd, "results.json"), "w", encoding='utf-8') as f:
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
        with open(os.path.join(pwd, "report.html"), "w", encoding='utf-8') as metrics_file:
            metrics_file.write(html)
        return summary

    def to_absolute(self, key, value, normalizer=None) -> float:
        if not normalizer or normalizer == 0:
            raise ValueError("Normalizer must be a non-zero value.")
        return 100 - (value / normalizer) * 100.0

    def get_weights(self) -> dict:
        return {
            "valgrind_errors": {"direction": -1, "weight": 1.0},
            "valgrind_leaks": {"direction": -1, "weight": 1.0},
        }