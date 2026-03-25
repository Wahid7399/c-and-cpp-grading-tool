"""
BasePlugin interface for CodeQualityScorer plugins
"""
from typing import Tuple


class BasePlugin:
    def __init__(self, name: str, report_name: str, description: str, slug: str, version: str):
        self.name = name
        self.report_name = report_name
        self.description = description
        self.slug = slug
        self.version = version

    def initialize(self):
        """
        Initialize/install the plugin.
        This method should check if the plugin is installed and if not, download/install it.
        """
        raise NotImplementedError("Need to implement.")

    def run(self, input: str, output: str) -> Tuple[dict, dict, str]:
        """
        Collect metrics from the provided data.

        Args:
            input_path (str): Path to the input directory containing .cpp files.
            output_path (str): Path to the output directory where results will be stored.

        Returns:
            Tuple[dict, dict, str]: A tuple containing:
                - Simplified metrics result
                - Detailed output
                - Logs
        """
        raise NotImplementedError("Need to implement.")
    
    def generate_report(self, input: str, output: str, results: dict, log: str) -> dict:
        """
        Generate a report from the collected metrics.
        This method can be overridden by plugins to customize report generation.
        """
        raise NotImplementedError("Need to implement.")

    def to_absolute(self, key: str, value: float, normalizer: float) -> dict:
        """
        Convert the collected metrics to absolute values.
        This method can be overridden by plugins to customize conversion.
        """
        raise NotImplementedError("Need to implement.")

    def get_weights(self) -> dict:
        """
        Return the weights for the metrics collected by this plugin.
        This method can be overridden by plugins to customize weights.
        """
        raise NotImplementedError("Need to implement.")

class TestPlugin(BasePlugin):
    def setup_tests(self, test_file: str):
        """
        Setup the test plugin with the provided test file.
        This method should be overridden by test plugins to load and prepare tests.
        """
        raise NotImplementedError("Need to implement.")