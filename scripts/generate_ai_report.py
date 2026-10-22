from pathlib import Path
import os
import subprocess
import sys
import network_ai_engine as engine

root = Path(__file__).resolve().parents[1]
os.chdir(root)
config = engine.SITES["Global AI Report"]
report = engine.build_report("Global AI Report", config)
if not engine.validate_public_headline_integrity(report, "ai")["passed"]:
    raise RuntimeError("AI headline integrity check failed")

target = root / "public/latest_report.json"
previous = target.read_bytes() if target.exists() else None
try:
    engine.write_json(target, report)
    subprocess.run(
        [sys.executable, "scripts/check_ai_agent.py"],
        check=True,
    )
except BaseException:
    if previous is None:
        target.unlink(missing_ok=True)
    else:
        target.write_bytes(previous)
    raise

engine.write_json(root / "latest_report.json", report)
lines = [report["headline"], report["updated_at"]]
for card in report["sections"]:
    lines.extend([
        card["headline"], card["url"], card["snapshot"], ""
    ])
(root / "public/latest_report.txt").write_text(
    "\n".join(lines), encoding="utf-8"
)
print("Fresh AI report generated and validated.")
