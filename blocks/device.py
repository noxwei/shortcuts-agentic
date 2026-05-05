"""Device control blocks — focus, volume, brightness, appearance."""

from .schema import Block, BlockContext, ParamDef


def _render_set_focus(ctx: BlockContext) -> str:
    mode = ctx.params.get("mode", "Do Not Disturb")
    return f'setFocusMode("{mode}")'


def _render_set_volume(ctx: BlockContext) -> str:
    level = ctx.params.get("level", 0.5)
    return f"setVolume({level})"


def _render_set_brightness(ctx: BlockContext) -> str:
    level = ctx.params.get("level", 0.5)
    return f"setBrightness({level})"


def _render_toggle_appearance(ctx: BlockContext) -> str:
    mode = ctx.params.get("mode", "toggle")
    if mode == "dark":
        return "darkMode()"
    if mode == "light":
        return "lightMode()"
    return "toggleAppearance()"


def _render_screenshot(ctx: BlockContext) -> str:
    return f"const {ctx.output_var} = takeScreenshot()"


set_focus = Block(
    id="set_focus",
    category="device",
    description="Set Focus Mode",
    includes=["actions/settings"],
    params={"mode": ParamDef(type="enum", default="Do Not Disturb", choices=["Do Not Disturb", "Personal", "Work", "Sleep", "Driving"])},
    render=_render_set_focus,
)

set_volume = Block(
    id="set_volume",
    category="device",
    description="Set device volume",
    includes=["actions/settings"],
    params={"level": ParamDef(type="float", default=0.5, description="0.0 to 1.0")},
    render=_render_set_volume,
)

set_brightness = Block(
    id="set_brightness",
    category="device",
    description="Set screen brightness",
    includes=["actions/settings"],
    params={"level": ParamDef(type="float", default=0.5, description="0.0 to 1.0")},
    render=_render_set_brightness,
)

toggle_appearance = Block(
    id="toggle_appearance",
    category="device",
    description="Toggle or set dark/light mode",
    includes=["actions/settings"],
    params={"mode": ParamDef(type="enum", default="toggle", choices=["toggle", "dark", "light"])},
    render=_render_toggle_appearance,
)

take_screenshot = Block(
    id="take_screenshot",
    category="device",
    description="Take a screenshot",
    includes=["actions/media"],
    outputs=["screenshot"],
    render=_render_screenshot,
)

ALL = [set_focus, set_volume, set_brightness, toggle_appearance, take_screenshot]
