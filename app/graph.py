"""Agent graph — router + worker state machine with conversation persistence.

Covers kanban items A-1 (state machine with SQLite persistence),
A-2 (conversation_id thread keying), A-3 (router + worker nodes),
A-7 (tool execution loop), A-8 (prompt injection defenses).
"""

import json
import structlog
import re

from app.budget import check_budget, log_usage
from app.db import load_conversation, save_conversation
from app.inference import chat
from app.safety import sanitize_input, sanitize_output, validate_tool_args
from app.tools import MAX_TOOL_ITERATIONS, TOOL_SCHEMAS, TOOLS

logger = structlog.get_logger()


class BudgetExceededError(Exception):
    """Raised when the daily character budget is exhausted."""

_THINKING_RE = re.compile(r"<\|channel>thought.*?<channel\|>", re.DOTALL)
def _strip_thinking(text: str) -> str:
    """Remove Gemma thinking tokens from model output."""
    return _THINKING_RE.sub("", text).strip()


def _extract_tool_call(text: str) -> dict | None:
    """Try to extract a JSON tool call from model output."""
    # Find all { positions and try parsing JSON starting from each
    for i, ch in enumerate(text):
        if ch == "{":
            # Try to find matching brace by parsing
            depth = 0
            for j in range(i, len(text)):
                if text[j] == "{":
                    depth += 1
                elif text[j] == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            obj = json.loads(text[i : j + 1])
                            if isinstance(obj, dict) and "tool" in obj:
                                return obj
                        except json.JSONDecodeError:
                            pass
                        break
    return None


# Intent types the router can classify into.
INTENTS = ("question", "task", "search", "conversation")

# Max conversation turns kept (user+assistant pairs count as 2 messages each).
MAX_HISTORY = 10

_ROUTER_SYSTEM = (
    "Classify the user's message into exactly one intent: "
    "question, task, search, or conversation. "
    "Reply with ONLY the single word."
)

_TOOL_SCHEMA_TEXT = json.dumps(list(TOOL_SCHEMAS.values()), indent=2)

_WORKER_SYSTEM: dict[str, str] = {
    "question": (
        "You are a helpful assistant. Answer the user's question concisely and accurately."
    ),
    "task": (
        "You are a task execution assistant with access to tools.\n\n"
        "Available tools (call by emitting a JSON object on its own line):\n"
        f"{_TOOL_SCHEMA_TEXT}\n\n"
        "To use a tool, reply with ONLY a JSON object like: "
        '{"tool": "shell", "args": {"command": "ls -la"}}\n'
        "After receiving a tool result, analyze it and either call another tool "
        "or provide your final answer as plain text.\n"
        "Do NOT wrap tool calls in markdown code blocks."
    ),
    "search": (
        "You are a search assistant. Provide relevant information about the "
        "user's query in a well-organized format."
    ),
    "conversation": (
        "You are a friendly conversational assistant. Be natural and helpful."
    ),
}



async def _route(user_text: str) -> tuple[str, float]:
    """Classify user_text into an intent string. Fast, ~100 tokens."""
    raw = await chat(
        [
            {"role": "system", "content": _ROUTER_SYSTEM},
            {"role": "user", "content": user_text},
        ],
        max_tokens=10,
    )
    intent = _strip_thinking(raw).strip().lower().rstrip(".")
    if intent not in INTENTS:
        return "conversation", 0.5  # fallback
    return intent, 1.0


async def _work(intent: str, messages: list[dict]) -> str:
    """Generate a response given the intent and conversation history."""
    system_prompt = _WORKER_SYSTEM.get(intent, _WORKER_SYSTEM["conversation"])
    full_messages = [{"role": "system", "content": system_prompt}] + messages
    raw = await chat(full_messages, max_tokens=500)
    return _strip_thinking(raw)


async def _work_with_tools(intent: str, messages: list[dict]) -> str:
    """Worker with tool execution loop (max MAX_TOOL_ITERATIONS iterations)."""
    if intent != "task":
        return await _work(intent, messages)

    working_messages = list(messages)

    for iteration in range(MAX_TOOL_ITERATIONS):
        response = await _work(intent, working_messages)
        tool_call = _extract_tool_call(response)

        if tool_call is None:
            # No tool call — this is the final answer.
            return response

        tool_name = tool_call.get("tool", "")
        tool_args = tool_call.get("args", {})
        if not isinstance(tool_args, dict):
            tool_args = {}

        logger.info("tool_call", iteration=iteration + 1, max=MAX_TOOL_ITERATIONS, tool=tool_name, args=tool_args)

        # Validate tool args (A-8).
        ok, reason = validate_tool_args(tool_name, tool_args)
        if not ok:
            tool_result = f"TOOL ERROR: {reason}"
        elif tool_name not in TOOLS:
            tool_result = f"TOOL ERROR: unknown tool '{tool_name}'"
        else:
            tool_fn = TOOLS[tool_name]
            tool_result = await tool_fn(tool_args)

        # Append the assistant's tool call and the tool result.
        working_messages.append({"role": "assistant", "content": response})
        working_messages.append({"role": "user", "content": f"Tool result:\n{tool_result}"})

    # Hit iteration limit — do one final generation without tools.
    response = await _work(intent, working_messages)
    return response


async def run_graph(conversation_id: str, user_text: str) -> dict:
    """Main entry point. Load state -> sanitize -> route -> work -> sanitize -> save -> return."""
    # 0. Budget check (X-3)
    within_budget, _ = await check_budget()
    if not within_budget:
        raise BudgetExceededError("Daily inference budget exceeded. Try again tomorrow.")

    # 1. Load conversation history
    messages = await load_conversation(conversation_id)

    # 2. Sanitize input (A-8)
    clean_text = sanitize_input(user_text)

    # 3. Router: classify intent
    intent, confidence = await _route(clean_text)

    # 4. Append user message
    messages.append({"role": "user", "content": clean_text})

    # 5. Worker: generate response with history (and tools for "task" intent)
    response = await _work_with_tools(intent, messages)

    # 6. Sanitize output (A-8)
    response = sanitize_output(response)

    # 7. Append assistant message
    messages.append({"role": "assistant", "content": response})

    # 8. Trim to last MAX_HISTORY messages
    if len(messages) > MAX_HISTORY:
        messages = messages[-MAX_HISTORY:]

    # 9. Persist
    await save_conversation(conversation_id, messages)

    # 10. Log usage (X-3)
    await log_usage(user_text, response)

    return {"response": response, "intent": intent, "confidence": confidence}
