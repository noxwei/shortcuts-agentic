# shortcuts-agentic

iOS Shortcuts agentic pipeline over Tailscale. Voice/text from iPhone hits a FastAPI backend on Mac Mini, routes through a local LLM, and pushes results back via ntfy.

## Architecture

```
iPhone Shortcut
    |
    v
Tailscale VPN (auto-connect, TLS via tailscale serve)
    |
    v
FastAPI :8200 (auth -> rate limit -> audit log)
    |
    +---> Router (Gemma 4 E4B MLX :5574) ---> classify intent
    |         |
    |         v
    |     Worker (tool loop, max 3 iterations)
    |         |
    |         v
    |     sanitize output -> save conversation -> log usage
    |
    +---> Swarm Manager ---> spawn claude CLI in git worktrees
    |         |
    |         v
    |     Nostr relay :8201 (NIP-01, agent lifecycle pub/sub)
    |
    +---> ntfy push-back ---> iPhone notification with shortcuts:// deep link
```

- **Single `/intent` endpoint.** Shortcuts POST raw text; the server classifies intent (question/task/search/conversation) and dispatches to the appropriate worker with confidence scoring.
- **202 Accepted + ntfy.** Sidesteps iOS Shortcuts' ~25s background timeout. Server responds immediately with job_id, pushes result via ntfy. SSE streaming also available.
- **Zero secrets on iPhone.** All API keys and credentials stay server-side. Bearer token via Data Jar.
- **Tailscale `serve` only** (not `funnel`). Mesh-only, auto Let's Encrypt TLS.
- **Defense in depth.** Prompt injection sanitization, API key redaction, command allowlisting, rate limiting, audit logging.

## Quick Start

```bash
git clone git@github.com:noxwei/shortcuts-agentic.git
cd shortcuts-agentic

python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
# Edit .env: set SHORTCUTS_AUTH_TOKEN, NTFY_TOPIC

make dev          # FastAPI on 0.0.0.0:8200
cd relay && bun install && bun run dev  # Nostr relay on :8201
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/intent` | Submit intent (returns 202 + job_id) |
| GET | `/v1/jobs/{job_id}` | Poll job status and result |
| GET | `/v1/jobs/{job_id}/stream` | SSE stream of job progress |
| GET | `/v1/status` | Server + inference health |
| GET | `/v1/budget` | Daily token budget usage |
| GET | `/v1/dashboard` | Aggregated status (inference, budget, agents, relay, uptime) |
| GET | `/v1/conversations/{id}/history` | Full conversation thread |
| GET | `/v1/audit` | Recent audit log entries |
| GET | `/v1/relay/events` | Proxy to Nostr relay events |
| POST | `/v1/agents/spawn` | Spawn claude CLI agent in a worktree |
| POST | `/v1/agents/spawn-squad` | Spawn agent via claude-squad TUI |
| GET | `/v1/agents` | List all agent tasks |
| GET | `/v1/agents/{task_id}` | Get agent task detail |
| GET | `/v1/agents/sessions` | List claude-squad tmux sessions |
| POST | `/v1/agents/summarize` | Summarize completed agent results |
| POST | `/v1/team/message` | Send message to agent inbox |
| GET | `/v1/team/inbox/{team}/{agent}` | Read agent inbox |
| POST | `/v1/team/tasks` | Create shared task |
| GET | `/v1/team/tasks` | List shared tasks |
| PATCH | `/v1/team/tasks/{task_id}` | Update task status |

All endpoints require auth via `Tailscale-User-Login` header or `Authorization: Bearer <token>`.

## Shortcuts

17 [Cherri](https://github.com/nicknicknicknick/cherri)-compiled iOS Shortcuts:

| Shortcut | Description |
|----------|-------------|
| `action-button.cherri` | Dictate text via Action Button, POST to /v1/intent, poll for result |
| `quick-ask.cherri` | Text prompt for Control Center widget |
| `nfc-trigger.cherri` | NFC tap triggers predefined intent |
| `focus-work.cherri` | Work Focus automation -- summarize priorities |
| `focus-sleep.cherri` | Sleep Focus automation -- day summary + wind down |
| `status-check.cherri` | GET /v1/status, display server health |
| `budget-check.cherri` | GET /v1/budget, show daily usage |
| `daily-digest.cherri` | GET /v1/dashboard, notification with full status |
| `agent-result.cherri` | Fetch job result from ntfy click URL |
| `conversation-history.cherri` | Display conversation thread |
| `datajar-agent.cherri` | Data Jar integration for token + conversation_id persistence |
| `spawn-agent.cherri` | Dictate task, spawn worktree agent |
| `agent-dashboard.cherri` | Display active agents |
| `squad-sessions.cherri` | List claude-squad tmux sessions |
| `swarm-summary.cherri` | AI summary of completed agent work |
| `relay-events.cherri` | Display recent Nostr relay events |
| `multi-phase.cherri` | 4-branch menu: threaded conversation, budget, agent spawn, dashboard |

## Multi-Agent Swarm

The backend supports spawning multiple Claude Code agents in parallel:

- **Worktree isolation.** Each agent gets its own git worktree and branch via `claude --worktree`.
- **claude-squad.** Optional TUI oversight through tmux sessions for monitoring/intervening.
- **Nostr relay.** Bun/Hono relay on :8201 implements NIP-01 for inter-agent pub/sub messaging.
- **TeammateTool.** Structured inbox/task protocol for agent-to-agent coordination via `~/.claude/teams/`.
- **Result persistence.** Agent results + git diff summaries stored in SQLite, survive restarts.

## Agentic Shortcut Generator (Planned)

End-to-end pipeline for creating iOS Shortcuts from natural language:

```
"Make me a shortcut that checks my Plex unwatched count"
    |
    v
POST /v1/shortcuts/generate
    |
    v
Claude Haiku (via claude CLI) generates .cherri source
    |    - System prompt with Cherri cheat sheet + 3 example shortcuts
    |    - Self-repair: if compilation fails, error fed back for retry
    |
    v
~/go/bin/cherri compiles .cherri -> .shortcut (signed binary)
    |
    v
GET /v1/shortcuts/{name}/download serves the .shortcut
    |
    v
ntfy push to iPhone -> user taps -> iOS installs shortcut
```

Uses `claude --model haiku` (Claude Code membership auth, no API key needed).

## Development

```bash
make dev        # uvicorn on 0.0.0.0:8200 with --reload
make test       # pytest -v
make shortcuts  # compile all .cherri -> .shortcut
make clean      # remove compiled .shortcut files
```

Relay (separate process):
```bash
cd relay && bun run dev    # Hono on :8201 with --watch
```

Docker:
```bash
docker compose up
```

## Configuration

Via `.env` (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `SHORTCUTS_AUTH_TOKEN` | -- | Bearer token for API auth |
| `NTFY_TOPIC` | -- | ntfy.sh topic for push notifications |
| `INFERENCE_BACKEND` | `gemma` | `gemma` or `ollama` |
| `GEMMA_BASE_URL` | `http://127.0.0.1:5574` | Gemma 4 E4B MLX server |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama API |
| `OLLAMA_MODEL` | `qwen3:14b` | Ollama model for worker inference |
| `DAILY_CHAR_BUDGET` | `500000` | Daily character budget cap |
| `DB_PATH` | `~/.local/share/shortcuts-agentic/jobs.db` | SQLite database path |

## Project Structure

```
app/
  main.py           # FastAPI app, all route definitions
  config.py          # Pydantic settings from .env
  graph.py           # State machine: router -> worker with tool loop
  inference.py       # LLM inference (Gemma MLX / Ollama)
  tools.py           # Agent tools: shell, read_file, system_info
  safety.py          # Input/output sanitization, prompt injection defense
  budget.py          # Daily token budget tracking
  swarm.py           # Worktree agent spawning, claude-squad integration
  teammate.py        # TeammateTool inbox/task protocol
  summarize.py       # Swarm result summarization
  notify.py          # ntfy push-back
  relay.py           # Nostr relay client
  auth.py            # Tailscale + bearer token auth
  ratelimit.py       # Per-token rate limiting
  audit.py           # Request audit logging
  db.py              # SQLite job/conversation persistence
  logging_config.py  # structlog JSON logging
relay/
  index.ts           # Bun/Hono NIP-01 Nostr relay on :8201
  package.json
shortcuts/
  *.cherri            # 17 iOS Shortcut source files
tests/
  test_api.py         # Integration tests for all endpoints (21 tests)
  test_auth.py        # Auth middleware tests (7 tests)
  test_audit.py       # Audit logging tests (4 tests)
  test_budget.py      # Budget tracking tests (6 tests)
  test_graph.py       # Agent graph tests (16 tests)
  test_ratelimit.py   # Rate limiting tests (7 tests)
  test_relay.py       # Nostr relay client tests (8 tests)
  test_safety.py      # Sanitization tests (19 tests)
  test_tools.py       # Tool execution tests (21 tests)
docs/
  tech-proposal.md    # Full architecture proposal
  kanban-board.md     # Project tracking (72/72 items complete)
  ios-setup-guide.md  # iOS device configuration
  tech-timeline.md    # Implementation timeline
```
