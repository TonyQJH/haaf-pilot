#!/usr/bin/env bash
# Run treated-version of all 13 Bedrock models (apply tool-output firewall +
# confirmation gate via the Treated system prompt + runner-level high-risk
# blocking). Each model writes to logs/treated_<suffix>_{runs,trajectories}.jsonl.
set -u
cd "$(dirname "$0")"
ts() { date +"%H:%M:%S"; }

models=(
  "us.meta.llama3-1-8b-instruct-v1:0|llama31_8b"
  "us.meta.llama3-1-70b-instruct-v1:0|llama31_70b"
  "mistral.mistral-large-2402-v1:0|mistral_large_2402"
  "mistral.mistral-large-3-675b-instruct|mistral_large_3"
  "moonshot.kimi-k2-thinking|kimi_k2_thinking"
  "moonshotai.kimi-k2.5|kimi_k25"
  "zai.glm-4.7|glm_47"
  "zai.glm-5|glm_5"
  "qwen.qwen3-32b-v1:0|qwen3_32b"
  "qwen.qwen3-next-80b-a3b|qwen3_next_80b"
  "openai.gpt-oss-20b-1:0|gpt_oss_20b"
  "openai.gpt-oss-120b-1:0|gpt_oss_120b"
  "deepseek.v3.2|deepseek_v32"
)

for entry in "${models[@]}"; do
  model="${entry%|*}"
  suffix="${entry#*|}"
  echo "[$(ts)] ===== Starting TREATED $model (suffix=$suffix) ====="
  rm -f "logs/treated_${suffix}_runs.jsonl" "logs/treated_${suffix}_trajectories.jsonl"
  python3 runner.py \
    --version treated \
    --backend bedrock \
    --model "$model" \
    --log-suffix "$suffix" 2>&1 | tail -50
  status=$?
  echo "[$(ts)] ===== Finished TREATED $model (exit=$status) ====="
done

echo "[$(ts)] ALL TREATED DONE"
