"""AI processing blocks — all use askChatGPT with specific prompts.

Apple Intelligence writing tools (adjustTextTone, generateSummary, etc.) are avoided
because they produce limited/bad results. ChatGPT with precise prompts is far better.
"""

from .schema import Block, BlockContext, ParamDef


def _resolve_prompt(ctx: BlockContext) -> str:
    """Resolve {var} references in a prompt string using input_vars."""
    prompt = ctx.params.get("prompt", "")
    for name, var in ctx.input_vars.items():
        prompt = prompt.replace(f"{{{name}}}", f"{{{var}}}")
    return prompt


def _render_chatgpt(ctx: BlockContext) -> str:
    prompt = _resolve_prompt(ctx)
    result_type = ctx.params.get("result_type", "")
    if result_type and result_type != "Automatic":
        return f'const {ctx.output_var} = askChatGPT("{prompt}", false, "{result_type}")'
    return f'const {ctx.output_var} = askChatGPT("{prompt}")'


def _render_device_llm(ctx: BlockContext) -> str:
    prompt = _resolve_prompt(ctx)
    return f'const {ctx.output_var} = askDeviceLLM("{prompt}")'


def _render_cloud_llm(ctx: BlockContext) -> str:
    prompt = _resolve_prompt(ctx)
    return f'const {ctx.output_var} = askCloudLLM("{prompt}")'


def _render_summarize(ctx: BlockContext) -> str:
    ref = ctx.input_vars.get("input", ctx.params.get("input", ""))
    return f'const {ctx.output_var} = askChatGPT("Summarize this concisely. Output only the summary, no preamble:\\n\\n{{{ref}}}")'


def _render_key_points(ctx: BlockContext) -> str:
    ref = ctx.input_vars.get("input", ctx.params.get("input", ""))
    return f'const {ctx.output_var} = askChatGPT("Extract the key points as a bullet list. Output only the bullets, no intro:\\n\\n{{{ref}}}")'


def _render_adjust_tone(ctx: BlockContext) -> str:
    ref = ctx.input_vars.get("input", ctx.params.get("input", ""))
    tone = ctx.params.get("tone", "friendly")
    return f'const {ctx.output_var} = askChatGPT("Rewrite in a {tone} tone. Output only the rewritten text, no additions:\\n\\n{{{ref}}}")'


def _render_make_list(ctx: BlockContext) -> str:
    ref = ctx.input_vars.get("input", ctx.params.get("input", ""))
    return f'const {ctx.output_var} = askChatGPT("Format as a clean numbered list. Output only the list:\\n\\n{{{ref}}}")'


def _render_make_table(ctx: BlockContext) -> str:
    ref = ctx.input_vars.get("input", ctx.params.get("input", ""))
    return f'const {ctx.output_var} = askChatGPT("Format as a text table with columns. Output only the table, no explanation:\\n\\n{{{ref}}}")'


def _render_generate_image(ctx: BlockContext) -> str:
    prompt = _resolve_prompt(ctx)
    style = ctx.params.get("style", "animation")
    return f'const {ctx.output_var} = generateImage("{prompt}", false, "{style}")'


chatgpt_analyze = Block(
    id="chatgpt_analyze",
    category="ai",
    description="Send prompt to ChatGPT for analysis",
    includes=["actions/intelligence"],
    inputs=["input"],
    outputs=["analysis"],
    params={
        "prompt": ParamDef(type="str", required=True, description="Prompt with {var} refs. Be specific about output format."),
        "result_type": ParamDef(type="enum", default="Automatic", choices=["Automatic", "Text", "Number", "Date", "Boolean", "List", "Dictionary"]),
    },
    render=_render_chatgpt,
)

device_llm = Block(
    id="device_llm",
    category="ai",
    description="On-device Apple Intelligence LLM (private, no network)",
    includes=["actions/intelligence"],
    inputs=["input"],
    outputs=["result"],
    params={"prompt": ParamDef(type="str", required=True)},
    render=_render_device_llm,
)

cloud_llm = Block(
    id="cloud_llm",
    category="ai",
    description="Private Cloud Compute LLM (Apple servers)",
    includes=["actions/intelligence"],
    inputs=["input"],
    outputs=["result"],
    params={"prompt": ParamDef(type="str", required=True)},
    render=_render_cloud_llm,
)

summarize = Block(
    id="summarize",
    category="ai",
    description="Summarize text via ChatGPT",
    includes=["actions/intelligence"],
    inputs=["input"],
    outputs=["summary"],
    params={"input": ParamDef(type="str", required=True)},
    render=_render_summarize,
)

key_points = Block(
    id="key_points",
    category="ai",
    description="Extract key points as bullet list via ChatGPT",
    includes=["actions/intelligence"],
    inputs=["input"],
    outputs=["points"],
    params={"input": ParamDef(type="str", required=True)},
    render=_render_key_points,
)

adjust_tone = Block(
    id="adjust_tone",
    category="ai",
    description="Rewrite text in a specific tone via ChatGPT",
    includes=["actions/intelligence"],
    inputs=["input"],
    outputs=["adjusted"],
    params={
        "input": ParamDef(type="str", required=True),
        "tone": ParamDef(type="enum", default="friendly", choices=["friendly", "professional", "concise"]),
    },
    render=_render_adjust_tone,
)

make_list = Block(
    id="make_list",
    category="ai",
    description="Format text as numbered list via ChatGPT",
    includes=["actions/intelligence"],
    inputs=["input"],
    outputs=["list"],
    params={"input": ParamDef(type="str", required=True)},
    render=_render_make_list,
)

make_table = Block(
    id="make_table",
    category="ai",
    description="Format text as table via ChatGPT",
    includes=["actions/intelligence"],
    inputs=["input"],
    outputs=["table"],
    params={"input": ParamDef(type="str", required=True)},
    render=_render_make_table,
)

generate_image = Block(
    id="generate_image",
    category="ai",
    description="Generate image with Image Playground",
    includes=["actions/intelligence"],
    outputs=["image"],
    params={
        "prompt": ParamDef(type="str", required=True),
        "style": ParamDef(type="enum", default="animation", choices=["animation", "illustration", "sketch", "chatgpt", "chatgpt_anime", "chatgpt_watercolor"]),
    },
    render=_render_generate_image,
)

ALL = [
    chatgpt_analyze, device_llm, cloud_llm, summarize, key_points,
    adjust_tone, make_list, make_table, generate_image,
]
