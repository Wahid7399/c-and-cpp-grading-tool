"""
BasePlugin interface for CodeQualityScorer plugins
"""
class BasePlugin:
    def __init__(self, name: str, description: str, slug: str, version: str):
        self.name = name
        self.description = description
        self.slug = slug
        self.version = version

    def initialize(self):
        """
        Initialize/install the plugin.
        This method should check if the plugin is installed and if not, download/install it.
        """
        raise NotImplementedError("Need to implement.")

    def run(self, input: str, output: str) -> dict:
        """
        Collect metrics from the provided data.
        """
        raise NotImplementedError("Need to implement.")
