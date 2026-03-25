import * as vscode from 'vscode';
import { spawn } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';

let setupPromise: Promise<string> | undefined;
type PythonLauncher = { command: string; prefixArgs: string[] };
const DOCKER_INSTALL_URL = 'https://www.docker.com/products/docker-desktop/';

function isDockerMissingMessage(text: string): boolean {
  const normalized = text.toLowerCase();
  return (
    normalized.includes('docker')
    && (
      normalized.includes('not installed')
      || normalized.includes('command not found')
      || normalized.includes('docker: not found')
      || normalized.includes("'docker' is not recognized")
    )
  );
}

function maybeOpenDockerInstallPage(text: string, state: { opened: boolean }, output: vscode.OutputChannel): void {
  if (state.opened || !isDockerMissingMessage(text)) {
    return;
  }

  state.opened = true;
  output.appendLine('\nDetected missing Docker installation. Opening Docker Desktop download page...');
  void vscode.env.openExternal(vscode.Uri.parse(DOCKER_INSTALL_URL));
  void vscode.window.showWarningMessage('Docker is not installed. Opened Docker Desktop download page in your browser.');
}

function runProcess(
  command: string,
  args: string[],
  cwd: string,
  output: vscode.OutputChannel,
  label: string
): Promise<void> {
  return new Promise<void>((resolve, reject) => {
    output.appendLine(`${label}: ${command} ${args.map((a) => JSON.stringify(a)).join(' ')}`);
    const child = spawn(command, args, { cwd, shell: true, env: process.env });
    child.stdout.on('data', (chunk: Buffer) => output.append(chunk.toString()));
    child.stderr.on('data', (chunk: Buffer) => output.append(chunk.toString()));
    child.on('error', (err) => reject(err));
    child.on('close', (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`${label} failed with exit code ${code}`));
      }
    });
  });
}

function canRunCommand(command: string, args: string[]): Promise<boolean> {
  return new Promise<boolean>((resolve) => {
    // shell: true is needed on Windows so app execution aliases (Microsoft Store
    // Python) and user-scope PATH entries are visible to the process lookup.
    const child = spawn(command, args, { shell: true, env: process.env });
    child.on('error', () => resolve(false));
    child.on('close', (code) => resolve(code === 0));
  });
}

async function detectBootstrapPython(config: vscode.WorkspaceConfiguration): Promise<PythonLauncher> {
  const configured = config.get<string>('pythonPath', '').trim();
  if (configured) {
    return { command: configured, prefixArgs: [] };
  }

  if (process.platform === 'win32') {
    if (await canRunCommand('py', ['-3', '--version'])) {
      return { command: 'py', prefixArgs: ['-3'] };
    }
  }

  if (await canRunCommand('python3', ['--version'])) {
    return { command: 'python3', prefixArgs: [] };
  }

  if (await canRunCommand('python', ['--version'])) {
    return { command: 'python', prefixArgs: [] };
  }

  throw new Error('Could not find Python. Set qualityMetrics.pythonPath in settings.');
}

function bundledRoot(context: vscode.ExtensionContext): string {
  return path.join(context.extensionPath, 'bundled', 'quality-metrics');
}

function venvDir(context: vscode.ExtensionContext): string {
  return path.join(context.globalStorageUri.fsPath, 'quality-metrics-venv');
}

function venvPythonPath(context: vscode.ExtensionContext): string {
  const dir = venvDir(context);
  return process.platform === 'win32'
    ? path.join(dir, 'Scripts', 'python.exe')
    : path.join(dir, 'bin', 'python');
}

function setupMarkerPath(context: vscode.ExtensionContext): string {
  return path.join(venvDir(context), '.setup-complete');
}

async function ensureVirtualEnv(
  context: vscode.ExtensionContext,
  output: vscode.OutputChannel,
  showNotifications: boolean
): Promise<string> {
  if (setupPromise) {
    return setupPromise;
  }

  setupPromise = (async () => {
    const config = vscode.workspace.getConfiguration('qualityMetrics');
    const bootstrapPython = await detectBootstrapPython(config);
    const root = bundledRoot(context);
    const storagePath = context.globalStorageUri.fsPath;
    const envDir = venvDir(context);
    const envPython = venvPythonPath(context);
    const marker = setupMarkerPath(context);
    const reqMain = path.join(root, 'requirements.txt');
    const reqMetrix = path.join(root, 'plugins', 'metrixplusplus', 'implementation', 'requirements.txt');

    fs.mkdirSync(storagePath, { recursive: true });

    const alreadyReady = fs.existsSync(envPython) && fs.existsSync(marker);
    if (alreadyReady) {
      return envPython;
    }

    if (showNotifications) {
      void vscode.window.showInformationMessage('Setting up Quality Metrics Python environment (first run only)...');
    }

    output.show(true);
    output.appendLine('Preparing Quality Metrics virtual environment...');

    if (!fs.existsSync(envPython)) {
      await runProcess(
        bootstrapPython.command,
        [...bootstrapPython.prefixArgs, '-m', 'venv', envDir],
        root,
        output,
        'Create venv'
      );
    }

    await runProcess(envPython, ['-m', 'pip', 'install', '--upgrade', 'pip'], root, output, 'Upgrade pip');
    await runProcess(envPython, ['-m', 'pip', 'install', '-r', reqMain, '-r', reqMetrix], root, output, 'Install requirements');

    fs.writeFileSync(marker, new Date().toISOString(), 'utf8');

    if (showNotifications) {
      void vscode.window.showInformationMessage('Quality Metrics environment is ready.');
    }

    return envPython;
  })();

  try {
    return await setupPromise;
  } catch (error) {
    setupPromise = undefined;
    throw error;
  }
}

function resolveMaybeRelative(base: string, candidate: string): string {
  return path.isAbsolute(candidate) ? candidate : path.join(base, candidate);
}

function resolveScriptPath(
  context: vscode.ExtensionContext,
  workspacePath: string,
  config: vscode.WorkspaceConfiguration
): string {
  const configured = config.get<string>('scriptPath', '').trim();
  if (configured) {
    return resolveMaybeRelative(workspacePath, configured);
  }
  return path.join(context.extensionPath, 'bundled', 'quality-metrics', 'main.py');
}

function resolveInputPath(
  workspacePath: string,
  config: vscode.WorkspaceConfiguration,
  inputOverride?: string
): string {
  const configuredInputPath = resolveMaybeRelative(workspacePath, config.get<string>('inputPath', 'examples/0'));
  return inputOverride ?? configuredInputPath;
}

function resolveOutputPath(
  workspacePath: string,
  config: vscode.WorkspaceConfiguration,
  inputPath: string
): string {
  const configuredOutputPath = config.get<string>('outputPath', '').trim();
  if (configuredOutputPath) {
    return resolveMaybeRelative(workspacePath, configuredOutputPath);
  }

  const baseInputDir = fs.existsSync(inputPath) && fs.statSync(inputPath).isFile()
    ? path.dirname(inputPath)
    : inputPath;
  return path.join(baseInputDir, 'Quality Report');
}

function buildArgs(
  workspacePath: string,
  scriptPath: string,
  inputPath: string,
  outputPath: string,
  config: vscode.WorkspaceConfiguration,
): string[] {
  const testsPath = config.get<string>('testsPath', '').trim();
  const configPath = config.get<string>('configPath', '').trim();
  const threads = config.get<number>('threads', 1);
  const multifolder = config.get<boolean>('multifolder', false);
  const checkZips = config.get<boolean>('checkZips', true);
  const grading = config.get<string>('grading', 'relative');

  const args = [
    scriptPath,
    '--input',
    inputPath,
    '--output',
    outputPath,
    '--threads',
    String(Math.max(1, Math.floor(threads))),
    '--check-zips',
    checkZips ? 'true' : 'false',
    '--grading',
    grading
  ];

  if (testsPath) {
    args.push('--tests', resolveMaybeRelative(workspacePath, testsPath));
  }

  if (configPath) {
    args.push('--config', resolveMaybeRelative(workspacePath, configPath));
  }

  if (multifolder) {
    args.push('--multifolder');
  }

  return args;
}

function findReportToOpen(outputPath: string): string | undefined {
  const direct = path.join(outputPath, 'report.html');
  if (fs.existsSync(direct)) {
    return direct;
  }

  if (!fs.existsSync(outputPath) || !fs.statSync(outputPath).isDirectory()) {
    return undefined;
  }

  for (const item of fs.readdirSync(outputPath)) {
    const candidate = path.join(outputPath, item, 'report.html');
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }

  return undefined;
}

export function activate(context: vscode.ExtensionContext): void {
  const output = vscode.window.createOutputChannel('Quality Metrics');

  void ensureVirtualEnv(context, output, false).catch((err) => {
    output.appendLine(`\nEnvironment setup failed: ${(err as Error).message}`);
  });

  const runCommand = vscode.commands.registerCommand('qualityMetrics.run', async (resource?: vscode.Uri) => {
    const workspace = vscode.workspace.workspaceFolders?.[0];
    if (!workspace) {
      vscode.window.showErrorMessage('Open a workspace folder before running Quality Metrics.');
      return;
    }

    const workspacePath = workspace.uri.fsPath;
    const config = vscode.workspace.getConfiguration('qualityMetrics');
    const scriptPath = resolveScriptPath(context, workspacePath, config);
    const selectedInputPath = resource
      ? (fs.existsSync(resource.fsPath) && fs.statSync(resource.fsPath).isFile()
        ? path.dirname(resource.fsPath)
        : resource.fsPath)
      : undefined;
    const inputPath = resolveInputPath(workspacePath, config, selectedInputPath);
    const outputPath = resolveOutputPath(workspacePath, config, inputPath);
    const args = buildArgs(workspacePath, scriptPath, inputPath, outputPath, config);

    if (!fs.existsSync(scriptPath)) {
      vscode.window.showErrorMessage(`Quality Metrics script does not exist: ${scriptPath}`);
      return;
    }

    let pythonPath: string;
    try {
      pythonPath = await ensureVirtualEnv(context, output, true);
    } catch (err) {
      const message = (err as Error).message;
      output.appendLine(`\nEnvironment setup failed: ${message}`);
      vscode.window.showErrorMessage(`Quality Metrics environment setup failed: ${message}`);
      return;
    }

    output.show(true);
    output.appendLine('Running quality-metrics...');
    output.appendLine(`Command: ${pythonPath} ${args.map((a) => JSON.stringify(a)).join(' ')}`);

    await vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: 'Quality Metrics',
        cancellable: false
      },
      () =>
        new Promise<void>((resolve) => {
          const dockerPromptState = { opened: false };
          const processHandle = spawn(pythonPath, args, {
            cwd: path.dirname(scriptPath),
            shell: false,
            env: {
              ...process.env,
              PATH: [path.dirname(pythonPath), process.env.PATH ?? ''].join(path.delimiter)
            }
          });

          processHandle.stdout.on('data', (chunk: Buffer) => {
            const text = chunk.toString();
            output.append(text);
            maybeOpenDockerInstallPage(text, dockerPromptState, output);
          });
          processHandle.stderr.on('data', (chunk: Buffer) => {
            const text = chunk.toString();
            output.append(text);
            maybeOpenDockerInstallPage(text, dockerPromptState, output);
          });

          processHandle.on('error', (err) => {
            output.appendLine(`\nFailed to start process: ${err.message}`);
            vscode.window.showErrorMessage(`Quality Metrics failed to start: ${err.message}`);
            resolve();
          });

          processHandle.on('close', (code) => {
            if (code === 0) {
              output.appendLine('\nQuality Metrics finished successfully.');
              const reportPath = findReportToOpen(outputPath);
              if (reportPath) {
                void vscode.env.openExternal(vscode.Uri.file(reportPath));
                vscode.window.showInformationMessage('Quality Metrics finished successfully. Opened report in browser.');
              } else {
                vscode.window.showWarningMessage('Quality Metrics finished, but report.html was not found in output.');
              }
            } else {
              output.appendLine(`\nQuality Metrics failed with exit code ${code}.`);
              vscode.window.showErrorMessage(`Quality Metrics failed (exit code ${code}). See Output: Quality Metrics.`);
            }
            resolve();
          });
        })
    );
  });

  context.subscriptions.push(runCommand, output);
}

export function deactivate(): void {}
