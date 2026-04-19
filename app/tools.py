"""Tool system for agent graph — A-7: tool execution loop.

Provides async tools that the worker can invoke via JSON tool calls.
Each tool is an async function: (args: dict) -> str
"""

import asyncio
import logging
import os
import shutil

logger = logging.getLogger(__name__)

# Commands considered safe (read-only).
_SAFE_COMMANDS = frozenset({
    "ls", "cat", "head", "tail", "grep", "find", "wc", "du", "df",
    "file", "stat", "which", "whoami", "hostname", "uname", "date",
    "uptime", "pwd", "echo", "tree",
    "git", "ollama",
})

# Git subcommands that are read-only.
_SAFE_GIT_SUBCMDS = frozenset({
    "status", "log", "diff", "show", "branch", "tag", "remote",
    "rev-parse", "describe", "shortlog",
})

# Ollama subcommands that are read-only.
_SAFE_OLLAMA_SUBCMDS = frozenset({
    "list", "ps", "show",
})

# Tokens that indicate destructive / dangerous intent.
_DANGEROUS_TOKENS = frozenset({
    "rm", "mv", "cp", "sudo", "kill", "killall", "pkill",
    "chmod", "chown", "mkfs", "dd", "shutdown", "reboot",
    "curl", "wget", "nc", "ncat", "python", "perl", "ruby",
    "bash", "sh", "zsh", "eval", "exec",
})

_ALLOWED_PATH_PREFIX = os.path.expanduser("~/Local_Dev/")
_MAX_TOOL_ITERATIONS = 3


def _is_command_safe(command: str) -> tuple[bool, str]:
    """Check if a shell command is safe to run. Returns (ok, reason)."""
    parts = command.strip().split()
    if not parts:
        return False, "empty command"

    base = os.path.basename(parts[0])

    if base not in _SAFE_COMMANDS:
        return False, f"command '{base}' not in allowlist"

    # Git: only allow read-only subcommands.
    if base == "git" and len(parts) > 1:
        subcmd = parts[1]
        if subcmd not in _SAFE_GIT_SUBCMDS:
            return False, f"git subcommand '{subcmd}' not allowed"

    # Ollama: only allow read-only subcommands.
    if base == "ollama" and len(parts) > 1:
        subcmd = parts[1]
        if subcmd not in _SAFE_OLLAMA_SUBCMDS:
            return False, f"ollama subcommand '{subcmd}' not allowed"

    # Scan all tokens for dangerous commands hiding in pipes / semicolons.
    for token in parts[1:]:
        clean = os.path.basename(token.strip(";|&"))
        if clean in _DANGEROUS_TOKENS:
            return False, f"dangerous token '{clean}' in arguments"

    return True, ""


async def shell(args: dict) -> str:
    """Run a read-only shell command, return stdout (max 2000 chars)."""
    command = args.get("command", "")
    if not isinstance(command, str) or not command.strip():
        return "ERROR: 'command' must be a non-empty string"

    ok, reason = _is_command_safe(command)
    if not ok:
        return f"ERROR: command rejected — {reason}"

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=_ALLOWED_PATH_PREFIX,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
        output = stdout.decode(errors="replace")
        if len(output) > 2000:
            output = output[:2000] + "\n... (truncated)"
        return output or "(no output)"
    except asyncio.TimeoutError:
        return "ERROR: command timed out (15s limit)"
    except Exception as exc:
        return f"ERROR: {exc}"


async def read_file(args: dict) -> str:
    """Read a file's contents (max 5000 chars). Path must be under ~/Local_Dev/."""
    path = args.get("path", "")
    if not isinstance(path, str) or not path.strip():
        return "ERROR: 'path' must be a non-empty string"

    expanded = os.path.expanduser(path)
    resolved = os.path.realpath(expanded)

    if not resolved.startswith(_ALLOWED_PATH_PREFIX):
        return f"ERROR: path must be under {_ALLOWED_PATH_PREFIX}"

    if not os.path.isfile(resolved):
        return f"ERROR: not a file or does not exist: {path}"

    try:
        with open(resolved, "r", errors="replace") as f:
            content = f.read(5000)
        if len(content) == 5000:
            content += "\n... (truncated at 5000 chars)"
        return content or "(empty file)"
    except Exception as exc:
        return f"ERROR: {exc}"


async def system_info(args: dict) -> str:
    """Return system stats: uptime, memory, disk, running Ollama models."""
    lines: list[str] = []

    # Uptime
    try:
        proc = await asyncio.create_subprocess_exec(
            "uptime", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        out, _ = await proc.communicate()
        lines.append(f"Uptime: {out.decode().strip()}")
    except Exception:
        lines.append("Uptime: unavailable")

    # Memory (macOS vm_stat)
    try:
        proc = await asyncio.create_subprocess_shell(
            "memory_pressure | head -3",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        out, _ = await proc.communicate()
        lines.append(f"Memory:\n{out.decode().strip()}")
    except Exception:
        lines.append("Memory: unavailable")

    # Disk
    total, used, free = shutil.disk_usage("/")
    lines.append(
        f"Disk /: {used // (1 << 30)} GB used / {total // (1 << 30)} GB total "
        f"({free // (1 << 30)} GB free)"
    )

    # Ollama models
    try:
        proc = await asyncio.create_subprocess_exec(
            "ollama", "ps",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
        output = out.decode().strip()
        lines.append(f"Ollama running:\n{output or '(none)'}")
    except Exception:
        lines.append("Ollama: unavailable")

    return "\n\n".join(lines)


# --- Tool registry ---

TOOLS: dict[str, callable] = {
    "shell": shell,
    "read_file": read_file,
    "system_info": system_info,
}

# JSON schemas for the worker prompt.
TOOL_SCHEMAS = {
    "shell": {
        "tool": "shell",
        "args": {"command": "<shell command string>"},
    },
    "read_file": {
        "tool": "read_file",
        "args": {"path": "<absolute file path>"},
    },
    "system_info": {
        "tool": "system_info",
        "args": {},
    },
}

MAX_TOOL_ITERATIONS = _MAX_TOOL_ITERATIONS
