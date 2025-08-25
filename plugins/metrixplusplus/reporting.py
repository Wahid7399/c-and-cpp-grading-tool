from datetime import datetime
import re

def humanize(check: str) -> str:
  check = check.replace("-", " ").replace("_", " ")
  check = re.sub(r'([a-z])([A-Z])', r'\1 \2', check)
  check = check.replace(".", " ")
  check = check.title()
  return check

def traffic_light(value, good_max=None, warn_max=None, reverse=False):
    if good_max is None and warn_max is None:
        return "Info", "#94a3b8"
    if reverse:
        if value >= good_max: return "Good", "#16a34a"
        if value >= warn_max: return "Warning", "#f59e0b"
        return "Poor", "#ef4444"
    else:
        if value <= good_max: return "Good", "#16a34a"
        if value <= warn_max: return "Warning", "#f59e0b"
        return "Poor", "#ef4444"

thresholds = {
    "cyclomatic": dict(good_max=10, warn_max=20, reverse=False),
    "lines_of_code": dict(good_max=200, warn_max=500, reverse=False),
    "comment_ratio": dict(good_max=25, warn_max=40, reverse=True),
    "halstead_volume": dict(good_max=1000, warn_max=8000, reverse=False),
    "halstead_difficulty": dict(good_max=20, warn_max=100, reverse=False),
    "halstead_effort": dict(good_max=20000, warn_max=100000, reverse=False),
    "maintainability_index": dict(good_max=85, warn_max=65, reverse=True),
}

descriptions = {
    "cyclomatic": "Counts independent paths through the code. Higher means more branching and complexity.",
    "lines_of_code": "Approximate size of the module in lines of code (non-blank).",
    "lines_of_comments": "How many lines are comments. Useful as context for documentation level.",
    "comment_ratio": "Percentage of comment lines vs total lines. Higher usually means better documentation (within reason).",
    "halstead_n1": "Number of distinct operators (e.g., +, -, function calls).",
    "halstead_n2": "Number of distinct operands (e.g., variables, constants).",
    "halstead_N1": "Total occurrences of operators.",
    "halstead_N2": "Total occurrences of operands.",
    "halstead_volume": "Information content based on Halstead; grows with program size and vocabulary.",
    "halstead_difficulty": "How hard the program is to understand/modify per Halstead; higher is harder.",
    "halstead_effort": "Estimated mental effort to implement/understand; proportional to difficulty × volume.",
    "maintainability_index": "Composite score (lines, complexity, Halstead) – higher usually means easier to maintain."
}

improvement_tips = {
    "cyclomatic": [
        "Split long functions into smaller ones with single responsibilities.",
        "Reduce deep nesting with early returns/guard clauses.",
        "Replace large if/elif/switch blocks with polymorphism/strategy tables."
    ],
    "lines_of_code": [
        "Extract reusable helpers and remove duplication.",
        "Eliminate dead code; keep functions short and focused."
    ],
    "lines_of_comments": [
        "Prefer self-explanatory names; use comments for the 'why', not the 'what'."
    ],
    "comment_ratio": [
        "Add docstrings and brief explanations for tricky logic.",
        "Remove redundant comments that restate the code."
    ],
    "halstead_volume": [
        "Reduce unnecessary abstraction layers and indirection.",
        "Consolidate repeated logic (DRY)."
    ],
    "halstead_difficulty": [
        "Favor simpler data flows and small, pure functions.",
        "Avoid clever one-liners; write clear, stepwise code."
    ],
    "halstead_effort": [
        "Lower difficulty and volume via refactoring and better naming.",
        "Add unit tests to aid understanding and safe changes."
    ],
    "maintainability_index": [
        "Refactor large/complex functions; strengthen tests and docs.",
        "Reduce complexity hot-spots; separate concerns into modules."
    ]
}

def gauge_html(value, good_max, warn_max, reverse=False, min_val=0, max_val=None):
    if max_val is None:
        candidates = [value]
        if good_max is not None: candidates.append(good_max)
        if warn_max is not None: candidates.append(warn_max)
        max_val = max(candidates) if candidates else 1.0
        max_val = max_val if max_val > 0 else 1.0
    label, color = traffic_light(value, good_max, warn_max, reverse)
    pct = min(100, (value / max_val) * 100 if max_val else 0)
    return f'''
      <div class="meter"><div class="bar" style="width:{pct:.1f}%; background:{color};"></div></div>
      <div class="meter-label">{label}</div>'''

def generate_html_report(metrics: dict) -> None:
    # Ensure all expected metrics are present
    for key in thresholds.keys():
        if key not in metrics:
            metrics[key] = 0.0

    rows = []
    for key, val in metrics.items():
        t = thresholds.get(key, {})
        desc = descriptions.get(key, "No description available.")
        tips = improvement_tips.get(key, [])
        gauge = ""
        if "good_max" in t or "warn_max" in t:
            gauge = gauge_html(val, t.get("good_max"), t.get("warn_max"), t.get("reverse", False))
        tips_html = "".join(f"<li>{tip}</li>" for tip in tips) if tips else "<li>No specific tips.</li>"
        rows.append(f"""
        <section class="card">
            <div class="card-header"><h3>{humanize(key)}</h3><div class="value">{val:,.0f}</div></div>
            <p class="desc">{desc}</p>
            {gauge}
            <details class="tips"><summary>How to improve</summary><ul>{tips_html}</ul></details>
        </section>
        """)

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Code Metrics Report</title>
<style>
:root {{ --bg:#0f172a; --panel:#111827; --card:#0b1220; --text:#e5e7eb; --muted:#94a3b8; --accent:#60a5fa; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; padding:24px; background:var(--bg); color:var(--text); font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial; }}
header {{ display:flex; align-items:baseline; justify-content:space-between; gap:12px; margin-bottom:20px; border-bottom:1px solid #1f2937; padding-bottom:12px; }}
h1 {{ margin:0; font-size:28px; }}
.meta {{ color:var(--muted); font-size:14px; }}
.summary-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:12px; margin:16px 0 28px; }}
.summary-tile {{ background:var(--panel); padding:14px 16px; border-radius:14px; border:1px solid #1f2937; }}
.summary-tile .k {{ color:var(--muted); font-size:12px; }}
.summary-tile .v {{ font-weight:700; font-size:18px; }}
main {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:16px; }}
.card {{ background:var(--card); border:1px solid #1f2937; border-radius:16px; padding:16px; box-shadow:0 10px 20px rgba(0,0,0,.2); }}
.card-header {{ display:flex; align-items:center; justify-content:space-between; gap:8px; }}
.card h3 {{ margin:0; font-size:16px; text-transform:capitalize; }}
.value {{ font-variant-numeric:tabular-nums; color:var(--accent); font-weight:700; }}
.desc {{ color:var(--muted); margin:8px 0 10px; line-height:1.4; }}
.meter {{ width:100%; height:10px; background:#111827; border:1px solid #1f2937; border-radius:999px; overflow:hidden; }}
.bar {{ height:100%; transition:width .6s ease; }}
.meter-label {{ margin-top:6px; font-size:12px; color:var(--muted); }}
details.tips {{ margin-top:10px; }}
details.tips summary {{ cursor:pointer; color:#cbd5e1; }}
footer {{ margin-top:28px; color:#94a3b8; font-size:12px; }}
</style></head>
<body>
<header>
    <h1>Code Quality Report</h1>
    <div class="meta">Generated {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
</header>

<section class="summary-grid">
    <div class="summary-tile"><div class="k">Cyclomatic complexity</div><div class="v">{metrics['cyclomatic']:.0f}</div></div>
    <div class="summary-tile"><div class="k">Lines of Code</div><div class="v">{metrics['lines_of_code']:.0f}</div></div>
    <div class="summary-tile"><div class="k">Comment Lines</div><div class="v">{metrics['lines_of_comments']:.0f}</div></div>
    <div class="summary-tile"><div class="k">Comment %</div><div class="v">{metrics['comment_ratio']:.1f}%</div></div>
    <div class="summary-tile"><div class="k">Halstead Volume</div><div class="v">{metrics['halstead_volume']:.0f}</div></div>
    <div class="summary-tile"><div class="k">Halstead Difficulty</div><div class="v">{metrics['halstead_difficulty']:.1f}</div></div>
    <div class="summary-tile"><div class="k">Effort</div><div class="v">{metrics['halstead_effort']:.0f}</div></div>
    <div class="summary-tile"><div class="k">Maintainability Index</div><div class="v">{metrics['maintainability_index']:.0f}</div></div>
</section>

<main>{''.join(rows)}</main>

<footer><p><strong>Notes:</strong> Thresholds are heuristic guidelines; interpret within your project’s context.</p></footer>
</body></html>
    """

    return html