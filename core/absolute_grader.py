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
        if cfg["weight"] == 0:
            continue
        
        if cfg.get("normalized") is False:
            df[metric] = (df[metric] / df["lines_of_code"]) * 100

        if cfg["direction"] == -1:
            df[metric] = df[metric].apply(lambda x: -x if x != 0 else 0)

        weighted = df[metric] * cfg["weight"]
        weighted = weighted.round(2)
        results[metric] = weighted

    df_out = (
        results.set_index("key").T.reset_index().rename(columns={"index": "metric"}).sort_index(axis=1)
    )
    df_out = df_out[["metric"] + sorted(df_out.columns.drop("metric"))]
    df_out.to_csv(os.path.join(output, "grades.csv"), index=False)
