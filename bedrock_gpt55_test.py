#!/usr/bin/env python3
"""
Minimal smoke test for OpenAI GPT-5.5 on AWS Bedrock via the bedrock-mantle
endpoint.

WHY THIS EXISTS
---------------
As of 2026, AWS Bedrock exposes OpenAI's proprietary GPT-5 series (5.4, 5.5,
Codex) and the open-weight gpt-oss models through a NEW endpoint called
"bedrock-mantle" — separate from the classic "bedrock-runtime" endpoint that
serves Anthropic / Mistral / Llama / etc. via the Converse API.

bedrock-mantle speaks OpenAI's native Responses API (not Converse), so you
use the standard `openai` Python SDK pointed at the Bedrock URL.

SETUP
-----
1) Create a Bedrock API key (this is NOT a regular IAM access key):
     AWS Console -> Amazon Bedrock -> "API keys" -> "Generate long-term API key"

2) Install the OpenAI SDK:
     pip install openai

3) Set environment variables:
     export OPENAI_API_KEY="<your-bedrock-api-key>"
     export OPENAI_BASE_URL="https://bedrock-mantle.us-east-2.api.aws/openai/v1"

   Available regions today: us-east-1 (Virginia), us-east-2 (Ohio).
   This script defaults to us-east-2 if you don't set OPENAI_BASE_URL.

4) Run:
     python bedrock_gpt55_test.py

   Optional overrides:
     MODEL="openai.gpt-5.4"  python bedrock_gpt55_test.py
     PROMPT="Hello, world."  python bedrock_gpt55_test.py

COST NOTE
---------
GPT-5.5 is OpenAI's flagship — a single call here is cheap, but per-token
pricing is meaningfully higher than gpt-oss or third-party models on Bedrock.
Check the Bedrock pricing page before batching many requests.

REFERENCES
----------
- Bedrock GPT-5.5 model card:
    https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-openai-gpt-5-5.html
- bedrock-mantle endpoint docs:
    https://docs.aws.amazon.com/bedrock/latest/userguide/bedrock-mantle.html
- OpenAI Responses API:
    https://platform.openai.com/docs/api-reference/responses
"""

import os
import sys

try:
    from openai import OpenAI
except ImportError:
    sys.exit("openai SDK not installed. Run: pip install openai")


DEFAULT_BASE_URL = "https://bedrock-mantle.us-east-2.api.aws/openai/v1"
DEFAULT_MODEL = "openai.gpt-5.5"
DEFAULT_PROMPT = "Can you explain the features of Amazon Bedrock in two sentences?"


def main() -> int:
    os.environ.setdefault("OPENAI_BASE_URL", DEFAULT_BASE_URL)

    if not os.environ.get("OPENAI_API_KEY"):
        print(
            "OPENAI_API_KEY env var is not set.\n"
            "Generate a Bedrock API key in the AWS Console -> Amazon Bedrock -> API keys.\n"
            "Then: export OPENAI_API_KEY=<your-bedrock-api-key>",
            file=sys.stderr,
        )
        return 1

    model = os.environ.get("MODEL", DEFAULT_MODEL)
    prompt = os.environ.get("PROMPT", DEFAULT_PROMPT)

    client = OpenAI()

    print(f"endpoint: {os.environ['OPENAI_BASE_URL']}")
    print(f"model:    {model}")
    print(f"prompt:   {prompt}\n")

    try:
        response = client.responses.create(model=model, input=prompt)
    except Exception as e:
        print(f"Request failed: {type(e).__name__}: {e}", file=sys.stderr)
        print(
            "\nCommon causes:\n"
            "  - OPENAI_API_KEY is an IAM key, not a Bedrock API key (these are different).\n"
            "  - The region in OPENAI_BASE_URL does not have the model enabled — try us-east-1 or us-east-2.\n"
            "  - The model id is wrong. Current ids:\n"
            "      openai.gpt-5.5, openai.gpt-5.4, openai.gpt-oss-120b, openai.gpt-oss-20b\n",
            file=sys.stderr,
        )
        return 2

    text = getattr(response, "output_text", None)
    if text is None and getattr(response, "output", None):
        try:
            text = response.output[0].content[0].text
        except (AttributeError, IndexError, TypeError):
            text = None

    print("=== Text output ===")
    print(text or "(no output_text attribute; raw response below)")

    if text is None:
        print("\n=== Raw response ===")
        print(response)

    return 0


if __name__ == "__main__":
    sys.exit(main())
