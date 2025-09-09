from typing import Any, Dict, List, Union
from datetime import datetime
from html import escape
import os
import json
import math
import re

def clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))

def pct(n: float, d: float) -> float:
    try:
        return clamp((n / d) * 100.0)
    except Exception:
        return 0.0

def short(text: str, max_len: int = 160) -> str:
    t = (text or "").strip()
    return (t if len(t) <= max_len else t[: max_len - 1] + "…")

def nice_num(x: Union[int, float]) -> str:
    if isinstance(x, (int,)) or (isinstance(x, float) and x.is_integer()):
        return f"{int(x)}"
    if abs(x) >= 1000:
        return f"{x:,.2f}"
    return f"{x:.3g}"

def badge(label: str, count: Union[int, float, None] = None) -> str:
    count_html = f"<span class='badge-count'>{nice_num(count)}</span>" if count is not None else ""
    return f"<span class='badge'>{escape(label)}{count_html}</span>"

def progress(label: str, value: float, tooltip: str = "") -> str:
    value = clamp(value)
    title = escape(tooltip or f"{value:.0f}%")
    return f"""
    <div class="progress">
      <div class="progress-top">
        <span class="progress-label">{escape(label)}</span>
        <span class="progress-val">{value:.0f}%</span>
      </div>
      <div class="progress-bar" title="{title}">
        <div class="progress-fill" style="width:{value:.2f}%"></div>
      </div>
    </div>
    """

def humanize(check: str) -> str:
  check = check.replace("-", " ").replace("_", " ")
  check = re.sub(r'([a-z])([A-Z])', r'\1 \2', check)
  check = check.replace(".", " ")
  check = check.title()
  return check

def kv_table(d: Dict[str, Any], limit: int = 6) -> str:
    items = list(d.items())[:limit]
    rows = []
    for k, v in items:
        if isinstance(v, (int, float)):
            v_str = nice_num(v)
        elif isinstance(v, str):
            v_str = short(v, 120)
        else:
            v_str = short(json.dumps(v, ensure_ascii=False), 120)
        rows.append(f"<div class='kv'><div class='k'>{escape(str(k))}</div><div class='v'>{escape(v_str)}</div></div>")
    return "<div class='kv-grid'>" + "".join(rows) + "</div>"

def render_summary(name: str, summary: Any) -> str:
    """
    Smartly renders the "summary" field depending on its structure.
    """
    # Special handling: Test Results with scores
    if isinstance(summary, dict) and {"total_score", "obtained_score"} <= summary.keys():
        total = float(summary.get("total_score", 0))
        got = float(summary.get("obtained_score", 0))
        score_pct = pct(got, total) if total else 0.0
        parts = [progress("Score", score_pct, f"{nice_num(got)} / {nice_num(total)}")]
        fails = summary.get("failures") or []
        lis = []
        if isinstance(fails, list) and len(fails) > 0:
            f = fails[0]
            fail_title = f.get("name") or "Failure"
            fail_line = f.get("failed_check") or ""
            # fail_val  = f.get("failed_value") or ""
            lis.append(f"""
              <li>
                <div class="li-title">{escape(fail_title)}</div>
                <div class="li-body mono">{escape(fail_line)}</div>
              </li>""")
        return "<ul class='issue-list'>" + "".join(lis) + "</ul>"
        #     parts.append(f"""
        #       <div class="callout ">
        #         <div class="callout-body">
        #           <div class="callout-line"><strong>{escape(short(fail_title, 80))}</strong></div>
        #           <div class="callout-line mono">{escape(short(fail_line, 140))}</div>
        #           <div class="callout-line faint mono">{escape(short(fail_val, 140))}</div>
        #         </div>
        #       </div>
        #     """)
        #     if len(fails) > 1:
        #         parts.append(f"<div class='muted tiny'>+{len(fails)-1} more failure(s)…</div>")
        # return "\n".join(parts)

    # Special handling: clang-tidy style categories
    if isinstance(summary, dict) and "cat_totals" in summary:
        cat_totals: Dict[str, Any] = summary.get("cat_totals", {})
        cat_items: Dict[str, List[Dict[str, Any]]] = summary.get("cat_items", {})
        badges = "".join(badge(k, v) for k, v in cat_totals.items())
        # Show one representative issue with a tip if present
        # example = ""
        lis = []
        for cat, lst in cat_items.items():
            if lst:
                ex = lst[0]
                tip = ex.get("tip") or ""
                lis.append(f"""
                  <li>
                    <div class="li-title">{escape(ex.get('check', ''))}</div>
                    <div class="li-body">{escape(short(tip if tip else "", 160))}</div>
                  </li>""")
        return "<ul class='issue-list'>" + "".join(lis) + "</ul>"
        #         example += f"""
        #         <div class="callout ">
        #           <div class="callout-title">{escape(ex.get('check', ''))}</div>
        #           <div class="callout-body">
        #             {f"<div class='callout-line'>{escape(short(tip, 160))}</div>" if tip else ""}
        #           </div>
        #         </div>"""
        #         # break
        # return f"<div class='badge-row'>{badges}</div>{example}"

    # Special handling: memory report (Valgrind-like): dict of issue->explanation
    if isinstance(summary, dict) and all(isinstance(v, str) for v in summary.values()):
        # show up to three
        items = list(summary.items())[:3]
        lis = []
        for k, v in items:
            lis.append(f"""
              <li>
                <div class="li-title">{escape(short(k, 120))}</div>
                <div class="li-body">{escape(short(v, 200))}</div>
              </li>""")
        return "<ul class='issue-list'>" + "".join(lis) + "</ul>"

    # Special handling: software quality metrics (has maintainability_index or cyclomatic)
    if isinstance(summary, dict) and any(k in summary for k in ("maintainability_index", "cyclomatic")):
        parts = []
        if "maintainability_index" in summary:
            mi = float(summary.get("maintainability_index", 0))
            # MI can vary widely; normalize gently into 0-100
            mi_norm = clamp(mi if 0 <= mi <= 100 else 100.0 * (1 - math.exp(-mi / 40.0)))
            parts.append(progress("Maintainability", mi_norm, f"MI: {nice_num(mi)}"))
        if "cyclomatic" in summary:
            cyc = float(summary.get("cyclomatic", 0))
            cyc_norm = clamp(100.0 * max(0.0, 1.0 - (cyc / 20.0)))  # fewer is better
            parts.append(progress("Cyclomatic (lower is better)", cyc_norm, f"CC: {nice_num(cyc)}"))
        # Add a small key/value grid
        hide = ("maintainability_index", "cyclomatic", "halstead_n1", "halstead_n2", "halstead_N1", "halstead_N2")
        parts.append(kv_table({humanize(k): v for k, v in summary.items() if k not in hide}, limit=6))
        return "\n".join(parts)

    # Fallback: render first few keys/values compactly
    if isinstance(summary, dict):
        return kv_table(summary, limit=6)
    if isinstance(summary, list):
        items = [f"<li>{escape(short(json.dumps(x, ensure_ascii=False), 160))}</li>" for x in summary[:5]]
        return "<ul class='bullets'>" + "".join(items) + "</ul>"
    if isinstance(summary, str):
        return f"<p>{escape(short(summary, 240))}</p>"
    return f"<p class='muted'>No summary available</p>"

# -------------------------
# 3) HTML template
# -------------------------

def build_html(data: List[Dict[str, Any]], title: str = "Project Reports") -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    cards_html = []
    for entry in data:
        name = str(entry.get("name", "Untitled"))
        desc = str(entry.get("description", ""))
        path = str(entry.get("path", "#")) or "#"
        summary = entry.get("summary", None)
        # card
        cards_html.append(f"""
        <a class="card" href="{escape(path)}">
          <div class="card-top">
            <div class="card-icon" aria-hidden="true">
              <!-- simple doc icon -->
              <svg viewBox="0 0 24 24" width="24" height="24">
                <path d="M6 2h8l6 6v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z" fill="currentColor" opacity="0.12"/>
                <path d="M14 2v6h6" stroke="currentColor" fill="none" stroke-width="1.5"/>
              </svg>
            </div>
            <div class="card-headings">
              <div class="card-title">{escape(name)}</div>
              <div class="card-desc">{escape(short(desc, 140))}</div>
            </div>
          </div>
          <div class="card-body">
            {render_summary(name, summary)}
          </div>
          <div class="card-foot">
            <span class="foot-left mono">{escape(path)}</span>
            <span class="chip">Open</span>
          </div>
        </a>
        """)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>{escape(title)}</title>
<style>
  :root {{
    --bg: #0f172a;
    --panel: #121621;
    --panel-2: #161b29;
    --text: #e9eefb;
    --muted: #9aa7bd;
    --faint: #7b869a;
    --accent: #6ea8fe;   /* blue */
    --accent-2: #9b87f5;  /* violet */
    --green: #37d39e;
    --yellow: #ffd166;
    --red: #ff6b6b;
    --ring: rgba(110,168,254,0.28);
    --shadow: 0 6px 24px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.03);
    --radius-xl: 18px;
    --radius-lg: 14px;
    --radius-md: 12px;
  }}
  @media (prefers-color-scheme: light) {{
    :root {{
      --bg: #0f172a;
      --panel: #ffffff;
      --panel-2: #f0f3f9;
      --text: #0e1320;
      --muted: #46546d;
      --faint: #6c7a92;
      --accent: #2563eb;
      --ring: rgba(37,99,235,0.20);
      --shadow: 0 4px 18px rgba(19,28,45,0.08), inset 0 1px 0 rgba(255,255,255,0.6);
    }}
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ height: 100%; }}
  body {{
    margin: 0;
    font: 14px/1.5 system-ui, -apple-system, Segoe UI, Roboto, Inter, "Helvetica Neue", Arial, "Apple Color Emoji","Segoe UI Emoji";
    color: var(--text);
    /*background: radial-gradient(1200px 600px at 20% -10%, rgba(110,168,254,0.08), transparent 60%),
                radial-gradient(1000px 600px at 80% -20%, rgba(155,135,245,0.10), transparent 60%),
                var(--bg);*/
    background: var(--bg);
  }}
  /*.wrap {{
    max-width: 1100px;
    margin: 48px auto;
    padding: 0 20px 40px;
  }}*/
  .wrap {{ max-width: 1000px; margin: 40px auto; padding: 0 16px; }}
  header {{
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 22px;
  }}
  h1 {{
    margin: 0;
    font-size: 28px; letter-spacing: 0.2px;
    display: flex; align-items: center; gap: 10px;
  }}
  .subtitle {{ color: var(--muted); margin-top: 6px; }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(12, 1fr);
    gap: 16px;
  }}
  @media (max-width: 700px) {{
    .grid {{ grid-template-columns: repeat(6, 1fr); }}
  }}
  .card {{
    grid-column: span 6;
    display: flex; flex-direction: column;
    text-decoration: none; color: inherit;
    padding: 16px;
    background: linear-gradient(180deg, var(--panel), var(--panel-2));
    border-radius: var(--radius-xl);
    box-shadow: var(--shadow);
    border: 1px solid rgba(255,255,255,0.04);
    transition: transform .15s ease, box-shadow .15s ease, border-color .15s ease;
    position: relative; overflow: hidden;
  }}
  .card:hover {{ transform: translateY(-2px); box-shadow: 0 10px 34px rgba(0,0,0,0.45); border-color: var(--ring); }}
  .card:active {{ transform: translateY(0); }}
  .card::after {{
    content: ""; position: absolute; inset: -1px;
    border-radius: inherit; pointer-events: none;
    background: linear-gradient(135deg, rgba(110,168,254,0.12), rgba(155,135,245,0.10) 30%, transparent 60%);
    mask: radial-gradient(300px 200px at 20% -30%, #000 40%, transparent 60%);
  }}
  .card-top {{ display: flex; gap: 12px; align-items: center; margin-bottom: 10px; }}
  .card-icon {{
    width: 44px; height: 44px; border-radius: 12px;
    background: linear-gradient(135deg, rgba(110,168,254,0.22), rgba(155,135,245,0.18));
    display: grid; place-items: center; color: var(--accent);
    border: 1px solid rgba(255,255,255,0.08);
  }}
  .card-title {{ font-weight: 700; font-size: 16px; letter-spacing: 0.2px; }}
  .card-desc {{ color: var(--muted); font-size: 13px; margin-top: 2px; }}
  .card-body {{ margin-top: 6px; display: grid; gap: 10px; flex: 1 }}
  .card-foot {{
    display: flex; align-items: center; justify-content: space-between;
    margin-top: 10px; padding-top: 10px; border-top: 1px dashed rgba(255,255,255,0.08);
  }}
  .chip {{
    font-size: 12px; padding: 6px 10px; border-radius: 999px;
    background: rgba(110,168,254,0.18); color: var(--text); border: 1px solid rgba(110,168,254,0.35);
  }}
  .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, "Roboto Mono", Consolas, "Liberation Mono", monospace; }}
  .muted {{ color: var(--muted); }}
  .faint {{ color: var(--faint); }}
  .tiny {{ font-size: 12px; }}

  /* Badges */
  .badge-row {{ display: flex; flex-wrap: wrap; gap: 8px; }}
  .badge {{
    display: inline-flex; align-items: center; gap: 8px;
    padding: 6px 10px; border-radius: 999px; font-size: 12px;
    background: rgba(155,135,245,0.16); border: 1px solid rgba(155,135,245,0.38);
  }}
  .badge-count {{
    display: inline-grid; place-items: center; min-width: 20px; height: 20px; padding: 0 6px;
    border-radius: 10px; background: rgba(255,255,255,0.12);
    font-variant-numeric: tabular-nums;
  }}

  /* Progress */
  .progress {{ display: grid; gap: 6px; }}
  .progress-top {{ display: flex; justify-content: space-between; align-items: baseline; }}
  .progress-label {{ font-size: 12px; color: var(--muted); }}
  .progress-val {{ font-size: 12px; color: var(--text); }}
  .progress-bar {{
    width: 100%; height: 10px; border-radius: 999px;
    background: rgba(255,255,255,0.06); overflow: hidden; border: 1px solid rgba(255,255,255,0.08);
  }}
  .progress-fill {{
    height: 100%; background: linear-gradient(90deg, var(--accent), var(--accent-2));
  }}

  /* Callouts */
  .callout {{ border-radius: var(--radius-md); padding: 10px 12px; border: 1px solid transparent; }}
  .callout .callout-title {{ font-weight: 600; margin-bottom: 6px; }}
  .callout .callout-line {{ margin: 3px 0; }}
  .callout.error {{
    background: rgba(255,107,107,0.08); border-color: rgba(255,107,107,0.35);
  }}
  .callout.warn {{
    background: rgba(255,209,102,0.10); border-color: rgba(255,209,102,0.38);
  }}

  /* Issue list */
  .issue-list {{ margin: 0; padding-left: 18px; }}
  .issue-list .li-title {{ font-weight: 600; }}
  .issue-list .li-body {{ color: var(--muted); }}

  /* Key/Value grid */
  .kv-grid {{
    display: grid; gap: 6px; grid-template-columns: repeat(2, minmax(0, 1fr));
  }}
  .kv {{ display: grid; grid-template-columns: 1fr auto; gap: 8px; align-items: baseline;
        padding: 8px 10px; border: 1px dashed rgba(255,255,255,0.08);
        border-radius: var(--radius-lg); background: rgba(255,255,255,0.03); }}
  .kv .k {{ color: var(--muted); font-size: 12px; }}
  .kv .v {{ font-size: 13px; }}

  /* Footer */
  footer {{ margin-top: 26px; color: var(--muted); font-size: 13px; text-align: center; }}
</style>
</head>
<body>
  <div class="wrap">
    <header>
      <div>
        <h1>Quality Metrics Report</h1>
        <div class="subtitle">Summary of key quality metrics</div>
      </div>
      <div class="tiny muted mono">{escape(now)}</div>
    </header>
    <section class="grid">
      {''.join(cards_html)}
    </section>
    <!--footer>
      Generated by Python • No external CSS/JS required
    </footer-->
  </div>
</body>
</html>
"""

def build_single_report(items, output_path):
    html = build_html(items)
    with open(os.path.join(output_path, "report.html"), "w") as f:
        f.write(html)

# def build_single_report(items, output_path, title="Quality Metrics Report") -> None:
#     card_html = []
#     for it in items:
#         name = it.get("name", "Untitled")
#         desc = it.get("description", "")
#         path = it.get("path", "#")
#         card_html.append(f"""
#           <a class="card" href="{path}">
#             <div class="card-name">{name}</div>
#             <div class="card-desc">{desc}</div>
#             <div class="card-pill">{path}</div>
#           </a>
#         """)
#     html_content = f"""<!DOCTYPE html>
# <html lang="en">
# <head>
# <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
# <title>{title}</title>
# <style>
#   :root {{
#     --bg: #0f172a;        /* slate-900 */
#     --panel: #111827;     /* gray-900 */
#     --soft: #1f2937;      /* gray-800 */
#     --text: #e5e7eb;      /* gray-200 */
#     --muted: #9ca3af;     /* gray-400 */
#     --pill: #334155;      /* slate-700 */
#     --accent: #22c55e;    /* green-500 */
#   }}
#   * {{ box-sizing: border-box; }}
#   body {{
#     margin: 0; padding: 28px; background: var(--bg); color: var(--text);
#     font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
#   }}
#   .wrapper {{ max-width: 1000px; margin: 40px auto; padding: 0 16px; }}
#   header {{
#     display: flex; align-items: baseline; justify-content: space-between; gap: 12px;
#     margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid var(--soft);
#   }}
#   h1 {{ margin: 0; font-size: 28px; letter-spacing: .2px; }}
#   .meta {{ color: var(--muted); font-size: 13px; }}
#   .grid {{
#     display: grid; gap: 14px;
#     grid-template-columns: repeat(auto-fit, minmax(315px, 1fr));
#   }}
#   .card {{
#     background: linear-gradient(180deg, var(--panel), var(--soft));
#     border: 1px solid var(--soft);
#     border-radius: 16px;
#     padding: 16px;
#     text-decoration: none;
#     color: var(--text);
#     box-shadow: 0 12px 22px rgba(0,0,0,.25);
#     transition: transform .12s ease, border-color .12s ease, box-shadow .12s ease;
#     display: grid; gap: 10px;
#   }}
#   .card:hover {{
#     transform: translateY(-2px);
#     border-color: var(--accent);
#     box-shadow: 0 14px 28px rgba(0,0,0,.3);
#   }}
#   .card-name {{ font-weight: 700; font-size: 18px; }}
#   .card-desc {{ color: var(--muted); line-height: 1.45; min-height: 40px; }}
#   .card-pill {{
#     align-self: end; width: fit-content; font-size: 12px; color: var(--text);
#     background: var(--pill); border: 1px solid var(--soft);
#     padding: 6px 10px; border-radius: 999px;
#   }}
#   .toolbar {{ display: flex; gap: 10px; margin-bottom: 16px; }}
#   .search {{
#     flex: 1; background: var(--panel); border: 1px solid var(--soft); border-radius: 12px;
#     padding: 10px 12px; color: var(--text); outline: none;
#   }}
# </style>
# </head>
# <body>
#   <div class="wrapper">
#     <header>
#       <h1>{title}</h1>
#       <div class="meta">Generated {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
#     </header>

#     <div class="toolbar">
#       <input class="search" id="search" placeholder="Filter cards by name or description…" oninput="filterCards(this.value)">
#     </div>

#     <div class="grid" id="grid">
#       {''.join(card_html)}
#     </div>

#   <script>
#     function normalize(s) {{ return (s||'').toLowerCase(); }}
#     function filterCards(q) {{
#       const needle = normalize(q);
#       const cards = document.querySelectorAll('.card');
#       for (const c of cards) {{
#         const name = normalize(c.querySelector('.card-name')?.textContent);
#         const desc = normalize(c.querySelector('.card-desc')?.textContent);
#         c.style.display = (name.includes(needle) || desc.includes(needle)) ? '' : 'none';
#       }}
#     }}
#   </script>
#   </div>
# </body>
# </html>"""
#     with open(os.path.join(output_path, "report.html"), "w") as f:
#         f.write(html_content)