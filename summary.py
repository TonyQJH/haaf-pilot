"""Full summary of all run results."""
import json
from pathlib import Path

logs_dir = Path("pilot/logs")

for version in ["control", "treated"]:
    path = logs_dir / f"{version}_runs.jsonl"
    if not path.exists():
        print(f"{version}: no logs found")
        continue
    runs = [json.loads(l) for l in open(path) if l.strip()]
    s = sum(1 for r in runs if r["success"])
    v = sum(1 for r in runs if r["violation"])
    print(f"\n{'='*60}")
    print(f" {version.upper()} | {len(runs)} runs | Success={s} | Violation={v}")
    print(f"{'='*60}")
    for r in runs:
        flag = "OK" if r["success"] else "FAIL"
        vflag = " VIOLATION" if r["violation"] else ""
        vd = r.get("violation_details", [])
        hr = " HIGH_RISK_BLOCKED" if r.get("attempted_high_risk_action") else ""
        detail = f" [{vd[0][:60]}...]" if vd else ""
        print(f"  {r['scenario_id']:4s} {flag:4s}{vflag}{hr} | "
              f"steps={r['steps_used']} tools={r['tool_calls_used']} "
              f"term={r['terminated_by']}{detail}")
