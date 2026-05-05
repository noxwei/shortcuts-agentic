"""Integration blocks — Drafts, sub-shortcuts, dictionary extraction."""

from .schema import Block, BlockContext, ParamDef


def _render_drafts_save(ctx: BlockContext) -> str:
    ref = ctx.input_vars.get("input", ctx.params.get("input", ""))
    tags = ctx.params.get("tags", [])
    tag_str = ", ".join(f'"{t}"' for t in tags)
    return (
        f'rawAction("com.agiletortoise.Drafts5.CaptureIntent", {{\n'
        f'\t"AppIntentDescriptor": "",\n'
        f'\t"ShowWhenRun": false,\n'
        f'\t"content": "{{{ref}}}",\n'
        f'\t"tags": [{tag_str}]\n'
        f"}})"
    )


def _render_run_shortcut(ctx: BlockContext) -> str:
    name = ctx.params["shortcut_name"]
    input_ref = ctx.params.get("input", "")
    if input_ref:
        ref = ctx.input_vars.get("input", input_ref)
        return f'const {ctx.output_var} = run("{name}", {ref})'
    return f'const {ctx.output_var} = run("{name}")'


def _render_dict_extract(ctx: BlockContext) -> str:
    ref = ctx.input_vars.get("input", ctx.params.get("input", ""))
    keys = ctx.params.get("keys", [])
    v = ctx.output_var
    lines = [f"const {v}_dict = getDictionary({ref})"]
    for key in keys:
        safe = key.lower().replace(" ", "_").replace("-", "_")
        lines.append(f'const {v}_{safe} = getValue({v}_dict, "{key}")')
    return "\n".join(lines)


drafts_save = Block(
    id="drafts_save",
    category="integration",
    description="Save text to Drafts app",
    includes=[],
    inputs=["input"],
    params={
        "input": ParamDef(type="str", required=True, description="Block ref to save"),
        "tags": ParamDef(type="list[str]", default=["Shortcuts_automation"]),
    },
    render=_render_drafts_save,
)

run_shortcut = Block(
    id="run_shortcut",
    category="integration",
    description="Run another iOS Shortcut by name",
    includes=["actions/shortcuts"],
    outputs=["result"],
    params={
        "shortcut_name": ParamDef(type="str", required=True),
        "input": ParamDef(type="str", description="Block ref to pass as input"),
    },
    render=_render_run_shortcut,
)

dict_extract = Block(
    id="dict_extract",
    category="integration",
    description="Parse JSON dictionary and extract keys",
    includes=["actions/scripting"],
    inputs=["input"],
    outputs=["dict"],
    params={
        "input": ParamDef(type="str", required=True, description="Block ref containing JSON"),
        "keys": ParamDef(type="list[str]", required=True, description="Keys to extract"),
    },
    render=_render_dict_extract,
)

ALL = [drafts_save, run_shortcut, dict_extract]
