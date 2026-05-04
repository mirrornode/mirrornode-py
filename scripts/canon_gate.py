#!/usr/bin/env python3
"""
Canon Gate - Pre-Audit Contract Enforcement
MIRRORNODE-CORE-HUB
Runs on every PR targeting main. Reads SYSTEM_CONTRACT.md, REPO_MAP.md, and AGENTS_TODO.md as ground truth,
then checks the incoming diff for contract violations before any merge is allowed.
Exit 0 = clean, merge allowed. Exit 1 = violation found, merge blocked.
Expand PHANTOM_ROUTES and AUTHORITY_CONFLICTS as contracts evolve.
"""
import os
import re
import subprocess
import sys

CONTRACT_FILE = "SYSTEM_CONTRACT.md"
REPO_MAP_FILE = "REPO_MAP.md"
AGENTS_FILE = "AGENTS_TODO.md"

PHANTOM_ROUTES = [
    "/system/execute",
    "/system/replay",
    "/execute-task",
]

AUTHORITY_CONFLICTS = [
    r"osiris.*execution.*(engine|authority|core)",
    r"execution.*(engine|authority|core).*osiris",
    r"triaden?gine",
]

CANONICAL_PORTS = {"7700", "7701", "7702", "7703", "7704", "7705", "7706"}

def get_diff() -> str:
    base = os.environ.get("BASE_SHA", "HEAD~1")
    head = os.environ.get("HEAD_SHA", "HEAD")
    try:
        result = subprocess.run(
            ["git", "diff", base, head, "--unified=0"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"[Canon Gate] WARNING: Could not get diff: {e}")
        return ""

def load_contract() -> str:
    try:
        with open(CONTRACT_FILE, "r") as f:
            return f.read()
    except FileNotFoundError:
        print(f"[Canon Gate] ERROR: {CONTRACT_FILE} not found. Cannot validate.")
        sys.exit(1)

def check_governance_files_present() -> list:
    violations = []
    for f in [CONTRACT_FILE, REPO_MAP_FILE, AGENTS_FILE]:
        if not os.path.exists(f):
            violations.append(
                f"CONTRACT DELETION: '{f}' is missing. "
                f"Governance files are protected and cannot be removed."
            )
    return violations

def check_phantom_routes(diff: str) -> list:
    violations = []
    for route in PHANTOM_ROUTES:
        pattern = re.compile(
            r"^\+.*" + re.escape(route),
            re.MULTILINE | re.IGNORECASE
        )
        if pattern.search(diff):
            violations.append(
                f"PHANTOM ROUTE: '{route}' is declared non-real in "
                f"{CONTRACT_FILE} but appears as an addition in this PR."
            )
    return violations

def check_authority_conflicts(diff: str) -> list:
    violations = []
    for pattern_str in AUTHORITY_CONFLICTS:
        pattern = re.compile(
            r"^\+.*" + pattern_str,
            re.MULTILINE | re.IGNORECASE
        )
        if pattern.search(diff):
            violations.append(
                f"AUTHORITY CONFLICT: Pattern '{pattern_str}' contradicts "
                f"LUCIAN as the declared execution authority in {CONTRACT_FILE}."
            )
    return violations

def check_unregistered_ports(diff: str) -> list:
    violations = []
    pattern = re.compile(r"^\+.*port[:\s]+([0-9]{4,5})", re.MULTILINE | re.IGNORECASE)
    for match in pattern.finditer(diff):
        port = match.group(1)
        if port not in CANONICAL_PORTS:
            violations.append(
                f"UNREGISTERED PORT: Port {port} is not in the canonical "
                f"agent registry (7700-7706). Update AGENTS_TODO.md first."
            )
    return violations

def main():
    print("[Canon Gate] " + "=" * 50)
    print("[Canon Gate] MIRRORNODE Contract Compliance Check")
    print("[Canon Gate] " + "=" * 50)
    print("[Canon Gate] Loading contract...")
    load_contract()
    print("[Canon Gate] Fetching PR diff...")
    diff = get_diff()
    if not diff:
        print("[Canon Gate] No diff detected. Passing.")
        sys.exit(0)
    print("[Canon Gate] Running checks...\n")
    violations = (
        check_governance_files_present()
        + check_phantom_routes(diff)
        + check_authority_conflicts(diff)
        + check_unregistered_ports(diff)
    )
    if violations:
        print("[Canon Gate] RESULT: VIOLATIONS FOUND - merge blocked\n")
        for i, v in enumerate(violations, 1):
            print(f" {i}. {v}")
        print(
            f"\n[Canon Gate] Resolve all violations against "
            f"{CONTRACT_FILE} before this PR can merge."
        )
        print("[Canon Gate] " + "=" * 50)
        sys.exit(1)
    print("[Canon Gate] RESULT: All checks passed. Contract coherent.")
    print("[Canon Gate] Merge authorized.")
    print("[Canon Gate] " + "=" * 50)
    sys.exit(0)

if __name__ == "__main__":
    main()
