from datetime import datetime

def write_report(findings: list, severity: int):
    lines = []
    lines.append("# OSIRIS Audit Report")
    lines.append("")
    lines.append(f"Generated: {datetime.utcnow().isoformat()}Z")
    lines.append(f"Severity: {severity}")
    lines.append("")
    lines.append("## Findings")

    for f in findings:
        status = "PASS" if f.get("pass") else "FAIL"
        extra = ""
        if "value" in f:
            extra = f" (value: {f['value']})"
        lines.append(f"- [{f.get('category','general')}] {f['name']}: **{status}**{extra}")

    with open("osiris-report.md", "w") as fp:
        fp.write("\n".join(lines))
