"""
Bedrock adapter exposing an OpenAI-compatible chat-completions interface.

Used by runner.py so that the same agent loop can run against Bedrock models
without rewriting the orchestration logic. Translates between:
  - OpenAI tool spec (TOOL_SPECS in tools.py)              <-> Bedrock toolConfig
  - OpenAI chat messages (system/user/assistant/tool)      <-> Bedrock messages
  - OpenAI tool_calls in assistant message                 <-> Bedrock toolUse blocks
"""
import json
import uuid
from dataclasses import dataclass
from typing import Any, List, Optional

import boto3


# ---------- response data classes mirroring the openai SDK shape ----------

@dataclass
class _FuncCall:
    name: str
    arguments: str  # JSON-encoded string, matching openai


@dataclass
class _ToolCall:
    id: str
    type: str
    function: _FuncCall


@dataclass
class _Message:
    role: str
    content: Optional[str]
    tool_calls: Optional[List[_ToolCall]]

    # When the message is appended back to history we need an openai-shaped
    # dict; runner.py does `messages.append(msg)` where msg is the SDK object
    # (the openai SDK objects are dict-coercible). We mimic that with a
    # to_history() method, and override __iter__ /dict() so json.dumps works.
    def to_history(self) -> dict:
        d: dict = {"role": self.role, "content": self.content or ""}
        if self.tool_calls:
            d["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in self.tool_calls
            ]
        return d


@dataclass
class _Choice:
    message: _Message
    finish_reason: str


@dataclass
class _Response:
    choices: List[_Choice]


# ---------- main client ----------

class BedrockChatClient:
    """OpenAI-style facade over a Bedrock Converse runtime."""

    def __init__(self, profile_name: str = "haaf-bedrock", region: str = "us-east-1"):
        session = boto3.Session(profile_name=profile_name)
        self.runtime = session.client("bedrock-runtime", region_name=region)
        self.chat = _ChatNamespace(self)


class _ChatNamespace:
    def __init__(self, parent: BedrockChatClient):
        self._parent = parent
        self.completions = _CompletionsNamespace(parent)


class _CompletionsNamespace:
    def __init__(self, parent: BedrockChatClient):
        self._parent = parent

    def create(
        self,
        *,
        model: str,
        messages: list,
        tools: Optional[list] = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        extra_body: Optional[dict] = None,  # accepted+ignored for parity
        **_: Any,
    ) -> _Response:
        bedrock_messages, system_blocks = _translate_messages(messages)
        tool_config = _translate_tools(tools) if tools else None

        kwargs = dict(
            modelId=model,
            messages=bedrock_messages,
            inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
        )
        if system_blocks:
            kwargs["system"] = system_blocks
        if tool_config:
            kwargs["toolConfig"] = tool_config

        resp = self._parent.runtime.converse(**kwargs)

        out_msg = resp["output"]["message"]
        text_parts: list = []
        tool_calls: list = []
        for block in out_msg.get("content", []):
            if "text" in block:
                text_parts.append(block["text"])
            elif "toolUse" in block:
                tu = block["toolUse"]
                tool_calls.append(
                    _ToolCall(
                        id=tu["toolUseId"],
                        type="function",
                        function=_FuncCall(
                            name=tu["name"],
                            arguments=json.dumps(tu.get("input", {})),
                        ),
                    )
                )

        msg = _Message(
            role="assistant",
            content=("\n".join(text_parts) if text_parts else None),
            tool_calls=(tool_calls or None),
        )
        choice = _Choice(message=msg, finish_reason=resp.get("stopReason", "stop"))
        return _Response(choices=[choice])


# ---------- translators ----------

def _translate_tools(openai_tools: list) -> dict:
    """OpenAI tools list -> Bedrock toolConfig."""
    specs = []
    for t in openai_tools:
        fn = t.get("function", t)
        specs.append({
            "toolSpec": {
                "name": fn["name"],
                "description": fn.get("description", ""),
                "inputSchema": {"json": fn.get("parameters", {"type": "object", "properties": {}})},
            }
        })
    return {"tools": specs}


def _coerce_history_msg(m: Any) -> dict:
    """Accept either a dict or our _Message (from a previous turn) and return a plain dict."""
    if isinstance(m, _Message):
        return m.to_history()
    if hasattr(m, "to_history"):
        return m.to_history()
    return dict(m)


def _translate_messages(openai_messages: list) -> tuple:
    """
    Returns (bedrock_messages, system_blocks).
    Bedrock keeps system separate; tool_calls become toolUse blocks; tool
    role messages become user-role toolResult blocks (Bedrock convention).
    Consecutive same-role messages are merged.
    """
    system_blocks: list = []
    out: list = []
    pending: Optional[dict] = None  # current message we are accumulating

    def flush():
        nonlocal pending
        if pending is not None:
            out.append(pending)
            pending = None

    def push(role: str, blocks: list):
        nonlocal pending
        if pending is not None and pending["role"] == role:
            pending["content"].extend(blocks)
        else:
            flush()
            pending = {"role": role, "content": list(blocks)}

    for raw in openai_messages:
        m = _coerce_history_msg(raw)
        role = m.get("role")

        if role == "system":
            content = m.get("content", "")
            if content:
                system_blocks.append({"text": content})
            continue

        if role == "tool":
            tc_id = m.get("tool_call_id")
            content = m.get("content", "")
            push("user", [{
                "toolResult": {
                    "toolUseId": tc_id,
                    "content": [{"text": content if isinstance(content, str) else json.dumps(content)}],
                }
            }])
            continue

        if role == "assistant":
            blocks = []
            text = m.get("content")
            if text:
                blocks.append({"text": text})
            for tc in m.get("tool_calls", []) or []:
                fn = tc["function"]
                try:
                    args = json.loads(fn["arguments"]) if isinstance(fn["arguments"], str) else (fn["arguments"] or {})
                except json.JSONDecodeError:
                    args = {}
                blocks.append({
                    "toolUse": {
                        "toolUseId": tc["id"],
                        "name": fn["name"],
                        "input": args,
                    }
                })
            if not blocks:
                blocks = [{"text": ""}]
            push("assistant", blocks)
            continue

        if role == "user":
            content = m.get("content", "")
            push("user", [{"text": content if isinstance(content, str) else json.dumps(content)}])
            continue

    flush()
    return out, system_blocks
