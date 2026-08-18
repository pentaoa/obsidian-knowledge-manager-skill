#!/usr/bin/env python3
"""Dependency-free Obsidian property, Base, query, and link tooling."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, Iterable


WIKILINK = re.compile(r"!?\[\[([^\]]+)\]\]")
INLINE_TAG = re.compile(r"(?<![\w/])#([\w\-/\u3400-\u9fff]+)")


class VaultError(RuntimeError):
    pass


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode if path.exists() else None
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
        tmp.write(text)
        tmp_path = Path(tmp.name)
    if mode is not None:
        os.chmod(tmp_path, mode)
    os.replace(tmp_path, path)


def split_frontmatter(text: str) -> tuple[str | None, str, str]:
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return None, text, newline
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "".join(lines[1:index]), "".join(lines[index + 1 :]), newline
    raise VaultError("frontmatter opens with --- but has no closing delimiter")


def decode_key(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith('"'):
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise VaultError(f"invalid quoted YAML key: {raw}") from exc
        if not isinstance(value, str):
            raise VaultError(f"non-string YAML key: {raw}")
        return value
    if raw.startswith("'") and raw.endswith("'"):
        return raw[1:-1].replace("''", "'")
    return raw


def split_mapping_line(line: str) -> tuple[str, str] | None:
    raw = line.rstrip("\r\n")
    if not raw or raw[0].isspace() or raw.startswith("#"):
        return None
    quote = None
    escaped = False
    for index, char in enumerate(raw):
        if escaped:
            escaped = False
            continue
        if char == "\\" and quote == '"':
            escaped = True
            continue
        if char in "\"'":
            if quote is None:
                quote = char
            elif quote == char:
                quote = None
            continue
        if char == ":" and quote is None:
            return decode_key(raw[:index]), raw[index + 1 :].strip()
    return None


def frontmatter_blocks(frontmatter: str) -> list[tuple[str, int, int, str]]:
    lines = frontmatter.splitlines(keepends=True)
    starts: list[tuple[str, int, str]] = []
    for index, line in enumerate(lines):
        pair = split_mapping_line(line)
        if pair is not None:
            starts.append((pair[0], index, pair[1]))
    blocks: list[tuple[str, int, int, str]] = []
    for pos, (key, start, value) in enumerate(starts):
        end = starts[pos + 1][1] if pos + 1 < len(starts) else len(lines)
        blocks.append((key, start, end, value))
    return blocks


def parse_scalar(raw: str) -> Any:
    value = raw.strip()
    if value == "":
        return None
    if value.startswith('"'):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    lowered = value.lower()
    if lowered in {"null", "~"}:
        return None
    if lowered in {"true", "false"}:
        return lowered == "true"
    if value.startswith("[") and value.endswith("]"):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            inner = value[1:-1].strip()
            return [] if not inner else [parse_scalar(part) for part in inner.split(",")]
    if value.startswith("{") and value.endswith("}"):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    if re.fullmatch(r"[-+]?\d+", value):
        return int(value)
    if re.fullmatch(r"[-+]?(?:\d+\.\d*|\d*\.\d+)(?:[eE][-+]?\d+)?", value):
        return float(value)
    return value


def parse_frontmatter(frontmatter: str | None) -> dict[str, Any]:
    if frontmatter is None:
        return {}
    lines = frontmatter.splitlines(keepends=True)
    result: dict[str, Any] = {}
    for key, start, end, inline in frontmatter_blocks(frontmatter):
        if key in result:
            raise VaultError(f"duplicate frontmatter key: {key}")
        if inline:
            result[key] = parse_scalar(inline)
            continue
        items: list[Any] = []
        valid_list = True
        for line in lines[start + 1 : end]:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            match = re.match(r"^\s+-\s*(.*)$", line.rstrip("\r\n"))
            if match is None:
                valid_list = False
                break
            items.append(parse_scalar(match.group(1)))
        result[key] = items if valid_list else "".join(lines[start + 1 : end]).rstrip()
    return result


def dump_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return json.dumps(value, ensure_ascii=False, allow_nan=False)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def dump_property(key: str, value: Any, newline: str) -> str:
    if "\n" in key or "\r" in key or key == "":
        raise VaultError("property name must be a non-empty single line")
    rendered_key = key if re.fullmatch(r"[\w .\-/\u3400-\u9fff]+", key) else json.dumps(key, ensure_ascii=False)
    if isinstance(value, list) and value:
        return rendered_key + ":" + newline + "".join(f"  - {dump_scalar(item)}{newline}" for item in value)
    return f"{rendered_key}: {dump_scalar(value)}{newline}"


def set_property(path: Path, key: str, value: Any) -> None:
    text = read_text(path)
    front, body, newline = split_frontmatter(text)
    replacement = dump_property(key, value, newline)
    if front is None:
        write_atomic(path, f"---{newline}{replacement}---{newline}{body}")
        return
    lines = front.splitlines(keepends=True)
    matches = [block for block in frontmatter_blocks(front) if block[0] == key]
    if len(matches) > 1:
        raise VaultError(f"duplicate frontmatter key: {key}")
    if matches:
        _, start, end, _ = matches[0]
        lines[start:end] = [replacement]
    else:
        if lines and not lines[-1].endswith(("\n", "\r")):
            lines[-1] += newline
        lines.append(replacement)
    write_atomic(path, f"---{newline}{''.join(lines)}---{newline}{body}")


def remove_property(path: Path, key: str) -> None:
    text = read_text(path)
    front, body, newline = split_frontmatter(text)
    if front is None:
        return
    lines = front.splitlines(keepends=True)
    matches = [block for block in frontmatter_blocks(front) if block[0] == key]
    if len(matches) > 1:
        raise VaultError(f"duplicate frontmatter key: {key}")
    if not matches:
        return
    _, start, end, _ = matches[0]
    del lines[start:end]
    write_atomic(path, f"---{newline}{''.join(lines)}---{newline}{body}")


def iter_notes(vault: Path, folder: str | None = None) -> Iterable[Path]:
    root = vault / folder if folder else vault
    if not root.exists():
        raise VaultError(f"folder does not exist: {root}")
    for path in sorted(root.rglob("*.md")):
        if ".obsidian" not in path.parts and ".trash" not in path.parts:
            yield path


def note_tags(props: dict[str, Any], body: str) -> set[str]:
    raw = props.get("tags", [])
    values = raw if isinstance(raw, list) else [raw]
    tags = {str(item).lstrip("#") for item in values if item not in (None, "")}
    tags.update(match.group(1) for match in INLINE_TAG.finditer(body))
    return tags


def command_query(args: argparse.Namespace) -> int:
    expected = json.loads(args.equals_json) if args.equals_json is not None else None
    rows = []
    for path in iter_notes(args.vault, args.folder):
        front, body, _ = split_frontmatter(read_text(path))
        props = parse_frontmatter(front)
        if args.property:
            if args.property not in props:
                continue
            if args.equals_json is not None and props[args.property] != expected:
                continue
        if args.tag and args.tag.lstrip("#") not in note_tags(props, body):
            continue
        rows.append({"path": path.relative_to(args.vault).as_posix(), "properties": props})
    if args.format == "paths":
        print("\n".join(row["path"] for row in rows))
    else:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


def yaml_dump(value: Any, indent: int = 0) -> list[str]:
    pad = " " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            key_text = key if re.fullmatch(r"[A-Za-z0-9_.-]+", str(key)) else json.dumps(str(key), ensure_ascii=False)
            if isinstance(item, (dict, list)) and item:
                lines.append(f"{pad}{key_text}:")
                lines.extend(yaml_dump(item, indent + 2))
            elif item == {}:
                lines.append(f"{pad}{key_text}: {{}}")
            elif item == []:
                lines.append(f"{pad}{key_text}: []")
            else:
                lines.append(f"{pad}{key_text}: {dump_scalar(item)}")
        return lines
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, (dict, list)) and item:
                lines.append(f"{pad}-")
                lines.extend(yaml_dump(item, indent + 2))
            else:
                lines.append(f"{pad}- {dump_scalar(item)}")
        return lines
    return [f"{pad}{dump_scalar(value)}"]


def command_base_render(args: argparse.Namespace) -> int:
    if args.output.exists() and not args.force:
        raise VaultError(f"output exists; pass --force to replace it: {args.output}")
    spec = json.loads(read_text(args.spec))
    if not isinstance(spec, dict) or not isinstance(spec.get("views"), list):
        raise VaultError("Base spec must be an object with a views list")
    write_atomic(args.output, "\n".join(yaml_dump(spec)) + "\n")
    return 0


def yaml_subset_load(text: str) -> Any:
    prepared: list[tuple[int, str]] = []
    for number, raw in enumerate(text.splitlines(), 1):
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise VaultError(f"tabs are not supported in Base indentation (line {number})")
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        prepared.append((len(raw) - len(raw.lstrip(" ")), stripped))

    def parse(index: int, indent: int) -> tuple[Any, int]:
        if index >= len(prepared) or prepared[index][0] < indent:
            return None, index
        is_list = prepared[index][0] == indent and prepared[index][1].startswith("-")
        container: Any = [] if is_list else {}
        while index < len(prepared):
            current_indent, content = prepared[index]
            if current_indent < indent:
                break
            if current_indent > indent:
                raise VaultError(f"unexpected indentation near: {content}")
            if is_list:
                if not content.startswith("-"):
                    break
                rest = content[1:].strip()
                index += 1
                if not rest:
                    if index < len(prepared) and prepared[index][0] > indent:
                        item, index = parse(index, prepared[index][0])
                    else:
                        item = None
                elif split_mapping_line(rest) is not None:
                    key, raw_value = split_mapping_line(rest)  # type: ignore[misc]
                    item = {key: parse_scalar(raw_value)} if raw_value else {key: None}
                    if not raw_value and index < len(prepared) and prepared[index][0] > indent:
                        child, index = parse(index, prepared[index][0])
                        item[key] = child
                    if index < len(prepared) and prepared[index][0] > indent:
                        extra, index = parse(index, prepared[index][0])
                        if not isinstance(extra, dict):
                            raise VaultError("list mapping continuation must be a mapping")
                        item.update(extra)
                else:
                    item = parse_scalar(rest)
                container.append(item)
            else:
                if content.startswith("-"):
                    break
                pair = split_mapping_line(content)
                if pair is None:
                    raise VaultError(f"expected mapping entry: {content}")
                key, raw_value = pair
                index += 1
                if raw_value:
                    container[key] = parse_scalar(raw_value)
                elif index < len(prepared) and prepared[index][0] > indent:
                    container[key], index = parse(index, prepared[index][0])
                else:
                    container[key] = None
        return container, index

    if not prepared:
        return {}
    result, final = parse(0, prepared[0][0])
    if final != len(prepared):
        raise VaultError(f"could not parse Base near: {prepared[final][1]}")
    return result


def split_boolean(expression: str, operator: str) -> list[str] | None:
    quote = None
    depth = 0
    start = 0
    parts = []
    index = 0
    while index <= len(expression) - len(operator):
        char = expression[index]
        if char in "\"'":
            quote = None if quote == char else char if quote is None else quote
        elif quote is None:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif depth == 0 and expression.startswith(operator, index):
                parts.append(expression[start:index].strip())
                start = index + len(operator)
                index += len(operator)
                continue
        index += 1
    if not parts:
        return None
    parts.append(expression[start:].strip())
    return parts


def field_value(token: str, props: dict[str, Any], path: Path, vault: Path) -> Any:
    token = token.strip()
    if token.startswith("note."):
        return props.get(token[5:])
    if token == "file.name":
        return path.stem
    if token == "file.path":
        return path.relative_to(vault).as_posix()
    if token == "file.folder":
        return path.parent.relative_to(vault).as_posix()
    if token == "file.ext":
        return path.suffix.lstrip(".")
    literal = parse_scalar(token)
    if isinstance(literal, str) and literal == token:
        return props.get(token)
    return literal


def evaluate_expression(expr: str, props: dict[str, Any], body: str, path: Path, vault: Path) -> bool:
    expression = expr.strip()
    if expression.startswith("(") and expression.endswith(")"):
        expression = expression[1:-1].strip()
    parts = split_boolean(expression, " || ")
    if parts:
        return any(evaluate_expression(part, props, body, path, vault) for part in parts)
    parts = split_boolean(expression, " && ")
    if parts:
        return all(evaluate_expression(part, props, body, path, vault) for part in parts)
    if expression.startswith("!"):
        return not evaluate_expression(expression[1:].strip(), props, body, path, vault)
    match = re.fullmatch(r"file\.inFolder\((.+)\)", expression)
    if match:
        folder = str(parse_scalar(match.group(1))).strip("/")
        relative = path.parent.relative_to(vault).as_posix()
        return relative == folder or relative.startswith(folder + "/")
    match = re.fullmatch(r"file\.hasTag\((.+)\)", expression)
    if match:
        return str(parse_scalar(match.group(1))).lstrip("#") in note_tags(props, body)
    match = re.fullmatch(r"contains\(([^,]+),\s*(.+)\)", expression)
    if match:
        haystack = field_value(match.group(1), props, path, vault)
        needle = field_value(match.group(2), props, path, vault)
        return needle in haystack if isinstance(haystack, (list, str, dict)) else False
    match = re.fullmatch(r"(.+?)\.contains\((.+)\)", expression)
    if match:
        haystack = field_value(match.group(1), props, path, vault)
        needle = field_value(match.group(2), props, path, vault)
        return needle in haystack if isinstance(haystack, (list, str, dict)) else False
    match = re.fullmatch(r"(.+?)\s*(==|!=|<=|>=|<|>)\s*(.+)", expression)
    if match:
        left = field_value(match.group(1), props, path, vault)
        right = field_value(match.group(3), props, path, vault)
        operation = match.group(2)
        try:
            if operation == "==":
                return left == right
            if operation == "!=":
                return left != right
            if operation == "<":
                return left < right
            if operation == "<=":
                return left <= right
            if operation == ">":
                return left > right
            return left >= right
        except TypeError:
            return False
    raise VaultError(f"unsupported Base filter expression: {expr}")


def evaluate_filter(node: Any, props: dict[str, Any], body: str, path: Path, vault: Path) -> bool:
    if node in (None, ""):
        return True
    if isinstance(node, str):
        return evaluate_expression(node, props, body, path, vault)
    if isinstance(node, list):
        return all(evaluate_filter(item, props, body, path, vault) for item in node)
    if isinstance(node, dict):
        if set(node) == {"and"}:
            values = node["and"] if isinstance(node["and"], list) else [node["and"]]
            return all(evaluate_filter(item, props, body, path, vault) for item in values)
        if set(node) == {"or"}:
            values = node["or"] if isinstance(node["or"], list) else [node["or"]]
            return any(evaluate_filter(item, props, body, path, vault) for item in values)
        if set(node) == {"not"}:
            values = node["not"] if isinstance(node["not"], list) else [node["not"]]
            return not any(evaluate_filter(item, props, body, path, vault) for item in values)
    raise VaultError(f"unsupported Base filter structure: {node!r}")


def command_base_query(args: argparse.Namespace) -> int:
    base = yaml_subset_load(read_text(args.base))
    if not isinstance(base, dict) or not isinstance(base.get("views"), list):
        raise VaultError("invalid Base: expected a views list")
    matches = [view for view in base["views"] if isinstance(view, dict) and view.get("name") == args.view]
    if len(matches) != 1:
        available = [view.get("name") for view in base["views"] if isinstance(view, dict)]
        raise VaultError(f"view not found or duplicated: {args.view}; available: {available}")
    view = matches[0]
    rows = []
    for path in iter_notes(args.vault):
        front, body, _ = split_frontmatter(read_text(path))
        props = parse_frontmatter(front)
        if not evaluate_filter(base.get("filters"), props, body, path, args.vault):
            continue
        if not evaluate_filter(view.get("filters"), props, body, path, args.vault):
            continue
        row = {"path": path.relative_to(args.vault).as_posix()}
        for field in view.get("order", []):
            row[str(field)] = field_value(str(field), props, path, args.vault)
        rows.append(row)
    if args.format == "paths":
        print("\n".join(row["path"] for row in rows))
    else:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


def resolve_link(target: str, source: Path, vault: Path, exact: dict[str, Path], names: dict[str, list[Path]]) -> Path | None:
    clean = target.split("|", 1)[0].split("#", 1)[0].split("^", 1)[0].strip().replace("\\", "/")
    if not clean:
        return source
    suffix = Path(clean).suffix.lower()
    if suffix and suffix != ".md":
        return None
    clean = clean[:-3] if clean.lower().endswith(".md") else clean
    candidates = [clean.strip("/")]
    relative_parent = source.parent.relative_to(vault).as_posix()
    candidates.append(str(Path(relative_parent) / clean))
    for candidate in candidates:
        normalized = Path(candidate).as_posix().lstrip("./")
        if normalized in exact:
            return exact[normalized]
    matches = names.get(Path(clean).name, [])
    return matches[0] if len(matches) == 1 else None


def command_audit(args: argparse.Namespace) -> int:
    notes = list(iter_notes(args.vault, args.folder))
    exact = {path.relative_to(args.vault).with_suffix("").as_posix(): path for path in notes}
    names: dict[str, list[Path]] = {}
    for path in notes:
        names.setdefault(path.stem, []).append(path)
    incoming = {path: 0 for path in notes}
    outgoing = {path: 0 for path in notes}
    unresolved = []
    invalid_frontmatter = []
    for path in notes:
        try:
            text = read_text(path)
            front, _, _ = split_frontmatter(text)
            parse_frontmatter(front)
        except VaultError as exc:
            invalid_frontmatter.append({"path": path.relative_to(args.vault).as_posix(), "error": str(exc)})
            continue
        resolved_targets = set()
        for match in WIKILINK.finditer(text):
            raw_target = match.group(1)
            resolved = resolve_link(raw_target, path, args.vault, exact, names)
            if resolved is None:
                clean = raw_target.split("|", 1)[0].split("#", 1)[0].strip()
                if not Path(clean).suffix or Path(clean).suffix.lower() == ".md":
                    unresolved.append({"source": path.relative_to(args.vault).as_posix(), "target": clean})
            elif resolved != path:
                resolved_targets.add(resolved)
        outgoing[path] = len(resolved_targets)
        for target in resolved_targets:
            incoming[target] += 1
    report = {
        "notes": len(notes),
        "invalid_frontmatter": invalid_frontmatter,
        "unresolved": unresolved,
        "orphans": [path.relative_to(args.vault).as_posix() for path, count in incoming.items() if count == 0],
        "deadends": [path.relative_to(args.vault).as_posix() for path, count in outgoing.items() if count == 0],
    }
    if args.format == "summary":
        report = {
            "notes": report["notes"],
            "invalid_frontmatter": len(report["invalid_frontmatter"]),
            "unresolved": len(report["unresolved"]),
            "orphans": len(report["orphans"]),
            "deadends": len(report["deadends"]),
        }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if invalid_frontmatter else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prop_set = sub.add_parser("property-set")
    prop_set.add_argument("file", type=Path)
    prop_set.add_argument("name")
    prop_set.add_argument("--value-json", required=True)
    prop_get = sub.add_parser("property-get")
    prop_get.add_argument("file", type=Path)
    prop_get.add_argument("name")
    prop_remove = sub.add_parser("property-remove")
    prop_remove.add_argument("file", type=Path)
    prop_remove.add_argument("name")
    query = sub.add_parser("query")
    query.add_argument("vault", type=Path)
    query.add_argument("--folder")
    query.add_argument("--property")
    query.add_argument("--equals-json")
    query.add_argument("--tag")
    query.add_argument("--format", choices=("paths", "json"), default="paths")
    audit = sub.add_parser("audit")
    audit.add_argument("vault", type=Path)
    audit.add_argument("--folder")
    audit.add_argument("--format", choices=("summary", "json"), default="summary")
    render = sub.add_parser("base-render")
    render.add_argument("spec", type=Path)
    render.add_argument("output", type=Path)
    render.add_argument("--force", action="store_true")
    base_query = sub.add_parser("base-query")
    base_query.add_argument("vault", type=Path)
    base_query.add_argument("base", type=Path)
    base_query.add_argument("--view", required=True)
    base_query.add_argument("--format", choices=("paths", "json"), default="paths")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "property-set":
            set_property(args.file, args.name, json.loads(args.value_json))
            return 0
        if args.command == "property-get":
            front, _, _ = split_frontmatter(read_text(args.file))
            props = parse_frontmatter(front)
            if args.name not in props:
                raise VaultError(f"property not found: {args.name}")
            print(json.dumps(props[args.name], ensure_ascii=False, indent=2))
            return 0
        if args.command == "property-remove":
            remove_property(args.file, args.name)
            return 0
        if args.command == "query":
            return command_query(args)
        if args.command == "audit":
            return command_audit(args)
        if args.command == "base-render":
            return command_base_render(args)
        if args.command == "base-query":
            return command_base_query(args)
        parser.error(f"unknown command: {args.command}")
    except (VaultError, OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
