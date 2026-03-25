from math import erf, sqrt
import pandas as pd
import os

def zscore(series: pd.Series) -> pd.Series:
    mean, std = series.mean(), series.std(ddof=0)
    return (series - mean) / std if std > 0 else pd.Series(0.0, index=series.index)

def normal_cdf(z: pd.Series) -> pd.Series:
    return ((1.0 + z.apply(lambda x: erf(x / sqrt(2)))) / 2.0) * 100

def run(results: dict, weights: dict, output: str) -> None:
    if not results:
        print("No results to grade.")
        return
    
    if "lines_of_code" not in weights:
        raise ValueError("lines_of_code must be included for absolute grading (configure metrixplusplus)")

    scale="minmax"
    df = pd.DataFrame.from_dict(results, orient="index").reset_index()
    df.rename(columns={"index": "key"}, inplace=True)

    results = pd.DataFrame()
    results["key"] = df["key"]

    for metric, cfg in weights.items():
        if metric not in df.columns:
            continue

        # 0 weight means skip
        if cfg["weight"] == 0 or metric == "halstead_difficulty": # skip halstead_difficulty
            continue
        
        # Convert to absolute
        plugin_instance = cfg.get("plugin", None)
        df[metric] = df.apply(
            lambda row: plugin_instance.to_absolute(metric, row[metric], row.get("lines_of_code", None)), axis=1
        )

        df[metric] = df[metric].fillna(100)
        # if cfg["direction"] == -1:
        #     df[metric] = df[metric].apply(lambda x: -x if x != 0 else 0)

        weighted = df[metric] * cfg["weight"]
        weighted = weighted.round(2)
        results[metric] = weighted

    # Give total "Code Quality" score => sum of non-test case weights (exclude test_)
    # Give "Out of" => sum of weights * 100
    keys = [m for m in weights.keys() if not m.startswith("test_") and m != "halstead_difficulty"]
    for key in results["key"]:
        total = sum(results.loc[results["key"] == key, m].values[0] for m in keys if m in results.columns)
        results.loc[results["key"] == key, "quality_total"] = round(total, 2)
    total_out_of = sum(cfg["weight"] for m, cfg in weights.items() if not m.startswith("test_") and m != "halstead_difficulty") * 100
    results["quality_out_of"] = total_out_of
    results["quality_percentage"] = (results["quality_total"] / results["quality_out_of"] * 100).round(2)
    df_out = (
        results.set_index("key").T.reset_index().rename(columns={"index": "metric"}).sort_index(axis=1)
    )
    df_out = df_out[["metric"] + sorted(df_out.columns.drop("metric"))]
    df_out.to_csv(os.path.join(output, "grades.csv"), index=False)
