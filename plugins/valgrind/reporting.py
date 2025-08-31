from datetime import datetime
from collections import Counter, defaultdict
import html

# ---------- Theme ----------
theme = {
    "--bg": "#0f172a",
    "--panel": "#111827",
    "--soft": "#1f2937",
    "--text": "#e5e7eb",
    "--muted": "#9ca3af",
    "--pill": "#334155",
    "--accent": "#22c55e",
    "--good": "var(--accent)",
    "--warn": "#f59e0b",
    "--bad": "#ef4444",
    "--border": "#1f2937",
}

# ---------- Helpers ----------
def categorize(title: str):
    t = title.lower()
    if "definitely lost" in t or "leak" in t:
        return ("Memory Leak", "bad")
    if "use of uninitialised" in t or "uninitialized" in t:
        return ("Uninitialized Value", "warn")
    if "conditional jump" in t:
        return ("Uninitialized Use (Branch)", "warn")
    return ("Other", "warn")

def simple_explanation(cat: str):
    notes = {
        "Memory Leak": "The program asked for memory but never gave it back. Fix by deleting/freeing what you new()/malloc().",
        "Uninitialized Value": "A variable was used before it was given a starting value. Fix by assigning an initial value.",
        "Uninitialized Use (Branch)": "A decision (if/while) used a variable that wasn't set. Initialize variables before using them.",
        "Other": "Memcheck found an issue. Read the stack trace and confirm variable setup and memory management.",
    }
    return notes.get(cat, "Check variable initialization and memory management.")

def severity_color(tag: str):
    return {"good": "var(--good)", "warn": "var(--warn)", "bad": "var(--bad)"}[tag]

def escape(s: str) -> str:
    return html.escape(str(s), quote=True)

def pill(label, tone):
    return f'<span class="pill {tone}">{escape(label)}</span>'

def generate_html_report(data: dict) -> None:
  categories = []
  grouped = defaultdict(list)
  for e in data.get("errors", []):
      cat, sev = categorize(e["title"])
      categories.append((cat, sev))
      grouped[(cat, sev)].append(e)

  counts = Counter(cat for cat, _ in categories)

  leaks_bytes = (data.get("leak_summary") or {}).get("totals", {}).get("bytes_lost", 0)
  leaks_blocks = (data.get("leak_summary") or {}).get("totals", {}).get("blocks_lost", 0)
  overall_sev = "bad" if leaks_bytes > 0 else ("warn" if data["error_count"] > 0 else "good")

  # ---------- Build HTML ----------
  css_vars = "\n  ".join(f"{k}: {v};" for k, v in theme.items())
  timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

  head = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Memory Issues Report</title>
<style>
:root {{
  {css_vars}
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Noto Sans, Helvetica, Arial, "Apple Color Emoji","Segoe UI Emoji";
  background: var(--bg); color: var(--text);
}}
.wrapper {{ max-width: 1000px; margin: 40px auto; padding: 0 16px; }}
.panel {{
  background: var(--panel); border: 1px solid var(--border);
  border-radius: 16px; padding: 20px; box-shadow: 0 10px 24px rgba(0,0,0,.25);
}}
.hstack {{ display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }}
.section-title {{ margin: 24px 0 8px; font-weight: 700; font-size: 1.1rem; color: var(--text); }}
.subtitle {{ color: var(--muted); font-size: .95rem; }}
.kpi-grid {{
  display: grid; grid-template-columns: repeat(auto-fit,minmax(220px,1fr));
  gap: 12px; margin: 16px 0 8px;
}}
.kpi {{
  background: var(--soft); border: 1px solid var(--border); border-radius: 14px; padding: 16px;
}}
.kpi .label {{ color: var(--muted); font-size: .85rem; }}
.kpi .value {{ font-size: 1.6rem; font-weight: 800; margin-top: 4px; }}
.pill {{
  display: inline-block; padding: 4px 10px; border-radius: 999px; background: var(--pill); font-size: .8rem; border: 1px solid var(--border);
}}
.pill.warn {{ border-color: var(--warn); color: var(--warn); }}
.pill.bad {{ border-color: var(--bad); color: var(--bad); }}
.pill.good {{ border-color: var(--good); color: var(--good); }}
.card {{
  background: var(--soft); border: 1px solid var(--border); border-radius: 14px; padding: 14px; margin: 8px 0;
}}
.card h4 {{ margin: 0 0 6px; font-size: 1rem; }}
.stack {{ display: flex; flex-direction: column; gap: 6px; }}
.code {{
  white-space: pre-wrap; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: .85rem; color: var(--muted); background: #0b1220; padding: 10px; border-radius: 8px; border: 1px dashed var(--border);
}}
hr.div {{ border: 0; border-top: 1px solid var(--border); margin: 20px 0; }}
.footer {{ color: var(--muted); font-size: .85rem; text-align: right; }}
.badge-list {{ display: flex; gap: 6px; flex-wrap: wrap; }}
.table {{
  width: 100%; border-collapse: collapse; margin-top: 8px; font-size: .95rem;
}}
.table th, .table td {{
  padding: 10px 8px; border-bottom: 1px solid var(--border); vertical-align: top;
}}
.table th {{ text-align: left; color: var(--muted); font-weight: 600; }}
.cat-tag {{
  font-weight: 700;
}}
.tip {{ background: #052e1a; border: 1px solid #14532d; color: #a7f3d0; border-radius: 8px; padding: .4rem .6rem; margin-top: .6rem; }}
</style>
</head>
<body>
<div class="wrapper">
  <div class="panel">
    <div class="hstack" style="justify-content: space-between;">
      <div>
        <h1 style="margin:0; font-size:1.4rem;">Memory Issues Report</h1>
        <!--div class="subtitle">Tool: {escape(data['meta']['tool'])} {escape(data['meta']['version'])} · Command: {escape(data['meta']['command'])}</div-->
      </div>
      <div class="badge-list">
        {pill("Overall: " + ("Issues Found" if overall_sev!="good" else "All Good"), overall_sev)}
        {pill("Leak Status: " + escape(data['meta']['leak_status']), "bad" if leaks_bytes > 0 else "good")}
      </div>
    </div>

    <div class="kpi-grid">
      <div class="kpi">
        <div class="label">Total Errors</div>
        <div class="value">{data['error_count']}</div>
      </div>
      <div class="kpi">
        <div class="label">Memory Leaks</div>
        <div class="value">{leaks_blocks}<span class="subtitle">({leaks_bytes} bytes)</span></div>
      </div>
      <!--div class="kpi">
        <div class="label">Heap Allocs / Frees</div>
        <div class="value">{data['heap_summary']['total_heap_usage_allocs']} / {data['heap_summary']['total_heap_usage_frees']}</div>
      </div>
      <div class="kpi">
        <div class="label">Bytes Allocated</div>
        <div class="value">{data['heap_summary']['total_heap_usage_bytes_allocated']:,}</div>
      </div-->
    </div>

    <hr class="div" />

    <div class="section-title">What went wrong</div>
    <table class="table">
      <thead>
        <tr><th>Category</th><th>How to think about it</th><th>Count</th></tr>
      </thead>
      <tbody>
  """
  rows = []
  # Ensure deterministic ordering: Memory Leak, Uninitialized, Branch, Other
  order = ["Memory Leak", "Uninitialized Value", "Uninitialized Use (Branch)", "Other"]
  for cat in order:
      # find severity tag for this cat (take first match or default)
      tag = None
      for (c, sev) in grouped:
          if c == cat:
              tag = sev
              break
      if cat in counts:
          rows.append(
              f"""<tr>
  <td class="cat-tag">{pill(cat, tag or 'warn')}</td>
  <td>{escape(simple_explanation(cat))}</td>
  <td>{counts[cat]}</td>
</tr>"""
          )
  if not rows:
      rows.append('<tr><td colspan="3">🎉 No issues found</td></tr>')
  table_html = "\n".join(rows)

  errors_html = []
  for (cat, sev), items in grouped.items():
      errors_html.append(f'<div class="section-title">{escape(cat)}</div>')
      for e in items:
          stack = "\n".join(escape(line) for line in e.get("details", []))
          errors_html.append(f"""
          <div class="card">
            <div class="hstack">
              <h2 style="margin: 0">{e['title']}</h2>
              {pill(cat, sev)}
            </div>
            <div class="stack" style="margin-top:8px;">
              <div class="tip">💡 {escape(simple_explanation(cat))}</div>
              <div class="code">{e['title']}<br />{stack}</div>
            </div>
          </div>
          """)

  heap_raw = "\n".join(escape(line) for line in (data.get("heap_summary") or {}).get("raw", []))
  leak_raw = ""
  if data.get("leak_summary"):
    leak_raw = "\n".join(escape(line) for line in (data.get("leak_summary") or {}).get("raw", []))
    leak_raw = f'<div class="card"><h4>Leaks</h4><div class="code">{leak_raw}</div></div>'

  tail = f"""
        {table_html}
        </tbody>
      </table>

      <hr class="div" />

      <div class="section-title">Stack traces (for reference)</div>
      {''.join(errors_html) if errors_html else '<div class="card">No errors.</div>'}

      <hr class="div" />

      <div class="section-title">Raw summaries</div>
      <div class="card"><h4>Heap</h4><div class="code">{heap_raw}</div></div>
      {leak_raw}

      <div class="footer">Generated on {escape(timestamp)}</div>
    </div>
  </div>
  </body></html>
  """

  html_doc = head + tail
  return html_doc
