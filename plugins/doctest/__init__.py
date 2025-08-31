from pathlib import Path
from typing import Tuple
from config import settings
from plugins import TestPlugin
from tools.utils import find_entry_point
from tools import docker
from .reporting import generate_html_report
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
        print("✅ Doctest is installed")

    def setup_tests(self, test_file: str) -> bool:
        """
        Setup the test plugin with the provided test file.
        This method should be overridden by test plugins to load and prepare tests.
        """
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
            # If a test case contains contains TEST_CASE(" and doesnt end with Score: X"), error out
            # verify int value after "Score: "
            case_count = 0
            self.scoring = {}
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
                    self.scoring[case_count + 1] = score
                except ValueError:
                    print(f"❌ Doctest - Invalid score value in line: {line}")
                    return False
                # test case should start with a #number
                if not line.startswith(f"TEST_CASE(\"#{case_count + 1} ") and not line.startswith(f"TEST_CASE (\"#{case_count + 1} "):
                    print(f"❌ Doctest - Test case should start with a #{case_count + 1}. Error in line: {line}")
                    return False
                case_count += 1
            self.test_file_imports = "\n".join(includes)
            self.test_file_content = "\n".join(body)
        if not self.test_file_content:
            print(f"❌ Doctest - Test file {test_file} is empty.")
            return False
        self.has_tests = True
        return True

    def _execute_tests(self, pwd: str, input_path: str) -> Tuple[bool, str]:
        # Go through the input files, find one with a main func
        main_file_path = find_entry_point(input_path)
        if main_file_path is None:
            return False, "No main function found"

        # Prepare a main for doctest
        template_repl = os.path.relpath(main_file_path, input_path).replace("\\", "/")
        prepared_main = (
            self.test_file_imports + "\n" +
            DoctestPlugin.TEST_SETUP_TEMPLATE.replace("[DOCTEST_MAIN_FILE_PATH]", template_repl) + "\n" +
            self.test_file_content
        )

        # copy files to output_path
        prepared_main_path = os.path.join(input_path, "doctest_main.cpp")
        doctest_header_dst = os.path.join(input_path, "doctest.h")
        with open(prepared_main_path, 'w') as f:
            f.write(prepared_main)
        shutil.copy(DoctestPlugin.DOCTEST_HEADER_PATH, doctest_header_dst)

        # Compile the code with doctest
        try:
            extra = " ".join(shlex.quote(a) for a in (settings.plugins.doctest.extra_args or []))
            compile_cmd = f"set -e; mkdir doctest; g++ {extra} doctest_main.cpp -o doctest/doctest_executable.out"
            result = docker.run(DoctestPlugin.DOCKER_IMAGE, input_path, compile_cmd, 15)
            combined = (result.stdout or "") + "\n" + (result.stderr or "")
            with open(os.path.join(pwd, "compile.log"), "w") as f:
                f.write(combined)
            if result.returncode != 0:
                return False, combined
        except TimeoutExpired as e:
            return False, "Compilation timed out"
        finally:
            if os.path.exists(prepared_main_path):
                os.remove(prepared_main_path)
            if os.path.exists(doctest_header_dst):
                os.remove(doctest_header_dst)

        try:
            result = docker.run(DoctestPlugin.DOCKER_IMAGE, input_path, "cd doctest; ./doctest_executable.out", 15)
            combined = (result.stdout or "") + "\n" + (result.stderr or "")
            with open(os.path.join(pwd, "data.log"), "w") as f:
                f.write(combined)
            return True, combined
        except subprocess.TimeoutExpired as e:
            return True, "Test execution timed out"
        except Exception as e:
            return False, f"Failed to run tests: {e}"
        finally:
            shutil.rmtree(os.path.join(input_path, "doctest"), ignore_errors=True)

    def _parse_output(self, log: str) -> None:
        summary_pattern = re.compile(r"\[doctest\] test cases:\s+(\d+)\s+\|\s+(\d+) passed\s+\|\s+(\d+) failed")
        summary_match = summary_pattern.search(log)

        if summary_match:
            total_cases = int(summary_match.group(1))
            passed_cases = int(summary_match.group(2))
            failed_cases = int(summary_match.group(3))
        else:
            total_cases = passed_cases = failed_cases = 0

        # --- Extract failed test details ---
        fail_pattern = re.compile(
            r"TEST CASE:\s+#(\d+)\s+(.*?)\. Score:\s+(\d+).*?"
            r"ERROR: CHECK\(\s*(.*?)\s*\) is NOT correct!.*?"
            r"values:\s+CHECK\(\s*(.*?)\s*\)",
            re.S
        )

        failures = []
        for match in fail_pattern.finditer(log):
            failures.append({
                "number": int(match.group(1)),
                "name": match.group(2).strip(),
                "score": int(match.group(3)),
                "failed_check": match.group(4).strip(),
                "failed_value": match.group(5).strip()
            })

        total_score = sum(self.scoring.values())
        obtained_score = total_score - sum(f['score'] for f in failures)
        summary = {
            "total_cases": total_cases,
            "passed": passed_cases,
            "failed": failed_cases,
            "total_score": total_score,
            "obtained_score": obtained_score,
            "failures": failures,
        }

        scores = {}
        for i in range(1, total_cases + 1):
            if not any(f['number'] == i for f in failures):
                scores[f"test_case_{i}"] = self.scoring.get(i, 0)
            else:
                scores[f"test_case_{i}"] = 0
        
        return summary, scores


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

        success, data = self._execute_tests(pwd, input_path)
        summary, scores = {}, {}
        if success:
            summary, scores = self._parse_output(data)

        if not summary or not scores:
            summary = {
                "total_cases": self.scoring and len(self.scoring) or 0,
                "passed": 0,
                "failed": self.scoring and len(self.scoring) or 0,
                "total_score": self.scoring and sum(self.scoring.values()) or 0,
                "obtained_score": 0,
                "failures": [
                    {
                        "number": i,
                        "name": f"Test Case #{i}",
                        "score": self.scoring.get(i, 0),
                        "failed_check": "Failed to run",
                        "failed_value": "Failed to run"
                    } for i in range(1, (self.scoring and len(self.scoring) or 0) + 1)
                ],
            }
            scores = {f"test_case_{i}": 0 for i in range(1, (self.scoring and len(self.scoring) or 0) + 1)}

        with open(os.path.join(pwd, "results.json"), "w") as f:
            json.dump({"tests": scores, "raw": summary}, f, indent=4)

        return scores, summary, data

    def generate_report(self, input_path: str, output_path: str, results: dict, log: str) -> None:
        if not self.has_tests:
            return ""

        if not results:
            raise ValueError("No results, should not be a thing!")

        html = generate_html_report(results)

        pwd = os.path.join(output_path, f".{self.slug}")
        with open(os.path.join(pwd, "report.html"), "w") as metrics_file:
            metrics_file.write(html)
        return True
