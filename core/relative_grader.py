import os
import pandas as pd
from math import sqrt
from math import erf

def zscore(series: pd.Series) -> pd.Series:
    mean, std = series.mean(), series.std(ddof=0)
    return (series - mean) / std if std > 0 else pd.Series(0.0, index=series.index)

def normal_cdf(z: pd.Series) -> pd.Series:
    # Map z-score to percentile [0,100]
    return ((1.0 + z.apply(lambda x: erf(x / sqrt(2)))) / 2.0) * 100

def run(results: dict, weights: dict, output: str) -> None:
    if not results:
        print("No results to grade.")
        return

    df = pd.DataFrame.from_dict(results, orient="index").reset_index()
    df.rename(columns={"index": "key"}, inplace=True)

    scored = pd.DataFrame()
    scored["key"] = df["key"]

    final_metrices = {}

    # Build per-metric unweighted, direction-corrected z columns
    for metric, cfg in weights.items():
        if metric not in df.columns:
            continue
        if cfg["weight"] == 0:
            continue
        if df[metric].max() == df[metric].min():
            print(f"⚠️ Skipping {metric} because all values are identical.")
            continue

        z = zscore(df[metric])
        if cfg["direction"] == -1:
            z = z * -1  # simpler and no weird x!=0 branch

        out_metric_name = metric.replace("_violations", "_score")
        final_metrices[out_metric_name] = cfg
        scored[out_metric_name] = z

    # Write raw z-scores for debugging
    debug_out = (
        scored.set_index("key")
        .T.reset_index()
        .rename(columns={"index": "metric"})
        .sort_index(axis=1)
    )
    debug_out = debug_out[["metric"] + sorted(debug_out.columns.drop("metric"))]
    debug_out.to_csv(os.path.join(output, "raw_normalized.csv"), index=False)

    # Rescale each metric column to 0-100
    for metric in list(final_metrices.keys()):
        if metric in scored.columns:
            col = scored[metric]

            if col.max() == col.min():
                scored[metric] = 100.0
                continue

            # Option A: convert z -> percentile 0..100 (smooth, outlier-robust)
            col_scaled = normal_cdf(col)

            # Option B: strict min-max on z (comment A / uncomment B if you insist)
            # col_scaled = (col - col.min()) / (col.max() - col.min()) * 100

            scored[metric] = col_scaled

    # round after scaling so we don't lose precision for agg math
    scored_rounded = scored.copy()
    scored_rounded[list(final_metrices.keys())] = scored_rounded[list(final_metrices.keys())].round(2)

    # Compute aggregates using weights (weights act once here)
    metric_names = [m for m in final_metrices if not m.startswith("test_")]
    weight_vec = pd.Series({m: final_metrices[m].get("weight", 1.0) for m in metric_names})

    vals = (
        scored_rounded
        .reindex(columns=weight_vec.index, fill_value=0)
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0.0)
    )

    scored_rounded["quality_total"] = vals.dot(weight_vec).round(2)

    total_out_of = float(100 * weight_vec.sum())
    scored_rounded["quality_out_of"] = total_out_of
    scored_rounded["quality_percentage"] = (
        scored_rounded["quality_total"] / total_out_of * 100
    ).round(2)

    # Final export
    df_out = (
        scored_rounded.set_index("key")
        .T.reset_index()
        .rename(columns={"index": "metric"})
        .sort_index(axis=1)
    )
    df_out = df_out[["metric"] + sorted(df_out.columns.drop("metric"))]

    df_out.to_csv(os.path.join(output, "grades.csv"), index=False)
