#!/usr/bin/env bash
# Run all 13 Bedrock models x 2 versions in parallel.
# Each process gets its own sandbox directory under /tmp/haaf_sandbox_*/ so
# they don't race on shared sandbox files.
set -u
cd "$(dirname "$0")"

# 13 model entries; control + treated = 26 parallel processes.
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

mkdir -p logs
pids=()

ts() { date +"%H:%M:%S"; }

for entry in "${models[@]}"; do
  model="${entry%|*}"
  suffix="${entry#*|}"
  for version in control treated; do
    sandbox="/tmp/haaf_sandbox_${suffix}_${version}"
    rm -rf "$sandbox" && mkdir -p "$sandbox"
    log="logs/run_${suffix}_${version}.log"
    rm -f "logs/${version}_${suffix}_runs.jsonl" "logs/${version}_${suffix}_trajectories.jsonl"
    (
      echo "[$(ts)] start $suffix/$version"
      python3 runner.py \
        --version "$version" \
        --backend bedrock \
        --model "$model" \
        --log-suffix "$suffix" \
        --sandbox-dir "$sandbox" \
        > "$log" 2>&1
      echo "[$(ts)] done  $suffix/$version (exit=$?)"
    ) &
    pids+=($!)
  done
done

echo "[$(ts)] launched ${#pids[@]} parallel processes; waiting..."
wait
echo "[$(ts)] ALL DONE"
