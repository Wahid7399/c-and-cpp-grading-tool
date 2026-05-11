from pathlib import Path
from typing import Tuple
from config import settings
from plugins import TestPlugin
from tools.utils import create_single_entry_point, remove_single_entry_point
from tools import docker
from .reporting import generate_html_report
from .util import run_individual_tests
from subprocess import TimeoutExpired
import os
import subprocess
import json
import re
import shutil
import sys
import shlex
import requests

class DoctestPlugin(TestPlugin):
    """
    Doctest Plugin for Code Quality Scorer
    """
    DOCKER_IMAGE = "lumsdocker/cs200env:x86_64"
    TEST_SETUP_TEMPLATE = ""
    DOCTEST_HEADER_PATH = str(Path(__file__).parent.resolve() / "doctest.h")

    def __init__(self):
        super(DoctestPlugin, self).__init__(
            name="Doctest",
            report_name="Test Results",
            description="Functionality Tests - Code test with actual data using predefined test cases",
            slug="doctest",
            version="2.4.12"
        )
        self.test_file_imports = ""
        self.test_file_content = ""
        self.has_tests = False

    def initialize(self):
        if settings.plugins.doctest is None or settings.plugins.doctest.enabled is not True:
            return

        template_path = os.path.join(Path(__file__).parent.resolve(), "tests_setup_template.h")
        if not os.path.exists(DoctestPlugin.DOCTEST_HEADER_PATH):
            url = "https://github.com/doctest/doctest/releases/download/v2.4.12/doctest.h"
            print(f"⌛ Doctest not found, downloading v2.4.12 it from {url}")
            response = requests.get(url)
            if response.status_code == 200:
                with open(DoctestPlugin.DOCTEST_HEADER_PATH, 'wb') as f:
                    f.write(response.content)
            else:
                print(f"❌ Doctest - Failed to download doctest.h from {url}")
                sys.exit(1)

        if os.path.exists(template_path):
            with open(template_path, 'r') as f:
                DoctestPlugin.TEST_SETUP_TEMPLATE = f.read()
        else:
            print(f"❌ Doctest - test_setup_template.h not found")
            sys.exit(1)

        # Check if docker image is present
        try:
            docker.ensure_docker()
            if not docker.image_exists(DoctestPlugin.DOCKER_IMAGE):
                print(f"❌ Docker image '{DoctestPlugin.DOCKER_IMAGE}' not found. Pulling `{DoctestPlugin.DOCKER_IMAGE}`")
                docker.pull_image(DoctestPlugin.DOCKER_IMAGE)
            if not docker.image_exists(DoctestPlugin.DOCKER_IMAGE):
                raise Exception("Docker image not found after pull, please check...")
        except Exception as e:
            print(f"❌ {e}")
            sys.exit(1)
        print("✅ Doctest is ready")

    def setup_tests(self, test_files) -> bool:
        """
        Setup the test plugin with the provided test file(s).
        Accepts a single path string or a list of path strings.
        """
        if isinstance(test_files, str):
            test_files = [test_files]
        if not test_files:
            return True

        self.test_file_data = []
        self.scoring = {}

        for test_file in test_files:
            if not os.path.exists(test_file):
                print(f"❌ Doctest - Test file {test_file} does not exist.")
                return False
            with open(test_file, 'r') as f:
                content = f.read()
            includes = []
            body = []
            for line in content.splitlines():
                if line.strip().startswith("#include"):
                    includes.append(line)
                else:
                    body.append(line)
            case_count = len(self.scoring)
            file_scoring = {}
            for line in body:
                if 'TEST_CASE("' not in line and 'TEST_CASE (' not in line:
                    continue
                if "Score:" not in line:
                    print(f"❌ Doctest - Each TEST_CASE must have a Score. Error in line: {line}")
                    return False
                parts = line.split("Score:")
                if len(parts) != 2:
                    print(f"❌ Doctest - Invalid test case format in line: {line}")
                    return False
                score_part = parts[1].rstrip("{").strip().rstrip('")').strip()
                try:
                    score = int(score_part)
                    file_scoring[case_count + 1] = score
                except ValueError:
                    print(f"❌ Doctest - Invalid score value in line: {line}")
                    return False
                if not line.startswith(f"TEST_CASE(\"#{case_count + 1} ") and not line.startswith(f"TEST_CASE (\"#{case_count + 1} "):
                    print(f"❌ Doctest - Test case should start with a #{case_count + 1}. Error in line: {line}")
                    return False
                case_count += 1
            if not "\n".join(body).strip():
                print(f"❌ Doctest - Test file {test_file} is empty.")
                return False
            is_standalone = 'DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN' in content
            self.test_file_data.append({
                'original_path': test_file,
                'is_standalone': is_standalone,
                'imports': "\n".join(includes),
                'content': "\n".join(body),
                'scoring': file_scoring,
            })
            self.scoring.update(file_scoring)

        self.has_tests = bool(self.test_file_data)
        return True

    def _execute_tests(self, pwd: str, input_path: str, file_data: dict) -> Tuple[bool, str, str]:
        # Place doctest_main.cpp one level below input_path so that relative
        # includes in the test file (e.g. "../src/file.c") resolve correctly
        # against input_path.
        subdir = "_doctest_tmp"
        subdir_path = os.path.join(input_path, subdir)
        os.makedirs(subdir_path, exist_ok=True)

        prepared_main_path = os.path.join(subdir_path, "doctest_main.cpp")
        doctest_header_dst = os.path.join(subdir_path, "doctest.h")
        shutil.copy(DoctestPlugin.DOCTEST_HEADER_PATH, doctest_header_dst)

        existing_main = None
        main_file_path = None

        if file_data['is_standalone']:
            # Self-contained test file: use original content verbatim so the
            # #define / #include ordering is preserved exactly as written.
            with open(file_data['original_path'], 'r') as f:
                prepared_main = f.read()
            with open(prepared_main_path, 'w') as f:
                f.write(prepared_main)
        else:
            # Template approach: student code is injected via the entry-point.
            if os.path.exists(os.path.join(input_path, "main.cpp")) and os.path.isfile(os.path.join(input_path, "main.cpp")):
                with open(os.path.join(input_path, "main.cpp"), 'r') as f:
                    existing_main = f.read()

            main_file_path = create_single_entry_point(input_path, entry_point="main.cpp")
            if main_file_path is None:
                shutil.rmtree(subdir_path, ignore_errors=True)
                return False, "No main function found", "No main function found"

            # Relative path from the subdirectory to main.cpp in input_path
            template_repl = os.path.relpath(main_file_path, subdir_path).replace("\\", "/")
            prepared_main = (
                file_data['imports'] + "\n" +
                DoctestPlugin.TEST_SETUP_TEMPLATE.replace("[DOCTEST_MAIN_FILE_PATH]", template_repl) + "\n" +
                file_data['content']
            )
            with open(prepared_main_path, 'w') as f:
                f.write(prepared_main)

        # Compile the code with doctest
        compile_log_name = "compile_" + os.path.splitext(os.path.basename(file_data['original_path']))[0] + ".log"
        try:
            extra = " ".join(shlex.quote(a) for a in (settings.plugins.doctest.extra_args or []))
            include_flags = " ".join(
                f"-I{shlex.quote(d)}"
                for d in (settings.plugins.doctest.include_dirs or [])
            )
            compile_cmd = f"set -e; mkdir -p doctest; g++ {extra} {include_flags} {subdir}/doctest_main.cpp -o doctest/doctest_executable.out"
            result = docker.run(DoctestPlugin.DOCKER_IMAGE, input_path, compile_cmd, 300)
            combined = (result.stdout or "") + "\n" + (result.stderr or "")
            with open(os.path.join(pwd, compile_log_name), "w", encoding='utf-8') as f:
                f.write(combined)
            if result.returncode != 0:
                return False, combined, combined
        except TimeoutExpired as e:
            print(f"❌ Doctest - Compilation timed out.")
            print(e)
            return False, "Compilation timed out", "Compilation timed out"
        finally:
            shutil.rmtree(subdir_path, ignore_errors=True)
            if main_file_path is not None:
                remove_single_entry_point(input_path, entry_point="main.cpp")
            if existing_main is not None:
                with open(os.path.join(input_path, "main.cpp"), 'w') as f:
                    f.write(existing_main)

        timeout = getattr(settings.plugins.doctest, 'per_test_timeout', 15)
        return run_individual_tests(
            docker,
            DoctestPlugin.DOCKER_IMAGE,
            input_path,
            per_test_timeout=timeout,
            scoring_map=self.scoring,
        )

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
        if settings.plugins.doctest is None or settings.plugins.doctest.enabled is not True:
            return {}, {}, ""

        if not self.has_tests or not self.scoring:
            return {}, {}, "No tests configured."

        pwd = os.path.join(output_path, f".{self.slug}")
        os.makedirs(pwd, exist_ok=True)

        merged_scores = {}
        merged_failures = []
        merged_passed = 0
        merged_failed_count = 0
        last_data = {}
        all_logs = []

        for file_data in self.test_file_data:
            success, data, log_text = self._execute_tests(pwd, input_path, file_data)
            all_logs.append(f"=== {os.path.basename(file_data['original_path'])} ===")
            all_logs.append(log_text or "")
            if success:
                file_summary = data.get("summary", {})
                file_scores = data.get("scores", {})
                merged_scores.update(file_scores)
                merged_passed += file_summary.get("passed", 0)
                merged_failed_count += file_summary.get("failed", 0)
                merged_failures.extend(file_summary.get("failures", []))
                last_data = data
            else:
                for case_num, score in file_data['scoring'].items():
                    merged_scores[f"test_case_{case_num}"] = 0
                    merged_failures.append({
                        "number": case_num,
                        "name": f"Test Case #{case_num}",
                        "score": score,
                        "failed_check": "Compilation failed",
                        "failed_value": str(data) if isinstance(data, str) else "Compilation failed"
                    })
                    merged_failed_count += 1

        # Fill any missing score keys with 0
        for case_num in self.scoring:
            key = f"test_case_{case_num}"
            if key not in merged_scores:
                merged_scores[key] = 0

        summary = {
            "total_cases": len(self.scoring),
            "passed": merged_passed,
            "failed": merged_failed_count,
            "total_score": sum(self.scoring.values()),
            "obtained_score": sum(merged_scores.values()),
            "failures": sorted(merged_failures, key=lambda x: x["number"])
        }

        with open(os.path.join(pwd, "results.json"), "w", encoding='utf-8') as f:
            json.dump({"tests": merged_scores, "raw": summary}, f, indent=4)

        with open(os.path.join(pwd, "data.log"), "w", encoding='utf-8') as f:
            f.write("\n".join(all_logs))

        return merged_scores, summary, last_data

    def generate_report(self, input_path: str, output_path: str, results: dict, log: str) -> None:
        if not self.has_tests:
            return ""

        if not results:
            raise ValueError("No results, should not be a thing!")

        html, summary = generate_html_report(results)

        pwd = os.path.join(output_path, f".{self.slug}")
        with open(os.path.join(pwd, "report.html"), "w", encoding='utf-8') as metrics_file:
            metrics_file.write(html)
        return summary

    def to_absolute(self, key, value, normalizer=None) -> float:
        return value

    def get_weights(self) -> dict:
        if not self.has_tests or not self.scoring:
            return {}
        weights = {}
        for key, value in self.scoring.items():
            weights[f"test_case_{key}"] = {"direction": 1, "weight": 1}
        return weights