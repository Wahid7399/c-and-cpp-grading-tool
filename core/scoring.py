from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from config import settings


def _settings_dict() -> Dict[str, Any]:
    try:
        data = settings.to_dict()
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def get_metric_scoring(metric: str) -> Dict[str, Any]:
    scoring = _settings_dict().get("scoring", {})
    metrics = scoring.get("metrics", {})
    metric_cfg = metrics.get(metric, {})
    return metric_cfg if isinstance(metric_cfg, dict) else {}


def has_configured_metrics() -> bool:
    scoring = _settings_dict().get("scoring", {})
    metrics = scoring.get("metrics", {})
    return isinstance(metrics, dict) and len(metrics) > 0


def apply_weight_overrides(metric: str, weight_cfg: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(weight_cfg)
    metric_cfg = get_metric_scoring(metric)

    # When scoring.metrics is provided, treat it as the quality-metric whitelist.
    # Keep test_case_* untouched so functional scoring remains independent.
    if has_configured_metrics() and not metric_cfg and not metric.startswith("test_"):
        merged["weight"] = 0
        return merged

    for key in ("weight", "direction"):
        value = metric_cfg.get(key)
        if value is not None:
            merged[key] = value
    return merged


def resolve_absolute_rule(metric: str) -> Optional[Dict[str, Any]]:
    metric_cfg = get_metric_scoring(metric)
    rule = metric_cfg.get("absolute")
    return rule if isinstance(rule, dict) else None


def evaluate_absolute_rule(metric: str, value: Any) -> Optional[Tuple[float, float]]:
    rule = resolve_absolute_rule(metric)
    if not rule:
        return None

    strategy = rule.get("strategy", "identity")
    score_value = _to_float(value)

    if strategy == "identity":
        max_score = _to_float(rule.get("max_score", 100.0))
        min_score = _to_float(rule.get("min_score", 0.0))
        score = max(min_score, min(max_score, score_value))
        return score, max_score

    if strategy == "count_penalty":
        cap = _to_float(rule.get("cap", 0.0))
        return _penalty_score(score_value, 0.0, cap, rule)

    if strategy == "threshold_penalty":
        threshold = _to_float(rule.get("threshold", 0.0))
        cap = _to_float(rule.get("cap", 0.0))
        excess = max(0.0, score_value - threshold)
        return _penalty_score(excess, 0.0, cap, rule)

    if strategy == "comment_ratio":
        target = _to_float(rule.get("target", 8.0))
        base_score = _to_float(rule.get("base_score", 100.0))
        min_score = _to_float(rule.get("min_score", 0.0))
        bonus_cap = _to_float(rule.get("bonus_cap", 10.0))
        deficit = max(0.0, target - score_value)
        bonus = min(bonus_cap, max(0.0, score_value - target))
        score = max(min_score, base_score - deficit + bonus)
        return score, base_score + bonus_cap

    raise ValueError(f"Unknown absolute scoring strategy '{strategy}' for metric '{metric}'")


def default_max_score(metric: str) -> float:
    rule = resolve_absolute_rule(metric)
    if not rule:
        return 100.0

    strategy = rule.get("strategy", "identity")
    if strategy == "comment_ratio":
        return _to_float(rule.get("base_score", 100.0)) + _to_float(rule.get("bonus_cap", 10.0))
    if strategy == "identity":
        return _to_float(rule.get("max_score", 100.0))
    return _to_float(rule.get("base_score", 100.0))


def _penalty_score(value: float, threshold: float, cap: float, rule: Dict[str, Any]) -> Tuple[float, float]:
    base_score = _to_float(rule.get("base_score", 100.0))
    min_score = _to_float(rule.get("min_score", 0.0))
    penalty = min(cap, max(0.0, value - threshold))
    score = max(min_score, base_score - penalty)
    return score, base_score


def _to_float(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    return float(value)