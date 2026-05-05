"""Agentic shortcut generator — Claude Haiku generates .cherri, cherri compiles to .shortcut."""

import asyncio
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import structlog

logger = structlog.get_logger()

# Where generated shortcuts live
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "shortcuts" / "generated"

# Cherri compiler binary
CHERRI_BIN = Path.home() / "go" / "bin" / "cherri"

# System prompt for Haiku with Cherri cheat sheet + few-shot examples
_SYSTEM_PROMPT = """\
You are a Cherri compiler expert. You write iOS Shortcuts in the Cherri language.
Output ONLY valid .cherri source code. No markdown fences, no explanation.

## Cherri Language Cheat Sheet

### Header directives (required)
```
#define name My Shortcut
#define glyph gear
#define color blue
```

### Imports (pick what you need)
```
#include 'actions/web'
#include 'actions/scripting'
#include 'actions/text'
#include 'actions/notification'
```

### Variables and constants
```
const token = prompt("Enter API Token")
const spoken = listen()
var counter = 0
```

### HTTP requests
```
const resp = downloadURL("https://example.com/api", {"Authorization": "Bearer {token}"})
const resp = jsonRequest("https://example.com/api", "POST", {"key": "value"}, {"Authorization": "Bearer {token}"})
```

### JSON handling
```
const dict = getDictionary(resp)
const val = getValue(dict, "key_name")
```

### Control flow
```
if condition == "value" {
    // ...
}

repeat i for 5 {
    wait(3)
    // ...
}
```

### Output
```
show("Message to display")
speak("Text to speak aloud")
output("Return value")
```

### Available glyphs
gear, microphone, barGraph, globe, bell, book, camera, cloud, doc, flag, heart,
house, link, lock, magnifyingglass, music, pencil, person, phone, play, star, tag

### Available colors
red, orange, yellow, green, teal, blue, purple, pink, gray

## Rules
- The Tailscale hostname is: weixiangs-mac-mini.tail1ef495.ts.net:8443
- Always use HTTPS with the Tailscale hostname
- Always include auth: const token = prompt("API Token")
- Always include Authorization header: {"Authorization": "Bearer {token}"}
- Use downloadURL for GET, jsonRequest for POST
- Use getDictionary + getValue to extract JSON fields
- Output the final result with show()

## Example 1: Simple GET shortcut
```
#define name Budget Check
#define glyph barGraph
#define color yellow

#include 'actions/web'
#include 'actions/scripting'

const token = prompt("API Token")
const resp = downloadURL("https://weixiangs-mac-mini.tail1ef495.ts.net:8443/v1/budget", {"Authorization": "Bearer {token}"})
const dict = getDictionary(resp)
const used = getValue(dict, "chars_used")
const budget = getValue(dict, "chars_budget")

show("Daily Budget\\n\\nUsed: {used}\\nBudget: {budget}")
```

## Example 2: POST with polling
```
#define name Ask Agent
#define glyph microphone
#define color red

#include 'actions/web'
#include 'actions/scripting'
#include 'actions/text'

const token = prompt("API Token")
const spoken = listen()

const submitResp = jsonRequest("https://weixiangs-mac-mini.tail1ef495.ts.net:8443/v1/intent", "POST", {"source": "shortcut", "text": "{spoken}"}, {"Authorization": "Bearer {token}"})
const submitDict = getDictionary(submitResp)
const jobId = getValue(submitDict, "job_id")

repeat i for 8 {
    wait(3)
    const pollResp = downloadURL("https://weixiangs-mac-mini.tail1ef495.ts.net:8443/v1/jobs/{jobId}", {"Authorization": "Bearer {token}"})
    const pollDict = getDictionary(pollResp)
    const pollStatus = getValue(pollDict, "status")
    if pollStatus == "done" {
        const result = getValue(pollDict, "result")
        show("{result}")
        output("")
    }
}

show("Job {jobId} still pending. Check back later.")
```

## Example 3: Spawn agent
```
#define name Spawn Agent
#define glyph gear
#define color teal

#include 'actions/web'
#include 'actions/scripting'
#include 'actions/text'

const token = prompt("API Token")
const task = listen()

const resp = jsonRequest("https://weixiangs-mac-mini.tail1ef495.ts.net:8443/v1/agents/spawn", "POST", {"prompt": "{task}"}, {"Authorization": "Bearer {token}"})
const dict = getDictionary(resp)
const taskId = getValue(dict, "task_id")
const branch = getValue(dict, "branch")

show("Agent spawned!\\n\\nTask: {taskId}\\nBranch: {branch}")
```

Now write a Cherri shortcut for the following user request:
"""


@dataclass
class GeneratedShortcut:
    id: str
    name: str
    description: str
    status: str = "generating"  # generating, compiling, done, failed
    cherri_source: str = ""
    compile_error: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def safe_name(self) -> str:
        """Filename-safe version of the name."""
        return re.sub(r"[^a-z0-9-]", "-", self.name.lower().strip())[:50].strip("-")

    @property
    def cherri_path(self) -> Path:
        return OUTPUT_DIR / f"{self.safe_name}.cherri"

    @property
    def shortcut_path(self) -> Path:
        return OUTPUT_DIR / f"{self.safe_name}.shortcut"


# In-memory registry
_shortcuts: dict[str, GeneratedShortcut] = {}


async def _run_haiku(description: str) -> str:
    """Run claude CLI with --model haiku to generate .cherri source."""
    prompt = f"{_SYSTEM_PROMPT}\n{description}"

    proc = await asyncio.create_subprocess_exec(
        "claude", "-p", prompt,
        "--model", "haiku",
        "--output-format", "text",
        "--max-turns", "1",
        "-y",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)

    if proc.returncode != 0:
        error = stderr.decode(errors="replace")[:500]
        raise RuntimeError(f"Claude CLI failed: {error}")

    raw = stdout.decode(errors="replace").strip()

    # Strip markdown fences if Haiku wraps them
    if raw.startswith("```"):
        lines = raw.splitlines()
        # Remove first and last fence lines
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines)

    return raw


async def _compile_cherri(shortcut: GeneratedShortcut) -> bool:
    """Compile .cherri to .shortcut using the cherri binary.

    SAFETY: Always cd into the output directory and use relative filename.
    Never pass directory paths or use -o flag. See CLAUDE.md.
    """
    cherri_file = shortcut.cherri_path
    if not cherri_file.is_file():
        shortcut.compile_error = f"Cherri source not found: {cherri_file.name}"
        return False

    # CRITICAL: Verify the cherri binary exists
    if not CHERRI_BIN.is_file():
        shortcut.compile_error = f"Cherri compiler not found at {CHERRI_BIN}"
        return False

    # CRITICAL: cd into the directory, use relative filename only
    filename = cherri_file.name
    work_dir = str(cherri_file.parent)

    # Double-check: the argument must be a file, not a directory
    target = cherri_file.parent / filename
    if target.is_dir():
        shortcut.compile_error = "SAFETY: target resolves to a directory, aborting"
        return False

    proc = await asyncio.create_subprocess_exec(
        str(CHERRI_BIN), filename, "--skip-sign",
        cwd=work_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

    if proc.returncode != 0:
        shortcut.compile_error = stderr.decode(errors="replace")[:500] or stdout.decode(errors="replace")[:500]
        return False

    # Verify output exists
    if not shortcut.shortcut_path.is_file():
        shortcut.compile_error = "Compilation produced no output file"
        return False

    return True


async def generate_shortcut(description: str) -> GeneratedShortcut:
    """Full pipeline: Haiku generates .cherri -> cherri compiles -> .shortcut ready for download."""
    shortcut_id = uuid.uuid4().hex[:12]

    # Derive a name from the description
    name_words = description.strip().split()[:6]
    name = " ".join(name_words) if name_words else "custom-shortcut"

    shortcut = GeneratedShortcut(id=shortcut_id, name=name, description=description)
    _shortcuts[shortcut_id] = shortcut

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Generate .cherri via Haiku
    try:
        logger.info("shortcut_gen_start", id=shortcut_id, description=description[:100])
        source = await _run_haiku(description)
        shortcut.cherri_source = source
        shortcut.cherri_path.write_text(source)
        shortcut.status = "compiling"
    except Exception as e:
        shortcut.status = "failed"
        shortcut.compile_error = f"Haiku generation failed: {e}"
        logger.error("shortcut_gen_haiku_failed", id=shortcut_id, error=str(e))
        return shortcut

    # Step 2: Compile
    success = await _compile_cherri(shortcut)

    if not success:
        # Step 3: Self-repair — feed error back to Haiku for one retry
        logger.info("shortcut_gen_retry", id=shortcut_id, error=shortcut.compile_error[:100])
        try:
            repair_prompt = (
                f"The following Cherri code failed to compile:\n\n"
                f"```\n{shortcut.cherri_source}\n```\n\n"
                f"Compiler error:\n{shortcut.compile_error}\n\n"
                f"Fix the code and output ONLY the corrected .cherri source. No explanation."
            )
            repaired = await _run_haiku(repair_prompt)
            shortcut.cherri_source = repaired
            shortcut.cherri_path.write_text(repaired)
            success = await _compile_cherri(shortcut)
        except Exception as e:
            shortcut.status = "failed"
            shortcut.compile_error = f"Repair attempt failed: {e}"
            logger.error("shortcut_gen_repair_failed", id=shortcut_id, error=str(e))
            return shortcut

    if success:
        shortcut.status = "done"
        logger.info("shortcut_gen_done", id=shortcut_id, name=shortcut.safe_name)
    else:
        shortcut.status = "failed"
        logger.error("shortcut_gen_compile_failed", id=shortcut_id, error=shortcut.compile_error[:100])

    return shortcut


def get_shortcut(shortcut_id: str) -> GeneratedShortcut | None:
    return _shortcuts.get(shortcut_id)


def list_shortcuts() -> list[dict]:
    return [
        {
            "id": s.id,
            "name": s.name,
            "safe_name": s.safe_name,
            "status": s.status,
            "created_at": s.created_at,
        }
        for s in _shortcuts.values()
    ]
