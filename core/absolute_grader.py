from math import erf, sqrt
import pandas as pd
import os

from config import settings
from .scoring import default_max_score, evaluate_absolute_rule, get_metric_scoring, has_configured_metrics


def _resolve_test_out_of(weights: dict, fallback_count: int) -> float:
    """Resolve total available test points from doctest scoring if available."""
    for metric, cfg in weights.items():
        if not metric.startswith("test_case_"):
            continue
        plugin_instance = cfg.get("plugin")
        scoring_map = getattr(plugin_instance, "scoring", None)
        if isinstance(scoring_map, dict) and scoring_map:
            return float(sum(scoring_map.values()))
        break
    return float(fallback_count)

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

    df = pd.DataFrame.from_dict(results, orient="index").reset_index()
    df.rename(columns={"index": "key"}, inplace=True)

    results_df = pd.DataFrame()
    results_df["key"] = df["key"]

    configured_mode = has_configured_metrics()
    if configured_mode:
        metric_names = [
            m for m, cfg in weights.items()
            if not m.startswith("test_") and cfg.get("weight", 0) != 0 and get_metric_scoring(m)
        ]

        for metric in metric_names:
            cfg = weights[metric]
            w = float(cfg.get("weight", 0))
            metric_cfg = get_metric_scoring(metric)
            rule = metric_cfg.get("absolute", {})
            strategy = rule.get("strategy", "identity")

            series = pd.to_numeric(df.get(metric, 0), errors="coerce").fillna(0.0)

            if strategy == "identity":
                contrib = series * w
            elif strategy == "count_penalty":
                cap = float(rule.get("cap", 0.0))
                contrib = (-series.clip(lower=0.0, upper=cap)) * w
            elif strategy == "threshold_penalty":
                cap = float(rule.get("cap", 0.0))
                threshold = float(rule.get("threshold", 0.0))
                excess = (series - threshold).clip(lower=0.0)
                contrib = (-excess.clip(upper=cap)) * w
            elif strategy == "comment_ratio":
                target = float(rule.get("target", 8.0))
                bonus_cap = float(rule.get("bonus_cap", 10.0))
                deficit = (target - series).clip(lower=0.0)
                bonus = (series - target).clip(lower=0.0, upper=bonus_cap)
                contrib = (-deficit + bonus) * w
            else:
                # Unknown strategy: keep behavior safe by using fallback absolute score.
                plugin_instance = cfg.get("plugin", None)
                abs_series = df.apply(
                    lambda row: (
                        evaluate_absolute_rule(metric, row.get(metric, 0))[0]
                        if evaluate_absolute_rule(metric, row.get(metric, 0)) is not None
                        else plugin_instance.to_absolute(metric, row.get(metric, 0), row.get("lines_of_code", None))
                    ),
                    axis=1,
                )
                contrib = pd.to_numeric(abs_series, errors="coerce").fillna(0.0) * w

            results_df[metric] = contrib.round(2)

        if metric_names:
            results_df["quality_total"] = results_df[metric_names].sum(axis=1).round(2)
        else:
            results_df["quality_total"] = 0.0

        # Preserve functional scoring visibility in grades.csv.
        test_cols = sorted(c for c in df.columns if c.startswith("test_case_"))
        for test_col in test_cols:
            results_df[test_col] = pd.to_numeric(df[test_col], errors="coerce").fillna(0.0).round(2)
        if test_cols:
            results_df["test_total"] = results_df[test_cols].sum(axis=1).round(2)
            test_out_of = _resolve_test_out_of(weights, len(test_cols))
            results_df["test_out_of"] = test_out_of
            if test_out_of > 0:
                results_df["test_percentage"] = (
                    results_df["test_total"] / test_out_of * 100
                ).clip(lower=0.0).round(2)
            else:
                results_df["test_percentage"] = 0.0
        else:
            results_df["test_total"] = 0.0
            results_df["test_out_of"] = 0.0
            results_df["test_percentage"] = 0.0

        # In configured absolute mode, treat quality_total as the quality score out of 100.
        results_df["quality_out_of"] = 100.0
        results_df["quality_percentage"] = results_df["quality_total"].clip(lower=0.0, upper=100.0).round(2)

        # Calculate final score with configurable weights
        scoring_cfg = settings.to_dict().get("scoring", {})
        final_score_cfg = scoring_cfg.get("final_score", {})
        quality_weight = float(final_score_cfg.get("quality_weight", 0.3))
        test_weight = float(final_score_cfg.get("test_weight", 0.7))
        test_cap = float(final_score_cfg.get("test_cap", 100.0))
        
        results_df["final_score"] = (
            results_df["quality_percentage"] * quality_weight + 
            results_df["test_percentage"].clip(upper=test_cap) * test_weight
        ).clip(lower=0.0, upper=100.0).round(2)

        df_out = (
            results_df.set_index("key").T.reset_index().rename(columns={"index": "metric"}).sort_index(axis=1)
        )
        df_out = df_out[["metric"] + sorted(df_out.columns.drop("metric"))]
        df_out.to_csv(os.path.join(output, "grades.csv"), index=False)
        return

    metric_max_scores = {}

    for metric, cfg in weights.items():
        if metric not in df.columns:
            continue

        # 0 weight means skip
        if cfg["weight"] == 0:
            continue

        plugin_instance = cfg.get("plugin", None)

        def _absolute_value(row):
            resolved = evaluate_absolute_rule(metric, row[metric])
            if resolved is not None:
                return resolved[0]
            return plugin_instance.to_absolute(metric, row[metric], row.get("lines_of_code", None))

        df[metric] = df.apply(_absolute_value, axis=1)
        df[metric] = pd.to_numeric(df[metric], errors="coerce")
        df[metric] = df[metric].fillna(100)

        metric_max_scores[metric] = default_max_score(metric)

        weighted = df[metric] * cfg["weight"]
        weighted = weighted.round(2)
        results_df[metric] = weighted

    keys = [m for m in weights.keys() if not m.startswith("test_") and m in results_df.columns]
    for key in results_df["key"]:
        total = sum(results_df.loc[results_df["key"] == key, m].values[0] for m in keys)
        results_df.loc[results_df["key"] == key, "quality_total"] = round(total, 2)

    total_out_of = sum(metric_max_scores[m] * weights[m]["weight"] for m in keys)
    results_df["quality_out_of"] = round(total_out_of, 2)
    if total_out_of == 0:
        results_df["quality_percentage"] = 0.0
    else:
        results_df["quality_percentage"] = (results_df["quality_total"] / results_df["quality_out_of"] * 100).round(2)

        # Calculate final score with configurable weights if test scores exist
    if "test_percentage" in results_df.columns:
        scoring_cfg = settings.to_dict().get("scoring", {})
        final_score_cfg = scoring_cfg.get("final_score", {})
        quality_weight = float(final_score_cfg.get("quality_weight", 0.3))
        test_weight = float(final_score_cfg.get("test_weight", 0.7))
        test_cap = float(final_score_cfg.get("test_cap", 100.0))
        
        results_df["final_score"] = (
            results_df["quality_percentage"] * quality_weight + 
            results_df["test_percentage"].clip(upper=test_cap) * test_weight
        ).clip(lower=0.0, upper=100.0).round(2)
    else:
        results_df["final_score"] = results_df["quality_percentage"].clip(lower=0.0, upper=100.0).round(2)

    df_out = (
        results_df.set_index("key").T.reset_index().rename(columns={"index": "metric"}).sort_index(axis=1)
    )
    df_out = df_out[["metric"] + sorted(df_out.columns.drop("metric"))]
    df_out.to_csv(os.path.join(output, "grades.csv"), index=False)
