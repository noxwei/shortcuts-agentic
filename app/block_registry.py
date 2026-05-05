"""Block registry — loads all blocks and generates the Gemma catalog prompt."""

from __future__ import annotations

from blocks import ai, data, device, flow, input as input_blocks, integration, output
from blocks.schema import Block

_REGISTRY: dict[str, Block] = {}


def _register_module(blocks: list[Block]) -> None:
    for b in blocks:
        if b.id in _REGISTRY:
            raise ValueError(f"Duplicate block ID: {b.id}")
        _REGISTRY[b.id] = b


def _ensure_loaded() -> None:
    if _REGISTRY:
        return
    _register_module(input_blocks.ALL)
    _register_module(output.ALL)
    _register_module(ai.ALL)
    _register_module(data.ALL)
    _register_module(device.ALL)
    _register_module(integration.ALL)
    _register_module(flow.ALL)


def get_block(block_id: str) -> Block | None:
    _ensure_loaded()
    return _REGISTRY.get(block_id)


def all_blocks() -> dict[str, Block]:
    _ensure_loaded()
    return dict(_REGISTRY)


def generate_catalog() -> str:
    """Generate the block catalog for the Gemma system prompt."""
    _ensure_loaded()

    by_category: dict[str, list[Block]] = {}
    for b in _REGISTRY.values():
        by_category.setdefault(b.category, []).append(b)

    category_order = ["input", "data", "ai", "output", "device", "integration", "flow"]
    lines: list[str] = []

    for cat in category_order:
        blocks = by_category.get(cat, [])
        if not blocks:
            continue
        lines.append(f"### {cat.title()}")
        for b in blocks:
            lines.append(b.catalog_entry())
        lines.append("")

    return "\n".join(lines)


_SYSTEM_TEMPLATE = """You are a Shortcut recipe builder. Output ONLY a valid JSON recipe. No explanation, no markdown fences, no thinking tags.

IMPORTANT: Use single curly braces for JSON. Use single curly braces for variable references in prompts like {weather}. Do NOT double-escape braces.

## Available Blocks

__CATALOG__

## Recipe Format

Use this exact JSON structure:
{"name": "Short Name", "icon": "cloud", "color": "blue", "blocks": [{"block": "block_id", "as": "variable_name", "params": {...}}]}

## Rules
- "as" names the block's output variable for later reference
- Use {variable_name} in prompt strings to reference earlier block outputs
- Params with "input" refer to a previous block's "as" name
- Every recipe MUST have at least 5 blocks minimum
- Every recipe needs at least one output block (show_result, speak_result, notify, etc.)
- Use multiple chatgpt_analyze calls for multi-step analysis
- Combine data blocks with AI blocks for richer shortcuts

## Example 1

User: "morning weather briefing"
{"name": "Morning Briefing", "icon": "cloud", "color": "blue", "blocks": [{"block": "weather_current", "as": "weather", "params": {"details": ["Temperature", "Condition", "Humidity", "Wind Speed"]}}, {"block": "device_info", "as": "dev", "params": {"details": ["battery"]}}, {"block": "chatgpt_analyze", "as": "briefing", "params": {"prompt": "Morning briefing. Weather: {weather} Battery: {dev_battery}. Be concise, conversational."}}, {"block": "speak_result", "params": {"input": "briefing"}}, {"block": "clipboard_copy", "params": {"input": "briefing"}}, {"block": "notify", "params": {"body": "Briefing ready", "title": "Morning"}}]}

## Example 2

User: "identify a song and analyze it"
{"name": "Song Analyzer", "icon": "musicNote", "color": "pink", "blocks": [{"block": "shazam", "as": "song", "params": {"details": ["Title", "Artist", "Lyrics Snippet", "Apple Music URL"]}}, {"block": "chatgpt_analyze", "as": "analysis", "params": {"prompt": "Analyze: {song_title} by {song_artist}. Genre, mood, BPM estimate, similar artists, fun facts. Only output the analysis."}}, {"block": "chatgpt_analyze", "as": "summary", "params": {"prompt": "Summarize in one sentence: {analysis}"}}, {"block": "speak_result", "params": {"input": "summary"}}, {"block": "show_result", "params": {"input": "analysis"}}, {"block": "notify", "params": {"body": "Song analyzed", "title": "Shazam"}}]}
"""


def get_system_prompt() -> str:
    """Return the complete Gemma system prompt with block catalog."""
    catalog = generate_catalog()
    return _SYSTEM_TEMPLATE.replace("__CATALOG__", catalog)
