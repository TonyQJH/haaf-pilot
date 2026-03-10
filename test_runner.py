"""Verify runner can load scenarios and parse correctly."""
import sys
sys.path.insert(0, '.')
from runner import load_scenario, build_user_message, get_available_tool_specs
from runner import CONTROL_PROMPT, TREATED_PROMPT

# Test s01 (benign), s09 (adversarial), s21 (social)
for sid in ["s01", "s09", "s21"]:
    s = load_scenario(sid)
    msg = build_user_message(s)
    specs = get_available_tool_specs(s["available_tools"])
    print(f"{sid} [{s['category']}] severity={s['risk_severity']}: "
          f"{s['title']} | tools={len(specs)} | msg={len(msg)} chars")

print(f"\nControl prompt: {len(CONTROL_PROMPT)} chars")
print(f"Treated prompt: {len(TREATED_PROMPT)} chars")
print("\n=== RUNNER VERIFICATION OK ===")
