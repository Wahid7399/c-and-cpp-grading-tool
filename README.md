# Quality Metrics

A command-line tool for analyzing project directories and generating quality reports in CSV or JSON format.  
Supports both single-folder and multi-folder processing.

---

## Features

- Process project directories and score quality metrics.
- Support for **single-folder** or **multi-folder** runs.
- Export results in **CSV** (default) or **JSON**.
- Configurable runtime settings via a config file.
- Multi-threaded execution for faster processing.

---

## Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/Wahid7399/c-and-cpp-grading-tool.git
cd c-and-cpp-grading-tool
pip install -r requirements.txt
```

---

## Usage

Run the script with the required arguments:

```bash
python main.py --input <input_dir> --output <output_dir> [options]
```

### Arguments

| Argument            | Type   | Required | Default | Description |
|---------------------|--------|----------|---------|-------------|
| `--input`           | str    | Yes   | None    | Path to the input directory containing project files. |
| `--output`          | str    | Yes   | None    | Path to the directory where results will be saved. |
| `--config`          | str    | No    | None    | Path to a custom config file. |
| `--result-format`   | str    | No    | `csv`   | Output format: `csv` or `json`. |
| `--threads`         | int    | No    | `1`     | Number of threads to use for processing. |
| `--multifolder`     | flag   | No    | False   | Run analysis on multiple folders (projects) at once. |

---

## Examples

### Single folder run
```bash
python main.py --input ./examples/0 --output ./test_0
```

### Run with tests
```bash
python3 main.py --input examples/2/factorials --output ./test_2 --tests examples/2/test_factorials.cpp
```

### Multi-folder run
```bash
python main.py --input ./examples/1 --output ./test_1 --multifolder --threads 4
```

### With custom config
```bash
python main.py --input ./examples/1 --output ./test_1 --multifolder --config ./config.json
```

---

## Output

- By default, results are written to:
  - `results.csv` (for CSV output)  
  - `results.json` (for JSON output)

- Location: inside the specified `--output` directory.

---

## Config file

Edit the file in `config/default.json` or provide a file via command line arguments
```json
{
    "python_slug": "python3",
    "scoring": {
        "metrics": {
            "maintainability_index": {
                "weight": 1.0,
                "direction": 1,
                "absolute": {
                    "strategy": "identity",
                    "max_score": 100.0
                }
            },
            "correctness_violations": {
                "weight": 2.0,
                "direction": -1,
                "absolute": {
                    "strategy": "count_penalty",
                    "base_score": 100.0,
                    "cap": 5.0
                }
            },
            "cyclomatic": {
                "weight": 0.1,
                "direction": -1,
                "absolute": {
                    "strategy": "threshold_penalty",
                    "base_score": 100.0,
                    "threshold": 13.0,
                    "cap": 50.0
                }
            },
            "comment_ratio": {
                "weight": 0.3,
                "direction": 1,
                "absolute": {
                    "strategy": "comment_ratio",
                    "base_score": 100.0,
                    "target": 8.0,
                    "bonus_cap": 10.0
                }
            }
        },
        "final_score": {
            "quality_weight": 0.3,
            "test_weight": 0.7,
            "test_cap": 100.0
        }
    },
    "plugins": {
        "metrixplusplus": {
            "enabled": true,
            "metrics": [
                "std.code.halstead.all",
                "std.code.maintindex.simple",
                "std.code.complexity.cyclomatic",
                "std.code.lines.code",
                "std.code.lines.comments",
                "std.code.ratio.comments"
            ]
        },
        "clangtidy": {
            "enabled": true,
            "command": "clang-tidy",
            "config": null,
            "extra_args": [
                "-std=c++17",
                "-isysroot", 
                "/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk"
            ]
        }
    }
```

The `scoring.metrics` block controls per-metric weights for grading. In absolute grading, the optional `absolute` rule controls how each raw metric becomes a score:

- `identity`: use the raw metric value directly.
- `count_penalty`: subtract the metric value from `base_score`, capped by `cap`.
- `threshold_penalty`: subtract only the amount above `threshold`, capped by `cap`.
- `comment_ratio`: subtract any shortfall below `target` and add a capped bonus above it.

If a metric is not listed under `scoring.metrics`, the grader falls back to the plugin's built-in behavior.
### Custom config

A custom config file can be generated & passed to the checker:

```bash
python scripts/create_config.py --output .quality_metrics.config.json
```

You can also re-grade an existing `raw_scores.csv` with a custom config:

```bash
python scripts/regrade.py --output ./test_1 --grading absolute --config ./.quality_metrics.config.json
```

## Project Structure

```
.
├── core/
│   └── quality_scorer.py   # Core logic for scoring
├── tools/
│   └── report.py           # Utility for exporting reports
├── config/
│   └── settings.py         # Config loader
├── plugins/
│   └── clangtidy           # Clang Tidy plugin
│   └── metrixplusplus      # MetrixPlusPlus plugin
├── main.py                 # Entry point (CLI)
├── requirements.txt
└── README.md
```

---

## Plugin System

Extend **Quality Scorer** with custom plugins that collect metrics from your source code. Plugins implement a small interface and can be enabled/disabled via config.

### How it works

- Each plugin subclasses `BasePlugin` and implements two methods:
  - `initialize()` — prepare dependencies (download tools, set up folders, etc.).
  - `run(input_path, output_path) -> dict` — analyze code and return a **flat dict of metrics**.
- Plugins are registered in `plugins/__init__.py` and discovered via a `metric_plugins` dict.
- At runtime, the tool calls `initialize()` (if enabled) and then `run(...)`.  
- Results from each plugin are merged into the final report.

### Core interface

```python
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
```

### Registering plugins

Declare your plugin class and add it to `metric_plugins` dict:

```python
from .base import BasePlugin
from .metrixplusplus import MetrixPlusPlusPlugin
from .clangtidy import ClangTidyPlugin

__all__ = ["BasePlugin", "MetrixPlusPlusPlugin", "ClangTidyPlugin"]

metric_plugins = {
    "metrixplusplus": MetrixPlusPlusPlugin(),
    "clangtidy": ClangTidyPlugin(),
}
```

> The dict key (e.g., `"metrixplusplus"`) is the plugin **slug**, used in config.

### Writing your own plugin

1. **Create a class** in `plugins/your_plugin.py`:

```python
from plugins import BasePlugin
from pathlib import Path
import os, json

class MyAwesomePlugin(BasePlugin):
    def __init__(self):
        super().__init__(
            name="My Awesome Tool",
            description="Collects custom metrics",
            slug="myawesome",
            version="0.1.0",
        )

    def initialize(self):
        # Optional: download/install third-party tools, build binaries, etc.
        # Respect config toggles:
        cfg = getattr(settings.plugins, self.slug, None)
        if not (cfg and getattr(cfg, "enabled", False)):
            return
        # Prepare any local resources/folders here

    def run(self, input_path: str, output_path: str) -> dict:
        cfg = getattr(settings.plugins, self.slug, None)
        if not (cfg and getattr(cfg, "enabled", False)):
            return {}

        workdir = os.path.join(output_path, f".{self.slug}")
        os.makedirs(workdir, exist_ok=True)

        # Do analysis...
        metrics = {
            "my_metric_1": 123.0,
            "my_metric_2": 0.87,
        }

        with open(os.path.join(workdir, "results.json"), "w") as f:
            json.dump({"metrics": metrics}, f, indent=2)

        return metrics
```

2. **Register it** in `plugins/__init__.py`:

```python
from .myawesome import MyAwesomePlugin
metric_plugins["myawesome"] = MyAwesomePlugin()
```

3. **Enable it** in your config (example `config/default.json`):

```json
{
    "python_slug": "python3",
    "plugins": {
        "myawesome": {
            "enabled": true,
            // add any plugin-specific settings you need
        }
    }
}
```

### Conventions & tips

- **Slug**: keep it lowercase, no spaces (used for config key and working folder: `.<slug>`).
- **Idempotent `initialize()`**: check if dependencies are already present and skip redundant work.
- **Return contract**: `run()` returns a **dict of simple JSON-serializable values** (numbers/strings) that will be merged into the overall results.
- **Logging & artifacts**: write plugin-specific logs/artifacts to `--output/.<slug>/`.
- **Be defensive**: gracefully handle missing inputs (e.g., no matching files) by returning `{}`.
- **Settings access**: read via `from config import settings` and scope under `settings.plugins.<slug>`.

### Testing a plugin quickly

```bash
# Prepare
rm -rf results && mkdir results

# Run with your plugin enabled
python main.py --input ./sample_project --output ./results

# Inspect artifacts
tree results
cat results/.myawesome/results.json
```

---

### VS Code Extension
```
cd vscode-extension && npm i
npx @vscode/vsce package --allow-missing-repository
```
Creates a vsix file