#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Generate an automatic Bernese BPE documentation manual.

This script scans configured source directories containing:

- PCF/
- SCRIPT/
- OPT/

and writes a refreshed manual to the configured output directory.

The generated manual has two forms:

- Markdown:  <output>/bernese_bpe_manual.md
- HTML:      <output>/bernese_bpe_manual.html

The HTML version includes a lightweight search filter so the manual can be
searched directly in a browser.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import getpass
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional


ROOT = Path(__file__).resolve().parent

CONFIG_FILE = ROOT / "manual_config.json"


def load_manual_config() -> Dict[str, object]:
    defaults = {
        "default_user": "",
        "default_action": "a",
        "output_dir": "output/manual",
        "source_list_file": "manual_sources.txt",
        "default_comment_title": "Additional note",
        "handbook_import_dir": "manual_additions/import",
        "handbook_full_top_levels": [],
        "handbook_group_descriptions": {},
    }
    if not CONFIG_FILE.exists():
        return defaults
    try:
        configured = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Warning: could not read {CONFIG_FILE}: {exc}")
        return defaults
    if not isinstance(configured, dict):
        print(f"Warning: {CONFIG_FILE} must contain a JSON object.")
        return defaults
    return {**defaults, **configured}


MANUAL_CONFIG = load_manual_config()


def configured_path(key: str, fallback: str) -> Path:
    configured = MANUAL_CONFIG.get(key, fallback)
    value = str(configured).strip() or fallback
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path


HANDBOOK_IMPORT_DIR = configured_path("handbook_import_dir", "manual_additions/import")
HANDBOOK_DIR = ROOT / "manual_additions" / "handbook"
HISTORY_DIR = ROOT / "manual_additions" / "history"
HISTORY_LOG_FILE = HISTORY_DIR / "handbook_history.jsonl"
OUTPUT_DIR = configured_path("output_dir", "output/manual")
COMMENTS_DIR = ROOT / "manual_additions" / "comments"
SOURCE_LIST_FILE = configured_path("source_list_file", "manual_sources.txt")
ACTIVE_SOURCE_LABEL = ""
ACTIVE_USER_NAME = ""
MANUAL_INDEX_FILE = "bernese_bpe_manual.html"
OVERVIEW_PAGE_FILE = "index.html"
PCF_PAGE_FILE = "bernese_bpe_pcf.html"
SCRIPT_PAGE_FILE = "bernese_bpe_scripts.html"
FILE_PAGE_FILE = "bernese_bpe_files.html"
INP_PAGE_FILE = "bernese_bpe_inp.html"
HANDBOOK_PAGE_FILE = "bernese_bpe_handbook.html"
HISTORY_PAGE_FILE = "bernese_bpe_history.html"
STORY_PAGE_FILE = "bernese_bpe_stories.html"
HANDBOOK_SELECTED_RELATIVE_PATHS: List[str] = []
HANDBOOK_FULL_TOP_LEVELS = set(MANUAL_CONFIG.get("handbook_full_top_levels", []))
HANDBOOK_GROUP_DESCRIPTIONS = dict(MANUAL_CONFIG.get("handbook_group_descriptions", {}))


PCF_HEADER_RE = re.compile(r"^\s*PID\s+SCRIPT\s+OPT_DIR\s+PARAMETERS\s*$")
PCF_ENTRY_RE = re.compile(r"^\s*(\d+)\s+(\S+)\s+(\S+)\s*(.*?)\s*$")
PCF_PARAM_RE = re.compile(r"^\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$")
PCF_VAR_RE = re.compile(r"^\s*(V_[A-Z0-9_]+)\s*=\s*(.*?)(?:;\s*(.*))?$")

PACKAGE_RE = re.compile(r"^\s*package\s+([A-Za-z0-9_]+)\s*;\s*$")
PURPOSE_RE = re.compile(r"^\s*#\s*Purpose\s*:\s*(.*)\s*$", re.IGNORECASE)
RUN_PGMS_RE = re.compile(
    r"\$bpe->RUN_PGMS\(\s*(?:\$PGMNAM|\"([A-Za-z0-9_]+)\"|'([A-Za-z0-9_]+)')\s*\)"
)
SET_PGM_RE = re.compile(
    r"(?:my\s+)?\$PGMNAM\s*=\s*(?:\"([A-Za-z0-9_]+)\"|'([A-Za-z0-9_]+)')"
)
PUTKEY_RE = re.compile(
    r'\$bpe->putKey\("([^"]+\.INP)",\s*"([^"]+)",\s*(.*?)\);'
)
REPLSEL_RE = re.compile(
    r'\b(?:replaceSel|replaceSelLst)\(\$bpe,\s*"([^"]+)",\s*"([^"]+)",'
)
GETKEYS_RE = re.compile(r"\$bpe->getKeys\s*\((.*?)\);", re.DOTALL)
KEY_STRING_RE = re.compile(r"'([^']+)'|\"([^\"]+)\"")
GETKEYS_ASSIGN_RE = re.compile(
    r"my\s*\((.*?)\)\s*=\s*\$bpe->getKeys\s*\((.*?)\);",
    re.DOTALL,
)
SIMPLE_ASSIGN_RE = re.compile(
    r"my\s+\$([A-Za-z0-9_]+)\s*=\s*(\".*?\"|'.*?'|q\{.*?\}|qq\{.*?\});",
    re.DOTALL,
)
OPEN_RE = re.compile(
    r"\bopen\s*\(\s*(?:my\s+\$[A-Za-z0-9_]+|[A-Z]+|[A-Za-z0-9_]+)\s*,\s*([\'\"])([<>]{1,2})\1\s*,\s*(.+?)\s*\)",
    re.DOTALL,
)
OPEN_SHORT_RE = re.compile(
    r"\bopen\s*\(\s*(?:my\s+\$[A-Za-z0-9_]+|[A-Z]+|[A-Za-z0-9_]+)\s*,\s*([\'\"])([<>]{1,2})\1\s+(.+?)\s*\)",
    re.DOTALL,
)
COPYFILE_RE = re.compile(r"\bcopyfile\s*\(\s*(.+?)\s*,\s*(.+?)\s*\)", re.DOTALL)
UNLINK_RE = re.compile(r"\bunlink\s*\(?\s*([^\n;]+)")
GLOB_RE = re.compile(r"\bglob\s*\(\s*(.+?)\s*\)")

INP_FIELD_RE = re.compile(r"^([A-Z0-9_]+)\s+([01])(?:\s+(.*))?$")
SCRIPT_REF_SUFFIX_RE = re.compile(r"(_s_new|_s|_new)$", re.IGNORECASE)


@dataclass
class PCFEntry:
    pid: str
    script: str
    opt_dir: str
    parameters_raw: str
    parameters: Dict[str, str] = field(default_factory=dict)
    phase: str = ""


@dataclass
class PCFDocument:
    path: Path
    name: str
    source_label: str = ""
    identical_sources: List[str] = field(default_factory=list)
    description: str = ""
    comments: List[str] = field(default_factory=list)
    author: str = ""
    created: str = ""
    changes: str = ""
    entries: List[PCFEntry] = field(default_factory=list)
    variables: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class ScriptDocument:
    path: Path
    name: str
    source_label: str = ""
    identical_sources: List[str] = field(default_factory=list)
    package: str = ""
    purpose: str = ""
    programs: List[str] = field(default_factory=list)
    inp_paths: List[str] = field(default_factory=list)
    inp_keys: List[str] = field(default_factory=list)
    inp_modifications: List[tuple[str, str, str]] = field(default_factory=list)
    get_keys: List[str] = field(default_factory=list)
    file_reads: List[str] = field(default_factory=list)
    file_writes: List[str] = field(default_factory=list)
    file_deletes: List[str] = field(default_factory=list)
    file_globs: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


@dataclass
class ScriptIndex:
    by_name: Dict[str, ScriptDocument] = field(default_factory=dict)
    aliases: Dict[str, str] = field(default_factory=dict)


@dataclass
class INPField:
    key: str
    kind: str
    value: str = ""
    meta: Dict[str, str] = field(default_factory=dict)
    section: str = ""


@dataclass
class INPDocument:
    path: Path
    name: str
    source_label: str = ""
    identical_sources: List[str] = field(default_factory=list)
    title: str = ""
    sections: List[str] = field(default_factory=list)
    fields: List[INPField] = field(default_factory=list)


@dataclass
class HandbookDocument:
    path: Path
    name: str
    title: str
    category: str
    excerpt: List[str] = field(default_factory=list)


@dataclass
class HandbookHistoryRecord:
    timestamp: str
    user: str
    action: str
    target: str
    summary: str
    path: str = ""


def rel_link(target: Path, base: Path = OUTPUT_DIR) -> str:
    return Path(os.path.relpath(target, base)).as_posix()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def comment_file(kind: str, target: str) -> Path:
    return COMMENTS_DIR / kind / f"{slugify(target)}.md"


def manual_comment_html(
    kind: str,
    target: str,
    link_resolver: Optional[Callable[[str], str]] = None,
) -> str:
    path = comment_file(kind, target)
    if not path.exists():
        return ""
    body = render_simple_markdown_body(path, link_resolver, skip_first_heading=True)
    if not body:
        return ""
    return f"<section class='manual-comments'><h4>Comments</h4>{body}</section>"


def current_user_name() -> str:
    if ACTIVE_USER_NAME:
        return ACTIVE_USER_NAME
    configured_user = MANUAL_CONFIG.get("default_user", "").strip()
    if configured_user:
        return configured_user
    for value in (
        os.environ.get("DOCBUILDER_USER"),
        os.environ.get("USER"),
        os.environ.get("USERNAME"),
    ):
        if value:
            return value.strip()
    try:
        return getpass.getuser()
    except Exception:
        return "unknown"


def choose_user_name() -> None:
    global ACTIVE_USER_NAME
    default = current_user_name()
    entered = input(f"Your name for the change history [{default}]: ").strip()
    ACTIVE_USER_NAME = entered or default


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def ensure_history_store() -> None:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def load_handbook_history() -> List[HandbookHistoryRecord]:
    if not HISTORY_LOG_FILE.exists():
        return []
    records: List[HandbookHistoryRecord] = []
    for raw_line in read_text(HISTORY_LOG_FILE).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        records.append(
            HandbookHistoryRecord(
                timestamp=str(payload.get("timestamp", "")),
                user=str(payload.get("user", "")),
                action=str(payload.get("action", "")),
                target=str(payload.get("target", "")),
                summary=str(payload.get("summary", "")),
                path=str(payload.get("path", "")),
            )
        )
    records.sort(key=lambda entry: entry.timestamp, reverse=True)
    return records


def append_handbook_history(action: str, target: str, summary: str, path: str = "") -> None:
    ensure_history_store()
    record = {
        "timestamp": now_iso(),
        "user": current_user_name(),
        "action": action,
        "target": target,
        "summary": summary.strip(),
        "path": path,
    }
    with HISTORY_LOG_FILE.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def history_action_label(action: str) -> str:
    labels = {
        "added": "Added",
        "updated": "Updated",
        "deleted": "Deleted",
        "published": "Published",
        "built": "Built",
        "menu_action": "Menu action",
    }
    return labels.get(action.lower(), action.capitalize() or "Recorded")


def safe_handbook_filename(title: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", title).strip().strip(".")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned or "Untitled"


def editor_command() -> List[str]:
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if editor:
        return [editor]
    if os.name == "nt" and shutil.which("notepad.exe"):
        return ["notepad.exe"]
    if shutil.which("nano"):
        return ["nano"]
    if shutil.which("vi"):
        return ["vi"]
    return ["vi"]


def open_in_editor(path: Path) -> None:
    command = editor_command() + [str(path)]
    subprocess.run(command, check=False)


def select_from_numbered_list(prompt: str, options: List[tuple[str, Path]]) -> Optional[Path]:
    if not options:
        print("No matching handbook entries found.")
        return None
    print(prompt)
    for index, (label, _path) in enumerate(options, start=1):
        print(f"{index}. {label}")
    choice = input("Choose a number (or press Enter to cancel): ").strip()
    if not choice:
        return None
    if not choice.isdigit() or not (1 <= int(choice) <= len(options)):
        print("Invalid selection.")
        return None
    return options[int(choice) - 1][1]


def choose_startup_action() -> str:
    print("\nWhat would you like to do?")
    print("a. Only rebuild the manual")
    print("b1. Add GPSUSER")
    print("b2. Remove GPSUSER")
    print("b3. Update GPSUSER")
    print("c1. Add comment")
    print("c2. Remove comment")
    print("d1. Add handbook entry")
    print("d2. Remove handbook entry")
    print("d3. Edit handbook entry")
    default_action = MANUAL_CONFIG.get("default_action", "a").strip().lower()
    valid_actions = {"a", "b1", "b2", "b3", "c1", "c2", "d1", "d2", "d3"}
    if default_action not in valid_actions:
        default_action = "a"
    choice = input(f"Selection [{default_action}]: ").strip().lower() or default_action
    return choice if choice in valid_actions else default_action


def handbook_category_choices() -> List[str]:
    categories = sorted(
        {
            *HANDBOOK_FULL_TOP_LEVELS,
            *[path.relative_to(HANDBOOK_DIR).parts[0] for path in gather_handbook_files(HANDBOOK_DIR) if path.relative_to(HANDBOOK_DIR).parts],
        }
    )
    return categories


def handbook_entry_relpath(path: Path) -> str:
    try:
        return path.relative_to(HANDBOOK_DIR).as_posix()
    except ValueError:
        return path.as_posix()


def add_handbook_entry_interactively() -> bool:
    categories = handbook_category_choices()
    print("\nAdd handbook entry")
    for index, category in enumerate(categories, start=1):
        print(f"{index}. {category}")
    print("N. New category")
    choice = input("Choose a category (or press Enter to cancel): ").strip()
    if not choice:
        return False
    if choice.lower() == "n":
        category = input("New category name: ").strip()
        if not category:
            print("No category entered.")
            return False
    elif choice.isdigit() and 1 <= int(choice) <= len(categories):
        category = categories[int(choice) - 1]
    else:
        print("Invalid category selection.")
        return False

    title = input("Entry title: ").strip()
    if not title:
        print("A title is required.")
        return False
    summary = input("History summary: ").strip()
    if not summary:
        summary = f"Created handbook entry {title}"

    target_dir = HANDBOOK_DIR / category
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{safe_handbook_filename(title)}.md"
    if target_path.exists():
        print(f"That handbook entry already exists: {target_path}")
        return False

    timestamp = now_iso()
    seed = (
        f"# {title}\n\n"
        "Write the handbook entry here.\n\n"
        "## Notes\n\n"
        f"- Created by {current_user_name()} on {timestamp}\n"
    )
    write_text(target_path, seed)
    open_in_editor(target_path)
    append_handbook_history("added", handbook_entry_relpath(target_path), summary, handbook_entry_relpath(target_path))
    print(f"Handbook entry created: {target_path}")
    return True


def edit_handbook_entry_interactively() -> bool:
    handbook_docs = [doc for docs in gather_handbook_sections(HANDBOOK_DIR).values() for doc in docs]
    targets = [
        (f"{doc.path.relative_to(HANDBOOK_DIR).as_posix()} - {doc.title}", doc.path)
        for doc in handbook_docs
    ]
    selected = select_from_numbered_list("\nEdit handbook entry", targets)
    if not selected:
        return False
    open_in_editor(selected)
    summary = input("History summary for this edit: ").strip()
    if not summary:
        summary = f"Updated handbook entry {selected.stem}"
    append_handbook_history("updated", handbook_entry_relpath(selected), summary, handbook_entry_relpath(selected))
    print(f"Handbook entry updated: {selected}")
    return True


def remove_handbook_entry_interactively() -> bool:
    handbook_docs = [doc for docs in gather_handbook_sections(HANDBOOK_DIR).values() for doc in docs]
    targets = [
        (f"{doc.path.relative_to(HANDBOOK_DIR).as_posix()} - {doc.title}", doc.path)
        for doc in handbook_docs
    ]
    selected = select_from_numbered_list("\nRemove handbook entry", targets)
    if not selected:
        return False
    answer = input(f"Remove {selected.name}? [y/N]: ").strip().lower()
    if answer not in {"y", "yes", "j", "ja"}:
        return False
    selected.unlink()
    append_handbook_history(
        "deleted",
        handbook_entry_relpath(selected),
        f"Removed handbook entry {selected.stem}",
        handbook_entry_relpath(selected),
    )
    print(f"Handbook entry removed: {selected}")
    return True


def clean_line(line: str) -> str:
    return line.rstrip("\r\n")


def normalize_script_ref(name: str) -> str:
    stem = Path(name).stem if "." in name else name
    stem = SCRIPT_REF_SUFFIX_RE.sub("", stem)
    return stem.upper()


def parse_pcf_params(raw: str) -> Dict[str, str]:
    params: Dict[str, str] = {}
    for chunk in raw.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        match = PCF_PARAM_RE.match(chunk)
        if match:
            params[match.group(1)] = match.group(2).strip()
        else:
            params[f"RAW_{len(params) + 1}"] = chunk
    return params


def scan_pcf(path: Path, source_label: str = "") -> PCFDocument:
    lines = [clean_line(line) for line in read_text(path).splitlines()]
    doc = PCFDocument(path=path, name=path.name, source_label=source_label)

    header_mode = True
    in_entries = False
    in_vars = False

    pending_comment_lines: List[str] = []
    purpose_lines: List[str] = []
    in_purpose = False
    current_phase = ""
    for line in lines:
        stripped = line.strip()
        if header_mode:
            purpose_match = PURPOSE_RE.match(stripped)
            if purpose_match:
                purpose_lines = [purpose_match.group(1).strip()]
                in_purpose = True
            elif in_purpose and stripped.startswith("#"):
                purpose_line = stripped.lstrip("#").strip()
                if purpose_line.startswith("Author:"):
                    doc.author = purpose_line.split(":", 1)[1].strip()
                    in_purpose = False
                elif purpose_line.startswith("Created:"):
                    doc.created = purpose_line.split(":", 1)[1].strip()
                    in_purpose = False
                elif purpose_line.startswith("Changes:"):
                    in_purpose = False
                elif not purpose_line or set(purpose_line) <= {"-"}:
                    in_purpose = False
                else:
                    purpose_lines.append(purpose_line)
            elif stripped.startswith("# Description:"):
                doc.description = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("# Comments"):
                pass
            elif stripped.startswith("# Author"):
                doc.author = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("# Created"):
                doc.created = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("# Changes"):
                pass
            elif PCF_HEADER_RE.match(stripped):
                header_mode = False
                in_entries = True
            continue

        if stripped.startswith("VARIABLE"):
            in_entries = False
            in_vars = True
            continue

        if in_entries:
            if not stripped:
                continue
            if stripped.startswith("#"):
                phase_text = stripped.lstrip("#").strip()
                if phase_text and set(phase_text) != {"-"} and not phase_text.startswith("End of BPE"):
                    current_phase = phase_text
                continue
            match = PCF_ENTRY_RE.match(line)
            if not match:
                continue
            params_raw = match.group(4).strip()
            doc.entries.append(
                PCFEntry(
                    pid=match.group(1),
                    script=match.group(2),
                    opt_dir=match.group(3),
                    parameters_raw=params_raw,
                    parameters=parse_pcf_params(params_raw),
                    phase=current_phase,
                )
            )
            continue

        if in_vars:
            if not stripped:
                continue
            if stripped.startswith("#"):
                continue
            match = PCF_VAR_RE.match(line)
            if match:
                doc.variables.append(
                    {
                        "name": match.group(1),
                        "default": match.group(2).strip(),
                        "description": (match.group(3) or "").strip(),
                    }
                )
            else:
                pending_comment_lines.append(stripped)

    if pending_comment_lines and not doc.changes:
        doc.changes = " ".join(pending_comment_lines).strip()
    if purpose_lines and not doc.description:
        doc.description = " ".join(purpose_lines)

    return doc


def extract_keys_from_getkeys(argument_block: str) -> List[str]:
    keys: List[str] = []
    for match in KEY_STRING_RE.finditer(argument_block):
        key = match.group(1) or match.group(2)
        if key:
            keys.append(key)
    return keys


def categorize_read_keys(keys: List[str]) -> Dict[str, List[str]]:
    categories = {
        "V_ variables": [],
        "PARAM parameters": [],
        "Other keys": [],
    }
    for key in keys:
        if key.startswith("V_"):
            categories["V_ variables"].append(key)
        elif re.fullmatch(r"PARAM[A-Z0-9]+", key, re.IGNORECASE):
            categories["PARAM parameters"].append(key)
        else:
            categories["Other keys"].append(key)
    return categories


def normalize_file_expr(expr: str) -> str:
    expr = expr.strip()
    expr = expr.rstrip(");,")
    expr = re.split(r"\s+(?:or|and)\s+", expr, 1)[0]
    expr = re.split(r"\s+#", expr, 1)[0]
    if expr.startswith(("'", '"')) and expr.endswith(("'", '"')) and len(expr) >= 2:
        expr = expr[1:-1]
    expr = expr.strip()
    if expr.startswith("q{") and expr.endswith("}"):
        expr = expr[2:-1]
    expr = expr.strip()
    return expr


def strip_string_literal(expr: str) -> str:
    expr = expr.strip()
    if expr.startswith(("'", '"')) and expr.endswith(("'", '"')) and len(expr) >= 2:
        return expr[1:-1]
    if expr.startswith("q{") and expr.endswith("}"):
        return expr[2:-1]
    if expr.startswith("qq{") and expr.endswith("}"):
        return expr[3:-1]
    return expr


def build_symbolic_var_map(text: str) -> Dict[str, str]:
    compact = re.sub(r"\s+", " ", text)
    symbolic: Dict[str, str] = {}

    for match in GETKEYS_ASSIGN_RE.finditer(compact):
        vars_block = match.group(1)
        keys_block = match.group(2)
        var_names = [part.strip().lstrip("$") for part in vars_block.split(",") if part.strip()]
        key_values = [match.group(1) or match.group(2) for match in KEY_STRING_RE.finditer(keys_block)]
        for var_name, key_value in zip(var_names, key_values):
            symbolic[var_name] = key_value.strip()

    def resolve_expr(expr: str) -> str:
        expr = strip_string_literal(expr)

        def replace_var(match: re.Match[str]) -> str:
            var_name = match.group(1) or match.group(2)
            return symbolic.get(var_name, match.group(0))

        for _ in range(6):
            updated = re.sub(r"\$\{([A-Za-z0-9_]+)\}|\$([A-Za-z0-9_]+)", replace_var, expr)
            if updated == expr:
                break
            expr = updated
        return expr

    for _ in range(6):
        changed = False
        for match in SIMPLE_ASSIGN_RE.finditer(compact):
            var_name = match.group(1)
            resolved = resolve_expr(match.group(2))
            if symbolic.get(var_name) != resolved:
                symbolic[var_name] = resolved
                changed = True
        if not changed:
            break

    return symbolic


def expand_file_expr(expr: str, symbolic: Dict[str, str]) -> str:
    expr = strip_string_literal(expr)

    def replace_var(match: re.Match[str]) -> str:
        var_name = match.group(1) or match.group(2)
        return symbolic.get(var_name, match.group(0))

    for _ in range(6):
        updated = re.sub(r"\$\{([A-Za-z0-9_]+)\}|\$([A-Za-z0-9_]+)", replace_var, expr)
        if updated == expr:
            break
        expr = updated
    return normalize_file_expr(expr)


def collect_file_flows(text: str, symbolic: Optional[Dict[str, str]] = None) -> tuple[List[str], List[str], List[str], List[str]]:
    reads: List[str] = []
    writes: List[str] = []
    deletes: List[str] = []
    globs: List[str] = []

    symbolic = symbolic or {}

    compact = re.sub(r"\s+", " ", text)

    for match in OPEN_RE.finditer(compact):
        mode = match.group(2)
        expr = expand_file_expr(match.group(3), symbolic)
        if not expr:
            continue
        if "<" in mode:
            reads.append(expr)
        else:
            writes.append(expr)

    for match in OPEN_SHORT_RE.finditer(compact):
        mode = match.group(2)
        expr = expand_file_expr(match.group(3), symbolic)
        if not expr:
            continue
        if "<" in mode:
            reads.append(expr)
        else:
            writes.append(expr)

    for match in COPYFILE_RE.finditer(compact):
        src = expand_file_expr(match.group(1), symbolic)
        dst = expand_file_expr(match.group(2), symbolic)
        if src:
            reads.append(src)
        if dst:
            writes.append(dst)

    for match in UNLINK_RE.finditer(compact):
        expr = expand_file_expr(match.group(1), symbolic)
        if expr:
            if expr.startswith("glob("):
                globs.append(expr[5:-1] if expr.endswith(")") else expr[5:])
            else:
                deletes.append(expr)

    for match in GLOB_RE.finditer(compact):
        expr = expand_file_expr(match.group(1), symbolic)
        if expr:
            globs.append(expr)

    def unique(seq: List[str]) -> List[str]:
        return list(dict.fromkeys(seq))

    return unique(reads), unique(writes), unique(deletes), unique(globs)


def scan_script(path: Path, source_label: str = "") -> ScriptDocument:
    text = read_text(path)
    lines = text.splitlines()
    doc = ScriptDocument(path=path, name=path.name, source_label=source_label)

    purpose_lines: List[str] = []
    in_purpose = False
    for line in lines:
        package_match = PACKAGE_RE.match(line)
        if package_match and not doc.package:
            doc.package = package_match.group(1)
        purpose_match = PURPOSE_RE.match(line)
        if purpose_match and not purpose_lines:
            purpose_lines.append(purpose_match.group(1).strip())
            in_purpose = True
        elif in_purpose:
            stripped = line.strip()
            if not stripped.startswith("#"):
                in_purpose = False
                continue
            continuation = stripped.lstrip("#").strip()
            if not continuation:
                continue
            if re.match(r"^(Name|PARAMs?|Author|Created|Changes)\s*:", continuation, re.IGNORECASE):
                in_purpose = False
            else:
                purpose_lines.append(continuation)

    doc.purpose = " ".join(part for part in purpose_lines if part).strip()

    programs: List[str] = []
    for match in SET_PGM_RE.finditer(text):
        programs.append(match.group(1) or match.group(2))
    run_programs: List[str] = []
    for match in RUN_PGMS_RE.finditer(text):
        program = match.group(1) or match.group(2)
        if program:
            programs.append(program)
            run_programs.append(program)
    doc.programs = sorted(set(programs))

    inp_paths = set()
    inp_keys = set()
    inp_modifications: List[tuple[str, str, str]] = []
    for match in PUTKEY_RE.finditer(text):
        inp_paths.add(match.group(1))
        inp_keys.add(match.group(2))
        inp_modifications.append((normalize_inp_name(match.group(1)), match.group(2), match.group(3).strip()))
    for match in REPLSEL_RE.finditer(text):
        program = match.group(1)
        key = match.group(2)
        inp_paths.add(f"$ENV{{U}}/PAN/{program}.INP")
        inp_keys.add(key)
        inp_modifications.append((f"{program}.INP", key, "selection replacement"))
    # RUN_PGMS executes the Bernese program whose control file is <PGMNAM>.INP.
    # The PCF later supplies the OPT_DIR, so keep only the program-level name here.
    if RUN_PGMS_RE.search(text):
        for program in programs:
            inp_paths.add(f"{program}.INP")
    doc.inp_paths = sorted(inp_paths)
    doc.inp_keys = sorted(inp_keys)
    doc.inp_modifications = list(dict.fromkeys(inp_modifications))

    get_keys: List[str] = []
    for match in GETKEYS_RE.finditer(text):
        get_keys.extend(extract_keys_from_getkeys(match.group(1)))
    doc.get_keys = sorted(set(get_keys))

    symbolic_vars = build_symbolic_var_map(text)
    file_reads, file_writes, file_deletes, file_globs = collect_file_flows(text, symbolic_vars)
    doc.file_reads = file_reads
    doc.file_writes = file_writes
    doc.file_deletes = file_deletes
    doc.file_globs = file_globs

    notes: List[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") and "Run program" in stripped:
            notes.append(stripped.lstrip("#").strip())
    doc.notes = notes
    return doc


def scan_inp(path: Path, source_label: str = "") -> INPDocument:
    lines = [clean_line(line) for line in read_text(path).splitlines()]
    doc = INPDocument(path=path, name=path.name, source_label=source_label)

    current_section = ""
    pending_meta: Dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("!"):
            section_text = stripped.lstrip("!").strip()
            if section_text and not section_text.startswith("-"):
                current_section = section_text
                if section_text not in doc.sections:
                    doc.sections.append(section_text)
            continue
        if stripped.startswith("##"):
            meta = stripped.lstrip("#").lstrip("#").strip()
            if "=" in meta:
                key, value = meta.split("=", 1)
                pending_meta[key.strip()] = value.strip()
            continue
        match = INP_FIELD_RE.match(stripped)
        if not match:
            continue
        key, kind, value = match.groups()
        value = (value or "").strip()
        if value.startswith('"') and value.endswith('"') and len(value) >= 2:
            value = value[1:-1]
        doc.fields.append(
            INPField(
                key=key,
                kind=kind,
                value=value,
                meta=dict(pending_meta),
                section=current_section,
            )
        )
        if key == "TITLE" and not doc.title:
            doc.title = value
        pending_meta = {}
    return doc


def is_metadata_path(path: Path, base: Path) -> bool:
    try:
        relative_parts = path.relative_to(base).parts
    except ValueError:
        return False
    return any(part in {".git", ".hg", ".svn"} or part.startswith(".") for part in relative_parts[:-1])


def gather_files(base: Path, suffix: str) -> List[Path]:
    if not base.exists():
        return []
    return sorted(
        [
            path
            for path in base.rglob("*")
            if path.is_file()
            and not is_metadata_path(path, base)
            and path.suffix.lower() == suffix.lower()
        ]
    )


def gather_scripts(base: Path) -> List[Path]:
    if not base.exists():
        return []
    candidates = [
        path
        for path in base.rglob("*")
        if path.is_file()
        and not is_metadata_path(path, base)
        and path.suffix.lower() not in {".md", ".markdown", ".txt", ".rst"}
        and path.name.lower() not in {"thumbs.db", ".ds_store"}
    ]

    def script_priority(path: Path) -> tuple[int, int, str]:
        parts = [part.lower() for part in path.parts]
        in_orig = 1 if "orig" in parts else 0
        return (in_orig, len(path.parts), path.as_posix().lower())

    selected: Dict[str, Path] = {}
    for path in sorted(candidates, key=script_priority):
        key = path.name.lower()
        existing = selected.get(key)
        if existing is None or script_priority(path) < script_priority(existing):
            selected[key] = path

    return sorted(selected.values(), key=lambda path: path.name.lower())


def gather_inp_files(base: Path) -> List[Path]:
    if not base.exists():
        return []
    return sorted(
        [path for path in base.rglob("*.INP") if path.is_file() and not is_metadata_path(path, base)]
    )


def build_script_index(script_docs: List[ScriptDocument]) -> ScriptIndex:
    by_name: Dict[str, ScriptDocument] = {}
    aliases: Dict[str, str] = {}
    for doc in script_docs:
        keys = {
            normalize_script_ref(doc.name),
            normalize_script_ref(doc.package) if doc.package else "",
        }
        for key in keys:
            if not key:
                continue
            by_name[key] = doc
            aliases[doc.name] = doc.name
            aliases[doc.package or doc.name] = doc.name
    return ScriptIndex(by_name=by_name, aliases=aliases)


def resolve_script_doc(script_index: ScriptIndex, script_name: str) -> Optional[ScriptDocument]:
    return script_index.by_name.get(normalize_script_ref(script_name))


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def short_text(text: str, limit: int = 180) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def format_flow_items(items: List[str], limit: int = 12) -> str:
    shown = items[:limit]
    text = ", ".join(f"`{display_file_ref(item)}`" for item in shown) if shown else "-"
    if len(items) > limit:
        text += f" and {len(items) - limit} more"
    return text


def display_file_ref(value: str) -> str:
    """Use one readable separator style for generated file references."""
    value = value.replace("\\", "/")
    return re.sub(
        r"(\$\{(?:dir|path|pth)[A-Za-z0-9_]*\})(?!/)",
        r"\1/",
        value,
        flags=re.IGNORECASE,
    )


def build_file_registry(script_docs: List[ScriptDocument]) -> Dict[str, Dict[str, List[str]]]:
    registry: Dict[str, Dict[str, List[str]]] = defaultdict(
        lambda: {"reads": [], "writes": [], "deletes": [], "patterns": [], "directory": "", "basename": ""}
    )

    def add_item(item: str, bucket: str, script_name: str) -> None:
        item = item.strip()
        if not item:
            return
        entry = registry[item]
        if not entry["basename"]:
            normalized_item = item.replace("\\", "/")
            entry["directory"] = Path(normalized_item).parent.as_posix() if "/" in normalized_item else "(root)"
            entry["basename"] = Path(normalized_item).name
        scripts = entry[bucket]
        if script_name not in scripts:
            scripts.append(script_name)

    for script in script_docs:
        script_name = script.name
        for item in script.file_reads:
            add_item(item, "reads", script_name)
        for item in script.file_writes:
            add_item(item, "writes", script_name)
        for item in script.file_deletes:
            add_item(item, "deletes", script_name)
        for item in script.file_globs:
            add_item(item, "patterns", script_name)

    return dict(sorted(registry.items(), key=lambda item: item[0].lower()))


def group_file_registry_by_directory(
    file_registry: Dict[str, Dict[str, List[str]]]
) -> Dict[str, List[tuple[str, Dict[str, List[str]]]]]:
    grouped: Dict[str, List[tuple[str, Dict[str, List[str]]]]] = defaultdict(list)
    for item, info in file_registry.items():
        grouped[info["directory"] or "(root)"].append((item, info))
    for directory in grouped:
        grouped[directory].sort(key=lambda entry: entry[1]["basename"].lower() or entry[0].lower())
    return dict(sorted(grouped.items(), key=lambda item: item[0].lower()))


def group_handbook_by_category(
    handbook_docs: List[HandbookDocument],
) -> Dict[str, List[HandbookDocument]]:
    grouped: Dict[str, List[HandbookDocument]] = defaultdict(list)
    for doc in handbook_docs:
        grouped[handbook_group_key(doc.path)].append(doc)
    for group_key in grouped:
        grouped[group_key].sort(key=lambda doc: doc.title.lower())
    return dict(sorted(grouped.items(), key=lambda item: item[0].lower()))


def summarize_script_flow(doc: ScriptDocument) -> str:
    parts: List[str] = []
    if doc.file_reads:
        parts.append(f"R: {short_text(doc.file_reads[0], 35)}")
    if doc.file_writes:
        parts.append(f"W: {short_text(doc.file_writes[0], 35)}")
    if doc.file_deletes:
        parts.append(f"D: {short_text(doc.file_deletes[0], 35)}")
    if doc.file_globs:
        parts.append(f"P: {short_text(doc.file_globs[0], 35)}")
    return "; ".join(parts) if parts else "-"


def normalize_inp_name(inp_path: str) -> str:
    cleaned = strip_string_literal(inp_path).strip().replace("\\", "/")
    return Path(cleaned).name or cleaned


def resolve_entry_inp_targets(entry: PCFEntry, resolved: Optional[ScriptDocument]) -> List[str]:
    if not resolved or not resolved.inp_paths:
        return []
    targets: List[str] = []
    for inp_path in resolved.inp_paths:
        inp_name = normalize_inp_name(inp_path)
        if not inp_name:
            continue
        targets.append(f"{entry.opt_dir}/{inp_name}" if entry.opt_dir else inp_name)
    return list(dict.fromkeys(targets))


def wait_pids(entry: PCFEntry) -> List[str]:
    """Return the PIDs that must finish before this entry can run."""
    raw = entry.parameters.get("WAIT", "")
    return re.findall(r"\d+", raw)


def format_inp_targets(targets: List[str], limit: int = 8) -> str:
    shown = targets[:limit]
    text = ", ".join(f"`{item}`" for item in shown) if shown else "-"
    if len(targets) > limit:
        text += f" and {len(targets) - limit} more"
    return text


def render_link_chips(items: List[tuple[str, str]], limit: int = 8, empty_label: str = "-") -> str:
    shown = items[:limit]
    if not shown:
        return f"<span class='chip chip-empty'>{esc(empty_label)}</span>"
    chips = "".join(
        f"<a class='chip chip-link' href='{esc(href)}'>{esc(label)}</a>" for label, href in shown
    )
    if len(items) > limit:
        chips += f"<span class='chip chip-more'>+{len(items) - limit} more</span>"
    return f"<span class='chip-list'>{chips}</span>"


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "item"


def anchor_id(kind: str, title: str) -> str:
    return f"{kind}-{slugify(title)}"


def link_html(href: str, label: str, class_name: str = "ref-link") -> str:
    return f'<a class="{class_name}" href="{esc(href)}">{esc(label)}</a>'


def page_href(page_file: str, anchor: str = "") -> str:
    return f"{page_file}#{anchor}" if anchor else page_file


def rel_key(path: Path) -> str:
    return path.resolve().as_posix().lower()


def ref_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def ensure_handbook_source() -> bool:
    """Import the hand-written handbook once, then keep using the editable copy."""
    if HANDBOOK_DIR.exists():
        return False
    if not HANDBOOK_IMPORT_DIR.exists():
        return False

    HANDBOOK_DIR.mkdir(parents=True, exist_ok=True)
    imported = 0
    for source_path in HANDBOOK_IMPORT_DIR.rglob("*.md"):
        if not handbook_is_selected(source_path):
            continue
        relative = source_path.relative_to(HANDBOOK_IMPORT_DIR)
        target_path = HANDBOOK_DIR / relative
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        imported += 1

    if imported:
        marker = HANDBOOK_DIR / ".imported-from-configured-source"
        write_text(
            marker,
            "# Handbook source\n\n"
            "These Markdown files were imported automatically from the configured "
            "handbook import directory. Edit them here; `update_manual.py` will "
            "preserve the changes on every rebuild.\n",
        )
    return imported > 0


def gather_handbook_files(root: Path) -> List[Path]:
    if not root.exists():
        return []
    return sorted(root.rglob("*.md"), key=lambda path: path.relative_to(root).as_posix().lower())


def handbook_is_selected(path: Path) -> bool:
    try:
        rel = path.relative_to(HANDBOOK_DIR).as_posix()
    except ValueError:
        try:
            rel = path.relative_to(HANDBOOK_IMPORT_DIR).as_posix()
        except ValueError:
            return False
    try:
        path.relative_to(HANDBOOK_DIR)
        is_handbook_file = True
    except ValueError:
        is_handbook_file = False
    if is_handbook_file:
        return True
    top_level = rel.split("/", 1)[0]
    if top_level in HANDBOOK_FULL_TOP_LEVELS:
        return True
    return rel in HANDBOOK_SELECTED_RELATIVE_PATHS


def gather_handbook_selected_files(root: Path) -> List[Path]:
    files = [path for path in gather_handbook_files(root) if handbook_is_selected(path)]
    return sorted(files, key=lambda path: path.relative_to(root).as_posix().lower())


def clean_markdown_line(line: str) -> str:
    text = line.strip()
    if not text:
        return ""
    text = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    text = text.replace("**", "").replace("==", "")
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def strip_simple_markdown(text: str) -> str:
    text = text.replace("**", "").replace("==", "")
    text = re.sub(r"`([^`]*)`", r"\1", text)
    return text


def excerpt_markdown(path: Path, limit: int = 6) -> List[str]:
    lines = read_text(path).splitlines()
    excerpt: List[str] = []
    started = False
    for raw in lines:
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith("```"):
            continue
        cleaned = clean_markdown_line(stripped)
        if not cleaned:
            continue
        started = True
        excerpt.append(cleaned)
        if len(excerpt) >= limit:
            break
    return excerpt


def handbook_category(path: Path) -> str:
    parts = path.relative_to(HANDBOOK_DIR).parts
    if not parts:
        return "Handbook"
    return parts[0]


def handbook_group_key(path: Path) -> str:
    parts = path.relative_to(HANDBOOK_DIR).parts
    return parts[0] if parts else "Handbook"


def handbook_group_label(group_key: str) -> str:
    parts = group_key.split("/")
    if not parts:
        return group_key
    if len(parts) == 1:
        return parts[0].replace("_", " ")
    return " / ".join(part.replace("_", " ") for part in parts)


WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")


def scan_handbook_doc(path: Path) -> HandbookDocument:
    return HandbookDocument(
        path=path,
        name=path.name,
        title=path.stem,
        category=handbook_category(path),
        excerpt=excerpt_markdown(path),
    )


def gather_handbook_sections(root: Path) -> Dict[str, List[HandbookDocument]]:
    grouped: Dict[str, List[HandbookDocument]] = defaultdict(list)
    for path in gather_handbook_selected_files(root):
        doc = scan_handbook_doc(path)
        grouped[doc.category].append(doc)
    for category in grouped:
        grouped[category].sort(key=lambda doc: doc.title.lower())
    return dict(sorted(grouped.items(), key=lambda item: item[0].lower()))


def render_simple_markdown_body(
    path: Path,
    link_resolver: Optional[Callable[[str], str]] = None,
    skip_first_heading: bool = False,
) -> str:
    lines = read_text(path).splitlines()
    parts: List[str] = []
    bullets: List[str] = []
    first_heading_seen = False

    def render_inline(text: str) -> str:
        if link_resolver is None:
            return esc(text)
        rendered: List[str] = []
        last = 0
        for match in WIKILINK_RE.finditer(text):
            rendered.append(esc(text[last:match.start()]))
            target = match.group(1).strip()
            label = (match.group(2) or target).strip()
            href = link_resolver(target)
            if href:
                rendered.append(f'<a class="ref-link" href="{esc(href)}">{esc(label)}</a>')
            else:
                rendered.append(esc(label))
            last = match.end()
        rendered.append(esc(text[last:]))
        return "".join(rendered)

    def flush_bullets() -> None:
        nonlocal bullets
        if bullets:
            parts.append("<ul class='summary'>" + "".join(f"<li>{render_inline(item)}</li>" for item in bullets) + "</ul>")
            bullets = []

    for raw in lines:
        line = raw.strip()
        if not line:
            flush_bullets()
            continue
        if line.startswith("```"):
            flush_bullets()
            continue
        if line.startswith("#"):
            flush_bullets()
            heading = strip_simple_markdown(line.lstrip("#").strip())
            if skip_first_heading and not first_heading_seen:
                first_heading_seen = True
                continue
            first_heading_seen = True
            if heading:
                parts.append(f"<h4>{render_inline(heading)}</h4>")
            continue
        if line.startswith(("- ", "* ")):
            bullets.append(strip_simple_markdown(line[2:]).strip())
            continue
        if re.match(r"^[A-Za-z][A-Za-z0-9 _/-]*:\s*$", line):
            flush_bullets()
            parts.append(f"<h4>{render_inline(line[:-1].strip())}</h4>")
            continue
        flush_bullets()
        parts.append(f"<p>{render_inline(strip_simple_markdown(line))}</p>")

    flush_bullets()
    return "".join(parts)


def build_cross_refs(
    pcf_docs: List[PCFDocument],
    script_docs: List[ScriptDocument],
) -> Dict[str, List[str]]:
    refs: Dict[str, List[str]] = defaultdict(list)
    for pcf in pcf_docs:
        for entry in pcf.entries:
            refs[entry.script].append(pcf.name)
            refs[normalize_script_ref(entry.script)].append(pcf.name)
    return refs


def group_inp_by_directory(inp_docs: List[INPDocument]) -> Dict[str, List[INPDocument]]:
    grouped: Dict[str, List[INPDocument]] = defaultdict(list)
    for doc in inp_docs:
        try:
            rel_parent = doc.path.parent.relative_to(ROOT).as_posix()
        except ValueError:
            rel_parent = doc.path.parent.as_posix()
        grouped[rel_parent].append(doc)
    return dict(sorted(grouped.items(), key=lambda item: item[0].lower()))


def manual_markdown(
    generated_at: str,
    pcf_docs: List[PCFDocument],
    script_docs: List[ScriptDocument],
    inp_docs: List[INPDocument],
    handbook_docs: List[HandbookDocument],
    history_records: List[HandbookHistoryRecord],
    refs: Dict[str, List[str]],
    script_index: ScriptIndex,
    file_registry: Dict[str, Dict[str, List[str]]],
) -> str:
    inp_groups = group_inp_by_directory(inp_docs)
    file_groups = group_file_registry_by_directory(file_registry)
    total_pcf_entries = sum(len(doc.entries) for doc in pcf_docs)
    total_script_programs = sum(len(doc.programs) for doc in script_docs)
    total_script_reads = sum(len(doc.file_reads) for doc in script_docs)
    total_script_writes = sum(len(doc.file_writes) for doc in script_docs)
    total_script_deletes = sum(len(doc.file_deletes) for doc in script_docs)
    total_file_refs = len(file_registry)
    total_inp_fields = sum(len(doc.fields) for doc in inp_docs)
    total_inp_dirs = len(inp_groups)

    out: List[str] = []
    out.append("# Bernese GNSS Software BPE Documentation")
    out.append("")
    out.append(f"Generated: {generated_at}")
    out.append("")
    out.append("## Overview")
    out.append("")
    out.append(
        "This manual is generated from one or more configured source directories "
        "containing `PCF/`, `SCRIPT/`, and `OPT/`."
    )
    out.append("")
    out.append("### Snapshot")
    out.append("")
    out.append(f"- PCF files: {len(pcf_docs)}")
    out.append(f"- PCF process rows: {total_pcf_entries}")
    out.append(f"- Script files: {len(script_docs)}")
    out.append(f"- Bernese program references: {total_script_programs}")
    out.append(f"- Script file reads: {total_script_reads}")
    out.append(f"- Script file writes: {total_script_writes}")
    out.append(f"- Script file deletes: {total_script_deletes}")
    out.append(f"- File references: {total_file_refs}")
    out.append(f"- INP files: {len(inp_docs)}")
    out.append(f"- INP directories: {total_inp_dirs}")
    out.append(f"- INP fields: {total_inp_fields}")
    out.append("")
    out.append("### Workflow")
    out.append("")
    out.append("- `PCF` defines the process order.")
    out.append("- `SCRIPT` executes the task logic.")
    out.append("- The script updates one or more `.INP` files in the matching `OPT_DIR`.")
    out.append("- The script then calls one or more Bernese programs.")
    out.append("- The generated documentation shows the chain `PID -> Script -> Bernese program -> OPT_DIR -> INP`.")
    out.append("")

    out.append("## Handwritten Documentation")
    out.append("")
    out.append(
        "The following notes are imported from the configured handbook source and mirror the manually written project guide."
    )
    out.append("")
    handbook_groups = group_handbook_by_category(handbook_docs)
    for category, docs in handbook_groups.items():
        out.append(f"- {handbook_group_label(category)}: {len(docs)} page(s)")
    out.append("")

    out.append("## Change History")
    out.append("")
    out.append(
        "The handbook history is stored in `manual_additions/history/handbook_history.jsonl` and records who changed which entry."
    )
    out.append("")
    for record in history_records[:20]:
        out.append(
            f"- {record.timestamp} | {record.user or 'unknown'} | {history_action_label(record.action)} | {record.target} | {record.summary}"
        )
    if not history_records:
        out.append("- No handbook history entries have been recorded yet.")
    out.append("")

    out.append("## Quick Cross-Reference")
    out.append("")
    out.append("| PCF Script | Resolved Script | Primary Programs | Default INP targets |")
    out.append("| --- | --- | --- | --- |")
    for doc in pcf_docs:
        for entry in doc.entries:
            resolved = resolve_script_doc(script_index, entry.script)
            programs = ", ".join(f"`{p}`" for p in (resolved.programs[:3] if resolved else [])) or "-"
            resolved_name = resolved.package if resolved and resolved.package else (resolved.name if resolved else "-")
            inp_targets = format_inp_targets(resolve_entry_inp_targets(entry, resolved), limit=4)
            out.append(f"| `{entry.script}` | `{resolved_name}` | {programs} | {inp_targets} |")
    out.append("")

    out.append("## PCF Catalog")
    out.append("")
    for doc in pcf_docs:
        out.append(f"### {doc.name}")
        out.append("")
        if doc.description:
            out.append(f"{doc.description}")
            out.append("")
        if doc.author:
            out.append(f"- Author: {doc.author}")
        if doc.created:
            out.append(f"- Created: {doc.created}")
        if doc.comments:
            out.append(f"- Comments: {'; '.join(doc.comments)}")
        if doc.changes:
            out.append(f"- Changes: {doc.changes}")
        out.append(f"- Source: [{doc.path.name}]({rel_link(doc.path)})")
        out.append("")
        out.append("Resolution chain: `PID -> Script -> Bernese program -> OPT_DIR -> INP`")
        out.append("")
        out.append("Process Table")
        out.append("")
        out.append("| PID | Script | Resolved | OPT_DIR | INP files | File flow | Parameters |")
        out.append("| --- | --- | --- | --- | --- | --- | --- |")
        for entry in doc.entries:
            resolved = resolve_script_doc(script_index, entry.script)
            resolved_name = resolved.package if resolved and resolved.package else (resolved.name if resolved else "-")
            flow = summarize_script_flow(resolved) if resolved else "-"
            inp_targets = format_inp_targets(resolve_entry_inp_targets(entry, resolved), limit=6)
            out.append(
                "| {pid} | {script} | {resolved} | {opt_dir} | {inp_targets} | {flow} | {params} |".format(
                    pid=entry.pid,
                    script=entry.script,
                    resolved=resolved_name,
                    inp_targets=inp_targets,
                    flow=flow,
                    opt_dir=entry.opt_dir,
                    params=short_text(entry.parameters_raw or "-"),
                )
            )
        out.append("")
        if doc.variables:
            out.append("Variables:")
            out.append("")
            out.append("| Name | Default | Description |")
            out.append("| --- | --- | --- |")
            for var in doc.variables[:40]:
                out.append(
                    "| {name} | {default} | {desc} |".format(
                        name=var["name"],
                        default=short_text(var["default"], 80),
                        desc=short_text(var["description"], 140),
                    )
                )
            if len(doc.variables) > 40:
                out.append("")
                out.append(f"_... {len(doc.variables) - 40} more variables omitted in this summary._")
            out.append("")

    out.append("## Script Catalog")
    out.append("")
    for doc in script_docs:
        out.append(f"### {doc.name}")
        out.append("")
        if doc.package and doc.package != doc.name:
            out.append(f"- Package: `{doc.package}`")
        if doc.purpose:
            out.append(f"- Purpose: {doc.purpose}")
        if doc.programs:
            out.append(f"- Bernese programs: {', '.join(f'`{p}`' for p in doc.programs)}")
        if refs.get(normalize_script_ref(doc.name)):
            out.append(f"- Used in PCFs: {', '.join(sorted(set(refs[normalize_script_ref(doc.name)])))}")
        if doc.inp_paths:
            out.append(f"- INP files: {', '.join(f'`{Path(p).name}`' for p in doc.inp_paths)}")
        if doc.get_keys:
            out.append("- Read keys:")
            for category, keys in categorize_read_keys(doc.get_keys).items():
                if keys:
                    out.append(f"  - {category}: {', '.join(f'`{k}`' for k in keys[:20])}")
        if doc.file_reads:
            out.append(f"- File reads: {format_flow_items(doc.file_reads)}")
        if doc.file_writes:
            out.append(f"- File writes: {format_flow_items(doc.file_writes)}")
        if doc.file_deletes:
            out.append(f"- File deletes: {format_flow_items(doc.file_deletes)}")
        if doc.file_globs:
            out.append(f"- File patterns: {format_flow_items(doc.file_globs)}")
        out.append(f"- Source: [{doc.path.name}]({rel_link(doc.path)})")
    out.append("")

    out.append("## File Registry")
    out.append("")
    for directory, entries in file_groups.items():
        out.append(f"### {directory}")
        out.append("")
        out.append("| File | Reads | Writes | Deletes | Patterns |")
        out.append("| --- | --- | --- | --- | --- |")
        for item, info in entries:
            out.append(
                "| {file} | {reads} | {writes} | {deletes} | {patterns} |".format(
                    file=Path(item.replace("\\", "/")).name,
                    reads=", ".join(info["reads"]) if info["reads"] else "-",
                    writes=", ".join(info["writes"]) if info["writes"] else "-",
                    deletes=", ".join(info["deletes"]) if info["deletes"] else "-",
                    patterns=", ".join(info["patterns"]) if info["patterns"] else "-",
                )
            )
        out.append("")
    out.append("")

    out.append("## INP Catalog")
    out.append("")
    for doc in inp_docs:
        out.append(f"### {doc.name}")
        out.append("")
        if doc.sections:
            out.append(f"- Sections: {', '.join(doc.sections[:10])}")
            if len(doc.sections) > 10:
                out.append(f"- ... and {len(doc.sections) - 10} more sections")
        out.append(f"- Fields: {len(doc.fields)}")
        out.append(f"- Source: [{doc.path.name}]({rel_link(doc.path)})")
        out.append("")
        out.append("| Key | Type | Value | Section |")
        out.append("| --- | --- | --- | --- |")
        for field in doc.fields[:50]:
            out.append(
                "| {key} | {kind} | {value} | {section} |".format(
                    key=field.key,
                    kind=field.kind,
                    value=short_text(field.value, 120),
                    section=short_text(field.section, 80),
                )
            )
        if len(doc.fields) > 50:
            out.append("")
            out.append(f"_... {len(doc.fields) - 50} more fields omitted in this summary._")
        out.append("")

    out.append("## OPT Directory Catalog")
    out.append("")
    for dir_name, docs in inp_groups.items():
        out.append(f"### {dir_name}")
        out.append("")
        for doc in docs:
            out.append(f"- [{doc.name}]({rel_link(doc.path)})")
        out.append("")

    return "\n".join(out)


def card_html(
    doc_type: str,
    title: str,
    summary_lines: List[str],
    source: Optional[Path] = None,
    body: str = "",
    lead: str = "",
    card_id: str = "",
    collapsible: bool = False,
    action_href: str = "",
    action_label: str = "",
) -> str:
    summary_html = "".join(f"<li>{esc(line)}</li>" for line in summary_lines if line)
    lead_html = f"<p class='lead'>{esc(lead)}</p>" if lead else ""
    body_html = f"<div class='body'>{body}</div>" if body else ""
    source_html = (
        f'<a class="source-link" href="{esc(rel_link(source, OUTPUT_DIR))}">{esc(source.name)}</a>'
        if source
        else ""
    )
    action_html = (
        f"<a class='source-link' href='{esc(action_href)}'>{esc(action_label)}</a>"
        if action_href and action_label
        else ""
    )
    if collapsible:
        content = f"""
        <details class="pcf-details">
          <summary><span class="pcf-toggle-title">{esc(title)}</span>{action_html}<span class="pcf-toggle-hint">Show details</span>{source_html}</summary>
          {lead_html}
          <ul class="summary">{summary_html}</ul>
          {body_html}
        </details>
        """
        return f"""
    <article class="card" data-kind="{esc(doc_type)}" id="{esc(card_id)}">
      {content}
    </article>
    """
    return f"""
    <article class="card" data-kind="{esc(doc_type)}" id="{esc(card_id)}">
      <div class="card-head">
        <h3>{esc(title)}</h3>
        {source_html}
      </div>
      {lead_html}
      <ul class="summary">{summary_html}</ul>
      {body_html}
    </article>
    """


def table_html(headers: List[str], rows: List[List[str]]) -> str:
    head_html = "".join(f"<th>{esc(h)}</th>" for h in headers)
    row_html = []
    for row in rows:
        row_html.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>")
    return f"""
    <table class="table">
      <thead><tr>{head_html}</tr></thead>
      <tbody>
        {''.join(row_html)}
      </tbody>
    </table>
    """


def manual_html(
    generated_at: str,
    pcf_docs: List[PCFDocument],
    script_docs: List[ScriptDocument],
    inp_docs: List[INPDocument],
    handbook_docs: List[HandbookDocument],
    history_records: List[HandbookHistoryRecord],
    refs: Dict[str, List[str]],
    script_index: ScriptIndex,
    file_registry: Dict[str, Dict[str, List[str]]],
    page_kind: str = "index",
) -> str:
    inp_groups = group_inp_by_directory(inp_docs)
    file_groups = group_file_registry_by_directory(file_registry)
    handbook_groups = group_handbook_by_category(handbook_docs)
    total_pcf_entries = sum(len(doc.entries) for doc in pcf_docs)
    total_script_programs = sum(len(doc.programs) for doc in script_docs)
    total_script_reads = sum(len(doc.file_reads) for doc in script_docs)
    total_script_writes = sum(len(doc.file_writes) for doc in script_docs)
    total_script_deletes = sum(len(doc.file_deletes) for doc in script_docs)
    total_file_refs = len(file_registry)
    total_inp_fields = sum(len(doc.fields) for doc in inp_docs)
    total_inp_dirs = len(inp_groups)
    total_handbook_docs = len(handbook_docs)
    total_history_entries = len(history_records)

    page_title_map = {
        "index": "Bernese GNSS Software BPE Documentation",
        "pcf": "PCF Overview",
        "scripts": "Script Overview",
        "files": "File Overview",
        "inp": "INP Overview",
        "handbook": "Handbook",
        "history": "Change History",
        "stories": "Process Explanations",
    }
    current_title = page_title_map.get(page_kind, "Bernese GNSS Software BPE Documentation")
    current_page = {
        "index": MANUAL_INDEX_FILE,
        "pcf": PCF_PAGE_FILE,
        "scripts": SCRIPT_PAGE_FILE,
        "files": FILE_PAGE_FILE,
        "inp": INP_PAGE_FILE,
        "handbook": HANDBOOK_PAGE_FILE,
        "history": HISTORY_PAGE_FILE,
        "stories": STORY_PAGE_FILE,
    }.get(page_kind, MANUAL_INDEX_FILE)
    show_toolbar = page_kind != "index"

    pcf_cards = {doc.name: anchor_id("pcf", doc.name) for doc in pcf_docs}
    script_cards = {doc.name: anchor_id("script", doc.name) for doc in script_docs}
    # Use the resolved path for anchors so sources outside the builder folder work too.
    inp_cards = {rel_key(doc.path): anchor_id("inp", rel_key(doc.path)) for doc in inp_docs}
    file_cards = {item: anchor_id("file", item) for item in file_registry}
    handbook_cards = {rel_key(doc.path): anchor_id("handbook", doc.path.relative_to(HANDBOOK_DIR).as_posix()) for doc in handbook_docs}
    inp_group_cards = {directory: anchor_id("inp-group", directory) for directory in inp_groups}
    handbook_by_rel = {rel_key(doc.path): doc for doc in handbook_docs}
    handbook_by_key: Dict[str, List[HandbookDocument]] = defaultdict(list)
    for doc in handbook_docs:
        rel_path = doc.path.relative_to(HANDBOOK_DIR).as_posix()
        for candidate in {
            doc.name,
            doc.path.stem,
            doc.path.stem.replace("_", " "),
            doc.path.stem.replace("-", " "),
            rel_path,
            rel_path.rsplit(".", 1)[0],
        }:
            handbook_by_key[ref_key(candidate)].append(doc)
    inp_name_cards: Dict[str, str] = {}
    inp_target_cards: Dict[str, str] = {}
    inp_by_target: Dict[str, INPDocument] = {}
    for doc in inp_docs:
        inp_name_cards.setdefault(doc.name.lower(), inp_cards[rel_key(doc.path)])
        target_key = f"{doc.path.parent.name}/{doc.name}".lower()
        inp_target_cards[target_key] = inp_cards[rel_key(doc.path)]
        inp_by_target[target_key] = doc

    def render_opt_dir_cards() -> str:
        blocks: List[str] = []
        for dir_name, docs in inp_groups.items():
            doc_items = "".join(f"<li>{esc(doc.name)}</li>" for doc in docs)
            blocks.append(
                f"<article class='card' data-kind='inp' id='{esc(inp_group_cards[dir_name])}'><div class='card-head'><h3>{esc(dir_name)}</h3><span class='source-link'>{len(docs)} file(s)</span></div><ul class='summary'>{doc_items}</ul></article>"
            )
        return "".join(blocks)

    def href_for_script(script_name: str) -> str:
        card = script_cards.get(script_name)
        return page_href(SCRIPT_PAGE_FILE, card) if card else ""

    def href_for_pcf(pcf_name: str) -> str:
        card = pcf_cards.get(pcf_name)
        return page_href(PCF_PAGE_FILE, card) if card else ""

    def handbook_group_href(dir_name: str) -> str:
        card = inp_group_cards.get(dir_name)
        if card:
            return page_href(INP_PAGE_FILE, card)
        base = Path(dir_name).name
        card = inp_group_cards.get(base)
        return page_href(INP_PAGE_FILE, card) if card else ""

    def resolve_handbook_target(target: str) -> str:
        cleaned = target.strip().strip("`")
        if not cleaned:
            return ""
        cleaned = cleaned.replace("\\", "/")
        candidate_paths = [cleaned]
        if cleaned.endswith(".md"):
            candidate_paths.append(cleaned[:-3])
        else:
            candidate_paths.append(f"{cleaned}.md")
        for candidate in candidate_paths:
            candidate_path = HANDBOOK_DIR / candidate
            if candidate_path.exists() and candidate_path.is_file():
                doc = handbook_by_rel.get(rel_key(candidate_path))
                if doc:
                    return page_href(HANDBOOK_PAGE_FILE, handbook_cards[rel_key(doc.path)])
        key = ref_key(cleaned)
        matches = handbook_by_key.get(key, [])
        if matches:
            doc = matches[0]
            return page_href(HANDBOOK_PAGE_FILE, handbook_cards[rel_key(doc.path)])
        if cleaned in pcf_cards:
            return page_href(PCF_PAGE_FILE, pcf_cards[cleaned])
        if cleaned.upper().endswith(".PCF") and cleaned in pcf_cards:
            return page_href(PCF_PAGE_FILE, pcf_cards[cleaned])
        script_doc = resolve_script_doc(script_index, cleaned)
        if script_doc:
            return page_href(SCRIPT_PAGE_FILE, script_cards.get(script_doc.name, ""))
        group_href = handbook_group_href(cleaned)
        if group_href:
            return group_href
        return ""

    def href_for_inp_target(target: str) -> str:
        normalized = target.replace("\\", "/").strip()
        target_path = Path(normalized)
        target_name = target_path.name.lower()
        target_dir = target_path.parent.name.lower()
        exact_card = inp_target_cards.get(f"{target_dir}/{target_name}")
        if exact_card:
            return page_href(INP_PAGE_FILE, exact_card)
        card = inp_name_cards.get(target_name)
        if card:
            return page_href(INP_PAGE_FILE, card)
        rel_card = inp_cards.get(rel_key(Path(target)))
        return page_href(INP_PAGE_FILE, rel_card) if rel_card else ""

    inp_usage: Dict[str, List[str]] = defaultdict(list)
    inp_usage_pcfs: Dict[str, List[str]] = defaultdict(list)
    inp_usage_contexts: Dict[str, List[tuple[str, str, str, str]]] = defaultdict(list)
    script_usage_contexts: Dict[str, List[tuple[str, str, str]]] = defaultdict(list)
    for pcf in pcf_docs:
        for entry in pcf.entries:
            script = resolve_script_doc(script_index, entry.script)
            if not script:
                continue
            script_key = normalize_script_ref(script.name)
            for inp_target in resolve_entry_inp_targets(entry, script):
                inp_name = Path(inp_target.replace("\\", "/")).name.lower()
                context_key = f"{entry.opt_dir}/{inp_name}".lower()
                context = (pcf.name, entry.opt_dir, entry.pid, script.name)
                if context not in inp_usage_contexts[context_key]:
                    inp_usage_contexts[context_key].append(context)
                if script.name not in inp_usage[inp_name]:
                    inp_usage[inp_name].append(script.name)
                if pcf.name not in inp_usage_pcfs[inp_name]:
                    inp_usage_pcfs[inp_name].append(pcf.name)
                script_context = (pcf.name, entry.opt_dir, inp_target)
                if script_context not in script_usage_contexts[script_key]:
                    script_usage_contexts[script_key].append(script_context)

    cards: List[str] = []

    if page_kind == "index":
        overview_rows = [
            ("PCF pages", "Go to the PCF process chains", page_href(PCF_PAGE_FILE)),
            ("Process explanations", "Read an automatically generated explanation of each PCF", page_href(STORY_PAGE_FILE)),
            ("Scripts", "Inspect scripts used in the BPE's", page_href(SCRIPT_PAGE_FILE)),
            ("INP-files", "Inspect OPT_DIRs", page_href(INP_PAGE_FILE)),
            ("Handbook", "Open the additional documentation", page_href(HANDBOOK_PAGE_FILE)),
            ("Change History", "Review who updated the handbook and when", page_href(HISTORY_PAGE_FILE)),
        ]
        overview = [
            "<div class='section'>",
            "<div class='overview-heading'><span>DOCUMENTATION MAP</span><h2>Choose where to begin</h2><p>The links below lead from the process chain to the scripts and configuration files behind it.</p></div>",
            "<div class='overview-grid'>",
        ]
        for index, (title, desc, href) in enumerate(overview_rows, start=1):
            overview.append(
                f"<article class='overview-card'><div class='overview-card-number'>{index:02d}</div><h3>{esc(title)}</h3><p>{esc(desc)}</p><a class='overview-card-link' href='{esc(href)}'>Open page <span>-></span></a></article>"
            )
        overview.append("</div></div>")
        summary_blocks = "".join(overview)
    else:
        summary_blocks = ""

    def pcf_cards_html() -> List[str]:
        out: List[str] = []
        for doc in pcf_docs:
            summary = []
            if doc.author:
                summary.append(f"Author: {doc.author}")
            if doc.source_label:
                summary.append(f"Source: {doc.source_label}")
            if doc.identical_sources:
                summary.append(f"Identical 1:1 copy in: {', '.join(doc.identical_sources)}")
            summary.append(f"PCF rows: {len(doc.entries)}")
            if doc.variables:
                summary.append(f"Variables: {len(doc.variables)}")
            rows: List[List[str]] = []
            for entry in doc.entries:
                resolved = resolve_script_doc(script_index, entry.script)
                resolved_name = resolved.package if resolved and resolved.package else (resolved.name if resolved else "-")
                inp_targets = resolve_entry_inp_targets(entry, resolved)
                script_href = href_for_script(resolved.name if resolved else entry.script)
                script_cell = link_html(script_href, entry.script, "ref-link") if script_href else esc(entry.script)
                resolved_cell = link_html(script_href, resolved_name, "ref-link") if script_href else esc(resolved_name)
                inp_links = [(target, href_for_inp_target(target)) for target in inp_targets if href_for_inp_target(target)]
                rows.append([
                    esc(entry.pid),
                    script_cell,
                    resolved_cell,
                    esc(entry.opt_dir),
                    render_link_chips(inp_links, limit=5),
                    esc(short_text(entry.parameters_raw or "-", 90)),
                ])
            entry_by_pid = {entry.pid: entry for entry in doc.entries}
            wait_rows = []
            for entry in doc.entries:
                waits = wait_pids(entry)
                if waits:
                    wait_for = []
                    for pid in waits:
                        waited_entry = entry_by_pid.get(pid)
                        label = waited_entry.script if waited_entry else "PID " + pid
                        wait_for.append(f"<span class='chip'>{esc(pid)} {esc(label)}</span>")
                    wait_for_html = "".join(wait_for)
                    wait_rows.append(
                        f"<div class='wait-row'><span class='wait-pid'>PID {esc(entry.pid)}</span><span>{esc(entry.script)}</span><span class='wait-arrow'>←</span><span class='chip-list'>{wait_for_html}</span></div>"
                    )
            body_parts = [
                table_html(["PID", "Script", "Resolved", "OPT_DIR", "INP files", "Parameters"], rows),
            ]
            if wait_rows:
                body_parts.append("<h4>WAIT dependencies</h4><div class='wait-map'>" + "".join(wait_rows) + "</div>")
            body_parts.insert(0, "<h4>Process Table</h4>")
            if doc.variables:
                var_rows = []
                for var in doc.variables:
                    var_rows.append([esc(var["name"]), esc(short_text(var["default"], 60)), esc(short_text(var["description"], 120))])
                if len(doc.variables) > 20:
                    var_rows.append(["...", f"{len(doc.variables) - 20} more", ""])
                body_parts.append("<h4>Variables</h4>" + table_html(["Name", "Default", "Description"], var_rows))
            body_parts.append(manual_comment_html("pcf", doc.name))
            out.append(card_html("pcf", doc.name, summary, doc.path, "".join(body_parts), doc.description, pcf_cards[doc.name], collapsible=True, action_href=page_href(STORY_PAGE_FILE, anchor_id("story", doc.name)), action_label="Explain this process"))
        return out

    def script_cards_html() -> List[str]:
        out: List[str] = []
        for doc in script_docs:
            summary = []
            if doc.source_label:
                summary.append(f"Source: {doc.source_label}")
            if doc.identical_sources:
                summary.append(f"Identical 1:1 copy in: {', '.join(doc.identical_sources)}")
            if doc.package:
                summary.append(f"Package: {doc.package}")
            if doc.purpose:
                summary.append(f"Purpose: {doc.purpose}")
            if doc.programs:
                summary.append(f"Programs: {', '.join(doc.programs)}")
            if doc.inp_paths:
                summary.append(f"INP files: {len(doc.inp_paths)}")
            if doc.file_reads:
                summary.append(f"Reads: {len(doc.file_reads)}")
            if doc.file_writes:
                summary.append(f"Writes: {len(doc.file_writes)}")
            if doc.file_deletes:
                summary.append(f"Deletes: {len(doc.file_deletes)}")
            if refs.get(normalize_script_ref(doc.name)):
                summary.append(f"Used in PCFs: {len(set(refs[normalize_script_ref(doc.name)]))}")
            body_parts: List[str] = []
            if doc.programs:
                body_parts.append(table_html(["Bernese programs"], [[esc(prog)] for prog in doc.programs]))
            if doc.inp_paths:
                inp_rows = []
                contexts = script_usage_contexts.get(normalize_script_ref(doc.name), [])
                for pcf_name, opt_dir, target in contexts:
                    href = href_for_inp_target(target)
                    inp_rows.append([
                        link_html(href, Path(target).name, "ref-link") if href else esc(Path(target).name),
                        link_html(href_for_pcf(pcf_name), pcf_name, "ref-link") if href_for_pcf(pcf_name) else esc(pcf_name),
                        esc(opt_dir),
                    ])
                if inp_rows:
                    body_parts.append(table_html(["INP file", "PCF", "OPT_DIR"], inp_rows))
            if doc.inp_modifications:
                modification_rows = [
                    [esc(inp_name), esc(key), esc(short_text(value, 120) or "-")]
                    for inp_name, key, value in doc.inp_modifications[:60]
                ]
                body_parts.append(
                    "<section class='script-detail-section'><h4>INP modifications</h4>"
                    + table_html(["INP file", "Key", "Value or operation"], modification_rows)
                    + "</section>"
                )
            if doc.get_keys:
                read_key_parts = ["<section class='script-detail-section'><h4>Read keys</h4>"]
                for category, keys in categorize_read_keys(doc.get_keys).items():
                    if keys:
                        read_key_parts.append(
                            f"<h5>{esc(category)}</h5>"
                            + table_html(["Key"], [[esc(key)] for key in keys[:30]])
                        )
                read_key_parts.append("</section>")
                body_parts.append("".join(read_key_parts))
            if doc.file_reads or doc.file_writes or doc.file_deletes or doc.file_globs:
                flow_rows = []
                for item in doc.file_reads:
                    href = page_href(FILE_PAGE_FILE, file_cards[item]) if item in file_cards else ""
                    label = display_file_ref(item)
                    flow_rows.append(["read", link_html(href, label, "ref-link") if href else esc(label)])
                for item in doc.file_writes:
                    href = page_href(FILE_PAGE_FILE, file_cards[item]) if item in file_cards else ""
                    label = display_file_ref(item)
                    flow_rows.append(["write", link_html(href, label, "ref-link") if href else esc(label)])
                for item in doc.file_deletes:
                    href = page_href(FILE_PAGE_FILE, file_cards[item]) if item in file_cards else ""
                    label = display_file_ref(item)
                    flow_rows.append(["delete", link_html(href, label, "ref-link") if href else esc(label)])
                for item in doc.file_globs:
                    href = page_href(FILE_PAGE_FILE, file_cards[item]) if item in file_cards else ""
                    label = display_file_ref(item)
                    flow_rows.append(["pattern", link_html(href, label, "ref-link") if href else esc(label)])
                body_parts.append(table_html(["Type", "File or pattern"], flow_rows[:60]))
            pcf_refs = sorted(set(refs.get(normalize_script_ref(doc.name), [])))
            if pcf_refs:
                pcf_rows = [[link_html(href_for_pcf(name), name, "ref-link") if href_for_pcf(name) else esc(name)] for name in pcf_refs]
                body_parts.append(table_html(["PCF files"], pcf_rows))
            body_parts.append(manual_comment_html("scripts", doc.name))
            out.append(card_html("script", doc.name, summary, doc.path, "".join(body_parts), card_id=script_cards[doc.name], collapsible=True))
        return out

    def file_cards_html() -> List[str]:
        out: List[str] = []
        for directory, entries in file_groups.items():
            summary = [f"Files: {len(entries)}"]
            rows = []
            for item, info in entries:
                href = page_href(FILE_PAGE_FILE, file_cards[item])
                rows.append([
                    link_html(href, Path(item.replace("\\", "/")).name, "ref-link"),
                    esc(", ".join(info["reads"]) if info["reads"] else "-"),
                    esc(", ".join(info["writes"]) if info["writes"] else "-"),
                    esc(", ".join(info["deletes"]) if info["deletes"] else "-"),
                    esc(", ".join(info["patterns"]) if info["patterns"] else "-"),
                ])
            body = table_html(["File", "Reads", "Writes", "Deletes", "Patterns"], rows)
            out.append(card_html("file", directory, summary, None, body, directory, anchor_id("file-group", directory)))
        for item, info in file_registry.items():
            summary = [f"Directory: {info['directory']}" if info["directory"] else "Directory: (root)", f"Reads: {len(info['reads'])}", f"Writes: {len(info['writes'])}", f"Deletes: {len(info['deletes'])}", f"Patterns: {len(info['patterns'])}"]
            body_parts = []
            occ_rows = []
            for bucket, label in (("reads", "read"), ("writes", "write"), ("deletes", "delete"), ("patterns", "pattern")):
                for script_name in info[bucket]:
                    href = href_for_script(script_name)
                    occ_rows.append([label, link_html(href, script_name, "ref-link") if href else esc(script_name)])
            if occ_rows:
                body_parts.append(table_html(["Type", "Script"], occ_rows))
            basename = Path(item.replace("\\", "/")).name.lower()
            if basename in inp_name_cards:
                body_parts.append(table_html(["Related INP"], [[link_html(page_href(INP_PAGE_FILE, inp_name_cards[basename]), basename.upper(), "ref-link")]]))
            out.append(card_html("file", display_file_ref(item), summary, None, "".join(body_parts), item, file_cards[item]))
        return out

    def story_cards_html() -> List[str]:
        out: List[str] = []
        for pcf in pcf_docs:
            entry_by_pid = {entry.pid: entry for entry in pcf.entries}
            blocks: List[str] = []
            current_phase = ""
            step_number = 0
            for entry in pcf.entries:
                if entry.phase and entry.phase != current_phase:
                    if current_phase:
                        blocks.append("</section>")
                    blocks.append(f"<section class='story-phase'><h4>{esc(entry.phase)}</h4>")
                    current_phase = entry.phase
                elif not current_phase:
                    blocks.append("<section class='story-phase'><h4>Processing steps</h4>")
                    current_phase = "Processing steps"
                step_number += 1
                script = resolve_script_doc(script_index, entry.script)
                script_label = entry.script
                script_href = href_for_script(script.name if script else entry.script)
                script_html = link_html(script_href, script_label, "ref-link") if script_href else esc(script_label)
                program_names = script.programs if script else []
                if program_names:
                    program_text = ", ".join(esc(name) for name in program_names)
                    program_sentence = f"The Bernese program(s) called are {program_text}."
                    program_titles = []
                    for program_name in program_names:
                        inp_doc = inp_by_target.get(f"{entry.opt_dir}/{program_name}.INP".lower())
                        if inp_doc and inp_doc.title:
                            program_titles.append(
                                f"<span class='story-program-title'>{esc(program_name)}: {esc(inp_doc.title)}</span>"
                            )
                    title_html = "".join(program_titles)
                else:
                    program_sentence = "No Bernese program is called in this step."
                    title_html = ""
                waits = wait_pids(entry)
                wait_text = ""
                if waits:
                    wait_labels = [
                        f"PID {esc(pid)} ({esc(entry_by_pid[pid].script)})" if pid in entry_by_pid else f"PID {esc(pid)}"
                        for pid in waits
                    ]
                    wait_text = " Before it can start, it waits for " + ", ".join(wait_labels) + " to finish."
                purpose = script.purpose if script and script.purpose else "The script performs this processing step."
                purpose_text = purpose.strip()
                if purpose_text and purpose_text[-1] not in ".!?":
                    purpose_text += "."
                blocks.append(
                    f"<div class='story-step'><span class='story-number'>Step {step_number}</span><p>"
                    f"<strong>{script_html}</strong>. {esc(purpose_text)} {program_sentence}{wait_text}{title_html}</p></div>"
                )
            if current_phase:
                blocks.append("</section>")
            summary = [f"{len(pcf.entries)} processing steps"]
            out.append(card_html("story", f"{pcf.name}", summary, pcf.path, "".join(blocks), pcf.description, anchor_id("story", pcf.name), collapsible=True))
        return out

    def inp_cards_html() -> List[str]:
        out: List[str] = []
        grouped: Dict[str, List[INPDocument]] = defaultdict(list)
        for doc in inp_docs:
            grouped[doc.name.lower()].append(doc)
        for basename, versions in sorted(grouped.items()):
            versions.sort(key=lambda doc: doc.path.parent.name.lower())
            version_links = []
            version_cards = []
            for doc in versions:
                version_key = f"{doc.path.parent.name}/{doc.name}".lower()
                context_key = version_key
                contexts = inp_usage_contexts.get(context_key, [])
                context_text = ", ".join(
                    f"{pcf} / {opt}" for pcf, opt in sorted({(pcf, opt) for pcf, opt, _pid, _script in contexts})
                ) or "not used by a scanned PCF"
                version_links.append(
                    f"<li><a class='ref-link' href='#{esc(inp_cards[rel_key(doc.path)])}'>{esc(doc.path.parent.name)}/{esc(doc.name)}</a> <span class='context-note'>({esc(context_text)})</span></li>"
                )
                rows = [
                    [esc(field.key), esc(field.kind), esc(short_text(field.value, 100)), esc(short_text(field.section, 80))]
                    for field in doc.fields[:60]
                ]
                if len(doc.fields) > 60:
                    rows.append(["...", "...", f"{len(doc.fields) - 60} more fields", ""])
                body_parts = [table_html(["Key", "Type", "Value", "Section"], rows)]
                if contexts:
                    usage_rows = []
                    for pcf_name, opt_dir, pid, script_name in contexts:
                        usage_rows.append([
                            link_html(href_for_pcf(pcf_name), pcf_name, "ref-link") if href_for_pcf(pcf_name) else esc(pcf_name),
                            esc(opt_dir),
                            esc(pid),
                            link_html(href_for_script(script_name), script_name, "ref-link") if href_for_script(script_name) else esc(script_name),
                        ])
                    body_parts.append("<h4>Used in PCFs</h4>" + table_html(["PCF", "OPT_DIR", "PID", "Script"], usage_rows))
                body_parts.append(manual_comment_html("inp", version_key))
                version_summary = [f"Fields: {len(doc.fields)}"]
                if doc.source_label:
                    version_summary.append(f"Source: {doc.source_label}")
                if doc.identical_sources:
                    version_summary.append(f"Identical 1:1 copy in: {', '.join(doc.identical_sources)}")
                version_cards.append(card_html("inp", f"{doc.path.parent.name}/{doc.name}", version_summary, doc.path, "".join(body_parts), card_id=inp_cards[rel_key(doc.path)]))
            group_id = anchor_id("inp-group", basename)
            group_body = "<ul class='inp-version-list'>" + "".join(version_links) + "</ul>" + "".join(version_cards)
            out.append(
                f"<article class='card' data-kind='inp' id='{esc(group_id)}'><details class='inp-group'><summary>{esc(basename.upper())}<span class='context-note'>{len(versions)} version(s)</span></summary><div class='body'>{group_body}</div></details></article>"
            )
        return out

    def handbook_cards_html() -> List[str]:
        out: List[str] = []
        toc = []
        for category, docs in handbook_groups.items():
            toc.append(
                f"<a class='chip chip-link' href='#{esc(anchor_id('handbook-section', category))}'>{esc(handbook_group_label(category))} ({len(docs)})</a>"
            )
        out.append(f"<div class='handbook-toc'>{''.join(toc)}</div>")
        for idx, (category, docs) in enumerate(handbook_groups.items()):
            default_open = ""
            section_id = anchor_id("handbook-section", category)
            section_desc = HANDBOOK_GROUP_DESCRIPTIONS.get(category, "")
            doc_links = "".join(
                f"<li><a class='ref-link' href='#{esc(handbook_cards[rel_key(doc.path)])}'>{esc(doc.title)}</a></li>"
                for doc in docs
            )
            doc_cards = []
            for doc in docs:
                full_text = render_simple_markdown_body(doc.path, resolve_handbook_target)
                body_parts = [
                    f"<details class='handbook-text'><summary>Show full text</summary>{full_text}</details>",
                    manual_comment_html("handbook", doc.path.relative_to(HANDBOOK_DIR).as_posix(), resolve_handbook_target),
                ]
                doc_cards.append(
                    card_html(
                        "handbook",
                        doc.title,
                        [],
                        None,
                        "".join(body_parts),
                        card_id=handbook_cards[rel_key(doc.path)],
                    )
                )
            out.append(
                f"<details class='handbook-group' id='{esc(section_id)}' data-default-open='0'{default_open}><summary><span>{esc(handbook_group_label(category))}</span><span class='handbook-count'>{len(docs)} page(s)</span><span class='handbook-note'>{esc(section_desc)}</span></summary><div class='handbook-group-body'><ul class='handbook-doclist'>{doc_links}</ul>{''.join(doc_cards)}</div></details>"
            )
        return out

    def history_cards_html() -> List[str]:
        out: List[str] = []
        if not history_records:
            out.append(
                card_html(
                    "history",
                    "No history yet",
                    ["No handbook changes have been recorded so far."],
                    None,
                    "<p class='lead'>Add or edit handbook entries from the terminal to start building the change log.</p>",
                    card_id=anchor_id("history", "empty"),
                )
            )
            return out
        for record in history_records:
            summary = [
                f"User: {record.user or 'unknown'}",
                f"Action: {history_action_label(record.action)}",
                f"Target: {record.target or '-'}",
            ]
            body = (
                f"<p><strong>{esc(record.timestamp)}</strong></p>"
                f"<p>{esc(record.summary or '-')}</p>"
            )
            out.append(
                card_html(
                    "history",
                    record.target or record.timestamp,
                    summary,
                    None,
                    body,
                    card_id=anchor_id("history", record.timestamp + record.target),
                )
            )
        return out

    if page_kind == "index":
        cards.extend([])
    elif page_kind == "pcf":
        cards.extend(pcf_cards_html())
    elif page_kind == "scripts":
        cards.extend(script_cards_html())
    elif page_kind == "files":
        cards.extend(file_cards_html())
    elif page_kind == "stories":
        cards.extend(story_cards_html())
    elif page_kind == "inp":
        cards.extend(inp_cards_html())
    elif page_kind == "handbook":
        cards.extend(handbook_cards_html())
    elif page_kind == "history":
        cards.extend(history_cards_html())
    else:
        cards.extend(pcf_cards_html() + script_cards_html() + file_cards_html() + inp_cards_html() + handbook_cards_html() + history_cards_html())

    stats_html = f"""
    <div class="stats">
      <div class="stat"><div class="label">PCF files</div><div class="value">{len(pcf_docs)}</div></div>
      <div class="stat"><div class="label">PCF rows</div><div class="value">{total_pcf_entries}</div></div>
      <div class="stat"><div class="label">Script files</div><div class="value">{len(script_docs)}</div></div>
      <div class="stat"><div class="label">Program refs</div><div class="value">{total_script_programs}</div></div>
      <div class="stat"><div class="label">INP files</div><div class="value">{len(inp_docs)}</div></div>
      <div class="stat"><div class="label">OPT DIRS</div><div class="value">{total_inp_dirs}</div></div>
      <div class="stat"><div class="label">INP fields</div><div class="value">{total_inp_fields}</div></div>
      <div class="stat"><div class="label">Handbook pages</div><div class="value">{total_handbook_docs}</div></div>
      <div class="stat"><div class="label">History entries</div><div class="value">{total_history_entries}</div></div>
    </div>
    """

    nav_items = [
        ("Overview", MANUAL_INDEX_FILE, "index"),
        ("PCF", PCF_PAGE_FILE, "pcf"),
        ("Process Explanations", STORY_PAGE_FILE, "stories"),
        ("Scripts", SCRIPT_PAGE_FILE, "scripts"),
        ("INP", INP_PAGE_FILE, "inp"),
        ("Handbook", HANDBOOK_PAGE_FILE, "handbook"),
        ("History", HISTORY_PAGE_FILE, "history"),
    ]
    nav_html = "<nav class='nav'>" + "".join(
        f"<a class='{'active' if page_kind == key else ''}' href='{esc(href)}'>{esc(label)}</a>" for label, href, key in nav_items
    ) + "</nav>"

    toolbar_html = ""
    if show_toolbar:
        toolbar_html = """
    <div class="toolbar">
      <input id="q" type="search" placeholder="Search by file, script, program, OPT_DIR, key, or text">
      <select id="kind">
        <option value="all">All kinds</option>
        <option value="pcf">PCF</option>
        <option value="story">Process explanation</option>
        <option value="script">Script</option>
        <option value="file">File</option>
        <option value="inp">INP</option>
        <option value="handbook">Handbook</option>
        <option value="history">History</option>
      </select>
      <select id="sort">
        <option value="name">Sort by name</option>
        <option value="kind">Sort by kind</option>
      </select>
    </div>
    """

    cards_html = "\n".join(cards)
    index_intro = ""
    if page_kind == "index":
        index_intro = f"""
    <div class="section">
      <div class="grid-2">
        <article class="card"><h3>How to use the manual</h3><p class="lead">Start with the PCF page to follow the chain from PID to script, then jump to scripts, files, or INP-files from any link.</p></article>
        <article class="card"><h3>Navigation</h3><p class="lead">Every script, PCF, file, and INP-file is linked so you can jump between the related locations directly.</p></article>
      </div>
    </div>
    """

    page_sections = ""
    if page_kind == "index":
        page_sections = index_intro + summary_blocks
    else:
        page_sections = f"""
    <h2>{esc(current_title)}</h2>
    <div id="cards" class="section">
      {cards_html}
    </div>
    """

    body_html = page_sections
    if page_kind != "index":
        body_html = f"""
    <h2>{esc(current_title)}</h2>
    <div id="cards" class="section">
      {cards_html}
    </div>
    """
        if page_kind == "files":
            body_html += f"""
    <h2>OPT Directories</h2>
    <div class="section">
      {render_opt_dir_cards()}
    </div>
    """

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(current_title)}</title>
  <style>
    :root {{
      --bg: #f4f7fb;
      --panel: #ffffff;
      --text: #152033;
      --muted: #5b6b82;
      --border: #d7e0ea;
      --accent: #1f5fbf;
      --accent-soft: #e8f0fe;
      --shadow: 0 10px 30px rgba(16, 32, 64, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Segoe UI, Arial, sans-serif; background: linear-gradient(180deg, #f8fbff 0%, var(--bg) 100%); color: var(--text); }}
    .wrap {{ max-width: 1400px; margin: 0 auto; padding: 28px 24px 48px; }}
    .hero {{ background: linear-gradient(135deg, #10223d 0%, #1f5fbf 100%); color: #fff; border-radius: 20px; padding: 24px 28px; box-shadow: var(--shadow); margin-bottom: 20px; }}
    .hero h1 {{ margin: 0 0 8px; font-size: 34px; }}
    .hero p {{ margin: 6px 0; color: rgba(255,255,255,0.88); line-height: 1.5; }}
    .nav {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 16px; }}
    .nav a {{ color: #fff; text-decoration: none; border: 1px solid rgba(255,255,255,0.28); padding: 8px 12px; border-radius: 999px; }}
    .nav a.active {{ background: #fff; color: #10223d; }}
    .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(118px, 1fr)); gap: 8px; margin: 14px 0 18px; }}
    .stat, .card {{ background: var(--panel); border: 1px solid var(--border); border-radius: 16px; box-shadow: var(--shadow); }}
    .stat {{ padding: 10px 11px; }}
    .stat .label {{ color: var(--muted); font-size: 10px; text-transform: uppercase; letter-spacing: .06em; }}
    .stat .value {{ font-size: 20px; font-weight: 700; margin-top: 2px; }}
    .toolbar {{ background: var(--panel); border: 1px solid var(--border); border-radius: 16px; padding: 14px; box-shadow: var(--shadow); display: grid; gap: 10px; grid-template-columns: 1.6fr .8fr .8fr; margin-bottom: 18px; position: sticky; top: 12px; z-index: 10; }}
    .toolbar input, .toolbar select {{ width: 100%; border: 1px solid var(--border); border-radius: 12px; padding: 12px 14px; font-size: 14px; color: var(--text); background: #fff; }}
    .section {{ margin-top: 18px; display: grid; gap: 18px; }}
    .grid-2 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; }}
    .overview-heading {{ padding: 4px 2px 0; }}
    .overview-heading span {{ color: var(--accent); font-size: 11px; letter-spacing: .14em; font-weight: 800; }}
    .overview-heading h2 {{ margin: 5px 0 4px; color: #10223d; font-size: 25px; }}
    .overview-heading p {{ margin: 0; color: var(--muted); line-height: 1.5; }}
    .overview-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; }}
    .overview-card {{ min-height: 190px; padding: 18px; border: 1px solid var(--border); border-radius: 16px; background: var(--panel); box-shadow: var(--shadow); display: flex; flex-direction: column; }}
    .overview-card:hover {{ transform: translateY(-2px); border-color: #a9c5e8; transition: transform .15s ease, border-color .15s ease; }}
    .overview-card-number {{ color: var(--accent); font-size: 12px; font-weight: 800; letter-spacing: .1em; }}
    .overview-card h3 {{ margin: 22px 0 8px; color: #10223d; font-size: 19px; }}
    .overview-card p {{ margin: 0; color: var(--muted); line-height: 1.5; font-size: 14px; }}
    .overview-card-link {{ margin-top: auto; padding-top: 18px; color: var(--accent); text-decoration: none; font-weight: 700; }}
    .overview-card-link span {{ margin-left: 4px; }}
    .card {{ padding: 18px 18px 8px; scroll-margin-top: 92px; }}
    .card:target {{ border-color: var(--accent); box-shadow: 0 0 0 3px rgba(31, 95, 191, 0.16), var(--shadow); }}
    .card-head {{ display: flex; justify-content: space-between; align-items: baseline; gap: 18px; }}
    .card-head h3 {{ margin: 0; font-size: 20px; color: #10223d; }}
    .lead {{ margin: 0 0 12px; padding: 12px 14px; background: #f7faff; border-left: 4px solid var(--accent); border-radius: 10px; color: var(--text); line-height: 1.5; }}
    .source-link {{ color: var(--accent); text-decoration: none; font-size: 13px; white-space: nowrap; }}
    .ref-link {{ color: var(--accent); text-decoration: none; font-weight: 600; }}
    .ref-link:hover, .source-link:hover {{ text-decoration: underline; }}
    .summary {{ color: var(--muted); line-height: 1.55; margin: 12px 0 14px 18px; }}
    .summary li {{ margin: 2px 0; }}
    .handbook-toc {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }}
    .handbook-group {{ background: var(--panel); border: 1px solid var(--border); border-radius: 16px; box-shadow: var(--shadow); margin-bottom: 14px; overflow: hidden; }}
    .handbook-group summary {{ list-style: none; cursor: pointer; padding: 14px 16px; display: grid; gap: 6px; grid-template-columns: 1fr auto; align-items: center; background: linear-gradient(180deg, #fbfdff 0%, #f4f8fd 100%); }}
    .handbook-group summary::-webkit-details-marker {{ display: none; }}
    .handbook-group summary span {{ min-width: 0; }}
    .handbook-count {{ color: var(--accent); font-weight: 700; }}
    .handbook-note {{ grid-column: 1 / -1; color: var(--muted); font-size: 13px; line-height: 1.45; }}
    .handbook-group-body {{ padding: 14px 14px 4px; }}
    .handbook-doclist {{ margin: 0 0 12px 18px; color: var(--muted); }}
    .handbook-doclist li {{ margin: 5px 0; line-height: 1.4; }}
    .handbook-source {{ color: var(--muted); font-size: 12px; }}
    .handbook-text {{ margin-top: 8px; }}
    .handbook-text > summary {{ cursor: pointer; color: var(--accent); font-weight: 700; margin-bottom: 8px; }}
    .handbook-text > summary::-webkit-details-marker {{ display: none; }}
    .pcf-details > summary {{ list-style: none; cursor: pointer; display: flex; justify-content: space-between; gap: 12px; align-items: center; font-size: 18px; font-weight: 700; color: #10223d; }}
    .pcf-details > summary::-webkit-details-marker {{ display: none; }}
    .pcf-details > summary::before {{ content: '▸'; color: var(--accent); font-size: 20px; transition: transform .15s ease; }}
    .pcf-details[open] > summary::before {{ transform: rotate(90deg); }}
    .pcf-toggle-title {{ flex: 1; }}
    .pcf-toggle-hint {{ color: var(--muted); font-size: 12px; font-weight: 600; }}
    .script-detail-section {{ margin: 16px 0; padding: 14px 16px 4px; border: 1px solid var(--border); border-radius: 12px; background: #fbfdff; }}
    .script-detail-section h4 {{ margin: 0 0 10px; color: #173b68; }}
    .wait-map {{ display: grid; gap: 6px; margin: 0 0 16px; padding: 12px; background: #f7faff; border: 1px solid var(--border); border-radius: 12px; }}
    .wait-row {{ display: grid; grid-template-columns: 52px minmax(130px, 1fr) 26px minmax(160px, 2fr); gap: 8px; align-items: center; font-size: 13px; }}
    .wait-pid {{ color: var(--muted); font-variant-numeric: tabular-nums; }}
    .wait-arrow {{ color: var(--accent); font-size: 16px; text-align: center; }}
    .context-note {{ color: var(--muted); font-size: 12px; }}
    .inp-group > summary {{ list-style: none; cursor: pointer; display: flex; align-items: center; gap: 10px; font-size: 18px; font-weight: 700; color: #10223d; }}
    .inp-group > summary::-webkit-details-marker {{ display: none; }}
    .inp-group > summary::before {{ content: '▸'; color: var(--accent); font-size: 20px; transition: transform .15s ease; }}
    .inp-group[open] > summary::before {{ transform: rotate(90deg); }}
    .inp-version-list {{ margin: 12px 0 4px 28px; padding: 0; color: var(--muted); }}
    .inp-version-list li {{ margin: 6px 0; }}
    .story-phase {{ margin: 18px 0 22px; padding: 14px 16px 8px; border: 1px solid var(--border); border-left: 4px solid var(--accent); border-radius: 14px; background: #fbfdff; }}
    .story-phase h4 {{ margin-top: 0; font-size: 17px; }}
    .story-step {{ display: grid; grid-template-columns: 76px 1fr; gap: 12px; margin: 12px 0; padding: 12px 0; border-top: 1px solid #e5ebf4; line-height: 1.6; }}
    .story-step:first-of-type {{ border-top: 0; }}
    .story-number {{ color: var(--accent); font-weight: 700; white-space: nowrap; }}
    .story-step p {{ margin: 0; }}
    .story-program-title {{ display: block; margin-top: 4px; color: var(--muted); font-style: italic; font-size: 13px; }}
    .table {{ width: 100%; border-collapse: collapse; margin: 0 0 16px; overflow: hidden; }}
    .table th, .table td {{ border: 1px solid var(--border); padding: 8px 10px; text-align: left; vertical-align: top; font-size: 13px; }}
    .table th {{ background: var(--accent-soft); color: #173d7a; }}
    .body h4 {{ margin: 8px 0 10px; color: #173d7a; font-size: 15px; }}
    .trace {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; padding: 12px 14px; margin: 4px 0 14px; background: #f7faff; border: 1px solid var(--border); border-radius: 14px; }}
    .trace-label {{ font-weight: 700; color: #173d7a; }}
    .trace-arrow {{ color: var(--muted); font-size: 16px; line-height: 1; }}
    .chip-list {{ display: inline-flex; flex-wrap: wrap; gap: 6px; align-items: center; }}
    .chip {{ display: inline-flex; align-items: center; border: 1px solid #bfd0ea; background: #eff5ff; color: #17407d; border-radius: 999px; padding: 3px 10px; font-size: 12px; line-height: 1.4; white-space: nowrap; }}
    .chip-link {{ text-decoration: none; }}
    .chip-empty {{ background: #f5f7fa; color: var(--muted); border-color: var(--border); }}
    .chip-more {{ background: #fff6e6; border-color: #f0d39e; color: #8b5b00; }}
    .hidden {{ display: none !important; }}
    .footer {{ margin-top: 22px; color: var(--muted); font-size: 12px; }}
    .history-footer {{ margin-top: 5px; font-size: 11px; }}
    .history-footer a {{ color: var(--accent); text-decoration: none; }}
    .history-footer a:hover {{ text-decoration: underline; }}
    @media (max-width: 1100px) {{ .overview-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
    @media (max-width: 900px) {{ .toolbar {{ grid-template-columns: 1fr; }} .card-head {{ flex-direction: column; align-items: flex-start; }} }}
    @media (max-width: 560px) {{ .overview-grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <h1>{esc(current_title)}</h1>
      <p>Generated from: {esc(ACTIVE_SOURCE_LABEL)}</p>
      <p>Updated: {esc(generated_at)}</p>
      {nav_html}
    </div>
    {stats_html}
    {toolbar_html}
    {body_html}
    <div class="footer">To update this manual, run <code>update_manual.py</code>. Created by C.K.</div>
    <div class="history-footer">Last change: {esc(history_records[0].timestamp if history_records else 'none')} by {esc(history_records[0].user if history_records and history_records[0].user else 'unknown')} ({esc(history_action_label(history_records[0].action) if history_records else 'none')}) - <a href="{esc(HISTORY_PAGE_FILE)}">full change history</a></div>
  </div>
  <script>
    const q = document.getElementById('q');
    const kind = document.getElementById('kind');
    const sort = document.getElementById('sort');
    const cards = Array.from(document.querySelectorAll('.card'));
    const handbookGroups = Array.from(document.querySelectorAll('.handbook-group'));
    function normalize(s) {{ return (s || '').toLowerCase(); }}
    function refresh() {{
      if (!q || !kind || !sort) return;
      const query = normalize(q.value);
      const filterKind = kind.value;
      const byKind = {{ pcf: 0, story: 1, script: 2, file: 3, inp: 4, handbook: 5, history: 6 }};
      cards.forEach(card => {{
        const cardKind = card.dataset.kind;
        const text = normalize(card.innerText);
        const okKind = filterKind === 'all' || filterKind === cardKind;
        const okQuery = !query || text.includes(query);
        card.classList.toggle('hidden', !(okKind && okQuery));
      }});
      if (handbookGroups.length) {{
        handbookGroups.forEach(group => {{
          const visibleCards = Array.from(group.querySelectorAll('.card')).some(card => !card.classList.contains('hidden'));
          const defaultOpen = group.dataset.defaultOpen === '1';
          group.open = query || filterKind !== 'all' ? visibleCards : defaultOpen;
        }});
      }}
      const visible = cards.filter(card => !card.classList.contains('hidden'));
      visible.sort((a, b) => {{
        if (sort.value === 'kind') {{
            const titleA = a.querySelector('h3')?.innerText || a.querySelector('.pcf-toggle-title')?.innerText || '';
            const titleB = b.querySelector('h3')?.innerText || b.querySelector('.pcf-toggle-title')?.innerText || '';
            return (byKind[a.dataset.kind] ?? 99) - (byKind[b.dataset.kind] ?? 99) || titleA.localeCompare(titleB);
        }}
        const titleA = a.querySelector('h3')?.innerText || a.querySelector('.pcf-toggle-title')?.innerText || '';
        const titleB = b.querySelector('h3')?.innerText || b.querySelector('.pcf-toggle-title')?.innerText || '';
        return titleA.localeCompare(titleB);
      }});
      visible.forEach(card => card.parentElement.appendChild(card));
    }}
    function focusTargetFromHash() {{
      const id = decodeURIComponent((window.location.hash || '').replace('#', ''));
      if (!id) return;
      const target = document.getElementById(id);
      if (target) {{
        target.scrollIntoView({{ block: 'start', behavior: 'smooth' }});
      }}
    }}
    if (q && kind && sort) {{
      q.addEventListener('input', refresh);
      kind.addEventListener('change', refresh);
      sort.addEventListener('change', refresh);
    }}
    window.addEventListener('hashchange', focusTargetFromHash);
    window.addEventListener('load', focusTargetFromHash);
  </script>
</body>
</html>
"""


def collect_data(source_dir: Path | List[Path]) -> tuple[
    list[PCFDocument],
    list[ScriptDocument],
    list[INPDocument],
    list[HandbookDocument],
    Dict[str, List[str]],
    Dict[str, Dict[str, List[str]]],
]:
    ensure_handbook_source()
    if isinstance(source_dir, list):
        source_dirs = source_dir
    else:
        source_dirs = [source_dir]

    pcf_paths = []
    script_paths = []
    inp_entries = []
    for source in source_dirs:
        label = source_display_label(source)
        pcf_paths.extend((path, label) for path in gather_files(source / "PCF", ".PCF"))
        script_paths.extend((path, label) for path in gather_scripts(source / "SCRIPT"))
        inp_entries.extend((path, label) for path in gather_inp_files(source / "OPT"))

    pcf_docs = [scan_pcf(path, label) for path, label in pcf_paths]
    script_docs = [scan_script(path, label) for path, label in script_paths]
    if os.environ.get("DOCBUILDER_SKIP_PURPOSE_CHECK") != "1":
        report_missing_script_purposes(script_docs)
    inp_labels: Dict[str, str] = {}
    for path, label in inp_entries:
        key = str(path.resolve()).lower()
        inp_labels[key] = label
    raw_inp_paths = [path for path, _label in inp_entries]
    # Keep stable ordering while avoiding accidental duplicates by path.
    seen = set()
    unique_inp_paths: List[Path] = []
    for path in raw_inp_paths:
        key = str(path.resolve()).lower()
        if key in seen:
            continue
        seen.add(key)
        unique_inp_paths.append(path)
    inp_docs = [scan_inp(path, inp_labels.get(str(path.resolve()).lower(), "")) for path in unique_inp_paths]
    annotate_identical_sources(pcf_docs)
    annotate_identical_sources(script_docs)
    annotate_identical_sources(inp_docs)
    handbook_sections = gather_handbook_sections(HANDBOOK_DIR)
    handbook_docs = [doc for docs in handbook_sections.values() for doc in docs]
    refs = build_cross_refs(pcf_docs, script_docs)
    file_registry = build_file_registry(script_docs)
    return pcf_docs, script_docs, inp_docs, handbook_docs, refs, file_registry


def annotate_identical_sources(documents: List[object]) -> None:
    grouped: Dict[str, List[object]] = defaultdict(list)
    for document in documents:
        grouped[getattr(document, "name").lower()].append(document)
    for same_name_docs in grouped.values():
        by_content: Dict[bytes, List[object]] = defaultdict(list)
        for document in same_name_docs:
            try:
                content = getattr(document, "path").read_bytes()
            except OSError:
                continue
            by_content[content].append(document)
        for identical_docs in by_content.values():
            if len(identical_docs) < 2:
                continue
            labels = [getattr(document, "source_label") for document in identical_docs]
            for document in identical_docs:
                document.identical_sources = [label for label in labels if label != document.source_label]


def report_missing_script_purposes(script_docs: List[ScriptDocument]) -> None:
    missing = [doc for doc in script_docs if not doc.purpose.strip()]
    if not missing:
        print("Purpose check: every script has a Purpose in its header.")
        return
    print(f"Purpose check: {len(missing)} script(s) have no Purpose in the header:")
    for doc in sorted(missing, key=lambda item: (item.source_label.lower(), item.name.lower())):
        source = f" [{doc.source_label}]" if doc.source_label else ""
        print(f"- {doc.name}{source}")


def report_source_purposes(source: Path) -> None:
    source_label = source_display_label(source)
    script_docs = [
        scan_script(path, source_label)
        for path in gather_scripts(source / "SCRIPT")
    ]
    report_missing_script_purposes(script_docs)


def source_is_readable(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "does not exist"
    if not path.is_dir():
        return False, "is not a directory"
    if not os.access(path, os.R_OK):
        return False, "is not readable (permission denied)"
    missing = [name for name in ("PCF", "SCRIPT", "OPT") if not (path / name).is_dir()]
    if missing:
        return False, f"missing required folder(s): {', '.join(missing)}"
    return True, ""


def read_configured_sources() -> List[Path]:
    if not SOURCE_LIST_FILE.exists():
        return []
    paths: List[Path] = []
    for line in read_text(SOURCE_LIST_FILE).splitlines():
        value = line.strip()
        if value and not value.startswith("#"):
            path = Path(value).expanduser()
            if not path.is_absolute():
                path = SOURCE_LIST_FILE.parent / path
            paths.append(path.resolve())
    return paths


def write_configured_sources(paths: List[Path]) -> None:
    content = "# One GPSUSER directory per line\n" + "\n".join(str(path) for path in paths) + "\n"
    write_text(SOURCE_LIST_FILE, content)


def choose_gpsuser_interactively(
    configured_sources: List[Path],
    prompt: str = "Choose a GPSUSER (or press Enter to cancel): ",
) -> Optional[Path]:
    if not configured_sources:
        print("No GPSUSER sources are configured.")
        return None
    print("\nConfigured GPSUSER sources")
    for index, path in enumerate(configured_sources, start=1):
        print(f"{index}. {path}")
    choice = input(prompt).strip()
    if not choice:
        return None
    if not choice.isdigit() or not (1 <= int(choice) <= len(configured_sources)):
        print("Invalid selection.")
        return None
    return configured_sources[int(choice) - 1]


def add_gpsuser_interactively(configured_sources: List[Path]) -> tuple[List[Path], Optional[Path]]:
    print("\nAdd GPSUSER")
    if configured_sources:
        print("GPSUSER sources already configured:")
        for index, source in enumerate(configured_sources, start=1):
            print(f"{index}. {source}")
    raw_path = input("GPSUSER path (or press Enter to cancel): ").strip().strip('"')
    if not raw_path:
        return configured_sources, None
    path = Path(raw_path).expanduser().resolve()
    ok, reason = source_is_readable(path)
    if not ok:
        print(f"Cannot add this GPSUSER: {reason}")
        return configured_sources, None
    if path in configured_sources:
        print("This GPSUSER is already configured.")
        return configured_sources, None
    configured_sources = configured_sources + [path]
    write_configured_sources(configured_sources)
    print(f"GPSUSER added: {path}")
    return configured_sources, path


def remove_gpsuser_interactively(configured_sources: List[Path]) -> tuple[List[Path], Optional[Path]]:
    removed = choose_gpsuser_interactively(
        configured_sources,
        "Choose a GPSUSER to remove (or press Enter to cancel): ",
    )
    if removed is None:
        return configured_sources, None
    updated = [path for path in configured_sources if path != removed]
    write_configured_sources(updated)
    print(f"GPSUSER removed: {removed}")
    return updated, removed


def update_gpsuser_interactively(configured_sources: List[Path]) -> Optional[Path]:
    selected = choose_gpsuser_interactively(
        configured_sources,
        "Choose a GPSUSER to update (or press Enter to cancel): ",
    )
    if selected is not None:
        print(f"GPSUSER selected for update: {selected}")
    return selected


def remove_source_branch(output_dir: Path, source: Path) -> None:
    branch_dir = source_branch_dir(output_dir, source)
    if not branch_dir.is_dir():
        return

    def remove_readonly(func: Callable[..., object], path: str, _exc_info: object) -> None:
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except OSError:
            pass

    try:
        shutil.rmtree(branch_dir, onerror=remove_readonly)
    except OSError:
        pass
    if branch_dir.exists():
        print(
            "Warning: could not completely remove the GPSUSER branch "
            f"(it may be locked by OneDrive or another application): {branch_dir}"
        )


def copy_source_branch_to_root(output_dir: Path, source: Path) -> None:
    branch_dir = source_branch_dir(output_dir, source)
    clear_multi_source_root(output_dir)
    if not branch_dir.is_dir():
        return
    for item in branch_dir.iterdir():
        destination = output_dir / item.name
        if item.is_dir():
            shutil.copytree(item, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(item, destination)


def rebuild_selected_source_branch(
    output_dir: Path,
    source: Path,
    sources: List[Path],
) -> int:
    source_output = output_dir / "sources"
    source_output.mkdir(parents=True, exist_ok=True)
    result = build_single_source_branch(source, source_output / source_slug(source))
    if result != 0:
        return result
    write_multi_source_overview(output_dir, sources)
    return 0


def source_slug(path: Path) -> str:
    return slugify(f"{path.parent.name}-{path.name}")


def source_display_label(path: Path) -> str:
    return f"{path.parent.name}/{path.name}"


def source_branch_dir(output_dir: Path, source: Path) -> Path:
    return output_dir / "sources" / source_slug(source)


def source_branch_ready(output_dir: Path, source: Path) -> bool:
    return (source_branch_dir(output_dir, source) / MANUAL_INDEX_FILE).is_file()


def copy_single_source_output(output_dir: Path, source: Path) -> bool:
    branch_dir = source_branch_dir(output_dir, source)
    if source_branch_ready(output_dir, source):
        return False
    branch_dir.mkdir(parents=True, exist_ok=True)
    for item in output_dir.iterdir():
        if item.name == "sources":
            continue
        destination = branch_dir / item.name
        if item.is_dir():
            shutil.copytree(item, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(item, destination)
    return True


def build_single_source_branch(source: Path, output_dir: Path) -> int:
    report_source_purposes(source)
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--source-dir",
        str(source),
        "--output-dir",
        str(output_dir),
        "--no-prompts",
    ]
    child_env = os.environ.copy()
    child_env["DOCBUILDER_SKIP_PURPOSE_CHECK"] = "1"
    result = subprocess.run(command, check=False, env=child_env)
    return result.returncode


def clear_multi_source_root(output_dir: Path) -> None:
    for name in (
        OVERVIEW_PAGE_FILE,
        MANUAL_INDEX_FILE,
        PCF_PAGE_FILE,
        SCRIPT_PAGE_FILE,
        FILE_PAGE_FILE,
        INP_PAGE_FILE,
        HANDBOOK_PAGE_FILE,
        STORY_PAGE_FILE,
        HISTORY_PAGE_FILE,
        "bernese_bpe_index.json",
        "bernese_bpe_manual.md",
    ):
        target = output_dir / name
        if target.is_file():
            target.unlink()


def compare_source_files(sources: List[Path]) -> List[tuple[str, str, str]]:
    """Return relative files that are byte-identical in more than one source."""
    grouped: Dict[str, List[tuple[Path, bytes]]] = defaultdict(list)
    for source in sources:
        for relative in (Path("PCF"), Path("SCRIPT"), Path("OPT")):
            folder = source / relative
            if not folder.exists():
                continue
            for path in folder.rglob("*"):
                if path.is_file():
                    key = path.relative_to(source).as_posix().lower()
                    grouped[key].append((source, path.read_bytes()))
    identical: List[tuple[str, str, str]] = []
    for relative, files in sorted(grouped.items()):
        for index, (source, content) in enumerate(files):
            copies = [other for other, other_content in files[index + 1:] if content == other_content]
            for copy in copies:
                identical.append((relative, source_display_label(source), source_display_label(copy)))
    return identical


def write_multi_source_index(
    output_dir: Path,
    sources: List[Path],
    clear_root: bool = True,
) -> None:
    if clear_root:
        clear_multi_source_root(output_dir)
    cards = []
    for source in sources:
        folder = source_slug(source)
        if source_branch_ready(output_dir, source):
            href = f"sources/{esc(folder)}/{MANUAL_INDEX_FILE}"
            link_label = "Open GPSUSER manual"
        elif len(sources) == 1:
            href = MANUAL_INDEX_FILE
            link_label = "Open manual"
        else:
            href = "#"
            link_label = "Manual branch not built yet"
        cards.append(
            f"<article class='source-card'>"
            f"<div class='source-number'>{len(cards) + 1:02d}</div>"
            f"<div><h2>{esc(source.name)}</h2>"
            f"<p class='source-path'>{esc(str(source))}</p>"
            f"<a class='source-link' href='{href}'>{link_label} <span aria-hidden='true'>-&gt;</span></a>"
            f"</div></article>"
        )
    identical = compare_source_files(sources)
    comparison = "<p class='muted'>No byte-identical files were found across the configured sources.</p>"
    if identical:
        comparison = "<div class='comparison-list'>" + "".join(
            f"<div><code>{esc(relative)}</code><span>identical in {esc(first)} and {esc(second)}</span></div>"
            for relative, first, second in identical
        ) + "</div>"
    if sources:
        source_content = "".join(cards)
        source_intro = f"{len(sources)} GPSUSER source{'s' if len(sources) != 1 else ''} configured."
    else:
        source_content = (
            "<div class='empty-state'><div class='empty-icon'>+</div>"
            "<h2>No GPSUSER configured</h2>"
            "<p>Add a GPSUSER source with <code>update_manual.py</code> to build the first manual branch.</p></div>"
        )
        source_intro = "No GPSUSER source is configured yet."
    html_text = f"""<!doctype html>
<html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Bernese BPE Documentation</title>
<style>
:root{{--ink:#172235;--muted:#667085;--line:#dce4ee;--blue:#1769aa;--blue-dark:#0b416f;--cream:#fffaf0;--card:#ffffff}}
*{{box-sizing:border-box}}body{{margin:0;color:var(--ink);font-family:Inter,Segoe UI,sans-serif;background:linear-gradient(135deg,#eef5f8 0%,#f8f3e8 100%);min-height:100vh}}
main{{max-width:1120px;margin:0 auto;padding:clamp(24px,6vw,72px) 22px 64px}}
.hero{{position:relative;overflow:hidden;padding:clamp(30px,6vw,66px);border-radius:30px;background:linear-gradient(120deg,var(--blue-dark),#2196a6);color:white;box-shadow:0 24px 60px rgba(16,66,92,.22)}}
.hero:after{{content:'';position:absolute;width:330px;height:330px;right:-110px;top:-150px;border:1px solid rgba(255,255,255,.24);border-radius:50%;box-shadow:0 0 0 34px rgba(255,255,255,.06),0 0 0 68px rgba(255,255,255,.04)}}
.eyebrow{{margin:0 0 16px;text-transform:uppercase;letter-spacing:.16em;font-size:12px;font-weight:700;opacity:.75}}h1{{max-width:720px;margin:0;font:700 clamp(34px,6vw,68px)/.98 Georgia,serif;letter-spacing:-.04em}}.hero p{{max-width:620px;margin:22px 0 0;font-size:17px;line-height:1.6;color:rgba(255,255,255,.84)}}
.section-head{{display:flex;justify-content:space-between;gap:18px;align-items:end;margin:48px 0 18px}}.section-head h2{{margin:0;font:700 28px Georgia,serif}}.section-head p{{margin:0;color:var(--muted)}}
.source-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:16px}}.source-card{{display:grid;grid-template-columns:48px 1fr;gap:18px;padding:24px;border:1px solid var(--line);border-radius:20px;background:rgba(255,255,255,.86);box-shadow:0 10px 24px rgba(35,59,77,.06);transition:transform .2s ease,box-shadow .2s ease}}.source-card:hover{{transform:translateY(-3px);box-shadow:0 16px 32px rgba(35,59,77,.12)}}.source-number{{display:grid;place-items:center;width:40px;height:40px;border-radius:12px;background:#e1f1f3;color:var(--blue-dark);font-weight:800}}.source-card h2{{margin:0 0 8px;font-size:20px}}.source-path{{margin:0 0 20px;color:var(--muted);font-size:13px;line-height:1.45;overflow-wrap:anywhere}}.source-link{{color:var(--blue);font-weight:800;text-decoration:none}}.source-link:hover{{text-decoration:underline}}.empty-state{{padding:42px 26px;text-align:center;border:1px dashed #b9c9d8;border-radius:20px;background:rgba(255,255,255,.62)}}.empty-icon{{margin:0 auto 16px;display:grid;place-items:center;width:48px;height:48px;border-radius:50%;background:#e1f1f3;color:var(--blue-dark);font-size:28px}}.empty-state h2{{margin:0 0 8px;font:700 25px Georgia,serif}}.empty-state p{{margin:0;color:var(--muted)}}.details{{margin-top:34px;padding:24px;border-radius:20px;background:var(--cream);border:1px solid #eadfca}}.details h2{{margin:0 0 12px;font:700 22px Georgia,serif}}.muted{{color:var(--muted)}}.comparison-list{{display:grid;gap:8px}}.comparison-list div{{display:flex;flex-wrap:wrap;gap:10px;padding:10px 0;border-bottom:1px solid #eee2ca}}.comparison-list span{{color:var(--muted)}}code{{padding:3px 6px;border-radius:6px;background:#edf2f7;font-size:.9em}}
@media (max-width:600px){{.section-head{{display:block}}.section-head p{{margin-top:8px}}.hero{{border-radius:22px}}}}
</style></head><body><main>
<section class='hero'><p class='eyebrow'>Bernese GNSS Software</p><h1>BPE Documentation Hub</h1><p>Choose a GPSUSER documentation branch below. Each branch is built independently.</p></section>
<section class='section-head'><div><h2>Available GPSUSER branches</h2><p>{source_intro}</p></div></section>
<section class='source-grid'>{source_content}</section>
<section class='details'><h2>Source comparison</h2>{comparison}</section>
</main></body></html>"""
    write_text(output_dir / OVERVIEW_PAGE_FILE, html_text)
    if clear_root:
        write_text(output_dir / MANUAL_INDEX_FILE, html_text)


def write_multi_source_overview(output_dir: Path, sources: List[Path]) -> None:
    write_multi_source_index(output_dir, sources)
    write_text(
        output_dir / "bernese_bpe_manual.md",
        "# Bernese GNSS Software BPE Documentation\n\n"
        "This multi-source manual contains one complete documentation set per GPSUSER. "
        "Open `index.html` for the source overview.\n",
    )


def write_single_source_overview(output_dir: Path, sources: List[Path]) -> None:
    write_multi_source_index(output_dir, sources, clear_root=False)


def choose_comment_target(
    prompt: str,
    targets: List[tuple[str, str]],
) -> Optional[str]:
    query = input(f"{prompt} (leave empty to list all): ").strip().lower()
    matches = [
        (label, key) for label, key in targets
        if not query or query in label.lower() or query in key.lower()
    ]
    if not matches:
        print("No matching targets found.")
        return None
    for index, (label, _key) in enumerate(matches, start=1):
        print(f"{index}. {label}")
    while True:
        choice = input("Choose a number (or press Enter to cancel): ").strip()
        if not choice:
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(matches):
            return matches[int(choice) - 1][1]
        print("Please enter one of the displayed numbers.")


def add_comment_interactively(
    pcf_docs: List[PCFDocument],
    script_docs: List[ScriptDocument],
    inp_docs: List[INPDocument],
    handbook_docs: List[HandbookDocument],
) -> bool:
    print("\nAdd a comment")
    print("1. PCF")
    print("2. Script")
    print("3. INP file")
    print("4. Handbook page")
    kind_choice = input("Choose a component (or press Enter to cancel): ").strip()
    if not kind_choice:
        return False

    if kind_choice == "1":
        kind = "pcf"
        targets = [(doc.name, doc.name) for doc in pcf_docs]
    elif kind_choice == "2":
        kind = "scripts"
        targets = [(doc.name, doc.name) for doc in script_docs]
    elif kind_choice == "3":
        kind = "inp"
        targets = [(f"{doc.path.parent.name}/{doc.name}", f"{doc.path.parent.name}/{doc.name}") for doc in inp_docs]
    elif kind_choice == "4":
        kind = "handbook"
        targets = [(doc.title, doc.path.relative_to(HANDBOOK_DIR).as_posix()) for doc in handbook_docs]
    else:
        print("Unknown component type.")
        return False

    target = choose_comment_target("Search", sorted(targets, key=lambda item: item[0].lower()))
    if not target:
        return False

    title = input("Comment title: ").strip() or MANUAL_CONFIG.get("default_comment_title", "Additional note")
    print("Enter the comment. Finish with a line containing END.")
    lines: List[str] = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    comment = "\n".join(lines).strip()
    if not comment:
        print("No comment entered; nothing was changed.")
        return False

    path = comment_file(kind, target)
    existing = read_text(path).rstrip() if path.exists() else f"# Manual comments for {target}"
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    addition = f"\n\n## {title}\n\n{comment}\n\n<!-- Added: {stamp} -->\n"
    write_text(path, existing + addition)
    append_handbook_history(
        "updated",
        f"{kind}:{target}",
        f"Added manual comment: {title}",
        str(path.relative_to(ROOT)).replace(os.sep, "/"),
    )
    print(f"Comment saved for {target}: {path}")
    return True


def list_comment_entries() -> List[tuple[Path, str, str, datetime]]:
    entries: List[tuple[Path, str, str, datetime]] = []
    if not COMMENTS_DIR.exists():
        return entries
    for path in sorted(COMMENTS_DIR.rglob("*.md")):
        text = read_text(path)
        headings = list(re.finditer(r"^##\s+(.+?)\s*$", text, re.MULTILINE))
        if not headings:
            continue
        target_match = re.search(r"^#\s+Manual comments for\s+(.+?)\s*$", text, re.MULTILINE)
        target = target_match.group(1) if target_match else path.stem
        for index, heading in enumerate(headings):
            end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
            block = text[heading.start():end]
            stamp_match = re.search(r"<!--\s*Added:\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s*-->", block)
            try:
                stamp = datetime.strptime(stamp_match.group(1), "%Y-%m-%d %H:%M") if stamp_match else datetime.min
            except ValueError:
                stamp = datetime.min
            entries.append((path, target, heading.group(1).strip(), stamp))
    return sorted(entries, key=lambda entry: entry[3], reverse=True)


def delete_comment_interactively() -> bool:
    entries = list_comment_entries()
    if not entries:
        print("No manual comments found.")
        return False
    print("\nExisting manual comments")
    for index, (_path, target, title, _stamp) in enumerate(entries, start=1):
        print(f"{index}. {target} - {title}")
    choice = input("Choose a comment to delete (or press Enter to cancel): ").strip()
    if not choice:
        return False
    if not choice.isdigit() or not 1 <= int(choice) <= len(entries):
        print("Invalid comment number.")
        return False

    path, _target, _title, _stamp = entries[int(choice) - 1]
    text = read_text(path)
    selected_path, _selected_target, selected_title, _selected_stamp = entries[int(choice) - 1]
    file_headings = list(re.finditer(r"^##\s+(.+?)\s*$", text, re.MULTILINE))
    selected_index = sum(1 for entry in entries[:int(choice) - 1] if entry[0] == selected_path)
    selected_heading = file_headings[selected_index]
    start = selected_heading.start()
    end = next((match.start() for match in file_headings if match.start() > start), len(text))
    updated = (text[:start] + text[end:]).strip() + "\n"
    if updated.strip() in {"", f"# Manual comments for {_selected_target}"}:
        path.unlink()
    else:
        write_text(path, updated)
    append_handbook_history(
        "deleted",
        f"comment:{_selected_target}",
        f"Deleted manual comment: {selected_title}",
        str(path.relative_to(ROOT)).replace(os.sep, "/"),
    )
    print(f"Comment deleted: {_selected_target} - {selected_title}")
    return True


def collect_manual_comments(
    pcf_docs: List[PCFDocument],
    script_docs: List[ScriptDocument],
    inp_docs: List[INPDocument],
    handbook_docs: List[HandbookDocument],
    direct_mode: bool = False,
    delete_mode: bool = False,
) -> None:
    if delete_mode:
        delete_comment_interactively()
        return
    if not direct_mode:
        answer = input(
            "\nWhat would you like to do?\n"
            "  a = add a comment\n"
            "  d = delete a comment\n"
            "  N = build the manual without changing comments\n"
            "Selection [a/d/N]: "
        ).strip().lower()
        if answer in {"d", "delete", "l", "loeschen", "löschen"}:
            delete_comment_interactively()
            return
        if answer not in {"a", "add", "y", "yes", "j", "ja"}:
            return

    while True:
        added = add_comment_interactively(pcf_docs, script_docs, inp_docs, handbook_docs)
        if not added:
            return
        answer = input("\nWould you like to add another comment? [y/N]: ").strip().lower()
        if answer not in {"y", "yes", "j", "ja"}:
            return


def main() -> int:
    global ACTIVE_SOURCE_LABEL, ACTIVE_USER_NAME, OUTPUT_DIR
    parser = argparse.ArgumentParser(description="Generate the Bernese BPE manual.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory for the generated manual",
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        action="append",
        help="Real Bernese user directory containing PCF/, SCRIPT/, and OPT/",
    )
    parser.add_argument(
        "--add-comment",
        action="store_true",
        help="Interactively add a comment, then rebuild the manual",
    )
    parser.add_argument(
        "--delete-comment",
        action="store_true",
        help="Interactively delete one manual comment, then rebuild the manual",
    )
    parser.add_argument(
        "--add-handbook-entry",
        action="store_true",
        help="Interactively add a handbook entry, then rebuild the manual",
    )
    parser.add_argument(
        "--edit-handbook-entry",
        action="store_true",
        help="Interactively edit a handbook entry, then rebuild the manual",
    )
    parser.add_argument(
        "--no-prompts",
        action="store_true",
        help="Build without the interactive source and comment questions",
    )
    args = parser.parse_args()

    if not args.no_prompts:
        choose_user_name()

    startup_action = "a"
    if not args.no_prompts and not any(
        (
            args.add_comment,
            args.delete_comment,
            args.add_handbook_entry,
            args.edit_handbook_entry,
        )
    ):
        startup_action = choose_startup_action()
        args.add_comment = startup_action == "c1"
        args.delete_comment = startup_action == "c2"
        args.add_handbook_entry = startup_action == "d1"
        args.edit_handbook_entry = startup_action == "d3"

        action_labels = {
            "a": "Only rebuild the manual",
            "b1": "Add GPSUSER",
            "b2": "Remove GPSUSER",
            "b3": "Update GPSUSER",
            "c1": "Add comment",
            "c2": "Remove comment",
            "d1": "Add handbook entry",
            "d2": "Remove handbook entry",
            "d3": "Edit handbook entry",
        }
        append_handbook_history(
            "menu_action",
            startup_action,
            f"Selected option {startup_action}: {action_labels[startup_action]}",
        )

    configured_sources = [path.resolve() for path in args.source_dir] if args.source_dir else read_configured_sources()
    sources_before_menu = list(configured_sources)
    added_source: Optional[Path] = None
    removed_source: Optional[Path] = None
    updated_source: Optional[Path] = None
    selected_action_source: Optional[Path] = None
    if startup_action == "b1":
        configured_sources, added_source = add_gpsuser_interactively(configured_sources)
    elif startup_action == "b2":
        configured_sources, removed_source = remove_gpsuser_interactively(configured_sources)
    elif startup_action == "b3":
        updated_source = update_gpsuser_interactively(configured_sources)
    elif (
        not args.source_dir
        and (
            startup_action in {"c1", "c2", "d1", "d2", "d3"}
            or args.add_comment
            or args.delete_comment
            or args.add_handbook_entry
            or args.edit_handbook_entry
        )
    ):
        selected_action_source = choose_gpsuser_interactively(
            configured_sources,
            "Choose the GPSUSER to work with (or press Enter to cancel): ",
        )
        if selected_action_source is None:
            return 0
    if args.source_dir:
        for path in configured_sources:
            ok, reason = source_is_readable(path)
            if not ok:
                parser.error(f"GPSUSER source is not readable: {path} ({reason})")
    sources = configured_sources
    output_dir = args.output_dir.resolve() if args.output_dir else OUTPUT_DIR
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if not sources:
        clear_multi_source_root(output_dir)
        write_single_source_overview(output_dir, sources)
        print(f"Wrote GPSUSER overview: {output_dir / OVERVIEW_PAGE_FILE}")
        return 0

    append_handbook_history(
        "built",
        "manual",
        f"Generated manual from {len(sources)} source(s)",
    )

    if args.add_handbook_entry:
        if not add_handbook_entry_interactively():
            print("No handbook entry was added.")
    if args.edit_handbook_entry:
        if not edit_handbook_entry_interactively():
            print("No handbook entry was edited.")
    if startup_action == "d2":
        if not remove_handbook_entry_interactively():
            print("No handbook entry was removed.")
    handbook_changed = args.add_handbook_entry or args.edit_handbook_entry or startup_action == "d2"

    if startup_action == "b2" and removed_source is not None and len(sources) <= 1:
        remove_source_branch(output_dir, removed_source)
        if len(sources) == 1:
            copy_source_branch_to_root(output_dir, sources[0])
        else:
            clear_multi_source_root(output_dir)
        print(f"Sources: {', '.join(str(path) for path in sources) or 'none'}")
        return 0

    if len(sources) > 1:
        if not args.no_prompts and (args.add_comment or args.delete_comment):
            comment_sources = [selected_action_source] if selected_action_source else sources
            combined_data = collect_data(comment_sources)
            collect_manual_comments(
                combined_data[0],
                combined_data[1],
                combined_data[2],
                combined_data[3],
                direct_mode=args.add_comment,
                delete_mode=args.delete_comment,
            )
        source_output = output_dir / "sources"
        source_output.mkdir(parents=True, exist_ok=True)
        if startup_action == "b1" and added_source is not None:
            if len(sources_before_menu) == 1:
                copy_single_source_output(output_dir, sources_before_menu[0])
            for source in sources:
                if source_branch_ready(output_dir, source):
                    continue
                result = build_single_source_branch(source, source_output / source_slug(source))
                if result != 0:
                    return result
            write_multi_source_overview(output_dir, sources)
            print(f"Sources: {', '.join(str(path) for path in sources)}")
            print(f"Wrote GPSUSER overview: {output_dir / OVERVIEW_PAGE_FILE}")
            return 0

        if startup_action == "b2" and removed_source is not None:
            remove_source_branch(output_dir, removed_source)
            if len(sources) == 1:
                copy_source_branch_to_root(output_dir, sources[0])
            write_multi_source_overview(output_dir, sources)
            print(f"Sources: {', '.join(str(path) for path in sources)}")
            print(f"Wrote GPSUSER overview: {output_dir / OVERVIEW_PAGE_FILE}")
            return 0

        if startup_action == "b3" and updated_source is not None:
            result = rebuild_selected_source_branch(output_dir, updated_source, sources)
            if result != 0:
                return result
            print(f"Updated GPSUSER branch: {updated_source}")
            print(f"Wrote GPSUSER overview: {output_dir / OVERVIEW_PAGE_FILE}")
            return 0

        if handbook_changed:
            for source in sources:
                result = build_single_source_branch(
                    source,
                    output_dir / "sources" / source_slug(source),
                )
                if result != 0:
                    return result
            write_multi_source_overview(output_dir, sources)
            print(f"Synchronized handbook in {len(sources)} GPSUSER branch(es).")
            print(f"Wrote GPSUSER overview: {output_dir / OVERVIEW_PAGE_FILE}")
            return 0

        if selected_action_source is not None:
            if source_branch_ready(output_dir, selected_action_source):
                result = build_single_source_branch(
                    selected_action_source,
                    output_dir / "sources" / source_slug(selected_action_source),
                )
                if result != 0:
                    return result
            else:
                result = rebuild_selected_source_branch(output_dir, selected_action_source, sources)
                if result != 0:
                    return result
            write_multi_source_overview(output_dir, sources)
            print(f"Updated GPSUSER branch: {selected_action_source}")
            print(f"Wrote GPSUSER overview: {output_dir / OVERVIEW_PAGE_FILE}")
            return 0

        child_env = os.environ.copy()
        for source in sources:
            command = [
                sys.executable,
                str(Path(__file__).resolve()),
                "--source-dir",
                str(source),
                "--output-dir",
                str(source_output / source_slug(source)),
                "--no-prompts",
            ]
            result = subprocess.run(command, check=False, env=child_env)
            if result.returncode != 0:
                return result.returncode
        write_multi_source_overview(output_dir, sources)
        print(f"Sources: {', '.join(str(path) for path in sources)}")
        print(f"Wrote GPSUSER overview: {output_dir / OVERVIEW_PAGE_FILE}")
        return 0

    OUTPUT_DIR = output_dir

    ACTIVE_SOURCE_LABEL = ", ".join(str(path) for path in sources)
    pcf_docs, script_docs, inp_docs, handbook_docs, refs, file_registry = collect_data(sources)
    history_records = load_handbook_history()
    if not args.no_prompts and (args.add_comment or args.delete_comment):
        collect_manual_comments(
            pcf_docs,
            script_docs,
            inp_docs,
            handbook_docs,
            direct_mode=args.add_comment,
            delete_mode=args.delete_comment,
        )
    script_index = build_script_index(script_docs)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    md = manual_markdown(generated_at, pcf_docs, script_docs, inp_docs, handbook_docs, history_records, refs, script_index, file_registry)
    pages = {
        MANUAL_INDEX_FILE: manual_html(generated_at, pcf_docs, script_docs, inp_docs, handbook_docs, history_records, refs, script_index, file_registry, "index"),
        PCF_PAGE_FILE: manual_html(generated_at, pcf_docs, script_docs, inp_docs, handbook_docs, history_records, refs, script_index, file_registry, "pcf"),
        SCRIPT_PAGE_FILE: manual_html(generated_at, pcf_docs, script_docs, inp_docs, handbook_docs, history_records, refs, script_index, file_registry, "scripts"),
        FILE_PAGE_FILE: manual_html(generated_at, pcf_docs, script_docs, inp_docs, handbook_docs, history_records, refs, script_index, file_registry, "files"),
        STORY_PAGE_FILE: manual_html(generated_at, pcf_docs, script_docs, inp_docs, handbook_docs, history_records, refs, script_index, file_registry, "stories"),
        INP_PAGE_FILE: manual_html(generated_at, pcf_docs, script_docs, inp_docs, handbook_docs, history_records, refs, script_index, file_registry, "inp"),
        HANDBOOK_PAGE_FILE: manual_html(generated_at, pcf_docs, script_docs, inp_docs, handbook_docs, history_records, refs, script_index, file_registry, "handbook"),
        HISTORY_PAGE_FILE: manual_html(generated_at, pcf_docs, script_docs, inp_docs, handbook_docs, history_records, refs, script_index, file_registry, "history"),
    }

    md_path = output_dir / "bernese_bpe_manual.md"
    index_path = output_dir / "bernese_bpe_index.json"

    write_text(md_path, md)
    for filename, html_text in pages.items():
        write_text(output_dir / filename, html_text)

    index = {
        "generated_at": generated_at,
        "pcf_files": [doc.name for doc in pcf_docs],
        "script_files": [doc.name for doc in script_docs],
        "inp_files": [doc.name for doc in inp_docs],
        "handbook_files": [doc.name for doc in handbook_docs],
        "pcf_count": len(pcf_docs),
        "pcf_row_count": sum(len(doc.entries) for doc in pcf_docs),
        "script_count": len(script_docs),
        "program_ref_count": sum(len(doc.programs) for doc in script_docs),
        "inp_count": len(inp_docs),
        "inp_field_count": sum(len(doc.fields) for doc in inp_docs),
        "handbook_count": len(handbook_docs),
    }
    write_text(index_path, json.dumps(index, indent=2))
    write_single_source_overview(output_dir, sources)

    print(f"Wrote {md_path}")
    for filename in pages:
        print(f"Wrote {output_dir / filename}")
    print(f"Wrote {index_path}")
    print(f"Wrote GPSUSER overview: {output_dir / OVERVIEW_PAGE_FILE}")
    print(f"Sources: {', '.join(str(path) for path in sources)}")
    print(f"PCFs: {len(pcf_docs)}, scripts: {len(script_docs)}, INP files: {len(inp_docs)}, handbook pages: {len(handbook_docs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
