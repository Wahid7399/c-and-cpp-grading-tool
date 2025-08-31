#!/usr/bin/env python3
import re
from typing import List, Dict, Any, Optional

# ---------- Regexes & constants ----------
_VALGRIND_TAG = re.compile(r"^==\s*\d+\s*==\s?")
_ERROR_SUMMARY_RE = re.compile(r"ERROR SUMMARY:\s*(\d+)\s+errors?", re.IGNORECASE)
_VERSION_RE = re.compile(r"Using Valgrind-([0-9.]+)")
_COMMAND_RE = re.compile(r"Command:\s*(.*)$")

# Keep boilerplate ignores (do NOT include HEAP/LEAK SUMMARY so we can parse them).
_IGNORE_PREFIXES = (
    "Memcheck,",
    "Copyright",
    "Using Valgrind-",
    "Command:",
    "Use --track-origins=yes",
    "For lists of detected and suppressed errors, rerun with:",
    "ERROR SUMMARY:",
    "All heap blocks were freed -- no leaks are possible",
)

# HEAP SUMMARY lines
_IN_USE_RE = re.compile(r"in use at exit:\s*([\d,]+)\s*bytes in\s*([\d,]+)\s*blocks", re.I)
_TOTAL_USAGE_RE = re.compile(
    r"total heap usage:\s*([\d,]+)\s*allocs,\s*([\d,]+)\s*frees,\s*([\d,]+)\s*bytes allocated",
    re.I,
)

# LEAK SUMMARY lines: "<label>: X bytes in Y blocks"
# Allow leading/trailing whitespace, and labels with spaces (e.g., "still reachable").
_LEAK_LINE_RE = re.compile(
    r"(?i)^\s*((?:definitely|indirectly|possibly)\s+lost|still reachable|suppressed):\s*"
    r"([\d,]+)\s*bytes in\s*([\d,]+)\s*blocks\s*$"
)

# ---------- Helpers ----------
def _strip_tag(line: str) -> str:
    """Remove the leading '==PID==' tag if present."""
    return _VALGRIND_TAG.sub("", line.rstrip("\n"))

def _looks_like_separator(line: str) -> bool:
    """A separator is a line that becomes empty after stripping the tag (or a blank line)."""
    return _strip_tag(line).strip() == ""

def _is_ignorable_header(line: str) -> bool:
    s = _strip_tag(line).strip()
    return any(s.startswith(p) for p in _IGNORE_PREFIXES)

def _to_int(s: Optional[str]) -> Optional[int]:
    if s is None:
        return None
    try:
        return int(s.replace(",", ""))
    except ValueError:
        return None

def _norm_label(lbl: str) -> str:
    return lbl.lower().replace(" ", "_").replace("-", "_")

def _flush_error_block(errors: List[Dict[str, Any]],
                       current_title: List[str],
                       current_details: List[str]) -> None:
    if current_title or current_details:
        title_line = " ".join(current_title).strip() if current_title else ""
        errors.append(
            {"title": title_line, "details": [d for d in current_details if d.strip()]}
        )

# ---------- Public API ----------
def parse_valgrind_stdout(text: str, *, group: bool = False) -> Dict[str, Any]:
    """
    Parse Valgrind stdout into a structured dict.

    Args:
        text: Full stdout string from Valgrind.
        group: If True, aggregate identical error titles with counts and merged stacks.

    Returns:
        {
          "error_count": int,
          "errors": [
            {"title": str, "details": [str, ...]}  # if group=False
            # or, if group=True:
            {"title": str, "count": int, "examples": [[detail lines], ...]}
          ],
          "heap_summary": {
            "in_use_at_exit_bytes": int|None,
            "in_use_at_exit_blocks": int|None,
            "total_heap_usage_allocs": int|None,
            "total_heap_usage_frees": int|None,
            "total_heap_usage_bytes_allocated": int|None,
            "raw": [str, ...] | None
          },
          "leak_summary": {
            "definitely_lost": {"bytes": int|None, "blocks": int|None},
            "indirectly_lost": {"bytes": int|None, "blocks": int|None},
            "possibly_lost": {"bytes": int|None, "blocks": int|None},
            "still_reachable": {"bytes": int|None, "blocks": int|None},
            "suppressed": {"bytes": int|None, "blocks": int|None},
            "totals": {"bytes_lost": int, "blocks_lost": int},
            "raw": [str, ...] | None
          } | None,
          "meta": {"tool": str|None, "version": str|None, "command": str|None, "leak_status": str|None}
        }
    """
    lines = text.splitlines()

    # --- Meta detection (tool, version, command, leak_status)
    version = None
    command = None
    tool = None
    leak_status = "All heap blocks were not freed"

    for raw in lines:
        s = _strip_tag(raw).strip()
        if not s:
            continue
        if s.startswith("Memcheck"):
            tool = "Memcheck"
        m_ver = _VERSION_RE.search(s)
        if m_ver:
            version = m_ver.group(1)
        m_cmd = _COMMAND_RE.search(s)
        if m_cmd:
            command = m_cmd.group(1)
        if s.startswith("All heap blocks were freed"):
            leak_status = s  # keep full text

    # --- ERROR SUMMARY (authoritative error_count if present)
    explicit_error_count = None
    for raw in lines:
        s = _strip_tag(raw).strip()
        m = _ERROR_SUMMARY_RE.search(s)
        if m:
            explicit_error_count = int(m.group(1))
            break

    # --- Walk lines, collecting errors + summaries
    errors: List[Dict[str, Any]] = []
    current_title: List[str] = []
    current_details: List[str] = []

    heap_raw: List[str] = []
    leak_raw: List[str] = []
    in_heap_summary = False
    in_leak_summary = False

    for raw in lines:
        # Separators end current capture blocks
        if _looks_like_separator(raw):
            if in_heap_summary:
                in_heap_summary = False
            if in_leak_summary:
                in_leak_summary = False
            if current_title or current_details:
                _flush_error_block(errors, current_title, current_details)
                current_title, current_details = [], []
            continue

        s = _strip_tag(raw).rstrip()

        # Start/capture HEAP SUMMARY
        if s.startswith("HEAP SUMMARY:"):
            in_heap_summary = True
            heap_raw.append(s)
            continue
        if in_heap_summary:
            heap_raw.append(s)
            continue

        # Start/capture LEAK SUMMARY
        if s.startswith("LEAK SUMMARY:"):
            in_leak_summary = True
            leak_raw.append(s)
            continue
        if in_leak_summary:
            leak_raw.append(s)
            continue

        # Ignore other boilerplate
        if _is_ignorable_header(raw):
            continue

        # Build an error block: first line is title, the rest are details
        if not current_title:
            current_title = [s]
        else:
            current_details.append(s)

    # Flush a trailing error (file may not end with a blank line)
    if current_title or current_details:
        _flush_error_block(errors, current_title, current_details)

    # --- Parse HEAP SUMMARY
    in_use_bytes = in_use_blocks = total_allocs = total_frees = total_bytes_alloc = None
    for line in heap_raw:
        mi = _IN_USE_RE.search(line)
        if mi:
            in_use_bytes = _to_int(mi.group(1))
            in_use_blocks = _to_int(mi.group(2))
        mt = _TOTAL_USAGE_RE.search(line)
        if mt:
            total_allocs = _to_int(mt.group(1))
            total_frees = _to_int(mt.group(2))
            total_bytes_alloc = _to_int(mt.group(3))

    heap_summary = {
        "in_use_at_exit_bytes": in_use_bytes,
        "in_use_at_exit_blocks": in_use_blocks,
        "total_heap_usage_allocs": total_allocs,
        "total_heap_usage_frees": total_frees,
        "total_heap_usage_bytes_allocated": total_bytes_alloc,
        "raw": heap_raw if heap_raw else None,
    }

    # --- Parse LEAK SUMMARY
    leak_summary: Optional[Dict[str, Any]] = None
    if leak_raw:
        leak_summary = {
            "definitely_lost": {"bytes": None, "blocks": None},
            "indirectly_lost": {"bytes": None, "blocks": None},
            "possibly_lost": {"bytes": None, "blocks": None},
            "still_reachable": {"bytes": None, "blocks": None},
            "suppressed": {"bytes": None, "blocks": None},
            "raw": leak_raw,
        }

        for line in leak_raw:
            m = _LEAK_LINE_RE.search(line.strip())
            if not m:
                continue
            label, bytes_s, blocks_s = m.groups()
            key = _norm_label(label)  # e.g., "still reachable" -> "still_reachable"
            leak_summary.setdefault(key, {})
            leak_summary[key]["bytes"] = _to_int(bytes_s)
            leak_summary[key]["blocks"] = _to_int(blocks_s)

        # Convenience totals (lost = definitely + indirectly + possibly)
        def _val(cat, field):
            v = leak_summary.get(cat, {}).get(field)
            return 0 if v is None else v
        leak_summary["totals"] = {
            "bytes_lost": _val("definitely_lost", "bytes")
                          + _val("indirectly_lost", "bytes")
                          + _val("possibly_lost", "bytes"),
            "blocks_lost": _val("definitely_lost", "blocks")
                           + _val("indirectly_lost", "blocks")
                           + _val("possibly_lost", "blocks"),
        }

    # --- Grouping (optional)
    grouped_errors: List[Dict[str, Any]] = []
    if group:
        buckets: Dict[str, Dict[str, Any]] = {}
        for e in errors:
            title = e.get("title", "")
            details = e.get("details", [])
            b = buckets.setdefault(title, {"title": title, "count": 0, "examples": []})
            b["count"] += 1
            if details:
                b["examples"].append(details)
        grouped_errors = list(buckets.values())

    # --- Finalize
    error_count = explicit_error_count if explicit_error_count is not None else len(errors)
    result: Dict[str, Any] = {
        "error_count": error_count,
        "errors": grouped_errors if group else errors,
        "heap_summary": heap_summary,
        "leak_summary": leak_summary,
        "meta": {
            "tool": tool,
            "version": version,
            "command": command,
            "leak_status": leak_status,
        },
    }
    return result
