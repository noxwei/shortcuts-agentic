"""Output blocks — display, speak, notify, or export results."""

from .schema import Block, BlockContext, ParamDef


def _render_show(ctx: BlockContext) -> str:
    text = ctx.params.get("text", "")
    input_var = ctx.params.get("input", "")
    if input_var:
        ref = ctx.input_vars.get("input", input_var)
        return f"show({ref})"
    if text:
        return f'show("{text}")'
    # Fallback: show the implicit previous output
    ref = ctx.input_vars.get("default", "result")
    return f"show({ref})"


def _render_speak(ctx: BlockContext) -> str:
    input_var = ctx.params.get("input", "")
    ref = ctx.input_vars.get("input", input_var) or ctx.input_vars.get("default", "result")
    return f"speak({ref})"


def _render_notify(ctx: BlockContext) -> str:
    body = ctx.params.get("body", "Done")
    title = ctx.params.get("title", "")
    if title:
        return f'showNotification("{body}", "{title}")'
    return f'showNotification("{body}")'


def _render_clipboard_copy(ctx: BlockContext) -> str:
    input_var = ctx.params.get("input", "")
    ref = ctx.input_vars.get("input", input_var) or ctx.input_vars.get("default", "result")
    return f"setClipboard({ref})"


def _render_confirm(ctx: BlockContext) -> str:
    text = ctx.params.get("text", "")
    input_var = ctx.params.get("input", "")
    if input_var:
        ref = ctx.input_vars.get("input", input_var)
        return f"confirm({ref})"
    return f'confirm("{text}")'


def _render_open_url(ctx: BlockContext) -> str:
    url = ctx.params.get("url", "")
    input_var = ctx.params.get("input", "")
    if input_var:
        ref = ctx.input_vars.get("input", input_var)
        return f"openURL({ref})"
    return f'openURL("{url}")'


show_result = Block(
    id="show_result",
    category="output",
    description="Show alert dialog with text",
    includes=[],
    inputs=["input"],
    params={
        "input": ParamDef(type="str", description="Block ref to display"),
        "text": ParamDef(type="str", description="Static text to display"),
    },
    render=_render_show,
)

speak_result = Block(
    id="speak_result",
    category="output",
    description="Text-to-speech output",
    includes=["actions/text"],
    inputs=["input"],
    params={
        "input": ParamDef(type="str", description="Block ref to speak"),
        "language": ParamDef(type="str", default="en-US"),
    },
    render=_render_speak,
)

notify = Block(
    id="notify",
    category="output",
    description="Push notification",
    includes=[],
    params={
        "body": ParamDef(type="str", default="Done", required=True),
        "title": ParamDef(type="str"),
    },
    render=_render_notify,
)

clipboard_copy = Block(
    id="clipboard_copy",
    category="output",
    description="Copy to clipboard",
    includes=["actions/sharing"],
    inputs=["input"],
    params={"input": ParamDef(type="str", description="Block ref to copy")},
    render=_render_clipboard_copy,
)

confirm_action = Block(
    id="confirm_action",
    category="output",
    description="Show confirm/cancel dialog",
    includes=[],
    inputs=["input"],
    params={
        "input": ParamDef(type="str", description="Block ref to show"),
        "text": ParamDef(type="str", description="Static text"),
    },
    render=_render_confirm,
)

open_url = Block(
    id="open_url",
    category="output",
    description="Open a URL",
    includes=["actions/web"],
    inputs=["input"],
    params={
        "url": ParamDef(type="str", description="Static URL to open"),
        "input": ParamDef(type="str", description="Block ref containing URL"),
    },
    render=_render_open_url,
)

ALL = [show_result, speak_result, notify, clipboard_copy, confirm_action, open_url]
