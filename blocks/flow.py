"""Flow control blocks — if/else, repeat. These are special: they wrap other blocks."""

from .schema import Block, BlockContext, ParamDef


def _render_if_else(ctx: BlockContext) -> str:
    var = ctx.params.get("condition_var", "")
    ref = ctx.input_vars.get(var, var)
    op = ctx.params.get("operator", "equals")
    val = ctx.params.get("value", "")

    op_map = {"equals": "==", "not_equals": "!=", "less_than": "<", "greater_than": ">", "contains": "contains"}
    op_str = op_map.get(op, "==")

    # then/else bodies are rendered by the composer, injected via params
    then_code = ctx.params.get("_then_code", "    // then")
    else_code = ctx.params.get("_else_code", "")

    lines = [f'if {ref} {op_str} "{val}" {{', then_code, "}"]
    if else_code:
        lines.append(" else {")
        lines.append(else_code)
        lines.append("}")
    return "\n".join(lines)


def _render_repeat(ctx: BlockContext) -> str:
    count = ctx.params.get("count", 3)
    index_var = ctx.params.get("index_var", "i")
    body_code = ctx.params.get("_body_code", "    // body")
    return f"repeat {index_var} for {count} {{\n{body_code}\n}}"


if_else = Block(
    id="if_else",
    category="flow",
    description="Conditional: run blocks based on a condition",
    includes=[],
    params={
        "condition_var": ParamDef(type="str", required=True, description="Variable to test"),
        "operator": ParamDef(type="enum", default="equals", choices=["equals", "not_equals", "less_than", "greater_than", "contains"]),
        "value": ParamDef(type="str", required=True, description="Value to compare against"),
    },
    render=_render_if_else,
)

repeat = Block(
    id="repeat",
    category="flow",
    description="Repeat blocks N times",
    includes=[],
    params={
        "count": ParamDef(type="int", default=3),
        "index_var": ParamDef(type="str", default="i"),
    },
    render=_render_repeat,
)

ALL = [if_else, repeat]
