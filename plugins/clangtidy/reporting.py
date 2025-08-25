import re
import html
from collections import defaultdict, Counter
from datetime import datetime

def generate_html_report(results: dict, log: str):
    """
    Build a beginner-friendly HTML report from a clang-tidy results.json (your summarized metrics)
    and a raw clang-tidy log (with code frames and pointer/underline lines). The report:
      - Shows overall metrics with friendly names & colors (via mapping dicts)
      - Breaks issues down by severity, check, and file
      - Preserves and embeds original code frames with ^ and ~ indicators
      - Collapses detailed items by file for easy reading

    Args:
        results_json_path: Path to results.json (schema like the one you posted)
        log_path: Path to raw clang-tidy log (stdout/stderr concatenated)
        output_html_path: Path to write the generated HTML file
    """

    # ---------- Mapping dicts (customize freely) ----------
    category_friendly = {
        "identifier_naming_violations": ("Identifier Naming", "Names should follow a consistent style (e.g., lowerCamelCase for variables)."),
        "cognitive_complexity_violations": ("Cognitive Complexity", "Functions should be simple; break down deeply nested logic."),
        "readability_violations": ("Readability", "Prefer clear names, smaller functions, and const-correctness."),
        "correctness_violations": ("Correctness", "Resolve compile errors and undefined/invalid code paths first."),
        "performance_violations": ("Performance", "Avoid unnecessary copies; use efficient algorithms and containers."),
        "guidelines_violations": ("Guidelines", "General standards (e.g., modern C++ best practices)."),
    }

    severity_colors = {
        "error":    "#e03131",  # red
        "warning":  "#f08c00",  # orange
        "note":     "#2f9e44",  # green (notes are usually supporting info)
        "info":     "#228be6",  # blue (fallback)
    }

    # Optional: map specific check names to a broader category and quick tip.
    # Add/adjust as you meet more checks.
    check_category_map = {
        "readability-function-cognitive-complexity": "cognitive_complexity_violations",
        "readability-identifier-length": "identifier_naming_violations",
        "readability-identifier-naming": "identifier_naming_violations",
        "readability-non-const-parameter": "readability_violations",
        "clang-analyzer-cplusplus.NewDeleteLeaks": "correctness_violations",
        "clang-diagnostic-error": "correctness_violations",

        "clang-analyzer-core.UndefinedBinaryOperatorResult": "correctness_violations",
        "clang-analyzer-core.uninitialized.Assign": "correctness_violations",
        "readability-else-after-return": "readability_violations",
    }
    check_quick_tips = {
        "readability-avoid-const-params-in-decls": "Omit 'const' in function declarations; only keep it in definitions where it matters.",
        "readability-braces-around-statements": "Always use braces for if/else/for/while, even single-line bodies.",
        "readability-const-return-type": "Don’t return values as `const`; it doesn’t add safety and hinders usability.",
        "readability-container-size-empty": "Use `.empty()` instead of `.size() == 0` for clarity and possible perf gains.",
        "readability-delete-null-pointer": "Deleting a null pointer is safe but redundant — avoid it.",
        "readability-function-cognitive-complexity": "Split overly complex functions into smaller, focused helpers.",
        "readability-function-size": "Keep functions short; split when exceeding a screenful (~50 lines).",
        "readability-identifier-length": "Use descriptive names ≥ 3 chars (e.g., `idx` → `index`, `len` → `length`).",
        "readability-identifier-naming": "Stick to a naming convention (e.g., lowerCamelCase for vars, UpperCamelCase for classes).",
        "readability-implicit-bool-conversion": "Prefer explicit comparisons (`ptr != nullptr`, `x > 0`) over implicit bool conversion.",
        "readability-inconsistent-declaration-parameter-name": "Keep parameter names consistent across declarations and definitions.",
        "readability-isolate-declaration": "Declare one variable per line for clarity.",
        "readability-magic-numbers": "Replace raw numbers with named constants, enums, or constexpr.",
        "readability-misleading-indentation": "Ensure code indentation matches logical structure — avoid misleading braces.",
        "readability-misplaced-array-index": "Prefer `array[index]` over `index[array]` (the latter compiles but is confusing).",
        "readability-mixed-constructs": "Avoid mixing declarations with unrelated statements.",
        "readability-named-parameter": "Name parameters in function declarations for readability.",
        "readability-non-const-parameter": "Mark reference/pointer params as `const` if not modified.",
        "readability-qualified-auto": "Avoid redundant type qualifiers when using `auto`.",
        "readability-redundant-control-flow": "Remove redundant `else` after `return`, or `break` after `continue`.",
        "readability-redundant-declaration": "Remove duplicate variable/function declarations.",
        "readability-redundant-function-ptr-dereference": "Calling a function pointer doesn’t need `(*fp)()`, just `fp()`.",
        "readability-redundant-smartptr-get": "Avoid `.get()` unless API explicitly needs raw pointer.",
        "readability-redundant-string-cstr": "Pass `std::string` directly instead of `.c_str()` when API accepts it.",
        "readability-redundant-string-init": "Don’t initialize strings with empty string literal (`std::string s = \"\";` → `std::string s;`).",
        "readability-simplify-boolean-expr": "Simplify verbose boolean expressions (`if (cond) return true;` → `return cond;`).",
        "readability-simplify-subscript-expr": "Simplify nested or redundant subscript expressions.",
        "readability-static-definition-in-anonymous-namespace": "Use anonymous namespaces instead of `static` for internal linkage.",
        "readability-uppercase-literal-suffix": "Use uppercase for literal suffixes (`123U`, `1.0F`).",
        "readability-use-anyofallof": "Prefer `std::any_of` / `std::all_of` instead of manual loops.",
        "readability-use-auto": "Use `auto` when the type is obvious and improves readability.",
        "readability-use-emplace": "Use `emplace_back` / `emplace` instead of `push_back` / `insert` with temporaries.",
        "readability-use-std-min-max": "Use `std::min` / `std::max` instead of ternary operators for clarity.",
        "readability-uppercase-naming": "Reserve ALL_CAPS for macros and constants only.",
        "readability-var-init": "Initialize variables at declaration instead of in separate statements.",
        "readability-virtual-specifiers": "Order specifiers consistently (`virtual` first, then `override`/`final`).",
        "readability-redundant-access-specifiers": "Avoid repeating `public:`, `private:` if not needed.",
        "readability-avoid-unnecessary-else": "Don’t use `else` if previous branch ends with `return`/`throw`.",
        "readability-convert-member-functions-to-static": "Make methods `static` if they don’t use `this`.",
        "readability-prefer-early-return": "Flatten code by returning early instead of deep nesting.",
        "readability-prefer-const-ref-params": "Pass large objects as `const&` instead of by value.",
        "readability-use-enum-class": "Prefer `enum class` over plain enums to avoid name collisions.",
        "readability-prefer-std-array-to-c-array": "Use `std::array` instead of raw C arrays when size is fixed.",
        "readability-avoid-nested-loops": "Extract inner loops into helpers or algorithms for clarity.",
        "readability-avoid-side-effects-in-expr": "Avoid expressions with hidden side effects (like `if (x = foo())`).",

        "clang-diagnostic-error": "Fix compile errors first (types, overloads, missing headers, mismatched new/delete).",
        "clang-analyzer-core.CallAndMessage": "Check for null before dereferencing pointers.",
        "clang-analyzer-core.NullDereference": "Ensure pointer validity before use.",
        "clang-analyzer-core.DivideZero": "Check divisor for zero before dividing.",
        "clang-analyzer-cplusplus.NewDeleteLeaks": "Balance `new` with `delete` to avoid leaks.",
        "clang-analyzer-cplusplus.Move": "Don’t use objects after they have been `std::moved`.",
        "clang-analyzer-unix.Malloc": "Match `malloc/free`, avoid leaks.",
        "clang-analyzer-unix.API": "Validate results of system calls (`open`, `read`, etc.).",

        "clang-analyzer-core.UndefinedBinaryOperatorResult": "Check operands for undefined values before using in binary operations.",
        "clang-analyzer-core.uninitialized.Assign": "Always initialize variables before assignment; uninitialized values cause UB.",
        "readability-else-after-return": "Remove `else` after a branch that already `return`s, `throw`s, or exits.",
    }

    metrics = results.get("metrics", {})
    raw_metrics = results.get("raw_metrics", {})
    processed_files = results.get("processed_files", [])

    # Helper: shorten full absolute paths to relative-ish (if present in processed_files)
    def short_path(full):
        # Try to map to the tail end that appears in processed_files
        for pf in processed_files:
            if full.endswith(pf.split("/", 1)[-1]):
                return pf
        # fallback: just show filename and last 2 dirs
        parts = full.replace("\\", "/").split("/")
        return "/".join(parts[-3:]) if len(parts) > 3 else full

    # ---------- Parse the raw log into structured issues ----------
    # We capture:
    #   path:line:col: severity: message [check]
    # Then we gather the following code-frame lines (the ones with " | " and underlines) until next header.
    issue_header_re = re.compile(
        r"^(?P<file>.*?):(?P<line>\d+):(?P<col>\d+): (?P<sev>warning|error): (?P<msg>.*?)(?: \[(?P<check>[^\]]+)\])?$"
    )

    issues = []  # list of dicts
    current = None

    def flush_current():
        nonlocal current, issues
        if current:
            # Trim trailing empty lines in frame
            while current["frame_lines"] and not current["frame_lines"][-1].strip():
                current["frame_lines"].pop()
            issues.append(current)
            current = None

    for raw_line in log.splitlines():
        line = raw_line.rstrip("\n")

        m = issue_header_re.match(line)
        if m:
            # New header => flush previous
            flush_current()
            g = m.groupdict()
            current = {
                "file": g["file"],
                "file_short": short_path(g["file"]),
                "line": int(g["line"]),
                "col": int(g["col"]),
                "severity": g["sev"],
                "message": g["msg"].strip(),
                "check": g.get("check") or "unknown-check",
                "frame_lines": [],
            }
        else:
            # Continuation (code frame, notes, etc.)
            if current is not None:
                current["frame_lines"].append(line)

    # end-of-file flush
    flush_current()

    # ---------- Aggregate stats ----------
    by_severity = Counter([i["severity"] for i in issues])
    by_check = Counter([i["check"] for i in issues])
    by_file = defaultdict(list)
    for i in issues:
        by_file[i["file_short"]].append(i)

    # ---------- Build HTML ----------
    def badge(text, color):
        return f'<span class="badge" style="background:{color}">{html.escape(str(text))}</span>'

    def progress_bar(value, max_value, label, color):
        pct = 0 if max_value == 0 else (100.0 * value / max_value)
        return f"""
        <div class="bar">
          <div class="bar-fill" style="width:{pct:.1f}%; background:{color}"></div>
          <div class="bar-label">{html.escape(label)} — {value}</div>
        </div>
        """

    def render_metrics_table():
        rows = []
        # display in a stable order using our friendly mapping if possible
        for key in category_friendly.keys():
            count = metrics.get(key, 0)
            title, tip = category_friendly[key]
            rows.append(f"""
            <tr>
              <td><strong>{html.escape(title)}</strong><br><span class="muted">{html.escape(tip)}</span></td>
              <td class="count">{count}</td>
            </tr>
            """)
        return "\n".join(rows)

    def render_severity_summary():
        total = sum(by_severity.values())
        parts = []
        for sev in ("error", "warning", "note"):
            if by_severity.get(sev):
                parts.append(progress_bar(by_severity[sev], max(total, 1), sev.title(), severity_colors.get(sev, "#888")))
        return "\n".join(parts) or "<p class='muted'>No issues found.</p>"

    # def render_check_breakdown():
    #     # Top checks by frequency
    #     rows = []
    #     for check, cnt in by_check.most_common():
    #         cat_key = check_category_map.get(check)
    #         cat_name = category_friendly.get(cat_key, (None, None))[0] if cat_key else None
    #         tip = check_quick_tips.get(check)
    #         extra = []
    #         if cat_name:
    #             extra.append(html.escape(cat_name))
    #         if tip:
    #             extra.append(html.escape(tip))
    #         check = check.replace("-", " ")
    #         check = re.sub(r'([a-z])([A-Z])', r'\1 \2', check)
    #         check = check.replace(".", " ")
    #         check = check.title()
    #         rows.append(f"""
    #         <tr>
    #           <td><strong>{html.escape(check)}</strong><br><span class="muted">{' · '.join(extra)}</span></td>
    #           <td class="count"><span class="pill">{cnt}</span></td>
    #         </tr>
    #         """)
    #     return "\n".join(rows)

    def render_check_breakdown():
        # Build category -> list of items and track totals, preserving order by frequency
        cat_items = defaultdict(list)
        cat_totals = defaultdict(int)
        cat_order = []  # preserve first-seen order from by_check.most_common()

        for raw_check, cnt in by_check.most_common():
            cat_key = check_category_map.get(raw_check)
            cat_name = category_friendly.get(cat_key, (None, None))[0] if cat_key else "Uncategorized"

            if cat_name not in cat_order:
                cat_order.append(cat_name)

            # Format check label
            check = raw_check.replace("-", " ")
            check = re.sub(r'([a-z])([A-Z])', r'\1 \2', check)
            check = check.replace(".", " ")
            check = check.title()

            tip = check_quick_tips.get(raw_check)
            # one <li> per check
            parts = [f"<strong>{html.escape(check)}</strong>"]
            if tip:
                parts.append(html.escape(tip))
            li = f"<li><span class='pill'>{cnt}</span> {' · '.join(parts)}</li>"

            cat_items[cat_name].append(li)
            cat_totals[cat_name] += cnt

        # Render a table where each category is a single row with a nested <ul> of its checks
        rows = []
        for cat_name in cat_order:
            items_html = "".join(cat_items[cat_name])
            total = cat_totals[cat_name]
            row_html = f"""
            <tr class="category">
              <td>
                <div class="category-title"><strong>{html.escape(cat_name)}</strong></div>
                <ul class="category-checks muted">
                  {items_html}
                </ul>
              </td>
              <td class="count"><span class="pill">{total}</span></td>
            </tr>
            """
            rows.append(row_html)

        return "\n".join(rows)

    def render_issue_item(issue):
        sev_color = severity_colors.get(issue["severity"], "#666")
        # preserve the frame with a <pre> block; we HTML-escape but keep alignment
        frame_html = ""
        if issue["frame_lines"]:
            escaped = "\n".join(html.escape(l) for l in issue["frame_lines"])
            frame_html = f"<pre><code>{escaped}</code></pre>"
        check_tip = check_quick_tips.get(issue["check"])
        tip_html = f"<div class='tip'>💡 {html.escape(check_tip)}</div>" if check_tip else ""
        cat_key = check_category_map.get(issue["check"])
        cat_name = category_friendly.get(cat_key, (None, None))[0] if cat_key else "General"

        return f"""
        <div class="issue">
          <div class="issue-head">
            {badge(issue["severity"].upper(), sev_color)}
            <span class="message">{html.escape(issue["message"].capitalize())}</span>
          </div>
          <div class="where">Line {issue["line"]} Col {issue["col"]} · {html.escape(cat_name)} <span class="muted">{html.escape(issue["check"])}</span></div>
          {tip_html}
          {frame_html}
        </div>
        """

    def render_file_sections():
        blocks = []
        for fpath in sorted(by_file.keys()):
            items_html = "\n".join(render_issue_item(i) for i in by_file[fpath])
            count = len(by_file[fpath])
            blocks.append(f"""
            <details class="file-block">
              <summary><strong>{html.escape(fpath)}</strong> <span class="pill">{count}</span></summary>
              {items_html}
            </details>
            """)
        return "\n".join(blocks) or "<p class='muted'>No issues to show.</p>"

    # Summary header numbers (use results.json if available; fall back to parsed)
    total_warnings = raw_metrics.get("by_severity", {}).get("warning", by_severity.get("warning", 0))
    total_errors = raw_metrics.get("by_severity", {}).get("error", by_severity.get("error", 0))
    # total_notes = by_severity.get("note", 0)
    total_issues = total_warnings + total_errors

    # Small helper for "by_check" table from results.json (if present)
    def render_raw_by_check_table():
        rows = []
        for check, cnt in sorted(raw_metrics.get("by_check", {}).items(), key=lambda kv: (-kv[1], kv[0])):
            cat_key = check_category_map.get(check)
            cat_name = category_friendly.get(cat_key, (None, None))[0] if cat_key else ""
            rows.append(f"""
            <tr>
              <td><code class="check">{html.escape(check)}</code></td>
              <td class="count">{cnt}</td>
              <td class="muted">{html.escape(cat_name)}</td>
            </tr>
            """)
        if not rows:
            return ""
        return f"""
        <h3>Checks (from results.json)</h3>
        <table class="plain">
          <thead><tr><th>Check</th><th>Count</th><th>Category</th></tr></thead>
          <tbody>
            {''.join(rows)}
          </tbody>
        </table>
        """

    # Build HTML
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    title = "Readability & Correctness Report"

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
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
    margin: 0; padding: 2rem; background: var(--bg); color: var(--text);
    font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Cantarell, Noto Sans, Helvetica, Arial, "Apple Color Emoji", "Segoe UI Emoji";
    line-height: 1.5;
  }}
  .container {{ max-width: 1100px; margin: 0 auto; }}
  h1, h2, h3 {{ margin: 0.5rem 0 0.75rem; }}
  .muted {{ color: var(--muted); font-size: 0.9em; }}
  .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; margin: 1rem 0 1.5rem; }}
  .card {{
    background: var(--panel); border: 1px solid #1f2937; border-radius: 14px; padding: 1rem;
  }}
  .kpi {{ font-size: 2rem; font-weight: 700; }}
  .badge {{
    display: inline-block; color: white; padding: 0.15rem 0.5rem; border-radius: 999px; font-size: 0.75rem; margin-right: .5rem;
  }}
  .pill {{
    display: inline-block; background: var(--pill); color: #e2e8f0; border-radius: 999px; padding: 0 .5rem; font-size: .8rem; margin-left: .4rem;
  }}
  .grid-2 {{ display: grid; grid-template-columns: 1.2fr 1fr; gap: 1rem; }}
  table.plain {{ width: 100%; border-collapse: collapse; background: var(--panel); border-radius: 12px; overflow: hidden; }}
  table.plain th, table.plain td {{ padding: .6rem .8rem; border-bottom: 1px solid #1f2937; vertical-align: top; }}
  table.plain thead th {{ background: #0b1220; text-align: left; }}
  td.count {{ text-align: right; font-weight: 700; }}
  .bar {{ position: relative; height: 26px; background: var(--soft); border-radius: 999px; margin: .5rem 0 1rem; overflow: hidden; }}
  .bar-fill {{ height: 100%; }}
  .bar-label {{ position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; font-weight: 600; color: #e2e8f0; text-shadow: 0 1px 0 rgba(0,0,0,.6); }}
  details.file-block {{
    background: var(--panel); border: 1px solid #1f2937; border-radius: 12px; margin: .6rem 0; padding: .4rem .8rem;
  }}
  details.file-block summary {{ cursor: pointer; font-weight: 700; list-style: none; }}
  details.file-block[open] summary {{ margin-bottom: .5rem; }}
  .issue {{ background: #0b1220; border: 1px solid #1f2937; border-radius: 10px; padding: .6rem .8rem; margin: .6rem 0; }}
  .issue-head {{ display: flex; align-items: center; gap: .5rem; }}
  .where {{ /*font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;*/ color: #cbd5e1; font-size: .95rem; margin: .4rem 0 .2rem; }}
  .message {{ font-size: 1.2rem; }}
  pre, code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace; }}
  pre {{ background: #0a0f1c; color: #e2e8f0; border-radius: 8px; border: 1px solid #1f2937; padding: .6rem; overflow:auto; }}
  code.check {{ background: #0a0f1c; padding: .05rem .35rem; border-radius: 6px; border: 1px solid #1f2937; }}
  ul.checks {{ list-style: none; padding-left: 0; }}
  ul.checks li {{ background: var(--panel); border: 1px solid #1f2937; border-radius: 10px; padding: .5rem .7rem; margin: .4rem 0; }}
  .tip {{ background: #052e1a; border: 1px solid #14532d; color: #a7f3d0; border-radius: 8px; padding: .4rem .6rem; margin-top: .6rem; }}
  footer {{ margin-top: 2rem; color: var(--muted); font-size: .9rem; }}
  .category-title {{ margin-bottom: .3rem; }}
  .category-checks {{ margin: 0; list-style: none; padding-left: 0.5rem; }}  
  .category-checks li {{ padding: .1rem 0; }}
  .category-checks li .pill {{ padding: 0 .4rem; }}

</style>
</head>
<body>
  <div class="container">
    <h1>{html.escape(title)}</h1>
    <div class="muted">Generated: {html.escape(now)}</div>

    <div class="cards">
      <div class="card"><div class="kpi">{total_issues}</div><div>Total Issues</div></div>
      <div class="card"><div class="kpi" style="color:{severity_colors['error']}">{total_errors}</div><div>Errors</div></div>
      <div class="card"><div class="kpi" style="color:{severity_colors['warning']}">{total_warnings}</div><div>Warnings</div></div>
      <div class="card"><div class="kpi">{len(processed_files)}</div><div>Files Processed</div></div>
    </div>

    <!--div>
      <h2>Severity Summary</h2>
      {render_severity_summary()}
    </div-->

    <!--div>
      <h2>Category Overview</h2>
      <table class="plain">
        <thead><tr><th>Category</th><th>Count</th></tr></thead>
        <tbody>
          {render_metrics_table()}
        </tbody>
      </table>
    </div-->

    <!--div>
      {render_raw_by_check_table()}
    </div-->

    <div>
      <h2>Checks</h2>
      <table class="plain">
        <thead><tr><th>Check</th><th>Issues</th></tr></thead>
        <tbody>
          {render_check_breakdown()}
        </tbody>
      </table>
    </div>

    <br /><br />
    <h2>Issues by File</h2>
    {render_file_sections()}

    <footer>
      <p><strong>How to read code frames:</strong> The code line appears with its number on the left (from clang-tidy),
      and the pointer line uses <code>^</code> to indicate the exact column, and <code>~</code> to underline the span.</p>
      <p>Tips are suggestions, not strict rules—fix correctness and compile errors first, then readability.</p>
    </footer>
  </div>
</body>
</html>"""

    return html_doc
