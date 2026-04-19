# Tech Timeline: iOS Shortcuts as Agentic Mobile Trigger Layer

Mac Mini M2 Pro pipeline triggered from iOS Shortcuts, orchestrated via LangGraph, served over Tailscale.

---

## 1. Ecosystem Timeline (2024--2026)

Key milestones that made this architecture viable.

| Date | Milestone | Relevance |
|------|-----------|-----------|
| 2024-06 | **iOS 18 Controls API** (WWDC24) | Lock Screen / Control Center widgets can trigger Shortcuts without unlocking. Action Button gets first-class Shortcut binding. |
| 2024-09 | **iOS 18 GA** | Controls API ships. Shortcuts gains `Get Contents of URL` improvements and tighter background execution model (25s hard cap). |
| 2024-10 | **Ollama 0.14 -- Anthropic-compatible endpoint** | `/v1/messages` compatibility layer. Local models can be called with the same shape as Claude API, simplifying router logic. |
| 2025-01 | **MLX engine preview (Ollama 0.19)** | Apple Silicon native inference via MLX. Significant throughput gains on M2 Pro for 4-bit quantized models (qwen3:14b, llama3.2:3b). |
| 2025-03 | **LiteLLM unified /v1/messages** | Single proxy surface for Ollama, Claude, Gemini. Shortcuts can target one endpoint regardless of backing model. |
| 2025-06 | **claude-code-router maturity** (~32.5k GitHub stars) | Proven routing pattern: local-first with Claude fallback. Validates the hybrid local/cloud approach for agentic workloads. |
| 2025-08 | **claude-squad / ccswarm consolidation** | Multi-agent coordination patterns stabilize. `--worktree` spawning and parallel-code monitoring become reliable primitives. |
| 2025-10 | **LangGraph 1.0** | Stable graph-based agent orchestration with built-in `SqliteSaver` checkpointing, human-in-the-loop, and streaming support. |
| 2025-11 | **Tailscale improvements** | Automated HTTPS cert provisioning (`tailscale cert`), `tailscale serve` identity headers (`Tailscale-User-Login`), simplified peer auth. |
| 2026-06 | **iOS 26 -- Use Model action** (WWDC26, expected) | On-device Foundation Model access from Shortcuts. Limited to Apple's model and system prompt; no custom endpoint, but enables local-only fallback for simple tasks. |

---

## 2. Build Timeline (Weeks 1--4)

### Week 1: Foundation

**Goal:** Stable API endpoint reachable from any iOS device on the Tailnet.

| Task | Detail |
|------|--------|
| Tailscale serve | `tailscale serve https / http://127.0.0.1:8200` -- HTTPS termination with auto-cert. Verify from MacBook Air (100.99.9.76) and iPhone. |
| FastAPI scaffold | Uvicorn on `0.0.0.0:8200`. Endpoints: `POST /v1/ask`, `GET /v1/status`, `GET /v1/jobs/{id}`. Bearer token auth via env var. |
| Ollama config | `OLLAMA_HOST=0.0.0.0:11434`, `OLLAMA_KEEP_ALIVE=30m`, `OLLAMA_FLASH_ATTENTION=1`. Systemd/launchd managed. |
| Model preload | Pull and warm `qwen3:14b` (primary reasoning) and `llama3.2:3b` (fast classification/routing). Validate with `/api/generate` smoke test. |
| Health check | `/v1/status` returns Ollama liveness, loaded models, GPU memory, queue depth. Shortcuts can poll this before submitting work. |

**Dependencies:** Tailscale installed and authenticated on Mac Mini and iOS devices. Ollama >= 0.19 for MLX engine.

---

### Week 2: Agent Orchestration

**Goal:** Stateful, resumable agent graphs with async job tracking.

| Task | Detail |
|------|--------|
| LangGraph graph | Define agent graph: `route -> think -> act -> respond`. Tool nodes for file ops, shell, web search. |
| SqliteSaver | Checkpoint persistence at `~/.local/share/shortcuts-agentic/checkpoints.db`. Keyed by `conversation_id` (UUID, passed from Shortcut). |
| Job table | SQLite `jobs` table: `id`, `conversation_id`, `status` (queued/running/done/failed), `result`, `created_at`, `updated_at`. FastAPI `BackgroundTasks` writes status. |
| Polling endpoint | `GET /v1/jobs/{id}` -- Shortcuts poll this after the initial `POST /v1/ask` returns `202 Accepted` with job ID. Designed for the 25s timeout constraint. |
| ntfy push-back | On job completion, `POST` to `ntfy.sh/shortcuts-agentic-{device}` with result summary. iOS receives as push notification; tap opens result Shortcut. |
| Conversation resume | `POST /v1/ask` with existing `conversation_id` resumes from last checkpoint. Enables multi-turn from Shortcuts without local state. |

**Dependencies:** Week 1 endpoint operational. ntfy app installed on iOS devices.

---

### Week 3: iOS Shortcuts

**Goal:** Three trigger surfaces -- voice (Action Button), physical (NFC), manual (widget).

| Task | Detail |
|------|--------|
| Action Button dictation | Shortcut: `Dictate Text` -> `Get Contents of URL` (POST /v1/ask, bearer auth) -> parse job ID -> `Wait` + poll loop (3s interval, 8 iterations = 24s) -> `Show Result` or `Show Notification` via ntfy fallback. |
| NFC tag trigger | Write NFC tags with shortcut:// URLs encoding preset prompts (e.g., "summarize inbox", "start dev session"). Tap triggers `Run Shortcut` with payload. |
| Control Center widget | iOS 18 Controls API widget: single-tap sends a preconfigured prompt. Long-press opens dictation variant. |
| Data Jar state | Store `conversation_id`, `last_job_id`, `auth_token` in Data Jar (or Shortcuts' native `File` storage as fallback). Enables multi-turn without server-side device tracking. |
| Polling fallback | If poll loop exhausts 8 iterations without result, save `job_id` to Data Jar and show "Result pending -- check notifications." ntfy delivers result asynchronously. |
| Auth | Bearer token only (`Authorization: Bearer {token}`). Token stored in Data Jar. No OAuth (Shortcuts has no OAuth PKCE flow). No Keychain access from Shortcuts. |

**Dependencies:** Week 2 job system and ntfy integration. Data Jar app (or equivalent) installed.

---

### Week 4: Multi-Agent

**Goal:** Parallel agent spawning with mobile monitoring.

| Task | Detail |
|------|--------|
| claude-relay | Bun/Hono service on `:8201`. Nostr-based message relay between agents. Lightweight pub/sub for coordination signals. |
| Worktree spawning | `claude --worktree` per task. Each agent gets an isolated git worktree. Managed by a supervisor node in the LangGraph graph. |
| parallel-code monitoring | Mobile-accessible dashboard at `/v1/dashboard` (SSE or polling). Shows active agents, current tool calls, token usage, estimated completion. |
| Swarm coordination | Supervisor agent decomposes complex prompts into subtasks, assigns to worker agents, merges results. Uses `ccswarm`-style patterns. |
| Mobile controls | `POST /v1/agents/{id}/cancel`, `POST /v1/agents/{id}/pause`. Shortcuts can manage running agents. |

**Dependencies:** Weeks 1--3 complete. Bun runtime installed. Sufficient RAM for parallel model instances (32GB M2 Pro supports 2--3 concurrent qwen3:14b).

---

## 3. Key Constraints and Workarounds

### iOS Shortcuts Runtime

| Constraint | Impact | Workaround |
|------------|--------|------------|
| **25s background execution timeout** | Long-running agent tasks cannot complete within a single Shortcut run. | Fire-and-forget with `202 Accepted` + job ID. Poll in a `Repeat` loop (24s budget). Fall back to ntfy push notification for results. |
| **No streaming support** | `Get Contents of URL` waits for full response. No SSE, no WebSocket, no chunked transfer. | Return complete responses only. For progress, poll `/v1/jobs/{id}` which includes `progress` field (0.0--1.0). |
| **No OAuth / PKCE** | Cannot implement standard OAuth flows. No browser redirect handling. | Bearer token auth only. Token manually set in Data Jar during setup. Rotate via a separate "refresh token" Shortcut that calls a dedicated endpoint. |
| **No Keychain access** | Secrets cannot be stored securely in iOS Keychain from Shortcuts. | Store bearer token in Data Jar (encrypted at rest by iOS). Accept the tradeoff: Data Jar is app-sandboxed but not hardware-backed like Keychain. |
| **ATS enforcement** | App Transport Security requires HTTPS for all network requests. Plain HTTP blocked. | Tailscale serve provides automatic HTTPS with valid certs. No ATS exceptions needed. `tailscale cert` handles renewal. |

### iOS 26 Use Model Action

| Constraint | Impact | Workaround |
|------------|--------|------------|
| **No custom URL** | Cannot point Use Model at Ollama or custom API. Apple's on-device model only. | Use Model for simple local tasks (text cleanup, classification). Route complex tasks to Mac Mini pipeline via `Get Contents of URL`. |
| **Limited system prompt** | Restricted prompt customization. | Prepend context in user message. Use Mac Mini pipeline for tasks requiring detailed system prompts. |

### Infrastructure

| Constraint | Impact | Workaround |
|------------|--------|------------|
| **Single Mac Mini** | No redundancy. Restart or crash loses all running agents. | SqliteSaver checkpointing enables resume after restart. launchd auto-restarts FastAPI and Ollama. ntfy alerts on service failure. |
| **32GB RAM ceiling** | Limits concurrent model instances. qwen3:14b at 4-bit uses ~10GB. | Queue system with configurable concurrency (default: 1 large + 1 small model). Week 4 multi-agent limited to 2--3 parallel workers. |
| **Tailscale dependency** | No Tailscale = no access from iOS. | Fallback: Cloudflare Tunnel as secondary ingress (not default; adds latency and external dependency). |
