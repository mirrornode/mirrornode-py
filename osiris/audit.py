from pathlib import Path
from osiris.report import write_report
from osiris.preflight import run_preflight
from osiris.metrics import collect_metrics

def run_audit(target_path: str) -> int:
    target = Path(target_path).resolve()

    findings = []

    # 1) Preflight
    pre = run_preflight(target)
    findings.extend(pre["checks"])
    if not pre["pass"]:
        write_report(findings, severity=2)
        return 2

    # 2) Structure
    findings.extend([
        {"name": "README present", "pass": (target / "README.md").exists(), "category": "structure"},
        {"name": "pyproject.toml present", "pass": (target / "pyproject.toml").exists(), "category": "structure"},
        {"name": ".gitignore present", "pass": (target / ".gitignore").exists(), "category": "structure"},
    ])

    # 3) Metrics signals
    m = collect_metrics(target)
    findings.extend([
        {"name": "Python files detected", "pass": m["python_files"] > 0, "value": m["python_files"], "category": "metrics"},
        {"name": "Test directory present", "pass": m["has_tests"], "category": "metrics"},
    ])

    # 4) Severity (deterministic)
    failures = [f for f in findings if not f.get("pass", True)]
    severity = 2 if len(failures) >= 3 else 1 if failures else 0

    write_report(findings, severity)
    return severity
