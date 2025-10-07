from math import erf, sqrt
import pandas as pd
import os

def zscore(series: pd.Series) -> pd.Series:
    mean, std = series.mean(), series.std(ddof=0)
    return (series - mean) / std if std > 0 else pd.Series(0.0, index=series.index)

def normal_cdf(z: pd.Series) -> pd.Series:
    return ((1.0 + z.apply(lambda x: erf(x / sqrt(2)))) / 2.0) * 100

def run(results: dict, weights: dict, output: str) -> None:
    """
    Grader: z-score based scoring of code-quality metrics.

    Features
        - Reads CSV with a 'key' column and metric columns.
        - Z-scores each metric across the dataset.
        - Inverts "negative" metrics so that larger is better before weighting.
        - Supports per-metric multipliers (weights).
        - Rescales to 0-100.
    """

    if not results:
        print("No results to grade.")
        return

    scale="minmax"
    df = pd.DataFrame.from_dict(results, orient="index").reset_index()
    df.rename(columns={"index": "key"}, inplace=True)

    results = pd.DataFrame()
    results["key"] = df["key"]

    for metric, cfg in weights.items():
        if metric not in df.columns:
            continue
        if cfg["weight"] == 0:
            continue
        z = zscore(df[metric])
        if cfg["direction"] == -1:
            z = z.apply(lambda x: -x if x != 0 else 0)
        weighted = z * cfg["weight"]
        metric = metric.replace("_violations", "_score")
        results[metric] = weighted

    df_out = (
        results.set_index("key").T.reset_index().rename(columns={"index": "metric"}).sort_index(axis=1)
    )
    df_out = df_out[["metric"] + sorted(df_out.columns.drop("metric"))]
    df_out.to_csv(os.path.join(output, "raw_normalized.csv"), index=False)

    for metric in weights.keys():
        metric = metric.replace("_violations", "_score")
        if metric in results.columns:
            col = results[metric]
            if col.max() == col.min():  
                results[metric] = 100
            else:
                results[metric] = (col - col.min()) / (col.max() - col.min()) * 100

    results = results.round(2)
    df_out = (
        results.set_index("key").T.reset_index().rename(columns={"index": "metric"}).sort_index(axis=1)
    )
    df_out = df_out[["metric"] + sorted(df_out.columns.drop("metric"))]
    df_out.to_csv(os.path.join(output, "grades.csv"), index=False)
