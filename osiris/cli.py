import sys
from pathlib import Path
from osiris.audit import run_audit

def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    p = Path(target)
    if not p.exists():
        print(f"[OSIRIS] Target not found: {target}")
        sys.exit(2)
    sys.exit(run_audit(str(p)))

if __name__ == "__main__":
    main()
