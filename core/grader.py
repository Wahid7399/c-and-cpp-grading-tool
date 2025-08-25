from math import erf, sqrt
import pandas as pd

# Each metric maps to:
#   direction: +1 = higher is better, -1 = higher is worse
#   weight:    relative importance
MAPPING = {
    "cognitive_complexity_violations": {"direction": -1, "weight": 2.0},
    "comment_ratio": {"direction": +1, "weight": 1.0},
    "correctness_violations": {"direction": -1, "weight": 3.0},
    "cppcheck_error_violations": {"direction": -1, "weight": 2.0},
    "cppcheck_performance_violations": {"direction": -1, "weight": 1.5},
    "cppcheck_style_violations": {"direction": -1, "weight": 1.0},
    "cyclomatic": {"direction": -1, "weight": 1.5},
    "guidelines_violations": {"direction": -1, "weight": 1.5},
    "halstead_difficulty": {"direction": -1, "weight": 1.0},
    "halstead_effort": {"direction": -1, "weight": 1.0},
    "halstead_volume": {"direction": -1, "weight": 1.0},
    "identifier_naming_violations": {"direction": -1, "weight": 1.0},
    "lines_of_comments": {"direction": +1, "weight": 0.5},
    "maintainability_index": {"direction": +1, "weight": 2.0},
    "performance_violations": {"direction": -1, "weight": 2.0},
    "readability_violations": {"direction": -1, "weight": 2.0},
    # etc. (extend as needed)
}

def zscore(series: pd.Series) -> pd.Series:
    mean, std = series.mean(), series.std(ddof=0)
    return (series - mean) / std if std > 0 else pd.Series(0.0, index=series.index)

def normal_cdf(z: pd.Series) -> pd.Series:
    return ((1.0 + z.apply(lambda x: erf(x / sqrt(2)))) / 2.0) * 100

def run(results: dict, output: str, key_col="project") -> None:
    """
    Grader: z-score based scoring of code-quality metrics.

    Features
        - Reads CSV with a 'key' column and metric columns.
        - Z-scores each metric across the dataset.
        - Inverts "negative" metrics so that larger is better before weighting.
        - Supports per-metric multipliers (weights).
        - Produces a composite score and rescales to 0–100.
    """

    if not results:
        print("No results to grade.")
        return

    scale="minmax"
    df = pd.DataFrame.from_dict(results, orient="index").reset_index()
    df.rename(columns={"index": "key"}, inplace=True)

    results = pd.DataFrame()
    results["key"] = df["key"]

    weighted_scores = []
    for metric, cfg in MAPPING.items():
        if metric not in df.columns:
            continue
        z = zscore(df[metric])
        if cfg["direction"] == -1:
            z = -z
        weighted = z * cfg["weight"]
        results[f"z_{metric}"] = z
        results[f"w_{metric}"] = weighted
        weighted_scores.append(weighted)

    results["composite_raw"] = sum(weighted_scores)

    if scale == "cdf":
        results["score_0_100"] = normal_cdf(results["composite_raw"])
    else:
        xmin, xmax = results["composite_raw"].min(), results["composite_raw"].max()
        if xmax == xmin:
            results["score_0_100"] = 50.0
        else:
            results["score_0_100"] = (results["composite_raw"] - xmin) / (xmax - xmin) * 100

    results.to_csv(output, index=False)

    """
    # Collect all metric names
    metric_names = set()
    for project_results in results.values():
        # metrics = project_results.get("metrics", {})
        metric_names.update(project_results.keys())

    if not metric_names:
        print("No metrics found in results to grade.")
        return

    # Prepare data for z-score normalization
    metric_values = {metric: [] for metric in metric_names}
    for metrics in results.values():
        # metrics = project_results.get("metrics", {})
        for metric in metric_names:
            value = metrics.get(metric, 0)
            metric_values[metric].append(value)

    # Calculate mean and stddev for each metric
    metric_stats = {}
    for metric, values in metric_values.items():
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        stddev = variance ** 0.5
        metric_stats[metric] = (mean, stddev)

    # Calculate z-scores and overall grades
    graded_results = {}
    for project, metrics in results.items():
        # metrics = project_results.get("metrics", {})
        z_scores = {}
        total_z_score = 0
        count = 0
        for metric in metric_names:
            value = metrics.get(metric, 0)
            mean, stddev = metric_stats[metric]
            if stddev > 0:
                z_score = (value - mean) / stddev
            else:
                z_score = 0  # If stddev is 0, all values are the same; assign z-score of 0
            z_scores[metric] = z_score
            total_z_score += z_score
            count += 1
        overall_grade = total_z_score / count if count > 0 else 0
        graded_results[project] = {
            "z_scores": z_scores,
            "overall_grade": overall_grade,
            "metrics": metrics,
        }

    # Output to CSV
    import csv

    with open(output, mode="w", newline="") as csvfile:
        fieldnames = ["project"] + list(metric_names) + ["overall_grade"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for project, data in graded_results.items():
            row = {"project": project, "overall_grade": data["overall_grade"]}
            row.update(data["metrics"])
            writer.writerow(row)
    """