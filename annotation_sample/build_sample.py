#!/usr/bin/env python3
"""Build a stratified 150-trajectory sample for the W4 + R2-L2 LLM-judge experiment."""
from __future__ import annotations

import csv
import json
import random
from collections import defaultdict
from pathlib import Path

REPO = Path("/Users/jinhuqi/Documents/GitHub/haaf-pilot")
LOGS = REPO / "logs"
SCENARIOS = REPO / "scenarios"
OUT_DIR = REPO / "annotation_sample"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SEED = 42
TARGET_PER_PROPERTY = 30
TARGET_SUCCESS = 15
TARGET_VIOLATION = 15
MIN_MODELS_PER_AXIS = 3
MAX_TOOL_CALL_SUMMARY = 12
FINAL_ANSWER_MAX = 800

# primary_failure_target -> property
TARGET_TO_PROP = {
    "PI": "P2",
    "GD": "P1",
    "HT": "P1",
    "IR": "P1",
    "UA": "P3",
    "PL": "P3",
    "SH": "P4",
    "RF": "P5",
    "OF": "P5",
}


def discover_suffixes() -> list[str]:
    suffixes: set[str] = set()
    for p in LOGS.glob("control_*_runs.jsonl"):
        name = p.name
        # control_<suffix>_runs.jsonl
        suffix = name[len("control_") : -len("_runs.jsonl")]
        if suffix:
            suffixes.add(suffix)
    return sorted(suffixes)


def load_scenarios() -> dict[str, dict]:
    out = {}
    for p in sorted(SCENARIOS.glob("s*.json")):
        with p.open() as f:
            data = json.load(f)
        out[data["scenario_id"]] = data
    return out


def load_jsonl(p: Path) -> list[dict]:
    rows = []
    if not p.exists():
        return rows
    with p.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def summarize_tool_args(args) -> str:
    if args is None:
        return ""
    try:
        s = json.dumps(args, ensure_ascii=False, default=str)
    except Exception:
        s = str(args)
    if len(s) > 200:
        s = s[:197] + "..."
    return s


def step_status(step: dict) -> str:
    out = step.get("tool_output")
    if out is None:
        return "no_output"
    if isinstance(out, dict):
        if "error" in out:
            return "error"
        if out.get("status") == "blocked" or out.get("blocked"):
            return "blocked"
        if out.get("status"):
            return str(out.get("status"))
        if out.get("ok") is False:
            return "error"
        return "ok"
    return "ok"


def build_tool_call_summary(steps: list[dict]) -> list[dict]:
    summary = []
    for st in steps[:MAX_TOOL_CALL_SUMMARY]:
        summary.append(
            {
                "tool_name": st.get("tool_name"),
                "tool_args_summary": summarize_tool_args(st.get("tool_args")),
                "status": step_status(st),
            }
        )
    return summary


def main() -> None:
    rng = random.Random(SEED)
    scenarios = load_scenarios()

    # property -> list of scenario_ids
    prop_scenarios: dict[str, list[str]] = defaultdict(list)
    for sid, sc in scenarios.items():
        tgt = sc.get("primary_failure_target", "none")
        prop = TARGET_TO_PROP.get(tgt)
        if prop:
            prop_scenarios[prop].append(sid)

    suffixes = discover_suffixes()

    # Pre-load all runs and trajectories per (suffix, version)
    runs_idx: dict[tuple[str, str], dict[str, dict]] = {}
    traj_idx: dict[tuple[str, str], dict[str, list[dict]]] = {}
    for suffix in suffixes:
        for version in ("control", "treated"):
            runs_p = LOGS / f"{version}_{suffix}_runs.jsonl"
            traj_p = LOGS / f"{version}_{suffix}_trajectories.jsonl"
            runs = load_jsonl(runs_p)
            traj = load_jsonl(traj_p)
            run_by_sid = {r["scenario_id"]: r for r in runs if "scenario_id" in r}
            traj_by_sid: dict[str, list[dict]] = defaultdict(list)
            for t in traj:
                if "scenario_id" in t:
                    traj_by_sid[t["scenario_id"]].append(t)
            # sort steps by step_id (or timestamp)
            for sid, steps in traj_by_sid.items():
                steps.sort(key=lambda x: (x.get("step_id", 0), x.get("timestamp", "")))
            runs_idx[(suffix, version)] = run_by_sid
            traj_idx[(suffix, version)] = traj_by_sid

    # Build candidate pool keyed by property -> list of records
    # Each record: dict with property, scenario_id, model_suffix, version, run, steps, success_or_violation
    pool: dict[str, list[dict]] = defaultdict(list)
    for prop, sid_list in prop_scenarios.items():
        for sid in sid_list:
            for suffix in suffixes:
                for version in ("control", "treated"):
                    run = runs_idx[(suffix, version)].get(sid)
                    if not run:
                        continue
                    steps = traj_idx[(suffix, version)].get(sid, [])
                    if not steps:
                        # still allow if run exists but no steps? skip - judge needs trajectory
                        continue
                    is_violation = bool(run.get("violation"))
                    pool[prop].append(
                        {
                            "property": prop,
                            "scenario_id": sid,
                            "model_suffix": suffix,
                            "version": version,
                            "run": run,
                            "steps": steps,
                            "is_violation": is_violation,
                        }
                    )

    # Stratified selection per property
    selected_by_prop: dict[str, list[dict]] = {}
    actual_counts: dict[str, dict[str, int]] = {}

    for prop in ("P1", "P2", "P3", "P4", "P5"):
        candidates = pool.get(prop, [])
        viol = [c for c in candidates if c["is_violation"]]
        succ = [c for c in candidates if not c["is_violation"]]
        rng.shuffle(viol)
        rng.shuffle(succ)

        # try to maximize model diversity
        def pick_with_diversity(items: list[dict], n: int, used_models: set[str]) -> list[dict]:
            # pass 1: pick one per unused model first
            picked = []
            remaining = list(items)
            # prefer items with fewer occurrences of their model among already picked
            from collections import Counter
            picked_models: Counter = Counter()
            # try to ensure at least MIN_MODELS_PER_AXIS distinct models when possible
            while remaining and len(picked) < n:
                # sort remaining by (count of model in picked, original order index)
                remaining.sort(key=lambda c: (picked_models[c["model_suffix"]],))
                choice = remaining.pop(0)
                picked.append(choice)
                picked_models[choice["model_suffix"]] += 1
            return picked

        chosen_viol = pick_with_diversity(viol, min(TARGET_VIOLATION, len(viol)), set())
        # how many violations do we have?
        viol_count = len(chosen_viol)
        succ_needed = TARGET_PER_PROPERTY - viol_count
        chosen_succ = pick_with_diversity(succ, min(succ_needed, len(succ)), set())

        chosen = chosen_viol + chosen_succ
        # If still under TARGET_PER_PROPERTY (rare), top up with any leftover candidates
        if len(chosen) < TARGET_PER_PROPERTY:
            leftover = [c for c in candidates if c not in chosen]
            rng.shuffle(leftover)
            chosen.extend(leftover[: TARGET_PER_PROPERTY - len(chosen)])

        # Enforce MIN_MODELS_PER_AXIS by swapping if necessary
        models_in_chosen = {c["model_suffix"] for c in chosen}
        if len(models_in_chosen) < MIN_MODELS_PER_AXIS:
            # find candidates from unused models and swap with over-represented model entries
            unused_models = [
                c for c in candidates if c["model_suffix"] not in models_in_chosen and c not in chosen
            ]
            from collections import Counter
            mcounts = Counter(c["model_suffix"] for c in chosen)
            for cand in unused_models:
                if len({c["model_suffix"] for c in chosen}) >= MIN_MODELS_PER_AXIS:
                    break
                # swap out the most over-represented model entry that matches success_or_violation if possible
                target_label = cand["is_violation"]
                # find a chosen entry from a model with count > 1 and same label
                swap_idx = None
                for i, c in enumerate(chosen):
                    if mcounts[c["model_suffix"]] > 1 and c["is_violation"] == target_label:
                        swap_idx = i
                        break
                if swap_idx is None:
                    # fallback: swap with any over-represented entry
                    for i, c in enumerate(chosen):
                        if mcounts[c["model_suffix"]] > 1:
                            swap_idx = i
                            break
                if swap_idx is None:
                    break
                mcounts[chosen[swap_idx]["model_suffix"]] -= 1
                mcounts[cand["model_suffix"]] += 1
                chosen[swap_idx] = cand

        selected_by_prop[prop] = chosen
        actual_counts[prop] = {
            "total": len(chosen),
            "violation": sum(1 for c in chosen if c["is_violation"]),
            "success": sum(1 for c in chosen if not c["is_violation"]),
            "distinct_models": len({c["model_suffix"] for c in chosen}),
            "pool_total": len(candidates),
            "pool_violation": len(viol),
            "pool_success": len(succ),
        }

    # Serialize selected entries
    out_jsonl = OUT_DIR / "150_trajectories.jsonl"
    out_csv = OUT_DIR / "sample_index.csv"

    sample_id = 0
    records_out = []
    csv_rows = []
    for prop in ("P1", "P2", "P3", "P4", "P5"):
        for entry in selected_by_prop[prop]:
            sample_id += 1
            run = entry["run"]
            steps = entry["steps"]
            sc = scenarios.get(entry["scenario_id"], {})
            final_answer = run.get("final_answer") or ""
            if isinstance(final_answer, str) and len(final_answer) > FINAL_ANSWER_MAX:
                final_answer = final_answer[:FINAL_ANSWER_MAX]
            rec = {
                "sample_id": sample_id,
                "property": prop,
                "scenario_id": entry["scenario_id"],
                "model_suffix": entry["model_suffix"],
                "version": entry["version"],
                "user_goal": sc.get("user_goal", ""),
                "heuristic_label_violation": bool(run.get("violation")),
                "heuristic_label_violation_details": run.get("violation_details", []) or [],
                "heuristic_label_terminated_by": run.get("terminated_by", ""),
                "final_answer": final_answer,
                "tool_call_summary": build_tool_call_summary(steps),
            }
            records_out.append(rec)
            csv_rows.append(
                {
                    "sample_id": sample_id,
                    "property": prop,
                    "scenario_id": entry["scenario_id"],
                    "model_suffix": entry["model_suffix"],
                    "version": entry["version"],
                    "success_or_violation": "violation" if entry["is_violation"] else "success",
                }
            )

    with out_jsonl.open("w") as f:
        for rec in records_out:
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")

    with out_csv.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "sample_id",
                "property",
                "scenario_id",
                "model_suffix",
                "version",
                "success_or_violation",
            ],
        )
        writer.writeheader()
        writer.writerows(csv_rows)

    # Print diagnostics
    print(f"WROTE: {out_jsonl}")
    print(f"WROTE: {out_csv}")
    print(f"TOTAL_SAMPLES: {len(records_out)}")
    print("PER_PROPERTY_COUNTS:")
    print(
        f"{'property':<10}{'success':>10}{'violation':>12}{'total':>8}{'models':>8}{'pool_v':>8}{'pool_s':>8}"
    )
    for prop in ("P1", "P2", "P3", "P4", "P5"):
        c = actual_counts[prop]
        print(
            f"{prop:<10}{c['success']:>10}{c['violation']:>12}{c['total']:>8}{c['distinct_models']:>8}{c['pool_violation']:>8}{c['pool_success']:>8}"
        )

    print("FIRST_5_SAMPLES:")
    for rec in records_out[:5]:
        print(
            f"  id={rec['sample_id']} property={rec['property']} scenario={rec['scenario_id']} "
            f"model={rec['model_suffix']} version={rec['version']} violation={rec['heuristic_label_violation']}"
        )


if __name__ == "__main__":
    main()
