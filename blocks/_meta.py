"""Valid glyphs, colors, and include paths for Cherri shortcuts."""

VALID_COLORS = frozenset({
    "red", "orange", "darkorange", "yellow", "green", "teal",
    "blue", "purple", "violet", "pink", "gray",
})

# Subset of commonly used glyphs (cherri --glyph= for full list)
VALID_GLYPHS = frozenset({
    "gear", "microphone", "globe", "bell", "openBook", "closedBook",
    "camera", "cloud", "doc", "flag", "heart", "house", "link", "lock",
    "magnifyingglass", "music", "musicNote", "pencil", "person", "phone",
    "play", "star", "tag", "bookmark", "binoculars", "brain", "dice",
    "headphones", "fireplace", "sashBook", "bookshelf", "barGraph",
    "chartPie", "antenna", "bolt", "cpu", "display", "gamecontroller",
    "leaf", "map", "moon", "paintbrush", "paperplane", "scissors",
    "shield", "sparkles", "sun", "terminal", "text", "timer", "wand",
    "wifi", "wrench",
})

INCLUDE_PATHS = {
    "web": "actions/web",
    "scripting": "actions/scripting",
    "intelligence": "actions/intelligence",
    "text": "actions/text",
    "sharing": "actions/sharing",
    "shortcuts": "actions/shortcuts",
    "device": "actions/device",
    "settings": "actions/settings",
    "location": "actions/location",
    "media": "actions/media",
    "documents": "actions/documents",
    "contacts": "actions/contacts",
    "calendar": "actions/calendar",
    "photos": "actions/photos",
    "music": "actions/music",
}
