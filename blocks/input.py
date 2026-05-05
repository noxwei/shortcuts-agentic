"""Input blocks — capture data from the user or device."""

from .schema import Block, BlockContext, ParamDef


def _render_voice(ctx: BlockContext) -> str:
    # Cherri requires full locale codes like "en_US", not "en"
    # Safest to just call listen() with no args — defaults work fine
    return f"const {ctx.output_var} = listen()"


def _render_text_prompt(ctx: BlockContext) -> str:
    prompt_text = ctx.params.get("prompt_text", "Enter value")
    return f'const {ctx.output_var} = prompt("{prompt_text}")'


def _render_camera(ctx: BlockContext) -> str:
    mode = ctx.params.get("mode", "photo")
    if mode == "video":
        return f"const {ctx.output_var} = takeVideo()"
    count = ctx.params.get("count", 1)
    return f"const {ctx.output_var} = takePhoto({count})"


def _render_clipboard(ctx: BlockContext) -> str:
    return f"const {ctx.output_var} = getClipboard()"


voice_input = Block(
    id="voice_input",
    category="input",
    description="Capture speech-to-text via dictation",
    includes=["actions/text"],
    outputs=["text"],
    params={"language": ParamDef(type="str", description="Language code, e.g. en_US")},
    render=_render_voice,
)

text_prompt = Block(
    id="text_prompt",
    category="input",
    description="Show a text input dialog",
    includes=[],
    outputs=["text"],
    params={"prompt_text": ParamDef(type="str", default="Enter value")},
    render=_render_text_prompt,
)

camera_input = Block(
    id="camera_input",
    category="input",
    description="Take a photo or video",
    includes=["actions/media"],
    outputs=["media"],
    params={
        "mode": ParamDef(type="enum", default="photo", choices=["photo", "video"]),
        "count": ParamDef(type="int", default=1),
    },
    render=_render_camera,
)

clipboard_input = Block(
    id="clipboard_input",
    category="input",
    description="Read current clipboard contents",
    includes=["actions/sharing"],
    outputs=["text"],
    render=_render_clipboard,
)

ALL = [voice_input, text_prompt, camera_input, clipboard_input]
