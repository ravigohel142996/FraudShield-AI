#!/usr/bin/env python3
"""Build and verify the hackathon submission archive.

    python scripts/build_submission_zip.py            # build + verify
    python scripts/build_submission_zip.py --check    # verify an existing archive

The builder is deliberately paranoid, because a leaked key in a submission ZIP cannot be
un-leaked:

  1. selects files by allowlist of directory/file patterns (no blanket "everything");
  2. hard-excludes .env, .venv, .git, caches, videos, archives and node_modules;
  3. scans every included text file for credential-shaped strings and ABORTS on a hit;
  4. verifies README.md is at the archive root, the size is under the platform limit, and
     every required documentation file is present;
  5. prints the exact size and file count it produced.

Exit code 0 means the archive passed every check.
"""
from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_NAME = "RAGShield-Eval-micro1-Submission.zip"
ARCHIVE_PATH = PROJECT_ROOT / ARCHIVE_NAME
MAX_BYTES = 50 * 1024 * 1024  # platform limit for Q1

INCLUDE_PATTERNS = [
    "README.md",
    "PROJECT_AUDIT.md",
    "RESEARCH_METHODOLOGY.md",
    "SCORING_METHODOLOGY.md",
    "FAILURE_ANALYSIS.md",
    "STATE.md",
    "FINAL_SUBMISSION_REPORT.md",
    ".env.example",
    "requirements.txt",
    "config/*.yaml",
    "docs/*.md",
    "tasks/*.json",
    "src/*.py",
    "tests/*.py",
    "tests/fixtures/*.py",
    "dashboard/*.py",
    "video/*.md",
    "scripts/*.py",
    "results/README_RESULTS.md",
    "results/validation/*.json",
    "results/validation/*.jsonl",
    "results/validation/*.csv",
    "results/validation/*.md",
]

REQUIRED_FILES = [
    "README.md",
    "RESEARCH_METHODOLOGY.md",
    "SCORING_METHODOLOGY.md",
    "FAILURE_ANALYSIS.md",
    "PROJECT_AUDIT.md",
    "requirements.txt",
    ".env.example",
    "config/benchmark.yaml",
    "config/policy.yaml",
    "src/runner.py",
    "src/graders.py",
    "src/authorization_engine.py",
    "src/model_provider.py",
    "src/evaluation_runner.py",
    "tests/test_grading.py",
    "dashboard/app.py",
]
EXPECTED_TASKS = [f"tasks/task_0{i}.json" for i in range(1, 9)]

# Credential-shaped patterns. A hit anywhere aborts the build.
SECRET_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "OpenAI-style secret key"),
    (re.compile(r"sk-ant-[A-Za-z0-9\-_]{20,}"), "Anthropic-style secret key"),
    (re.compile(r"AIza[0-9A-Za-z\-_]{30,}"), "Google API key"),
    (re.compile(r"gsk_[A-Za-z0-9]{20,}"), "Groq API key"),
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"), "GitHub token"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key block"),
    (re.compile(r"(?i)\b(api[_-]?key|secret|password|passwd|token)\b\s*[:=]\s*['\"]?[A-Za-z0-9/+_\-]{16,}"),
     "hard-coded credential assignment"),
]
# Files whose *mention* of these words is documentation, not a secret.
SECRET_SCAN_ALLOWLIST = {".env.example"}
MAX_SCAN_BYTES = 2 * 1024 * 1024


def collect_files() -> list[Path]:
    selected: list[Path] = []
    for pattern in INCLUDE_PATTERNS:
        for path in sorted(PROJECT_ROOT.glob(pattern)):
            if path.is_file() and not _excluded(path):
                selected.append(path)
    # de-duplicate while keeping order
    seen, unique = set(), []
    for path in selected:
        if path not in seen:
            seen.add(path)
            unique.append(path)
    return unique


def _excluded(path: Path) -> bool:
    parts = set(path.relative_to(PROJECT_ROOT).parts)
    banned = {
        ".venv", "venv", "__pycache__", ".git", ".pytest_cache", "node_modules",
        ".mypy_cache", ".ruff_cache", "build", "dist", ".streamlit",
    }
    if parts & banned:
        return True
    name = path.name
    if name == ".env" or name.endswith((".zip", ".mp4", ".mov", ".mkv", ".pkl", ".pyc")):
        return True
    return False


def scan_for_secrets(files: list[Path]) -> list[str]:
    findings: list[str] = []
    for path in files:
        rel = path.relative_to(PROJECT_ROOT).as_posix()
        if rel in SECRET_SCAN_ALLOWLIST:
            continue
        try:
            if path.stat().st_size > MAX_SCAN_BYTES:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern, label in SECRET_PATTERNS:
            for match in pattern.finditer(text):
                snippet = match.group(0)[:12]
                findings.append(f"{rel}: {label} (starts with {snippet!r})")
    return findings


def build() -> tuple[Path, int]:
    files = collect_files()
    findings = scan_for_secrets(files)
    if findings:
        print("REFUSING TO BUILD — credential-shaped strings found:")
        for finding in findings:
            print("  " + finding)
        print("\nRemove the value (keep the variable name), then rebuild.")
        raise SystemExit(2)

    if ARCHIVE_PATH.exists():
        ARCHIVE_PATH.unlink()
    with zipfile.ZipFile(ARCHIVE_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            archive.write(path, arcname=path.relative_to(PROJECT_ROOT).as_posix())
    return ARCHIVE_PATH, len(files)


def verify(archive_path: Path = ARCHIVE_PATH) -> bool:
    ok = True
    if not archive_path.exists():
        print(f"MISSING: {archive_path}")
        return False
    size = archive_path.stat().st_size
    print(f"Archive: {archive_path}")
    print(f"Size:    {size:,} bytes ({size / 1024 / 1024:.2f} MB) — limit 50.00 MB")
    if size > MAX_BYTES:
        print("FAIL: archive exceeds the 50 MB platform limit")
        ok = False

    with zipfile.ZipFile(archive_path) as archive:
        bad = archive.testzip()
        if bad is not None:
            print(f"FAIL: corrupt member {bad}")
            ok = False
        names = archive.namelist()

    print(f"Members: {len(names)}")
    if "README.md" not in names:
        print("FAIL: README.md is not at the archive root")
        ok = False

    for required in REQUIRED_FILES + EXPECTED_TASKS:
        if required not in names:
            print(f"FAIL: required file missing from archive: {required}")
            ok = False

    forbidden_segments = {".git", ".venv", "venv", "__pycache__", "node_modules", ".pytest_cache"}
    for name in names:
        segments = set(Path(name).parts)
        if Path(name).name == ".env":
            print(f"FAIL: live .env included in archive: {name}")
            ok = False
        elif segments & forbidden_segments:
            print(f"FAIL: forbidden path in archive: {name}")
            ok = False
        if name.endswith((".zip", ".mp4", ".mov", ".pkl")):
            print(f"FAIL: binary/large artefact in archive: {name}")
            ok = False

    print("\nDirectory summary:")
    top: dict[str, int] = {}
    for name in names:
        key = name.split("/")[0] if "/" in name else "(root)"
        top[key] = top.get(key, 0) + 1
    for key in sorted(top):
        print(f"  {key:<28} {top[key]:>3} files")

    print("\nRESULT:", "PASS" if ok else "FAIL")
    return ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the RAGShield Eval submission ZIP")
    parser.add_argument("--check", action="store_true", help="verify an existing archive only")
    args = parser.parse_args(argv)

    if args.check:
        return 0 if verify() else 1

    archive_path, count = build()
    print(f"Built {count} files into {archive_path.name}\n")
    return 0 if verify(archive_path) else 1


if __name__ == "__main__":
    sys.exit(main())
