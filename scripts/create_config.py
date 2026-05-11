import argparse
import json
from pathlib import Path
from typing import Optional

MISSING = object()


def _print_header(title: str):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def _print_section(title: str):
    print("\n" + "-" * 60)
    print(title)
    print("-" * 60)


def _format_default(value, limit: int = 90) -> str:
    text = json.dumps(value) if isinstance(value, (dict, list, type(None), bool, int, float)) else str(value)
    text = text.replace("\n", " ")
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _print_field(label: str, default=None, meta: Optional[dict] = None, hint: Optional[str] = None):
    print(f"\n• {label}")
    if meta:
        _show_description(meta)
    if default is not MISSING:
        print(f"  Default: {_format_default(default)}")
    if hint:
        print(f"  Hint: {hint}")


def _path_to_label(path: tuple[str, ...], meta: dict) -> str:
    explicit = meta.get("label")
    if explicit:
        return explicit
    if not path:
        return "root"
    return path[-1].replace("_", " ").strip().capitalize()


def _show_description(meta: dict):
    description = meta.get("description")
    if description:
        print(f"  {description}")


def _prompt_text(label: str, default: Optional[str] = None, allow_empty: bool = False, meta: Optional[dict] = None) -> Optional[str]:
    _print_field(label, default, meta)
    while True:
        value = input("  Value> ").strip()
        if value:
            return value
        if default is not None:
            return default
        if allow_empty:
            return None
        print("Please provide a value.")


def _prompt_bool(label: str, default: bool, meta: Optional[dict] = None) -> bool:
    _print_field(label, default, meta, hint="Type y/yes or n/no. Press Enter to keep default.")
    default_hint = "Y/n" if default else "y/N"
    while True:
        value = input(f"  Value [{default_hint}]> ").strip().lower()
        if value == "":
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Please answer with y/yes or n/no.")


def _coerce_scalar(value: str, desired_type: type):
    if desired_type is bool:
        lowered = value.lower()
        if lowered in {"true", "1", "yes", "y"}:
            return True
        if lowered in {"false", "0", "no", "n"}:
            return False
        raise ValueError("Expected boolean value")
    if desired_type is int:
        return int(value)
    if desired_type is float:
        return float(value)
    return value


def _prompt_number(label: str, default, desired_type: type, meta: Optional[dict] = None):
    _print_field(label, default, meta, hint=f"Enter a {desired_type.__name__} value.")
    while True:
        value = input("  Value> ").strip()
        if value == "":
            return default
        try:
            return _coerce_scalar(value, desired_type)
        except ValueError:
            print(f"Please provide a valid {desired_type.__name__} value.")


def _prompt_none(label: str, meta: Optional[dict] = None):
    _print_field(
        label,
        None,
        meta,
        hint="Enter a value directly. Enter or 'null' keeps null.",
    )
    while True:
        value = input("  Value> ").strip()
        if value == "" or value.lower() == "null":
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value


def _prompt_list(label: str, default: list, meta: Optional[dict] = None) -> list:
    _print_field(label, default, meta)
    if default and all(not isinstance(x, (dict, list)) for x in default):
        print("  Hint: Comma-separated values or JSON list. Enter keeps default.")
        value = input("  Value> ").strip()
        if value == "":
            return default
        if value.startswith("["):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
            print("Invalid JSON list, falling back to comma-separated parsing.")
        sample = next((x for x in default if x is not None), None)
        desired_type = type(sample) if sample is not None else str
        items = [part.strip() for part in value.split(",") if part.strip()]
        try:
            return [_coerce_scalar(item, desired_type) for item in items]
        except ValueError:
            print("Could not parse one or more values; keeping them as strings.")
            return items

    print("  Hint: Enter a JSON list. Enter keeps default.")
    while True:
        value = input("  Value> ").strip()
        if value == "":
            return default
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
            print("Please provide a JSON list.")
        except json.JSONDecodeError:
            print("Invalid JSON list.")


def _load_base_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_fields_metadata(path: Optional[Path]) -> dict:
    if path is None or not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, dict):
        return {}
    return raw


def _get_field_meta(fields: dict, path: tuple[str, ...]) -> dict:
    return fields.get(".".join(path), {}) if fields else {}


def _prompt_value(default_value, path: tuple[str, ...], fields: dict):
    meta = _get_field_meta(fields, path)
    label = _path_to_label(path, meta)

    if isinstance(default_value, dict):
        if path:
            section = meta.get("section") or ".".join(path)
            _print_section(f"Section: {section}")
            if meta:
                _show_description(meta)
        result = {}
        for key, value in default_value.items():
            result[key] = _prompt_value(value, (*path, key), fields)
        return result

    if isinstance(default_value, bool):
        return _prompt_bool(label, default_value, meta)
    if isinstance(default_value, int):
        return _prompt_number(label, default_value, int, meta)
    if isinstance(default_value, float):
        return _prompt_number(label, default_value, float, meta)
    if isinstance(default_value, list):
        return _prompt_list(label, default_value, meta)
    if default_value is None:
        return _prompt_none(label, meta)
    return _prompt_text(label, str(default_value), meta=meta)


def _deep_diff(base, current):
    if isinstance(base, dict) and isinstance(current, dict):
        merged = {}
        keys = set(base.keys()) | set(current.keys())
        for key in keys:
            base_value = base.get(key, MISSING)
            current_value = current.get(key, MISSING)
            if base_value is MISSING:
                merged[key] = current_value
                continue
            if current_value is MISSING:
                continue
            diff = _deep_diff(base_value, current_value)
            if diff is not MISSING:
                merged[key] = diff
        return merged if merged else MISSING
    if base != current:
        return current
    return MISSING


def build_config_interactive(base_config: dict, fields: dict) -> tuple[dict, dict]:
    _print_header("Quality Metrics Configurator")
    print("Generic wizard based on base config keys.")
    print("Press Enter to keep defaults.")

    full_config = _prompt_value(base_config, tuple(), fields)
    overrides = _deep_diff(base_config, full_config)
    overrides = overrides if overrides is not MISSING else {}

    # _print_header("Review: Full Config")
    # print(json.dumps(full_config, indent=2))
    _print_header("Review: Overrides To Write")
    print(json.dumps(overrides, indent=2))

    if not _prompt_bool("Write this override config to file", True):
        print("Cancelled. No file was written.")
        raise SystemExit(0)

    return full_config, overrides


def main():
    project_root = Path(__file__).resolve().parent.parent
    default_base = project_root / "config" / "default.json"
    default_fields = project_root / "config" / "default.fields.json"

    parser = argparse.ArgumentParser(description="Interactive configurator for quality-metrics.")
    parser.add_argument(
        "--base-config",
        type=str,
        default=str(default_base),
        help="Base JSON config to start from.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=".quality_metrics.config.json",
        help="Output path for generated config.",
    )
    parser.add_argument(
        "--fields",
        type=str,
        default=str(default_fields),
        help="Optional path to field metadata JSON (labels/descriptions).",
    )
    args = parser.parse_args()

    base_path = Path(args.base_config)
    if not base_path.is_absolute():
        base_path = (Path.cwd() / base_path).resolve()
    if not base_path.exists():
        print(f"❌ Base config not found: {base_path}")
        raise SystemExit(1)

    fields_path = Path(args.fields)
    if not fields_path.is_absolute():
        fields_path = (Path.cwd() / fields_path).resolve()

    base_config = _load_base_config(base_path)
    field_metadata = _load_fields_metadata(fields_path)
    _, config_overrides = build_config_interactive(base_config, field_metadata)

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = (Path.cwd() / output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(config_overrides, f, indent=4)

    print(f"\n✅ Config written to: {output_path}")


if __name__ == "__main__":
    main()