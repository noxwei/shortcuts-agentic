"""Prompt injection defenses and output sanitization — A-8.

Defense-in-depth for a single-user tailnet system. Lightweight checks
to catch common injection patterns and accidental key leaks.
"""

import os
import structlog
import re

ALLOWED_PATH_PREFIX = os.environ.get("ALLOWED_PATH_PREFIX", os.path.expanduser("~/Local_Dev/"))

logger = structlog.get_logger()

# --- Input sanitization ---

_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions?", re.I),
    re.compile(r"ignore\s+all\s+previous", re.I),
    re.compile(r"disregard\s+(all\s+)?(previous|above|prior)", re.I),
    re.compile(r"^system\s*:", re.I | re.MULTILINE),
    re.compile(r"<\|"),
    re.compile(r"\|>"),
]

_API_KEY_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"AKIA[A-Z0-9]{16,}"),
]


def sanitize_input(text: str) -> str:
    """Strip known prompt injection patterns from user input."""
    cleaned = text
    for pat in _INJECTION_PATTERNS:
        match = pat.search(cleaned)
        if match:
            logger.warning("input_injection_stripped", pattern=match.group())
            cleaned = pat.sub("", cleaned)

    for pat in _API_KEY_PATTERNS:
        match = pat.search(cleaned)
        if match:
            logger.warning("api_key_stripped_input")
            cleaned = pat.sub("[REDACTED]", cleaned)

    return cleaned.strip()


# --- Output sanitization ---

_EXFIL_URL_PATTERNS = [
    re.compile(r"https?://[^\s]*\.(requestbin|pipedream|webhook\.site|burpcollaborator|interact\.sh)[^\s]*", re.I),
    re.compile(r"https?://[^\s]*\.ngrok\.[^\s]*", re.I),
]


def sanitize_output(text: str) -> str:
    """Strip sensitive data from model output."""
    cleaned = text

    for pat in _API_KEY_PATTERNS:
        match = pat.search(cleaned)
        if match:
            logger.warning("api_key_stripped_output")
            cleaned = pat.sub("[REDACTED]", cleaned)

    for pat in _EXFIL_URL_PATTERNS:
        match = pat.search(cleaned)
        if match:
            logger.warning("exfil_url_stripped", url=match.group()[:40])
            cleaned = pat.sub("[URL REMOVED]", cleaned)

    return cleaned


# --- Tool argument validation ---

_SHELL_DANGEROUS = re.compile(
    r"[`]|"                     # backticks
    r"\$\(|"                    # $() command substitution
    r"\|\s*(curl|wget|nc)\b",   # pipes to network tools
    re.I,
)


def validate_tool_args(tool_name: str, args: dict) -> tuple[bool, str]:
    """Validate tool arguments. Returns (ok, reason)."""
    if tool_name == "shell":
        cmd = args.get("command", "")
        if not isinstance(cmd, str):
            return False, "command must be a string"
        if _SHELL_DANGEROUS.search(cmd):
            return False, "shell command contains dangerous patterns (backticks, $(), pipe to curl/wget)"
        return True, ""

    if tool_name == "read_file":
        path = args.get("path", "")
        if not isinstance(path, str):
            return False, "path must be a string"
        if not path.startswith(ALLOWED_PATH_PREFIX):
            return False, f"path must start with {ALLOWED_PATH_PREFIX}"
        return True, ""

    if tool_name == "system_info":
        return True, ""

    return False, f"unknown tool: {tool_name}"
