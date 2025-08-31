from asyncio import log
from pathlib import Path
from typing import Tuple
from config import settings
from plugins import BasePlugin
from collections import Counter, defaultdict
from .reporting import generate_html_report
import subprocess
import glob
import re
import os
import json

class ClangTidyPlugin(BasePlugin):
    """
    Clang Tidy Plugin for Code Quality Scorer
    """
    PATH = str(Path(__file__).parent.resolve() / "implementation" / "clang_tidy.py")
    ANSI_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
    CATEGORY_RULES = [
        (re.compile(r"readability-identifier-length"), "identifier_naming_violations"),
        (re.compile(r"readability-function-cognitive-complexity"), "cognitive_complexity_violations"),
        (re.compile(r"readability-.*"), "readability_violations"),
        (re.compile(r"bugprone-.*"), "correctness_violations"),
        (re.compile(r"performance-.*"), "performance_violations"),
        (re.compile(r"cppcoreguidelines-.*"), "guidelines_violations"),
        (re.compile(r"clang-analyzer-.*"), "correctness_violations"),
        (re.compile(r"clang-.*"), "correctness_violations"),
    ]
    LINE_RE = re.compile(
        r"^(?P<file>.*?):(?P<line>\d+):(?P<col>\d+):\s*(?P<severity>warning|error):.*\[(?P<check>[^\]]+)\]",
        re.MULTILINE,
    )
    BAD_FILE_RE = re.compile(r'Error while processing\s+["\']?(?P<path>.+?\.(?:c|cc|cp|cxx|cpp|c\+\+|m|mm|ixx))["\']?\.?', re.IGNORECASE)

    def __init__(self):
        super(ClangTidyPlugin, self).__init__(
            name="Clang Tidy",
            report_name="Readability & Correctness Report",
            description="Static Analysis - Code style, Security, Correctness, Performance, and more",
            slug="clangtidy",
            version="20.1.0"
        )

    def initialize(self):
        if settings.plugins.clangtidy is None or settings.plugins.clangtidy.enabled is not True:
            return

        # Check if clang-tidy is installed
        try:
            subprocess.run(
                [settings.plugins.clangtidy.command, "--version"],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            print("✅ Clang Tidy is installed")
        except subprocess.CalledProcessError:
            print("❌ Clang Tidy is not installed. Please install it using `pip install -r requirements.txt` or `pip install clang-tidy==20.1.0`")

    def _run_once(self, files, config_path, build_dir=None, cmd=None):
        """
        Run clang-tidy for a single file with retries.
        Returns (returncode, stdout, stderr). Skips on persistent failure.
        """
        command = [
            settings.plugins.clangtidy.command,
            "-quiet",
            # "-allow-enabling-analyzer-alpha-checkers",
            f"--config-file={config_path}",
            *files,
            "--",
            "-ferror-limit=0",
            "-fno-color-diagnostics",
            "-Wunreachable-code",
            "-Wunused-variable",
            *settings.plugins.clangtidy.extra_args,
        ]
        proc = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True
        )

        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        combined = stdout + "\n" + stderr

        # Collect files that caused clang-tidy to choke
        bad_files = set()
        for m in ClangTidyPlugin.BAD_FILE_RE.finditer(combined):
            bad_files.add(m.group("path"))

        # Also treat obvious parser crashes per-file as bad (defensive)
        # e.g., "fatal error: error in backend: ..." tied to a path in the same line
        # (We keep the main explicit pattern above as the primary signal.)

        return proc.returncode, stdout, stderr, bad_files

    def _run_with_retries(self, files, config_path, build_dir=None, cmd=None, max_retries=3):
        """
        Try running clang-tidy; if some files are 'bad', drop them and retry.
        Returns: (combined_output, processed_files, skipped_files)
        """
        remaining = list(files)
        skipped = set()
        attempts = 0
        all_outputs = []

        while attempts < max_retries and remaining:
            rc, out, err, bad = self._run_once(remaining, config_path, build_dir, cmd)
            all_outputs.append((out or "") + ("\n" + err if err else ""))

            if not bad:
                break

            # Remove only the files we can confidently identify
            bad_normalized = set()
            remaining_set = set(map(os.path.abspath, remaining))
            for b in bad:
                abs_b = os.path.abspath(b)
                if abs_b in remaining_set:
                    bad_normalized.add(abs_b)

            # If reported bad files are in our set, drop them and retry.
            if bad_normalized:
                skipped.update(bad_normalized)
                remaining = [f for f in remaining if os.path.abspath(f) not in bad_normalized]
                attempts += 1
            else:
                # Could not map bad files back to input list; stop to avoid infinite loop.
                break

        combined_output = "\n".join(all_outputs).strip()
        processed = [f for f in files if os.path.abspath(f) not in skipped]
        return combined_output, processed, sorted(skipped)
    
    def __broad_concept(self, check_name: str) -> str:
        for regex, category in ClangTidyPlugin.CATEGORY_RULES:
            if regex.fullmatch(check_name) or regex.match(check_name):
                return category
        return check_name.split('-', 1)[0]

    def __strip_ansi(self, s: str) -> str:
        return ClangTidyPlugin.ANSI_RE.sub("", s)

    def __parse_clang_tidy_output(self, output: str):
        out = self.__strip_ansi(output)
        concept_counts = Counter({
            "identifier_naming_violations": 0,
            "cognitive_complexity_violations": 0,
            "readability_violations": 0,
            "correctness_violations": 0,
            "performance_violations": 0,
            "guidelines_violations": 0,
        })
        check_counts = Counter()
        severity_counts = Counter()
        by_file = defaultdict(Counter)

        for m in ClangTidyPlugin.LINE_RE.finditer(out):
            check = m.group("check")
            severity = m.group("severity")
            file_ = m.group("file")

            concept = self.__broad_concept(check)

            concept_counts[concept] += 1
            check_counts[check] += 1
            severity_counts[severity] += 1
            by_file[file_][concept] += 1

        return {
            "by_concept": concept_counts,
            "by_check": check_counts,
            "by_severity": severity_counts,
            "by_file_concept": by_file,
        }

    def run(self, input_path, output_path) -> Tuple[dict, dict, str]:
        """
        Run the Clang Tidy analysis.

        Args:
            input_path (str): Path to the input directory containing .cpp files.
            output_path (str): Path to the output directory where results will be stored.

        Returns:
            Tuple[dict, dict, str]: A tuple containing:
                - Simplified metrics result
                - Detailed output
                - Logs
        """
        if settings.plugins.clangtidy is None or settings.plugins.clangtidy.enabled is not True:
            return {}, {}, ""

        clang_tidy_config = settings.plugins.clangtidy.config or Path(__file__).parent.resolve() / "clang-tidy.yml"
        build_dir = getattr(settings.plugins.clangtidy, "build_dir", None)
        cmd = getattr(settings.plugins.clangtidy, "command", "clang-tidy")

        # Collect .cpp files
        cpp_files = glob.glob(os.path.join(input_path, "**", "*.cpp"), recursive=True)

        if not cpp_files:
            print(f"❌ No .cpp files found in {input_path}")
            return {}, {}, ""

        # Ensure output folder
        pwd = os.path.join(output_path, ".clangtidy")
        os.makedirs(pwd, exist_ok=True)

        # Run with retries
        combined, processed_files, skipped_files = self._run_with_retries(
            cpp_files,
            config_path=str(clang_tidy_config),
            build_dir=build_dir,
            cmd=cmd,
            max_retries=3,
        )

        # Always write a log
        with open(os.path.join(pwd, "data.log"), "w") as f:
            f.write(combined)

        # Parse whatever we got (even if some files failed)
        report = self.__parse_clang_tidy_output(combined) if combined else {
            "by_concept": {},
        }

        results = {
            "metrics": report.get("by_concept", {}),
            "raw": report,
            "processed_files": processed_files,
            "skipped_files": skipped_files,
        }
        with open(os.path.join(pwd, "results.json"), "w") as metrics_file:
            json.dump(results, metrics_file, indent=4)

        # IMPORTANT: never raise; treat as success even if some files were skipped
        return report.get("by_concept", {}), results, combined

    def generate_report(self, input_path: str, output_path: str, results: dict, log: str) -> bool:
        """
        Generate a report from the collected metrics.
        """
        if not results:
            return "No results to report."

        html = generate_html_report(results, log)

        pwd = os.path.join(output_path, ".clangtidy")
        with open(os.path.join(pwd, "report.html"), "w") as metrics_file:
            metrics_file.write(html)
        return True
