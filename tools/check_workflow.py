#!/usr/bin/env python3
"""Validate the pilot's flat task metadata, task index and local Markdown links.

This is a structural check, not proof of acceptance, permissions or publication.
"""
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

ENUMS = {
    "role": {"triage", "research", "architecture", "implementation", "review", "release"},
    "status": {"proposed", "ready", "active", "blocked", "review", "done", "cancelled"},
    "delivery": {"not-applicable", "unreleased", "released"},
    "verification": {"pending", "partial", "passed", "failed"},
}
FIELDS = set(ENUMS) | {"id", "owner", "base_commit", "artifact"}
SECTIONS = ("Objective", "Scope", "Acceptance", "Authorization", "Evidence", "Outcome and next action")
EMPTY = {"", "none", "unset", "unassigned", "not yet recorded.", "not yet recorded"}
ID = re.compile(r"[A-Z][A-Z0-9]*-[1-9][0-9]*")


def parse_task(text):
    lines = text.splitlines()
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        raise ValueError("missing metadata delimiters")
    end = lines.index("---", 1)
    data = {}
    for line in lines[1:end]:
        key, sep, value = line.partition(":")
        if not sep or not key.strip() or key.strip() in data:
            raise ValueError("invalid/duplicate metadata key")
        data[key.strip()] = value.strip()
    return data


def section(text, name):
    match = re.search(r"^## " + re.escape(name) + r"\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return match.group(1).strip() if match else ""


def validate(root):
    root = Path(root).resolve()
    errors = []
    records = {}
    task_paths = sorted((root / "docs/tasks").glob("*.md"))
    if not task_paths:
        errors.append("no task records")
    for path in task_paths:
        label = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        try:
            data = parse_task(text)
        except ValueError as exc:
            errors.append(f"{label}: {exc}")
            continue
        for field in FIELDS:
            if not data.get(field):
                errors.append(f"{label}: missing {field}")
        task_id = data.get("id", "")
        if not ID.fullmatch(task_id) or task_id != path.stem or task_id in records:
            errors.append(f"{label}: invalid, duplicate or mismatched ID")
        records[task_id] = data
        for field, allowed in ENUMS.items():
            if data.get(field) not in allowed:
                errors.append(f"{label}: invalid {field}")
        for name in SECTIONS:
            if not section(text, name):
                errors.append(f"{label}: missing/empty section {name}")
        if data.get("status") in {"active", "review", "done"}:
            if not re.fullmatch(r"[0-9a-f]{40}", data.get("base_commit", "")):
                errors.append(f"{label}: working task needs full base SHA")
            if data.get("owner", "").lower() in EMPTY:
                errors.append(f"{label}: working task needs owner")
        if data.get("status") == "done":
            if data.get("verification") != "passed" or section(text, "Evidence").lower() in EMPTY:
                errors.append(f"{label}: done requires passed verification and evidence")
        if data.get("delivery") == "released":
            artifact = data.get("artifact", "")
            if artifact.lower() in EMPTY:
                errors.append(f"{label}: released requires artifact")
            elif not urlsplit(artifact).scheme and not (root / artifact).exists():
                errors.append(f"{label}: artifact path missing")

    index = root / "KNOWN_ISSUES.md"
    indexed = {}
    if not index.exists():
        errors.append("missing KNOWN_ISSUES.md")
    else:
        for line in index.read_text(encoding="utf-8").splitlines():
            cells = [x.strip() for x in line.strip().strip("|").split("|")]
            if not cells or not ID.fullmatch(cells[0]):
                continue
            task_id = cells[0]
            if task_id in indexed:
                errors.append(f"duplicate index ID {task_id}")
            indexed[task_id] = cells
            data = records.get(task_id)
            if not data or len(cells) != 4 or cells[1:3] != [data.get("status"), data.get("role")]:
                errors.append(f"index status/role mismatch: {task_id}")
            if f"(docs/tasks/{task_id}.md)" not in line:
                errors.append(f"index task link mismatch: {task_id}")
        for task_id in records.keys() - indexed.keys():
            errors.append(f"task absent from index: {task_id}")

    documents = list(root.glob("*.md")) + list((root / "docs").rglob("*.md"))
    for path in sorted(documents):
        text = re.sub(r"^\x60\x60\x60.*?^\x60\x60\x60[^\n]*", "", path.read_text(encoding="utf-8"), flags=re.M | re.S)
        for target in re.findall(r"\]\(([^\s)]+)\)", text):
            parts = urlsplit(target)
            if parts.scheme or target.startswith("#"):
                continue
            destination = (path.parent / unquote(parts.path)).resolve()
            if not destination.is_relative_to(root) or not destination.exists():
                errors.append(f"{path.relative_to(root)}: broken local link {target}")
    return errors


if __name__ == "__main__":
    issues = validate(Path(__file__).resolve().parents[1])
    if issues:
        print("\n".join(issues))
        sys.exit(1)
    print("Workflow records, index and local document links validated.")
