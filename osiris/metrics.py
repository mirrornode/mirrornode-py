from pathlib import Path

def collect_metrics(target: Path) -> dict:
    py_files = list(target.rglob("*.py"))
    return {
        "python_files": len(py_files),
        "has_tests": (target / "tests").exists() or (target / "test").exists(),
    }
