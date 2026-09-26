#!/usr/bin/env python3
"""
CI / Pre-commit Linter: Enforces Architectural Rule §6.1
Every DB session must go through db/session.py (tenant_scoped_session / auditor_scoped_session).
Direct invocation of SessionLocal() or engine.connect() anywhere in application code
is strictly prohibited and fails the build.
"""

import sys
import re
from pathlib import Path

# Directories to inspect
TARGET_DIRS = ["api", "tasks", "services", "ml_services"]

# Patterns that represent unsanctioned direct DB access
FORBIDDEN_PATTERNS = [
    (re.compile(r"\bSessionLocal\s*\("), "Direct SessionLocal() invocation"),
    (re.compile(r"\bengine\.connect\s*\("), "Direct engine.connect() invocation"),
    (re.compile(r"\bengine\.execute\s*\("), "Direct engine.execute() invocation"),
    (re.compile(r"\bAuditorSessionLocal\s*\("), "Direct AuditorSessionLocal() invocation outside session.py"),
]


def lint_codebase() -> int:
    root_dir = Path(__file__).resolve().parent.parent
    violations = []

    print("[*] Running Architecture Rule §6.1 DB Access Linter...")
    for target_dir in TARGET_DIRS:
        target_path = root_dir / target_dir
        if not target_path.exists():
            continue

        for py_file in target_path.rglob("*.py"):
            with open(py_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line_no, line in enumerate(lines, start=1):
                # Ignore comment lines
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue

                for pattern, desc in FORBIDDEN_PATTERNS:
                    if pattern.search(line):
                        violations.append(
                            f"VIOLATION in {py_file.relative_to(root_dir)}:{line_no}\n"
                            f"  Line: {stripped}\n"
                            f"  Reason: {desc}\n"
                            f"  Fix: Use 'with tenant_scoped_session(tenant_id) as db:' from db.session."
                        )

    if violations:
        print("\n[ERROR] CI LINT FAILURE: Unsanctioned DB access detected!")
        print("Under Rule §6.1, direct DB sessions bypass PostgreSQL RLS.\n")
        for v in violations:
            print(f"- {v}\n")
        return 1

    print("[SUCCESS] All application code adheres to Rule §6.1. DB access strictly scoped via db/session.py.")
    return 0


if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    sys.exit(lint_codebase())
