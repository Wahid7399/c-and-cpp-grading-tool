import html
from datetime import datetime
import re

def humanize(check: str) -> str:
  check = check.replace("-", " ").replace("_", " ")
  check = re.sub(r'([a-z])([A-Z])', r'\1 \2', check)
  check = check.replace(".", " ")
  check = check.title()
  return check

def generate_html_report(data: dict, title: str = "Style & Security Report"):
  metrics = data.get("metrics", {})
  rows = data.get("raw", [])

  # Simple severity → color mapping
  sev_color = {
      "error":        "#6a5a5a",   # green for visibility
      "warning":      "#706b5f",         # amber-400
      "style":        "#495a75",         # blue-500
      "performance":  "#594869",         # purple-500
      "portability":  "#664556",         # pink-500
      "information":  "#9ca3af",
  }

  # Build metrics HTML
  metrics_rows = "\n".join(
    f"<tr><td>{html.escape(humanize(str(k)))}</td><td>{html.escape(str(v))}</td></tr>"
    for k, v in metrics.items()
  ) or '<tr><td colspan="2" style="color:#666">No metrics</td></tr>'

  # Build issues HTML
  issue_rows = []
  for r in rows:
    name = html.escape(str(r.get("name", "")))
    sev  = str(r.get("severity", "")).lower()
    msg  = html.escape(str(r.get("message", "")))
    loc  = r.get("location", {}) or {}
    fpath = html.escape(str(loc.get("file", "")))
    line  = html.escape(str(loc.get("line", "")))
    col   = html.escape(str(loc.get("column", "")))
    bg    = sev_color.get(sev, "#ffffff")
    issue_rows.append(
        f'<tr style="background:{bg}">'
        f"<td>{humanize(name)}</td>"
        f"<td>{html.escape(sev)}</td>"
        f"<td>{msg}</td>"
        f"<td><code>{fpath}</code></td>"
        f"<td>{line}</td>"
        f"<td>{col}</td>"
        f"</tr>"
    )
  issues_html = "\n".join(issue_rows) or '<tr><td colspan="6" style="color:#666">No issues</td></tr>'

  # Minimal, clean HTML with inline CSS
  now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>
:root {{
  --bg: #0f172a;        /* slate-900 */
  --panel: #111827;     /* gray-900 */
  --soft: #1f2937;      /* gray-800 */
  --text: #e5e7eb;      /* gray-200 */
  --muted: #9ca3af;     /* gray-400 */
  --pill: #334155;      /* slate-700 */
  --accent: #22c55e;    /* green-500 */
}}
body {{
  background: var(--bg);
  color: var(--text);
  font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
  margin: 24px;
}}
h1, h2 {{ color: var(--text); }}
.sub {{ color: var(--muted); margin-bottom: 16px; }}
.card {{
  background: var(--panel);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 24px;
  box-shadow: 0 1px 4px rgba(0,0,0,.5);
}}
table {{
  border-collapse: collapse;
  width: 100%;
  margin: 12px 0;
}}
th, td {{
  border: 1px solid var(--soft);
  padding: 8px 10px;
  vertical-align: top;
}}
th {{
  background: var(--soft);
  color: var(--text);
  text-align: left;
}}
code {{
  background: var(--pill);
  color: var(--text);
  padding: 2px 4px;
  border-radius: 4px;
}}
.muted {{ color: var(--muted); }}
</style>
</head>
<body>
  <h1>{html.escape(title)}</h1>
  <div class="sub">Generated: {now}</div>

  <div class="card">
    <h2>Summary Metrics</h2>
    <table>
      <thead><tr><th>Metric</th><th>Value</th></tr></thead>
      <tbody>{metrics_rows}</tbody>
    </table>
  </div>

  <div class="card">
    <h2>Issues</h2>
    <table>
      <thead>
        <tr>
          <th>Rule</th>
          <th>Severity</th>
          <th>Message</th>
          <th>File</th>
          <th>Line</th>
          <th>Col</th>
        </tr>
      </thead>
      <tbody>{issues_html}</tbody>
    </table>
  </div>
</body>
</html>"""
  return html_doc