from datetime import datetime
import os

def build_single_report(items, output_path, title="Quality Metrics Report") -> None:
    card_html = []
    for it in items:
        name = it.get("name", "Untitled")
        desc = it.get("description", "")
        path = it.get("path", "#")
        card_html.append(f"""
          <a class="card" href="{path}">
            <div class="card-name">{name}</div>
            <div class="card-desc">{desc}</div>
            <div class="card-pill">{path}</div>
          </a>
        """)
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
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
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 28px; background: var(--bg); color: var(--text);
    font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
  }}
  header {{
    display: flex; align-items: baseline; justify-content: space-between; gap: 12px;
    margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid var(--soft);
  }}
  h1 {{ margin: 0; font-size: 28px; letter-spacing: .2px; }}
  .meta {{ color: var(--muted); font-size: 13px; }}
  .grid {{
    display: grid; gap: 14px;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  }}
  .card {{
    background: linear-gradient(180deg, var(--panel), var(--soft));
    border: 1px solid var(--soft);
    border-radius: 16px;
    padding: 16px;
    text-decoration: none;
    color: var(--text);
    box-shadow: 0 12px 22px rgba(0,0,0,.25);
    transition: transform .12s ease, border-color .12s ease, box-shadow .12s ease;
    display: grid; gap: 10px;
  }}
  .card:hover {{
    transform: translateY(-2px);
    border-color: var(--accent);
    box-shadow: 0 14px 28px rgba(0,0,0,.3);
  }}
  .card-name {{ font-weight: 700; font-size: 18px; }}
  .card-desc {{ color: var(--muted); line-height: 1.45; min-height: 40px; }}
  .card-pill {{
    align-self: end; width: fit-content; font-size: 12px; color: var(--text);
    background: var(--pill); border: 1px solid var(--soft);
    padding: 6px 10px; border-radius: 999px;
  }}
  .toolbar {{ display: flex; gap: 10px; margin-bottom: 16px; }}
  .search {{
    flex: 1; background: var(--panel); border: 1px solid var(--soft); border-radius: 12px;
    padding: 10px 12px; color: var(--text); outline: none;
  }}
</style>
</head>
<body>
  <header>
    <h1>{title}</h1>
    <div class="meta">Generated {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
  </header>

  <div class="toolbar">
    <input class="search" id="search" placeholder="Filter cards by name or description…" oninput="filterCards(this.value)">
  </div>

  <div class="grid" id="grid">
    {''.join(card_html)}
  </div>

<script>
  function normalize(s) {{ return (s||'').toLowerCase(); }}
  function filterCards(q) {{
    const needle = normalize(q);
    const cards = document.querySelectorAll('.card');
    for (const c of cards) {{
      const name = normalize(c.querySelector('.card-name')?.textContent);
      const desc = normalize(c.querySelector('.card-desc')?.textContent);
      c.style.display = (name.includes(needle) || desc.includes(needle)) ? '' : 'none';
    }}
  }}
</script>
</body>
</html>"""
    with open(os.path.join(output_path, "report.html"), "w") as f:
        f.write(html_content)