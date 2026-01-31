from datetime import datetime
import json

def write_report(findings: list, severity: int):
    timestamp = datetime.utcnow().isoformat() + "Z"

    payload = {
        "generated_at": timestamp,
        "severity": severity,
        "findings": findings,
    }

    # Always write Markdown
    md_lines = []
    md_lines.append("# OSIRIS Audit Report")
    md_lines.append("")
    md_lines.append(f"Generated: {timestamp}")
    md_lines.append(f"Severity: {severity}")
    md_lines.append("")
    md_lines.append("## Findings")

    for f in findings:
        status = "PASS" if f.get("pass") else "FAIL"
        extra = ""
        if "value" in f:
            extra = f" (value: {f['value']})"
        md_lines.append(
            f"- [{f.get('category','general')}] {f['name']}: **{status}**{extra}"
        )

    with open("osiris-report.md", "w") as f:
        f.write("\n".join(md_lines))

    # Always write JSON (VIP default)
    with open("osiris-report.json", "w") as jf:
        json.dump(payload, jf, indent=2)
