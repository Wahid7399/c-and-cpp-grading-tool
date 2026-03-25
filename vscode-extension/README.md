# Quality Metrics Runner (VS Code Extension)

This extension runs the existing `quality-metrics` Python CLI from VS Code.

By default, it uses a bundled copy of the `quality-metrics` tool included inside the extension package.

## Command

- `Run Quality Metrics Analysis`
- `Create Quality Metrics Config File`

You can run it from:
- Command Palette
- Explorer right-click on a folder: `Run Quality Metrics Analysis`
- Explorer right-click on a file: `Run Quality Metrics Analysis` (uses that file's parent folder as input)

For `Create Quality Metrics Config File`, the extension asks you to pick a destination folder, then writes `quality_metrics.config.json` there.

When analysis finishes successfully, the extension automatically opens the generated `report.html` in your default browser.
If a run fails, an error notification appears in the bottom-right and full logs are in the `Quality Metrics` Output channel.

## Settings

- `qualityMetrics.pythonPath` (default: `python3`)
- `qualityMetrics.scriptPath` (default: empty = use bundled tool)
- `qualityMetrics.inputPath` (default: `examples/0`)
- `qualityMetrics.outputPath` (default: empty = `Quality Report` inside selected input folder)
- `qualityMetrics.testsPath` (optional)
- `qualityMetrics.configPath` (optional)
- `qualityMetrics.threads` (default: `1`)
- `qualityMetrics.multifolder` (default: `false`)
- `qualityMetrics.checkZips` (default: `true`)
- `qualityMetrics.grading` (`relative` or `absolute`)

Paths can be absolute or relative to the opened workspace root.

## Development

```bash
npm install
npm run compile
```

Press `F5` to launch an Extension Development Host.

## Package as VSIX

```bash
npm install -g @vscode/vsce
vsce package
```

Packaging automatically refreshes `bundled/quality-metrics` by deleting it and copying a fresh snapshot from the parent project before compile.

This generates a `.vsix` file in this folder.

## Install VSIX

In VS Code: **Extensions** → `...` menu → **Install from VSIX...**
