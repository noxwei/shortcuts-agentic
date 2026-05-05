"""Data blocks — fetch from APIs, sensors, weather, location, Shazam."""

from .schema import Block, BlockContext, ParamDef

_WEATHER_DETAILS = [
    "Temperature", "Feels Like", "Condition", "Wind Speed",
    "Humidity", "UV Index", "Sunrise Time", "Sunset Time", "High", "Low",
]


def _render_api_get(ctx: BlockContext) -> str:
    url = ctx.params["url"]
    headers = ctx.params.get("headers", {})
    if headers:
        h = ", ".join(f'"{k}": "{v}"' for k, v in headers.items())
        return f'const {ctx.output_var} = downloadURL("{url}", {{{h}}})'
    return f'const {ctx.output_var} = downloadURL("{url}")'


def _render_api_post(ctx: BlockContext) -> str:
    url = ctx.params["url"]
    body = ctx.params.get("body", {})
    headers = ctx.params.get("headers", {})
    b = ", ".join(f'"{k}": "{v}"' for k, v in body.items()) if body else ""
    h = ", ".join(f'"{k}": "{v}"' for k, v in headers.items()) if headers else ""
    return f'const {ctx.output_var} = jsonRequest("{url}", "POST", {{{b}}}, {{{h}}})'


def _render_weather_current(ctx: BlockContext) -> str:
    v = ctx.output_var
    details = ctx.params.get("details", ["Temperature", "Condition"])
    lines = [f"const {v} = getCurrentWeather()"]
    for d in details:
        safe = d.lower().replace(" ", "_")
        lines.append(f'const {v}_{safe} = getWeatherDetail({v}, "{d}")')
    return "\n".join(lines)


def _render_weather_forecast(ctx: BlockContext) -> str:
    ftype = ctx.params.get("type", "Daily")
    return f'const {ctx.output_var} = getWeatherForecast("{ftype}")'


def _render_location(ctx: BlockContext) -> str:
    v = ctx.output_var
    details = ctx.params.get("details", ["City", "State"])
    lines = [f"const {v} = currentLocation()"]
    for d in details:
        safe = d.lower().replace(" ", "_")
        lines.append(f'const {v}_{safe} = getLocationDetail({v}, "{d}")')
    return "\n".join(lines)


def _render_device_info(ctx: BlockContext) -> str:
    v = ctx.output_var
    details = ctx.params.get("details", ["Device Name"])
    lines = []
    detail_map = {
        "battery": ("getBatteryLevel()", "battery"),
        "charging": ("isCharging()", "charging"),
        "brightness": ('getDeviceDetail("Current Brightness")', "brightness"),
        "device_name": ('getDeviceDetail("Device Name")', "device_name"),
        "model": ('getDeviceDetail("Device Model")', "model"),
        "system_version": ('getDeviceDetail("System Version")', "system_version"),
        "volume": ('getDeviceDetail("Current Volume")', "volume"),
        "appearance": ('getDeviceDetail("Current Appearance")', "appearance"),
    }
    for d in details:
        key = d.lower().replace(" ", "_")
        if key in detail_map:
            expr, suffix = detail_map[key]
            lines.append(f"const {v}_{suffix} = {expr}")
    return "\n".join(lines) if lines else f'const {v} = getDeviceDetail("Device Name")'


def _render_screen_time(ctx: BlockContext) -> str:
    # getDeviceUsage(usageType, ?device, ?during, ?startTime, ?startTime)
    # usageType must be "all", "app", or "website"
    # Skip optional params — Cherri doesn't allow skipping positional args easily
    return f'const {ctx.output_var} = getDeviceUsage()'


def _render_shazam(ctx: BlockContext) -> str:
    v = ctx.output_var
    details = ctx.params.get("details", ["Title", "Artist"])
    lines = [f"const {v} = startShazam()"]
    for d in details:
        safe = d.lower().replace(" ", "_")
        lines.append(f'const {v}_{safe} = getShazamDetail({v}, "{d}")')
    return "\n".join(lines)


api_get = Block(
    id="api_get",
    category="data",
    description="HTTP GET request",
    includes=["actions/web"],
    outputs=["response"],
    params={
        "url": ParamDef(type="str", required=True, description="Full URL to fetch"),
        "headers": ParamDef(type="dict", default={}, description="HTTP headers"),
    },
    render=_render_api_get,
)

api_post = Block(
    id="api_post",
    category="data",
    description="HTTP POST request with JSON body",
    includes=["actions/web"],
    outputs=["response"],
    params={
        "url": ParamDef(type="str", required=True),
        "body": ParamDef(type="dict", default={}),
        "headers": ParamDef(type="dict", default={}),
    },
    render=_render_api_post,
)

weather_current = Block(
    id="weather_current",
    category="data",
    description="Get current weather conditions",
    includes=["actions/location"],
    outputs=["weather"] + [f"weather_{d.lower().replace(' ', '_')}" for d in _WEATHER_DETAILS],
    params={
        "details": ParamDef(
            type="list[str]", default=["Temperature", "Condition"],
            choices=_WEATHER_DETAILS,
            description="Weather details to extract",
        ),
    },
    render=_render_weather_current,
)

weather_forecast = Block(
    id="weather_forecast",
    category="data",
    description="Get weather forecast",
    includes=["actions/location"],
    outputs=["forecast"],
    params={"type": ParamDef(type="enum", default="Daily", choices=["Daily", "Hourly"])},
    render=_render_weather_forecast,
)

location_current = Block(
    id="location_current",
    category="data",
    description="Get current location with details",
    includes=["actions/location"],
    outputs=["location", "location_city", "location_state"],
    params={
        "details": ParamDef(
            type="list[str]", default=["City", "State"],
            choices=["Name", "City", "State", "Street", "ZIP Code", "Latitude", "Longitude", "Altitude"],
        ),
    },
    render=_render_location,
)

device_info = Block(
    id="device_info",
    category="data",
    description="Get device details like battery, brightness, model",
    includes=["actions/device"],
    outputs=["device_battery", "device_brightness", "device_name", "device_model"],
    params={
        "details": ParamDef(
            type="list[str]", default=["battery"],
            choices=["battery", "charging", "brightness", "device_name", "model", "system_version", "volume", "appearance"],
        ),
    },
    render=_render_device_info,
)

screen_time = Block(
    id="screen_time",
    category="data",
    description="Get screen time / app usage data",
    includes=["actions/device"],
    outputs=["usage"],
    params={
        "period": ParamDef(type="enum", default="today", choices=["today", "yesterday", "thisWeek", "thisMonth"]),
        "usage_type": ParamDef(type="enum", default="all", choices=["all", "app", "website"]),
    },
    render=_render_screen_time,
)

shazam = Block(
    id="shazam",
    category="data",
    description="Identify playing song with Shazam",
    includes=["actions/media"],
    outputs=["song", "song_title", "song_artist"],
    params={
        "details": ParamDef(
            type="list[str]", default=["Title", "Artist"],
            choices=["Title", "Artist", "Apple Music URL", "Lyrics Snippet", "Is Explicit", "Artwork", "Shazam URL"],
        ),
    },
    render=_render_shazam,
)

ALL = [api_get, api_post, weather_current, weather_forecast, location_current, device_info, screen_time, shazam]
