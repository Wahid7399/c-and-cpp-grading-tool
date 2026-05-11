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

        print("✅ Valgrind is ready")

    def _run_single(self, input_path: str, pwd: str, cfg: object) -> Tuple[dict, dict, str]:
        """
        Compile and run valgrind for a single config entry.
        cfg can be the top-level valgrind settings object or an item from configs[].
        Returns (metrics, raw_results, log).
        """
        explicit_main = getattr(cfg, "main_file", None)
        driver_dst = None
        if explicit_main:
            driver_dst = os.path.join(input_path, "_valgrind_main_driver.c")
            shutil.copy(explicit_main, driver_dst)
            compile_src = "_valgrind_main_driver.c"
        else:
            found = find_entry_point(input_path)
            if found is None:
                return {}, {}, "No main function found and no main_file configured."
            compile_src = os.path.relpath(found, input_path)

        extra = " ".join(getattr(cfg, "extra_args", None) or [])
        include_flags = " ".join(
            f"-I{d}" for d in (getattr(cfg, "include_dirs", None) or [])
        )
        compiler = getattr(cfg, "compiler", None) or "gcc"
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
            return {}, {}, f"COMPILATION FAILED:\n{compile_out}"

        run_cmd = f"valgrind --leak-check=full --error-exitcode=1 ./valgrind/a.out"
        try:
            res = docker.run(ValgrindPlugin.DOCKER_IMAGE, input_path, run_cmd, timeout=60)
        except TimeoutExpired as e:
            return {}, {}, f"Valgrind execution timed out: {e}"

        shutil.rmtree(Path(input_path) / "valgrind", ignore_errors=True)

        results = parse_valgrind_stdout(res.stderr or "")
        metrics = {
            "valgrind_errors": results.get("error_count", 0),
            "valgrind_leaks": (results.get("leak_summary") or {}).get("totals", {}).get("bytes_lost", 0),
        }
        log = (res.stdout or "") + (res.stderr or "")
        return metrics, results, log

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

        # Build list of configs to run.
        # If `configs` is set, each entry overrides the top-level defaults.
        # Otherwise fall back to a single run using top-level settings.
        top = settings.plugins.valgrind
        raw_configs = getattr(top, "configs", None)
        if raw_configs:
            # Each item in configs[] is a Settings object; fill missing fields
            # from the top-level valgrind settings so entries can be sparse.
            cfg_list = raw_configs if isinstance(raw_configs, list) else list(raw_configs)
        else:
            cfg_list = [top]

        merged_errors = 0
        merged_leaks = 0
        all_raw = []
        all_logs = []

        for i, cfg in enumerate(cfg_list):
            # cfg may be a plain dict (from JSON list) or a Settings object
            def _get(obj, key):
                if isinstance(obj, dict):
                    return obj.get(key)
                return getattr(obj, key, None)

            # Sparse cfg: fall back to top-level for missing keys
            class _Merged:
                pass
            merged_cfg = _Merged()
            for attr in ("main_file", "compiler", "extra_args", "include_dirs"):
                val = _get(cfg, attr)
                if val is None:
                    val = getattr(top, attr, None)
                setattr(merged_cfg, attr, val)

            metrics, raw, log = self._run_single(input_path, pwd, merged_cfg)
            all_raw.append(raw)
            all_logs.append(f"=== config {i} ===\n{log}")

            if log.startswith("COMPILATION FAILED"):
                with open(os.path.join(pwd, f"data_{i}.log"), "w", encoding="utf-8") as f:
                    f.write(log)
            else:
                with open(os.path.join(pwd, f"data_{i}.log"), "w", encoding="utf-8") as f:
                    f.write(log)

            merged_errors += metrics.get("valgrind_errors", 0)
            merged_leaks += metrics.get("valgrind_leaks", 0)

        # Write combined log for backward compat
        with open(os.path.join(pwd, "data.log"), "w", encoding="utf-8") as f:
            f.write("\n\n".join(all_logs))

        final_metrics = {
            "valgrind_errors": merged_errors,
            "valgrind_leaks": merged_leaks,
        }
        detailed = {
            "metrics": final_metrics,
            "raw": all_raw if len(all_raw) > 1 else (all_raw[0] if all_raw else {}),
        }

        import json
        with open(os.path.join(pwd, "results.json"), "w", encoding="utf-8") as f:
            json.dump(detailed, f, indent=4)

        return final_metrics, detailed, "\n\n".join(all_logs)

    def _merge_raw(self, raw) -> dict:
        """Merge one or more raw parse results into a single dict for reporting."""
        if isinstance(raw, list):
            merged = {"error_count": 0, "errors": [], "signals": [], "crashed": False, "heap_summary": None, "leak_summary": None, "meta": {}}
            for r in raw:
                if not r:
                    continue
                merged["error_count"] += r.get("error_count", 0)
                merged["errors"].extend(r.get("errors", []))
                merged["signals"].extend(r.get("signals", []))
                if r.get("crashed"):
                    merged["crashed"] = True
                if r.get("leak_summary"):
                    ls = r["leak_summary"]
                    if merged["leak_summary"] is None:
                        import copy
                        merged["leak_summary"] = copy.deepcopy(ls)
                    else:
                        t = merged["leak_summary"].setdefault("totals", {})
                        src = ls.get("totals", {})
                        t["bytes_lost"] = t.get("bytes_lost", 0) + src.get("bytes_lost", 0)
                        t["blocks_lost"] = t.get("blocks_lost", 0) + src.get("blocks_lost", 0)
                if not merged["meta"]:
                    merged["meta"] = r.get("meta", {})
            return merged
        return raw or {"error_count": 0, "errors": [], "signals": [], "crashed": False, "heap_summary": None, "leak_summary": None, "meta": {}}

    def generate_report(self, input_path: str, output_path: str, results: dict, log: str) -> None:
        """
        Generate a report from the collected metrics.
        """
        if not results:
            return "No results to report."

        # results may be the wrapper {"metrics": ..., "raw": ...} or the raw parse dict directly
        raw = results.get("raw", results) if isinstance(results, dict) and "raw" in results else results
        merged = self._merge_raw(raw)

        html, summary = generate_html_report(merged)

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