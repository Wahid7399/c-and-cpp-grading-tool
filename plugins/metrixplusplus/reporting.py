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


def _judgment(value, steps):
    """steps: list of (max_value, label, color) sorted ascending. Returns (label, color)."""
    for max_val, label, color in steps:
        if value <= max_val:
            return label, color
    return steps[-1][1], steps[-1][2]


def _healthbar_html(label, display_value, bar_pct, judgment_label, color, description, tips):
    tips_li = "".join("<li>" + tip + "</li>" for tip in tips) if tips else ""
    tips_block = (
        "<details class='tips'><summary>How to improve</summary><ul>"
        + tips_li + "</ul></details>"
    ) if tips_li else ""
    return (
        "<div class='health-card'>"
        "<div class='health-top'>"
        "<div class='health-meta'>"
        "<div class='health-label'>" + label + "</div>"
        "<div class='health-desc'>" + description + "</div>"
        "</div>"
        "<div class='health-right'>"
        "<div class='health-value'>" + display_value + "</div>"
        "<div class='health-judgment' style='color:" + color + ";'>" + judgment_label + "</div>"
        "</div>"
        "</div>"
        "<div class='healthbar-track'>"
        "<div class='healthbar-fill' style='width:" + f"{bar_pct:.1f}" + "%; background:" + color + ";'></div>"
        "</div>"
        + tips_block +
        "</div>"
    )


def generate_html_report(metrics: dict):
    for key in thresholds.keys():
        if key not in metrics:
            metrics[key] = 0.0

    # ── Health indicators ─────────────────────────────────────────────────
    cr = float(metrics.get("comment_ratio", 0))
    cr_bar = min(100.0, cr / 50.0 * 100.0)   # 0–50 % maps to full bar
    cr_label, cr_color = _judgment(cr, [
        (5,   "Poor",      "#ef4444"),
        (10,  "Fair",      "#f59e0b"),
        (20,  "Good",      "#22c55e"),
        (35,  "Excellent", "#10b981"),
        (50,  "Good",      "#22c55e"),
        (999, "Fair",      "#f59e0b"),   # over-commented
    ])

    mi = float(metrics.get("maintainability_index", 0))
    mi_bar = min(100.0, max(0.0, mi))   # MI is 0–100
    mi_label, mi_color = _judgment(mi, [
        (20,  "Poor",      "#ef4444"),
        (50,  "Fair",      "#f59e0b"),
        (75,  "Good",      "#22c55e"),
        (999, "Excellent", "#10b981"),
    ])

    health_html = (
        _healthbar_html(
            "Comment Ratio", f"{cr:.1f}%", cr_bar, cr_label, cr_color,
            descriptions["comment_ratio"], improvement_tips.get("comment_ratio", [])
        ) + _healthbar_html(
            "Maintainability Index", f"{mi:.0f} / 100", mi_bar, mi_label, mi_color,
            descriptions["maintainability_index"], improvement_tips.get("maintainability_index", [])
        )
    )

    # ── Raw metrics table ─────────────────────────────────────────────────
    SKIP = {"halstead_n1", "halstead_n2", "halstead_N1", "halstead_N2",
            "comment_ratio", "maintainability_index"}
    raw_rows = []
    for key, val in metrics.items():
        if key in SKIP:
            continue
        desc = descriptions.get(key, "")
        if isinstance(val, float) and val == int(val):
            val_str = f"{int(val):,}"
        elif isinstance(val, float):
            val_str = f"{val:,.2f}"
        else:
            val_str = str(val)
        raw_rows.append(
            "<tr>"
            "<td class='rk'>" + humanize(key) + "</td>"
            "<td class='rv'>" + val_str + "</td>"
            "<td class='rd'>" + desc + "</td>"
            "</tr>"
        )

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    css = (
        ":root{--bg:#0f172a;--panel:#111827;--card:#0b1220;--text:#e5e7eb;--muted:#94a3b8;--accent:#60a5fa}"
        "*{box-sizing:border-box}"
        "body{margin:0;padding:24px;background:var(--bg);color:var(--text);"
        "font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial}"
        ".wrapper{max-width:900px;margin:40px auto;padding:0 16px}"
        "header{display:flex;align-items:baseline;justify-content:space-between;gap:12px;"
        "margin-bottom:28px;border-bottom:1px solid #1f2937;padding-bottom:14px}"
        "h1{margin:0;font-size:26px;font-weight:700}"
        "h2{margin:0 0 14px;font-size:12px;text-transform:uppercase;letter-spacing:.08em;"
        "color:var(--muted);font-weight:600}"
        ".meta{color:var(--muted);font-size:13px}"
        ".health-section{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:28px}"
        "@media(max-width:600px){.health-section{grid-template-columns:1fr}}"
        ".health-card{background:#121a2e;border:1px solid #1f2937;border-radius:16px;padding:18px 20px}"
        ".health-top{display:flex;justify-content:space-between;align-items:flex-start;"
        "gap:12px;margin-bottom:14px}"
        ".health-meta{flex:1}"
        ".health-label{font-size:15px;font-weight:700;margin-bottom:4px}"
        ".health-desc{font-size:12px;color:var(--muted);line-height:1.45}"
        ".health-right{text-align:right;flex-shrink:0}"
        ".health-value{font-size:24px;font-weight:800;color:var(--accent);font-variant-numeric:tabular-nums}"
        ".health-judgment{font-size:12px;font-weight:700;margin-top:3px;letter-spacing:.06em;text-transform:uppercase}"
        ".healthbar-track{width:100%;height:10px;background:#1e293b;border-radius:999px;overflow:hidden}"
        ".healthbar-fill{height:100%;border-radius:999px;transition:width .6s ease}"
        "details.tips{margin-top:12px}"
        "details.tips summary{cursor:pointer;color:#cbd5e1;font-size:12px}"
        "details.tips ul{margin:6px 0 0 16px;padding:0;color:var(--muted);font-size:12px;line-height:1.6}"
        ".raw-section{background:#121a2e;border:1px solid #1f2937;border-radius:16px;padding:18px 20px}"
        ".raw-note{font-weight:400;font-size:11px;color:var(--muted);margin-left:8px}"
        "table{width:100%;border-collapse:collapse;font-size:13px}"
        "thead th{text-align:left;color:var(--muted);font-weight:600;font-size:11px;"
        "text-transform:uppercase;letter-spacing:.06em;padding:0 8px 10px;border-bottom:1px solid #1f2937}"
        "tbody tr:hover td{background:rgba(255,255,255,.025)}"
        "td{padding:9px 8px;vertical-align:top;border-bottom:1px solid #1e293b}"
        ".rk{font-weight:600;white-space:nowrap;color:#cbd5e1}"
        ".rv{font-variant-numeric:tabular-nums;color:var(--accent);white-space:nowrap;"
        "text-align:right;padding-right:20px}"
        ".rd{color:var(--muted);line-height:1.4}"
        "footer{margin-top:24px;color:#94a3b8;font-size:12px}"
    )

    html = (
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>Software Quality Report</title>"
        "<style>" + css + "</style></head>"
        "<body><div class='wrapper'>"
        "<header>"
        "<h1>Software Quality Report</h1>"
        "<div class='meta'>Generated " + now + "</div>"
        "</header>"
        "<h2>Quality Indicators</h2>"
        "<div class='health-section'>" + health_html + "</div>"
        "<div class='raw-section'>"
        "<h2>Raw Metrics <span class='raw-note'>context-dependent — interpret relative to project size</span></h2>"
        "<table><thead><tr>"
        "<th>Metric</th>"
        "<th style='text-align:right;padding-right:20px;'>Value</th>"
        "<th>Description</th>"
        "</tr></thead>"
        "<tbody>" + "".join(raw_rows) + "</tbody></table>"
        "</div>"
        "<footer><p><strong>Notes:</strong> Comment Ratio and Maintainability Index are the most "
        "size-independent indicators. All other metrics scale with project size — use them for "
        "comparison, not absolute judgment.</p></footer>"
        "</div></body></html>"
    )

    return html, metrics
