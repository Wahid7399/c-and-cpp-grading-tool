from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List
from config import settings
from plugins import metric_plugins, test_plugins, BasePlugin
from zipfile import ZipFile
from .reporting import build_single_report
import shutil
import os
import sys

all_plugins = {**test_plugins, **metric_plugins}

def init() -> dict:
    """
    Run the quality scorer on the provided input and output paths.
    """
    # Loop through all plugins and initialize them
    for plugin in all_plugins.keys():
        if not hasattr(settings.plugins, plugin) or not settings.plugins[plugin].enabled:
            continue
        plugin_instance = all_plugins[plugin]
        plugin_instance.initialize()
    print("")

def setup_tests(tests: str):
    """
    Setup the tests if any test framework is enabled.
    """
    if not tests:
        return
    for plugin in test_plugins.keys():
        if not hasattr(settings.plugins, plugin) or not settings.plugins[plugin].enabled:
            continue
        plugin_instance = test_plugins[plugin]
        if not plugin_instance.setup_tests(tests):
            sys.exit(1)
    print("")

def generate_report(plugin_instance, reports, input, output_path, detailed_output, log):
    """
    Generate a report from the collected metrics for plugin_instance,
    add to the reports list if a report was generated.
    """
    has_report = plugin_instance.generate_report(input, output_path, detailed_output, log)
    if has_report:
        # get relative path from output_path
        relative_path = os.path.relpath(os.path.join(output_path, f".{plugin_instance.slug}", "report.html"), output_path)
        reports.append({
            "name": plugin_instance.report_name,
            "description": plugin_instance.description,
            "path": relative_path
        })

def run(input: str, output: str) -> dict:
    """
    Run the quality scorer on the provided input and output paths.
    """

    # Create output directory if it doesn't exist
    output_path = output
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    # Loop through all plugins and run them
    results, reports = {}, []
    for plugin in all_plugins.keys():
        if not hasattr(settings.plugins, plugin) or not settings.plugins[plugin].enabled:
            continue
        plugin_instance: BasePlugin = all_plugins[plugin]
        metrics, detailed_output, log = plugin_instance.run(input, output)
        results.update(metrics)
        generate_report(plugin_instance, reports, input, output_path, detailed_output, log)
    if reports:
        build_single_report(reports, output)

    return results

def _multifolder_single_batch_run(input_dirs: List[str], output: str) -> dict:
    """
    Run the quality scorer on multiple folders.
    Loop through the main directory, go into each subfolder,
        Find a folder inside subfolder to unzip, run the quality scorer on it, and then delete the folder.
        If no folder to unzip, run on the input subfolder as it is.
    """
    results = {}
    for entry in input_dirs:
        output_message = ""
        if entry.is_dir():
            dir_path = entry.path
            output_message += f"ℹ️ Processing {dir_path}\n"
            dir_name = os.path.basename(dir_path)
            # If a zip exists, unzip it and run the quality scorer
            if any(file.endswith('.zip') for root, dirs, files in os.walk(dir_path) for file in files):
                zip_paths = []
                for root, dirs, files in os.walk(dir_path):
                    for file in files:
                        if file.endswith('.zip'):
                            zip_paths.append(os.path.join(root, file))
                if len(zip_paths) > 1:
                    output_message += f"⚠️ Multiple zip files found in {dir_path}! This should not happen, please check.\n"
                for zip_path in zip_paths:
                    unzip_temp = os.path.join(dir_path, "unzipped")
                    with ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(unzip_temp)
                    if not any(file.endswith(('.c', '.h', '.cpp')) for root, dirs, files in os.walk(unzip_temp) for file in files):
                        output_message += f"⚠️ No C/C++ files found in {unzip_temp}, skipping\n"
                        shutil.rmtree(unzip_temp, ignore_errors=True)
                        print(output_message)
                        continue
                    sub_results = run(unzip_temp, os.path.join(output, dir_name))
                    results[dir_name] = sub_results
                    shutil.rmtree(unzip_temp, ignore_errors=True)
            else:
                if not any(file.endswith(('.c', '.h', '.cpp')) for root, dirs, files in os.walk(dir_path) for file in files):
                    output_message += f"⚠️ No C/C++ files found in {dir_path}, skipping\n"
                    print(output_message)
                    continue
                sub_results = run(dir_path, os.path.join(output, dir_name))
                results[dir_name] = sub_results
            print(output_message)
    return results

def multifolder_run(input: str, output: str, num_threads: int) -> dict:
    """
    Run the quality scorer on multiple folders with optional multithreading.
    """
    if not os.path.exists(input):
        raise FileNotFoundError(f"Input path {input} does not exist")
    
    if not os.path.exists(output):
        os.makedirs(output, exist_ok=True)

    output = os.path.abspath(output)

    folders = []
    for entry in os.scandir(input):
        if entry.is_dir():
            folders.append(entry)

    if num_threads == 1:
        return _multifolder_single_batch_run(folders, output)
    else:
        results = {}
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = {executor.submit(_multifolder_single_batch_run, [folder], output): folder.path
                    for folder in folders}
            for future in as_completed(futures):
                results.update(future.result())
        return results
