import subprocess
import sys
from typing import Tuple
from config import settings
from plugins import BasePlugin
import platform

class ValgrindPlugin(BasePlugin):
    """
    Valgrind Plugin for Code Quality Scorer
    """

    def __init__(self):
        super(ValgrindPlugin, self).__init__(
            name="Valgrind",
            report_name="Memory Issues Report",
            description="Integrate Valgrind metrics into Code Quality Scorer",
            slug="valgrind",
            version="20.1.0"
        )

    def _run(self, cmd):
        print(f"→ Running: {cmd}")
        result = subprocess.run(cmd, shell=True)
        if result.returncode != 0:
            print(f"Command failed: {cmd}")
            sys.exit(1)

    def initialize(self):
        if settings.plugins.valgrind is None or settings.plugins.valgrind.enabled is not True:
            return

        # Check if valgrind is installed
        try:
            subprocess.run(
                [settings.plugins.valgrind.command, "--version"],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            print("✅ Valgrind is installed")
            return
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Valgrind is not installed, attempting an auto-install.")

        if platform.system() == "Darwin":
            print("❌ Not supported")
            raise NotImplementedError("Valgrind installation is not supported on macOS.")
        elif platform.system() == "Linux":
            subprocess.run(
                ["sudo", "apt-get", "install", "-y", "valgrind"],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            print("✅ Valgrind has been installed via apt-get")
        elif platform.system() == "Windows":
            print("❌ Valgrind auto-installation not supported on Windows. Please install it manually from https://valgrind.org/")
            raise NotImplementedError("Valgrind installation is not supported on Windows.")
        else:
            print("❌ Valgrind is not installed and auto-install is not supported. Please install it using your system's package manager.")
            raise NotImplementedError("Valgrind installation is not supported.")

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

        return {}, {}, "Valgrind integration is not yet implemented."

    def generate_report(self, input_path: str, output_path: str, results: dict, log: str) -> None:
        """
        Generate a report from the collected metrics.
        """
        return ""