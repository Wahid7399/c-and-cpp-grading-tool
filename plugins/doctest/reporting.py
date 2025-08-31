from datetime import datetime
from pathlib import Path
import html

PALETTE = {
    "bg": "#0f172a",       # slate-900
    "panel": "#111827",    # gray-900
    "soft": "#1f2937",     # gray-800
    "text": "#e5e7eb",     # gray-200
    "muted": "#9ca3af",    # gray-400
    "pill": "#334155",     # slate-700
    "accent": "#22c55e",   # green-500
}

def grade_from_pct(pct: float):
    if pct >= 90:  return "A", "Excellent work, keep it up!"
    if pct >= 80:  return "B", "Great job, just a little more polish."
    if pct >= 70:  return "C", "Good effort, review the tricky parts."
    if pct >= 60:  return "D", "Could improve, let’s revisit core concepts."
    return "F", "Let’s practice more, ask for help if needed."

def generate_html_report(data: dict) -> str:
    # Extract (with friendly defaults for a “student” vibe)
    student = str(data.get("student", "Student"))
    subject = str(data.get("subject", "Assessment"))
    total_cases = int(data.get("total_cases", 0))
    passed = int(data.get("passed", 0))
    failed = int(data.get("failed", 0))
    total_score = float(data.get("total_score", 0))
    obtained = float(data.get("obtained_score", 0))
    failures = data.get("failures", []) or []

    pass_rate = (passed / total_cases * 100.0) if total_cases else 0.0
    score_pct = (obtained / total_score * 100.0) if total_score else 0.0
    letter, remark = grade_from_pct(score_pct)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Failure rows
    if failures:
        rows = []
        for f in failures:
            rows.append(f"""
            <tr>
              <td class="num">{html.escape(str(f.get("number","")))}</td>
              <td class="name">{html.escape(str(f.get("name","")))}</td>
              <td class="score">{html.escape(str(f.get("score","")))}</td>
              <td class="check"><code>{html.escape(str(f.get("failed_check","")))}</code></td>
              <td class="value"><code>{html.escape(str(f.get("failed_value","")))}</code></td>
            </tr>""")
        failures_table = "\n".join(rows)
    else:
        failures_table = '<tr><td colspan="5" class="empty"><div class="value big">🎉</div><br /><br />No mistakes, Amazing work!</td></tr>'

    # Status chip
    if failed == 0 and total_cases > 0:
        status = "All Correct"
        status_tone = "good"
    elif passed > 0 and failed > 0:
        status = "Mixed Results"
        status_tone = "warn"
    else:
        status = "Needs Attention"
        status_tone = "bad"

    css = f"""
:root {{
  --bg: {PALETTE['bg']};
  --panel: {PALETTE['panel']};
  --soft: {PALETTE['soft']};
  --text: {PALETTE['text']};
  --muted: {PALETTE['muted']};
  --pill: {PALETTE['pill']};
  --accent: {PALETTE['accent']};
  --good: var(--accent);
  --warn: #f59e0b;
  --bad: #ef4444;
  --border: #1f2937;
}}
* {{ box-sizing: border-box; }}
html, body {{ margin:0; padding:0; background:var(--bg); color:var(--text); font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif; }}
.container {{ max-width: 1000px; margin: 36px auto 60px; padding: 0 20px; }}

.header {{
  display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:16px;
}}
.title-group .title {{ font-weight:800; font-size:1.6rem; }}
.title-group .subtitle {{ color:var(--muted); font-size:0.95rem; margin-top:4px; }}
.badge {{
  padding:8px 12px; border-radius:999px; background:var(--soft); color:var(--muted); border:1px solid var(--border);
}}
.badge.good {{ color:var(--good); }}
.badge.warn {{ color:var(--warn); }}
.badge.bad  {{ color:var(--bad); }}

.panel {{
  background: linear-gradient(180deg, var(--panel), var(--soft));
  border:1px solid var(--border); border-radius:16px; padding:18px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.35);
}}

.grid {{ display:grid; gap:14px; grid-template-columns: repeat(4, minmax(0,1fr)); }}
@media (max-width: 900px) {{ .grid {{ grid-template-columns: repeat(2, minmax(0,1fr)); }} }}
@media (max-width: 560px) {{ .grid {{ grid-template-columns: 1fr; }} }}

.card {{ background:var(--panel); border:1px solid var(--border); border-radius:14px; padding:14px; }}
.label {{ color:var(--muted); font-size:0.9rem; }}
.value {{ font-weight:800; font-size:1.5rem; margin-top:6px; }}
.value.big {{
  font-size:3rem; line-height:1; font-weight:900; margin-top: 15px; text-align: center;
}}

.kpi {{ margin-top:8px; display:flex; gap:8px; flex-wrap:wrap; }}
.pill {{ background:var(--pill); color:var(--text); border:1px solid var(--border); padding:4px 10px; border-radius:999px; font-size:0.85rem; }}
.pill.good {{ color:var(--good); }}
.pill.warn {{ color:var(--warn); }}
.pill.bad  {{ color:var(--bad); }}

.progress {{ height:12px; border-radius:999px; background: #0b1222; border:1px solid var(--border); overflow:hidden; margin-top:8px; }}
.progress > span {{ display:block; height:100%; width:{pass_rate:.4f}%; background: linear-gradient(90deg, var(--accent), #86efac); }}
.progress.score > span {{ width:{score_pct:.4f}%; }}

.section-title {{ font-size:1.05rem; color:var(--muted); margin:18px 2px 10px; }}

.hero {{
  display:flex; gap:16px; flex-wrap:wrap; align-items:stretch;
}}
.hero .left {{ flex:2 1 600px; }}
.hero .right {{ flex:1 1 180px; }}

.grade-card .grade {{
  font-size:3rem; line-height:1; font-weight:900; margin-top: 15px; text-align: center;
}}
.grade-card .remark {{ color:var(--muted); margin-top:6px; }}

.table-wrap {{ overflow-x:auto; }}
table {{ width:100%; border-collapse:collapse; }}
thead th {{
  text-align:left; color:var(--muted); padding:12px 10px; font-size:0.9rem; border-bottom:1px solid var(--border);
}}
tbody td {{
  padding:12px 10px; border-bottom:1px dashed var(--border); vertical-align:top;
}}
tbody tr:hover {{ background: rgba(255,255,255,0.03); }}
td.num, td.score {{ white-space:nowrap; color:var(--muted); }}
td.name {{ font-weight:600; }}
code {{ background:#0b1222; border:1px solid var(--border); border-radius:8px; padding:2px 6px; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size:0.9rem; }}
.empty {{ text-align:center; color:var(--muted); padding:24px; }}

.footer {{ margin-top:16px; color:var(--muted); display:flex; justify-content:space-between; flex-wrap:wrap; gap:8px; }}

@media print {{
  .panel, .card {{ box-shadow:none; }}
  .badge {{ border:1px solid #888; }}
}}
"""

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>Code Test Results</title>
<style>{css}</style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="title-group">
        <div class="title">Code Test Results</div>
        <div class="subtitle">Generated {html.escape(timestamp)}</div>
      </div>
      <div class="badge {status_tone}">{html.escape(status)}</div>
    </div>

    <div class="hero">
      <div class="left">
        <div class="panel">
          <div class="grid">
            <div class="card">
              <div class="label">Total Tests</div>
              <div class="value big">{total_cases}</div>
              <!--div class="kpi"><span class="pill">Correct {passed}</span><span class="pill bad">Incorrect {failed}</span></div-->
            </div>

            <div class="card">
              <div class="label">Score</div>
              <div class="value">{int(obtained) if obtained.is_integer() else obtained} / {int(total_score) if float(total_score).is_integer() else total_score}</div>
              <div class="progress score" title="Correct answers: {score_pct:.2f}%"><span></span></div>
              <div class="kpi"><span class="pill {'good' if score_pct>=80 else ('warn' if score_pct>=60 else 'bad')}">{score_pct:.0f}%</span></div>
            </div>

            <div class="card">
              <div class="label">Correctness</div>
              <div class="value">{passed} / {total_cases}</div>
              <div class="progress" title="Correct answers: {pass_rate:.2f}%"><span></span></div>
              <div class="kpi"><span class="pill {'good' if pass_rate>=80 else ('warn' if pass_rate>=60 else 'bad')}">{pass_rate:.0f}%</span></div>
            </div>

            <div class="card grade-card">
              <div class="label">Grade</div>
              <div class="grade" style="color:{'var(--good)' if score_pct>=80 else ('var(--warn)' if score_pct>=60 else 'var(--bad)')}">{letter}</div>
              <!--div class="remark">{html.escape(remark)}</div-->
            </div>
          </div>
        </div>
      </div>

      <div class="right">
        <div class="panel" style="height:100%;">
          <div class="label">Teacher’s Note</div>
          <div class="value" style="font-size:1.05rem;">{html.escape(remark)}</div>
          <!--div class="kpi" style="margin-top:10px;">
            <span class="pill">Reviewed</span>
            <span class="pill">Dark Mode</span>
            <span class="pill">Auto-graded</span>
          </div-->
        </div>
      </div>
    </div>

    <div class="section-title">Mistakes to Review</div>
    <div class="panel">
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Test</th>
              <th>Points</th>
              <th>Expected</th>
              <th>Evaluated</th>
            </tr>
          </thead>
          <tbody>
            {failures_table}
          </tbody>
        </table>
      </div>
      <div class="footer">
        <div>Keep practicing the highlighted topics. Small, consistent review beats cramming!</div>
        <div></div>
      </div>
    </div>
  </div>
</body>
</html>
"""

    return html_doc
