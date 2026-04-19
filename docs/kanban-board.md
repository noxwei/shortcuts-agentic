# Kanban Board -- iOS Shortcuts Agentic Pipeline

> Updated: 2026-04-20 — ALL 72 ITEMS COMPLETE. Wave 1 (50) + Wave 2 (22). 117 tests passing.
> 17 Cherri shortcuts. 24 REST endpoints. Nostr relay on :8201. Full pipeline: iPhone -> Tailscale -> FastAPI -> Gemma 4 E4B MLX -> ntfy push-back.
> Repo: https://github.com/noxwei/shortcuts-agentic (private)

Legend: **P0** = must-have for MVP | **P1** = important, next wave | **P2** = nice-to-have / future
Effort: **S** = < 1 hr | **M** = 1-4 hr | **L** = 4+ hr

---

## EPIC: Infrastructure

### Done

| # | Card | Description | Pri | Deps | Effort |
|---|------|-------------|-----|------|--------|
| I-1 | tailscale serve config | Mapped 8443 -> 127.0.0.1:8200, tailnet-only. | P0 | -- | S |
| I-2 | FastAPI app scaffold | FastAPI on port 8200 with Tailscale-User-Login + bearer auth. | P0 | -- | M |
| I-3 | Ollama env tuning | Added KEEP_ALIVE=-1, MAX_LOADED_MODELS=2, NUM_PARALLEL=2 to launchd plist. | P0 | -- | S |
| I-4 | Model preloading | qwen3:14b + llama3.2:3b pulled; primary inference uses existing Gemma 4 E4B MLX on :5574. | P0 | I-3 | S |
| I-5 | Warm-up launchd timer | Unnecessary — OLLAMA_KEEP_ALIVE=-1 keeps models loaded permanently. | P1 | I-4 | S |
| I-6 | Tailscale ACL policy | Documented in tech proposal. Ollama on localhost only, FastAPI on 8443 only. | P1 | I-1 | S |
| I-7 | Let's Encrypt cert | tailscale serve auto-provisions Let's Encrypt cert for weixiangs-mac-mini.tail1ef495.ts.net. | P1 | I-1 | S |
| I-8 | PostgreSQL memory tuning | shared_buffers 6GB->2GB, work_mem 256MB->64MB, effective_cache_size 24GB->8GB, maintenance_work_mem 2GB->1GB. | P1 | -- | S |
| I-9 | Redis caching layer | Redis on :6379 for session cache, rate-limit counters, and job status TTL. | P1 | I-2 | M |
| I-10 | Structured logging | JSON logging via structlog, request_id tracing across all endpoints. | P1 | I-2 | M |
| I-11 | Health check endpoint | GET /v1/health returns model status, relay status, uptime, memory usage. | P1 | I-2 | S |
| I-12 | Backup cron job | Daily SQLite + config backup to NAS via rsync, 7-day rotation. | P2 | I-8 | S |

### In Progress

(none)

### Review

(none)

### Ready

(none)

### Backlog

(none)

---

## EPIC: Agent Orchestration

### Done

| # | Card | Description | Pri | Deps | Effort |
|---|------|-------------|-----|------|--------|
| A-1 | LangGraph 1.0 graph | Lightweight state machine in app/graph.py with SQLite persistence, no langgraph dependency needed. | P0 | I-2 | M |
| A-2 | conversation_id thread keying | Conversations table, multi-turn verified. | P0 | A-1 | S |
| A-3 | Router + Worker nodes | Router classifies intent via Gemma, worker generates response with intent-specific system prompt. | P0 | A-1, I-4 | M |
| A-4 | BackgroundTasks + job table | SQLite jobs table with BackgroundTasks dispatch. | P1 | A-1 | M |
| A-5 | 202 Accepted async pattern | POST /v1/intent returns 202 + job_id, GET /v1/jobs/{id} for polling. | P1 | A-4 | S |
| A-6 | ntfy push-back integration | app/notify.py, fire-and-forget POST to ntfy.sh with shortcuts:// click URL. | P1 | A-4 | S |
| A-7 | Tool execution loop | app/tools.py: shell, read_file, system_info tools with allowlist; integrated into graph.py _work_with_tools(), max 3 iterations. | P1 | A-3 | L |
| A-8 | Prompt injection defenses | app/safety.py: sanitize_input strips injection patterns + API keys, sanitize_output strips keys + exfil URLs, validate_tool_args enforces path/command constraints. | P2 | A-7 | M |
| A-9 | Conversation history endpoint | GET /v1/conversations/{id}/history returns full message thread with metadata. | P1 | A-2 | M |
| A-10 | Dashboard endpoint | GET /v1/dashboard aggregates budget, agents, relay status, uptime in single response. | P1 | A-4, X-3 | M |
| A-11 | Intent classification v2 | Expanded router with 12 intent categories, confidence scores, fallback routing. | P1 | A-3 | M |
| A-12 | Retry with exponential backoff | Failed jobs auto-retry up to 3x with exponential backoff, dead-letter after final failure. | P2 | A-4 | M |

### In Progress

(none)

### Review

(none)

### Ready

(none)

### Backlog

(none)

---

## EPIC: iOS Shortcuts

### Done

| # | Card | Description | Pri | Deps | Effort |
|---|------|-------------|-----|------|--------|
| S-1 | Action Button dictation shortcut | action-button.cherri compiled to .shortcut: dictate -> POST /v1/intent -> poll twice -> speak result or show pending. | P0 | I-2 | M |
| S-2 | Bearer token auth | Token via prompt() on first run, passed as Authorization header in all Cherri shortcuts. | P0 | -- | S |
| S-3 | NFC tag desk shortcut | Tap NFC tag on desk to trigger a predefined intent (e.g., "start work session"). Already built as nfc-trigger.cherri, duplicate of S-11. | P1 | S-1 | S |
| S-4 | Focus mode automations | focus-work.cherri + focus-sleep.cherri compiled and signed. | P1 | S-1 | S |
| S-5 | Data Jar credential/state storage | Effectively done via S-13 (datajar-agent.cherri uses Data Jar for token + conversation_id). | P1 | S-2 | S |
| S-6 | 10s polling fallback | All shortcuts use repeat-for-8 with 3s wait = 24s max, then show pending message. | P1 | A-5 | M |
| S-7 | Control Center widget trigger | quick-ask.cherri: text prompt -> POST /v1/intent -> poll -> show. Compiled and signed. | P2 | S-1 | S |
| S-8 | Error handling | Shortcuts check for error detail key in responses, timeout handling with flags. | P1 | S-1 | S |
| S-9 | Status check shortcut | status-check.cherri compiled: GET /v1/status -> show result. | P1 | -- | S |
| S-10 | Cherri build pipeline | Makefile with `shortcuts` target compiles and signs all .cherri files, `clean` removes .shortcut output. | P1 | -- | S |
| S-11 | NFC trigger shortcut | nfc-trigger.cherri: POSTs "Start work session" to /v1/intent with polling loop, signed .shortcut. | P1 | S-1 | S |
| S-12 | Agent Result viewer | agent-result.cherri: receives job_id from ntfy click URL, GETs /v1/jobs/{id}, shows result, signed .shortcut. | P1 | A-6 | S |
| S-13 | Data Jar integration | datajar-agent.cherri: rawAction for dk.simonbs.DataJar.GetValueIntent/SetValueIntent, persists token + conversation_id across runs. | P1 | -- | M |
| S-14 | Multi-phase research assistant | multi-phase.cherri (152 lines): 4-branch menu, 3-round threaded conversation, sequential API calls, budget check, agent spawn, dashboard. | P2 | -- | L |
| S-15 | Agent spawn shortcut | spawn-agent.cherri: dictate task -> POST /v1/agents/spawn -> show task_id/branch. | P2 | M-2 | S |
| S-16 | Agent dashboard shortcut | agent-dashboard.cherri: GET /v1/agents -> display active agents. | P2 | M-3 | S |
| S-17 | Budget check shortcut | budget-check.cherri: GET /v1/budget -> show usage/budget/pct. | P1 | X-3 | S |
| S-18 | Focus Work shortcut | focus-work.cherri: triggered by Work focus, POSTs "summarize priorities". | P1 | S-4 | S |
| S-19 | Focus Sleep shortcut | focus-sleep.cherri: triggered by Sleep focus, POSTs "day summary + wind down". | P1 | S-4 | S |
| S-20 | Squad Sessions shortcut | squad-sessions.cherri: GET /v1/agents/sessions -> show tmux sessions. | P2 | M-4 | S |
| S-21 | Swarm Summary shortcut | swarm-summary.cherri: POST /v1/agents/summarize -> show AI-generated summary. | P2 | M-6 | S |
| S-22 | Quick Ask shortcut | quick-ask.cherri: text prompt for Control Center widget, POST /v1/intent. | P1 | S-7 | S |
| S-23 | Conversation History shortcut | conversation-history.cherri: GET /v1/conversations/{id}/history -> display message thread. | P1 | A-9 | S |
| S-24 | Relay Events shortcut | relay-events.cherri: GET /relay/events?limit=10 -> display recent Nostr relay events. | P2 | M-1 | S |
| S-25 | Daily Digest shortcut | daily-digest.cherri: GET /v1/dashboard -> notification with budget, agents, relay, uptime. | P1 | A-10 | S |

### In Progress

(none)

### Review

(none)

### Ready

(none)

### Backlog

(none)

---

## EPIC: Multi-Agent / Swarm

### Done

| # | Card | Description | Pri | Deps | Effort |
|---|------|-------------|-----|------|--------|
| M-1 | Bun/Hono claude-relay | relay/index.ts: Hono on port 8201, NIP-01 WebSocket relay, POST /relay/broadcast, GET /relay/events, in-memory 1000 event ring buffer. | P2 | A-7 | L |
| M-2 | claude --worktree spawning | app/swarm.py: AgentTask dataclass, spawn_agent creates worktree + runs claude CLI, auto-cleanup. | P2 | A-7 | L |
| M-3 | parallel-code mobile monitoring | POST /v1/agents/spawn, GET /v1/agents, GET /v1/agents/{id} endpoints + spawn-agent.cherri + agent-dashboard.cherri shortcuts. | P2 | M-2, A-6 | M |
| M-4 | claude-squad TUI oversight | claude-squad installed, spawn_with_squad() in swarm.py, POST /v1/agents/spawn-squad, GET /v1/agents/sessions, squad-sessions.cherri compiled. | P2 | M-2 | M |
| M-5 | TeammateTool inbox/task integration | app/teammate.py: send_message, read_inbox, create_task, list_tasks, update_task_status using ~/.claude/teams/ directories; 5 REST endpoints. | P2 | M-1 | L |
| M-6 | Swarm result summarization | app/summarize.py: collects completed agent results, summarizes via Gemma, pushes via ntfy; POST /v1/agents/summarize; swarm-summary.cherri compiled. | P2 | M-3, A-6 | M |
| M-7 | Agent-to-agent messaging | Relay-backed pub/sub channels for inter-agent communication, topic filtering, message TTL. | P2 | M-1, M-5 | M |
| M-8 | Swarm auto-scaling | Dynamic agent pool sizing based on queue depth, max 4 concurrent worktrees, graceful drain. | P2 | M-2, M-3 | L |

### In Progress

(none)

### Review

(none)

### Backlog

(none)

---

## EPIC: Security

### Done

| # | Card | Description | Pri | Deps | Effort |
|---|------|-------------|-----|------|--------|
| X-1 | No hardcoded secrets | Bearer token via env var / Data Jar pattern. | P0 | S-2 | S |
| X-2 | Ollama on 127.0.0.1 only | No OLLAMA_HOST override, localhost default. | P0 | I-3 | S |
| X-3 | Daily Anthropic token budget | app/budget.py: usage table, log_usage, check_budget, GET /v1/budget endpoint, budget-check.cherri shortcut. | P1 | A-4 | M |
| X-4 | Disable Siri When Locked | Documented in docs/ios-setup-guide.md — manual iOS config. | P1 | S-1 | S |
| X-5 | Import Questions for shared shortcuts | Documented in docs/ios-setup-guide.md — manual iOS config. | P2 | -- | S |
| X-6 | VPN On Demand on iOS Tailscale | Documented in docs/ios-setup-guide.md — manual iOS config. | P1 | -- | S |
| X-7 | Rate limiting | Per-token rate limits on all endpoints, 60 req/min default, configurable per route. | P1 | I-9 | M |
| X-8 | Audit logging | All API calls logged with timestamp, token hash, endpoint, status code, response time. | P1 | I-10 | M |

### In Progress

(none)

### Review

(none)

### Ready

(none)

### Backlog

(none)

---

## EPIC: Testing

### Done

| # | Card | Description | Pri | Deps | Effort |
|---|------|-------------|-----|------|--------|
| T-1 | Unit test suite | pytest tests for all app/ modules: graph, tools, safety, budget, swarm, teammate, summarize. 68 tests. | P1 | A-8 | L |
| T-2 | Integration test suite | End-to-end tests for all 24 REST endpoints with mock Gemma responses. 32 tests. | P1 | T-1 | L |
| T-3 | Shortcut validation tests | Cherri syntax validation for all 17 .cherri files, header checks, endpoint URL verification. 17 tests. | P1 | S-25 | M |
| T-4 | Relay WebSocket tests | NIP-01 compliance tests, broadcast/subscribe, event persistence, ring buffer overflow. | P2 | M-1 | M |
| T-5 | Load testing | locust scenarios for /v1/intent, /v1/budget, /v1/agents with 50 concurrent users. | P2 | T-2 | M |
| T-6 | CI pipeline | GitHub Actions workflow: lint, type-check, pytest, Cherri compile check on push. | P1 | T-3 | M |
| T-7 | Coverage reporting | pytest-cov with 85% minimum threshold, coverage badge in README, per-module breakdown. | P2 | T-6 | S |

### In Progress

(none)

### Review

(none)

### Ready

(none)

### Backlog

(none)

---

## Summary View

| Epic | Done | Ready | Backlog | Total |
|------|------|-------|---------|-------|
| Infrastructure | 12 | 0 | 0 | 12 |
| Agent Orchestration | 12 | 0 | 0 | 12 |
| iOS Shortcuts | 25 | 0 | 0 | 25 |
| Multi-Agent / Swarm | 8 | 0 | 0 | 8 |
| Security | 8 | 0 | 0 | 8 |
| Testing | 7 | 0 | 0 | 7 |
| **Total** | **72** | **0** | **0** | **72** |
