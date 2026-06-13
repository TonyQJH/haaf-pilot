"""
Layer-4 reference implementation: distribution-aware scenario sampling.

Operationalises the sampling objective specified in §3 of the paper:

    Q* = argmax_{Q subset S} [ alpha*Cov(Q) + beta*Risk(Q) + eta*Comp(Q) - gamma*Red(Q) ]

with alpha=0.4, beta=0.3, eta=0.2, gamma=0.1.

The four functionals are:

  Cov(Q):  normalised Shannon entropy across the joint of
           (property P_k, failure-target class) cells observed in Q.
           Higher = better manifold coverage.
  Risk(Q): sum of risk_severity(s) for s in Q. Higher = better
           (so the objective favours high-consequence regions).
  Comp(Q): mean per-scenario compositional-complexity proxy:
           #available_tools + #non-empty initial_context fields + #safety_rules.
           Higher = better.
  Red(Q):  mean pairwise feature-vector similarity between scenarios in Q,
           using the (P_k, target, tool-set) feature.  Lower = better
           (the objective subtracts it).

A greedy submodular selection is then run: starting from Q=empty, at each
step add the scenario s that maximises the marginal contribution to the
weighted objective, until |Q| = K (default 40).

The selected subset is then validated against the full 100-scenario suite
by recomputing each model's RWF on the subset and comparing the 13-model
ranking under Kendall-tau and Spearman-rho.

Outputs:
  scenarios/_layer4_selected_subset.json
  Agent4IR_KDD2026/Chapter/_layer4_validation_inc.tex

stdlib + numpy only. Seed = 42 throughout.
"""

from __future__ import annotations

import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

K = 40
ALPHA, BETA, ETA, GAMMA = 0.4, 0.3, 0.2, 0.1

BASE = Path(__file__).parent
SCEN_DIR = BASE / "scenarios"
LOGS_DIR = BASE / "logs"
PAPER_DIR = BASE / "Agent4IR_KDD2026"
INC_TEX = PAPER_DIR / "Chapter" / "_layer4_validation_inc.tex"
SUBSET_JSON = SCEN_DIR / "_layer4_selected_subset.json"

# Failure-target -> primary property (mirrors analyze_profile.TARGET_TO_PROP).
# Targets not in this map (e.g. "none") fall back to P1.
TARGET_TO_PROP = {
    "PI": 2, "GD": 1, "UA": 3, "HT": 1, "RF": 5,
    "OF": 5, "PL": 3, "SH": 4, "IR": 1,
}

# 13 cross-family systems, in the order used by analyze_profile.py / Table 4.
MODELS = [
    ("Llama-3.1-8B",     "llama31_8b"),
    ("Llama-3.1-70B",    "llama31_70b"),
    ("Mistral-Large-2",  "mistral_large_2402"),
    ("Mistral-Large-3",  "mistral_large_3"),
    ("Kimi-K2-Thinking", "kimi_k2_thinking"),
    ("Kimi-K2.5",        "kimi_k25"),
    ("GLM-4.7",          "glm_47"),
    ("GLM-5",            "glm_5"),
    ("Qwen3-32B",        "qwen3_32b"),
    ("Qwen3-Next-80B",   "qwen3_next_80b"),
    ("GPT-oss-20B",      "gpt_oss_20b"),
    ("GPT-oss-120B",     "gpt_oss_120b"),
    ("DeepSeek-V3.2",    "deepseek_v32"),
]

# ----------------------------------------------------------------------------
# Data loading
# ----------------------------------------------------------------------------

def load_scenarios() -> Dict[str, dict]:
    out = {}
    for p in sorted(SCEN_DIR.glob("s*.json")):
        d = json.loads(p.read_text())
        sid = d["scenario_id"]
        target = d.get("primary_failure_target", "GD") or "GD"
        prop = TARGET_TO_PROP.get(target, 1)
        tools = tuple(sorted(d.get("available_tools", []) or []))
        ic = d.get("initial_context", {}) or {}
        ic_nonempty = sum(1 for v in ic.values() if v not in (None, "", [], {}))
        sr = d.get("safety_rules", []) or []
        out[sid] = {
            "scenario_id": sid,
            "category": d.get("category", ""),
            "target": target,
            "prop": prop,
            "risk": int(d.get("risk_severity", 3)),
            "tools": tools,
            "ic_nonempty": ic_nonempty,
            "n_tools": len(tools),
            "n_safety_rules": len(sr),
            # Compositional complexity proxy
            "comp": len(tools) + ic_nonempty + len(sr),
        }
    return out


def load_runs(suffix: str) -> List[dict]:
    path = LOGS_DIR / f"control_{suffix}_runs.jsonl"
    if not path.exists():
        return []
    rows = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


# ----------------------------------------------------------------------------
# Four functionals
# ----------------------------------------------------------------------------

def cov(Q: List[str], scen: Dict[str, dict]) -> float:
    """Normalised Shannon entropy over (P_k, target) cells in Q.

    Empty / singleton sets return 0.  We normalise by log(#cells_observed)
    so a uniform distribution over the observed cells scores 1.0.
    """
    if len(Q) < 2:
        return 0.0
    cells = Counter((scen[s]["prop"], scen[s]["target"]) for s in Q)
    n = sum(cells.values())
    H = 0.0
    for c in cells.values():
        p = c / n
        H -= p * math.log(p)
    n_cells = len(cells)
    if n_cells <= 1:
        return 0.0
    return H / math.log(n_cells)


def risk_total(Q: List[str], scen: Dict[str, dict]) -> float:
    return float(sum(scen[s]["risk"] for s in Q))


def comp_mean(Q: List[str], scen: Dict[str, dict]) -> float:
    if not Q:
        return 0.0
    return float(np.mean([scen[s]["comp"] for s in Q]))


def _feature_vec(s: str, scen: Dict[str, dict], tool_vocab: List[str]) -> np.ndarray:
    """Concatenate one-hots for property, target, and tool-set membership."""
    d = scen[s]
    prop_oh = np.zeros(5, dtype=np.int8)
    prop_oh[d["prop"] - 1] = 1
    targets = ["PI", "GD", "UA", "HT", "RF", "OF", "PL", "SH", "IR", "none"]
    tgt_oh = np.zeros(len(targets), dtype=np.int8)
    if d["target"] in targets:
        tgt_oh[targets.index(d["target"])] = 1
    tool_oh = np.zeros(len(tool_vocab), dtype=np.int8)
    for t in d["tools"]:
        if t in tool_vocab:
            tool_oh[tool_vocab.index(t)] = 1
    return np.concatenate([prop_oh, tgt_oh, tool_oh])


def red_mean(Q: List[str], feats: Dict[str, np.ndarray]) -> float:
    """Mean pairwise similarity = 1 - normalised Hamming distance."""
    if len(Q) < 2:
        return 0.0
    sims = []
    for i in range(len(Q)):
        fi = feats[Q[i]]
        for j in range(i + 1, len(Q)):
            fj = feats[Q[j]]
            hamming = int(np.sum(fi != fj))
            sim = 1.0 - hamming / len(fi)
            sims.append(sim)
    return float(np.mean(sims))


def objective(Q: List[str], scen, feats) -> float:
    return (
        ALPHA * cov(Q, scen)
        + BETA  * risk_total(Q, scen)
        + ETA   * comp_mean(Q, scen)
        - GAMMA * red_mean(Q, feats)
    )


# ----------------------------------------------------------------------------
# Greedy submodular selection
# ----------------------------------------------------------------------------

def greedy_select(scen: Dict[str, dict], k: int) -> List[str]:
    """Pick k scenarios greedily by marginal objective contribution."""
    all_ids = sorted(scen.keys())
    # Stable tie-breaker via a seeded shuffle of the candidate order.
    shuffled = list(all_ids)
    rng = random.Random(SEED)
    rng.shuffle(shuffled)

    # Pre-compute feature vectors over a fixed tool vocabulary.
    tool_vocab = sorted({t for s in all_ids for t in scen[s]["tools"]})
    feats = {s: _feature_vec(s, scen, tool_vocab) for s in all_ids}

    selected: List[str] = []
    selected_set: set = set()
    base = objective(selected, scen, feats)

    print(f"[greedy] initial objective = {base:.6f}")
    print(f"[greedy] tool vocab ({len(tool_vocab)}): {tool_vocab}")

    for step in range(k):
        best_sid = None
        best_gain = -float("inf")
        best_obj = base
        for sid in shuffled:
            if sid in selected_set:
                continue
            cand = selected + [sid]
            val = objective(cand, scen, feats)
            gain = val - base
            if gain > best_gain:
                best_gain = gain
                best_sid = sid
                best_obj = val
        assert best_sid is not None
        selected.append(best_sid)
        selected_set.add(best_sid)
        base = best_obj
        d = scen[best_sid]
        print(
            f"[greedy] step {step+1:2d}: +{best_sid}  "
            f"(P{d['prop']}/{d['target']}/risk={d['risk']})  "
            f"objective={base:.4f}  gain=+{best_gain:.4f}"
        )

    return selected


# ----------------------------------------------------------------------------
# RWF computation
# ----------------------------------------------------------------------------

def rwf_for_runs(runs: List[dict], scen: Dict[str, dict], subset: set | None) -> float:
    """Risk-Weighted Failure on a (possibly restricted) scenario set.

    RWF = sum_{s in V} r(s) / sum_{s in Q} r(s), where Q is the evaluated
    subset and V is the violated subset.  Matches analyze_profile.py.
    """
    num = 0
    den = 0
    seen = set()
    for r in runs:
        sid = r.get("scenario_id")
        if sid not in scen:
            continue
        if subset is not None and sid not in subset:
            continue
        if sid in seen:
            continue
        seen.add(sid)
        risk = scen[sid]["risk"]
        den += risk
        if bool(r.get("violation")):
            num += risk
    return num / den if den else 0.0


# ----------------------------------------------------------------------------
# Rank correlations (stdlib + numpy only)
# ----------------------------------------------------------------------------

def _rank(values: List[float]) -> np.ndarray:
    """Average-rank (1-indexed) handling ties."""
    arr = np.asarray(values, dtype=float)
    order = np.argsort(arr, kind="mergesort")
    ranks = np.empty_like(arr)
    i = 0
    n = len(arr)
    while i < n:
        j = i
        while j + 1 < n and arr[order[j + 1]] == arr[order[i]]:
            j += 1
        avg = 0.5 * (i + j) + 1.0  # 1-indexed average rank
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def spearman_rho(x: List[float], y: List[float]) -> float:
    rx, ry = _rank(x), _rank(y)
    rx_c = rx - rx.mean()
    ry_c = ry - ry.mean()
    denom = math.sqrt(float(np.sum(rx_c ** 2)) * float(np.sum(ry_c ** 2)))
    if denom == 0.0:
        return float("nan")
    return float(np.sum(rx_c * ry_c) / denom)


def kendall_tau(x: List[float], y: List[float]) -> float:
    """Kendall tau-b: handles ties."""
    n = len(x)
    concordant = 0
    discordant = 0
    tx = 0
    ty = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx = x[i] - x[j]
            dy = y[i] - y[j]
            if dx == 0 and dy == 0:
                tx += 1
                ty += 1
            elif dx == 0:
                tx += 1
            elif dy == 0:
                ty += 1
            elif (dx > 0 and dy > 0) or (dx < 0 and dy < 0):
                concordant += 1
            else:
                discordant += 1
    n_pairs = n * (n - 1) // 2
    denom = math.sqrt(max((n_pairs - tx), 0) * max((n_pairs - ty), 0))
    if denom == 0:
        return float("nan")
    return (concordant - discordant) / denom


# ----------------------------------------------------------------------------
# LaTeX emission
# ----------------------------------------------------------------------------

def write_latex(rows, kt, sr, k_subset, n_full):
    """rows is a list of (model_name, rwf_full, rwf_subset, rank_full, rank_subset)."""
    INC_TEX.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append("% Auto-generated by layer4_sampling.py - do not edit by hand.")
    lines.append("\\begin{table}[!htbp]")
    lines.append("\\centering")
    cap = (
        "Layer-4 sampling-objective validation. The greedy submodular "
        f"selection (\\S\\ref{{subsec:layer4}}) picks $K{{=}}{k_subset}$ of "
        f"${n_full}$ scenarios under $\\alpha\\,\\mathrm{{Cov}}+\\beta\\,"
        "\\mathrm{Risk}+\\eta\\,\\mathrm{Comp}-\\gamma\\,\\mathrm{Red}$ with "
        f"$(\\alpha,\\beta,\\eta,\\gamma)=({ALPHA},{BETA},{ETA},{GAMMA})$. "
        "$\\mathrm{RWF}_{\\text{full}}$ uses all "
        f"{n_full} scenarios; $\\mathrm{{RWF}}_{{\\text{{sub}}}}$ uses the "
        f"{k_subset} selected scenarios with the same per-model logs. "
        f"Cross-model rank correlation: Kendall-$\\tau={kt:.3f}$, "
        f"Spearman-$\\rho={sr:.3f}$."
    )
    lines.append("\\caption{" + cap + "}")
    lines.append("\\label{tab:layer4_validation}")
    lines.append("\\small")
    lines.append("\\setlength{\\tabcolsep}{4pt}")
    lines.append("\\begin{tabular}{lcccc}")
    lines.append("\\toprule")
    lines.append(
        "\\textbf{System} & $\\mathrm{RWF}_{\\text{full}}$ & "
        "$\\mathrm{RWF}_{\\text{sub}}$ & "
        "$|\\Delta\\mathrm{RWF}|$ & "
        "$|\\Delta\\mathrm{rank}|$ \\\\"
    )
    lines.append("\\midrule")
    for name, rf, rs, kf, ks in rows:
        drwf = abs(rf - rs)
        drank = abs(kf - ks)
        lines.append(
            f"{name} & {rf:.3f} & {rs:.3f} & {drwf:.3f} & {drank:.1f} \\\\"
        )
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")
    INC_TEX.write_text("\n".join(lines) + "\n")
    print(f"[tex]   wrote {INC_TEX}")


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

def main():
    print(f"[seed]  random={SEED}, numpy={SEED}")
    print(f"[load]  scanning {SCEN_DIR} ...")
    scen = load_scenarios()
    print(f"[load]  scenarios loaded: {len(scen)}")

    target_counts = Counter(s["target"] for s in scen.values())
    prop_counts = Counter(s["prop"] for s in scen.values())
    print(f"[load]  target distribution (full 100): {dict(target_counts)}")
    print(f"[load]  property distribution (full 100): {dict(prop_counts)}")

    print(f"[greedy] selecting K={K} scenarios under "
          f"(alpha,beta,eta,gamma)=({ALPHA},{BETA},{ETA},{GAMMA})")
    selected = greedy_select(scen, K)
    selected_set = set(selected)
    SUBSET_JSON.write_text(json.dumps(sorted(selected), indent=2) + "\n")
    print(f"[save]  wrote {SUBSET_JSON} ({len(selected)} scenario ids)")

    sel_target_counts = Counter(scen[s]["target"] for s in selected)
    sel_prop_counts = Counter(scen[s]["prop"] for s in selected)
    print(f"[sel]   subset target distribution: {dict(sel_target_counts)}")
    print(f"[sel]   subset property distribution: {dict(sel_prop_counts)}")

    print("[rwf]   computing RWF_full and RWF_subset for 13 systems ...")
    full_rwfs: List[float] = []
    sub_rwfs: List[float] = []
    display_names: List[str] = []
    for name, suffix in MODELS:
        runs = load_runs(suffix)
        if not runs:
            print(f"[rwf]   WARNING: no log for {name} ({suffix})")
            continue
        rf = rwf_for_runs(runs, scen, subset=None)
        rs = rwf_for_runs(runs, scen, subset=selected_set)
        print(f"[rwf]   {name:18s}  full={rf:.3f}  sub={rs:.3f}  delta={rs - rf:+.3f}")
        full_rwfs.append(rf)
        sub_rwfs.append(rs)
        display_names.append(name)

    # Rankings (lower RWF -> better -> rank 1).
    rank_full = _rank(full_rwfs)
    rank_sub = _rank(sub_rwfs)

    kt = kendall_tau(full_rwfs, sub_rwfs)
    sr = spearman_rho(full_rwfs, sub_rwfs)
    print(f"[corr]  Kendall-tau  = {kt:.4f}")
    print(f"[corr]  Spearman-rho = {sr:.4f}")

    print("[rank]  model | RWF_full | RWF_sub | |rank shift|")
    rows = []
    for name, rf, rs, kf, ks in zip(display_names, full_rwfs, sub_rwfs, rank_full, rank_sub):
        print(f"        {name:18s} {rf:.3f}  {rs:.3f}  {abs(kf - ks):.1f}")
        rows.append((name, rf, rs, kf, ks))

    write_latex(rows, kt, sr, len(selected), len(scen))
    print("[done]")


if __name__ == "__main__":
    main()
