# C/C++ Grading Tool

VS Code extension and Python CLI for grading C/C++ assignments with:

- static analysis (clang-tidy)
- software metrics (Metrix++)
- memory checks (Valgrind)
- functional testing (Doctest)

The tool generates an HTML report plus CSV/JSON score artifacts.

## Prerequisites

### Required

- Python 3
- Docker Desktop (must be installed and running)
- `clang-tidy` available on PATH (default command: `clang-tidy`)

Doctest and Valgrind run inside a docker image. The image will be pulled automatically.

## Install and Use in VS Code

1. Clone the repository:

```bash
git clone https://github.com/Wahid7399/c-and-cpp-grading-tool.git
```

2. Install the extension:

- Open VS Code Extensions view.
- Select `...` -> `Install from VSIX...`
- Choose `c-cpp-grader-tool-0.0.5.vsix` from this repository.

3. Run commands from Command Palette:

- `C/C++ Grader Tool: Run Analysis`
- `C/C++ Grader Tool: Create Config File`

You can also right-click a folder/file in Explorer and run `C/C++ Grader Tool: Run Analysis`.

## Configuration

The extension auto-detects a workspace-root config file named:

- `.quality_metrics.config.json`

You can generate this file using `C/C++ Grader Tool: Create Config File`.

## Example Config

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
                    "threshold": 65.5,
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
                    "bonus_cap": 5.0
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
        "doctest": {
            "tests_files": [
                "./tests/test_file.cpp"
            ],
            "extra_args": [
                "-std=c++14",
                "-fpermissive"
            ],
            "include_dirs": [
                "."
            ]
        },
        "cppcheck": {
            "enabled": false
        },
        "valgrind": {
            "enabled": true,
            "main_file": "./tests/valgrind_main.c",
            "extra_args": [
                "-std=c11",
                "-w"
            ],
            "include_dirs": [
                "."
            ]
        }
    }
}
```

## CLI Usage (Optional)

You can run the Python tool directly:

```bash
python3 main.py \
  --input /path/to/submission_or_folder \
  --output /path/to/output \
  --grading absolute
```

Useful flags:

- `--config /path/to/.quality_metrics.config.json`
- `--tests /path/to/test_file.cpp` (or rely on `plugins.doctest.tests_files`)
- `--threads N`
- `--multifolder`
- `--check-zips true|false`
- `--grading absolute|relative`

Important: relative grading is supported only in multifolder mode.

## Output

By default (extension mode), output is written to `Quality Report` under the selected input folder unless `qualityMetrics.outputPath` is set in extension settings.

Artifacts:

- `report.html`: combined report entry page
- `grades.csv`: final grading table
- `raw_scores.csv`: per-metric raw values
- `raw.json`: raw structured results

Plugin-specific reports/logs are stored in sub-folders under output (for example: `.clangtidy`, `.doctest`, `.metrixplusplus`, `.valgrind`).
