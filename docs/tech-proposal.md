# Tech Proposal: iOS Shortcuts as Agentic Mobile Trigger Layer

**Author:** Wei Xiang Zhang
**Date:** 2026-04-18
**Status:** Draft

---

## 1. Executive Summary

This proposal defines an architecture for using iOS Shortcuts as a thin-client trigger layer that invokes complex, multi-step AI workflows on a Mac Mini M2 Pro (32 GB unified memory) over Tailscale.

Key design decisions:

- **Single webhook pattern.** Every Shortcut POSTs to one `/intent` endpoint. The server decides what to do, not the client.
- **Ollama native Anthropic endpoint.** Ollama 0.14+ exposes `/v1/messages` (Anthropic-compatible), eliminating the need for a custom relay for basic inference.
- **LangGraph 1.0 with SqliteSaver.** Durable, pausable multi-step agent sessions keyed by `conversation_id`, persisted across Shortcut invocations.
- **ntfy for async push-back.** The 202 Accepted + ntfy pattern sidesteps iOS Shortcuts' ~25-second background timeout.
- **Zero secrets on iPhone.** All API keys and credentials remain server-side. The iPhone holds at most a bearer token for defense-in-depth.

---

## 2. Problem Statement

iOS Shortcuts is a powerful automation surface -- Action Button, NFC tags, Focus mode automations, Siri voice triggers -- but it is a severely constrained HTTP client:

- **No streaming.** `stream: false` is mandatory; chunked transfer-encoding causes silent failures.
- **No OAuth flows.** No redirect URI handling, no token refresh.
- **~25-second background timeout.** Background Shortcut execution is killed by the system after roughly 25 seconds.
- **No custom endpoint for "Use Model" action.** The built-in Apple Intelligence action does not accept arbitrary API endpoints.
- **No status code inspection.** Error handling must inspect the response body, not HTTP status codes.
- **1-indexed arrays.** `Get Dictionary Value` uses 1-based indexing, a common source of off-by-one bugs.

Despite these constraints, Shortcuts is the only automation layer on iOS that can be wired to ambient triggers (Action Button press, NFC tap, Focus mode change, Siri invocation) without a custom app. The goal is to bridge these triggers to a full agentic backend running on the Mac Mini.

---

## 3. Proposed Architecture

### 3.1 System Diagram

```
+------------------+         +---------------------+         +------------------+
|   iPhone / iPad  |         |    Tailscale Mesh    |         |  Mac Mini M2 Pro |
|                  |         |                      |         |     (32 GB)      |
|  +-----------+   |  HTTPS  |  tailscale serve     |  HTTP   |  +-----------+   |
|  | Shortcut  |---------->|  :443 -> :8443        |-------->|  | FastAPI   |   |
|  +-----------+   |  TLS    |  (auto LE cert)      |         |  | :8443     |   |
|       |          |         +---------------------+         |  +-----+-----+   |
|       |          |                                          |        |         |
|  +-----------+   |         +---------------------+         |  +-----v-----+   |
|  | ntfy app  |<-----------| ntfy.sh (upstream)   |<--------|  | Background|   |
|  +-----------+   |  APNs   +---------------------+  curl   |  | Tasks     |   |
|       |          |                                          |  +-----+-----+   |
|  +-----------+   |                                          |        |         |
|  | Data Jar  |   |                                          |  +-----v-----+   |
|  | (conv_id) |   |                                          |  | LangGraph |   |
|  +-----------+   |                                          |  | 1.0       |   |
+------------------+                                          |  | SqliteSvr |   |
                                                              |  +-----+-----+   |
                                                              |        |         |
                                                              |  +-----v-----+   |
                                                              |  |  Ollama    |   |
                                                              |  | 127.0.0.1 |   |
                                                              |  |           |   |
                                                              |  | Router:   |   |
                                                              |  |  3B (~2G) |   |
                                                              |  | Worker:   |   |
                                                              |  |  14B(~10G)|   |
                                                              |  +-----------+   |
                                                              +------------------+
```

### 3.2 Request Flow

1. User triggers a Shortcut (Action Button, NFC, Siri, Focus automation).
2. Shortcut captures intent: dictated text, predefined payload, or sensor data.
3. Shortcut POSTs JSON to `https://<tailscale-hostname>:443/intent`:
   ```json
   {
     "source": "action_button",
     "text": "Schedule a deep work block tomorrow morning",
     "timestamp": "2026-04-18T09:30:00-07:00",
     "location": {"lat": 37.78, "lon": -122.41},
     "conversation_id": "abc-123"
   }
   ```
4. FastAPI validates the request, returns `202 Accepted` with a `job_id`.
5. `BackgroundTasks` dispatches to LangGraph:
   - **Router** (llama3.2:3b): classifies intent, selects tools/subgraph.
   - **Worker** (qwen3:14b): executes the multi-step plan.
6. On completion, the server pushes the result via ntfy.
7. iPhone receives the push notification with the response payload.

### 3.3 Server-Side Dispatch

The Shortcut never decides which agent or tool to invoke. It sends raw intent. The server-side router LLM classifies and dispatches. This keeps Shortcuts simple and allows the backend to evolve independently.

---

## 4. Technology Choices & Rationale

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Backend framework** | FastAPI | Native `BackgroundTasks`, Pydantic validation, async-first. Python ecosystem for ML/AI tooling. |
| **Local inference** | Ollama 0.14+ | Native `/v1/messages` (Anthropic-compatible) and `/v1/chat/completions` (OpenAI-compatible). No custom relay needed for basic calls. |
| **Agent orchestration** | LangGraph 1.0 | First-class pause/resume by `thread_id`. `SqliteSaver` for durable checkpoints. Explicit graph topology over implicit chain-of-thought. |
| **Tunnel** | Tailscale `serve` | Identity headers (`Tailscale-User-Login`), no public exposure (unlike `funnel`), auto Let's Encrypt TLS. |
| **Push notifications** | ntfy | Self-hostable, simple `curl` interface, APNs delivery via upstream ntfy.sh. No app signing or certificate management. |
| **Claude Code routing** | claude-code-router | Routes Claude Code CLI requests to local Ollama models when appropriate, falling back to Anthropic API for complex tasks. |
| **Multi-protocol proxy** | LiteLLM (optional) | Unified `/v1/chat/completions` proxy across Ollama, Anthropic, OpenAI. Useful when model count grows beyond two. |

### 4.1 Why Not...

- **Express/Hono (Node.js):** Python ecosystem is stronger for ML tooling. LangGraph is Python-first. No gain from JS here.
- **CrewAI/AutoGen:** Neither supports first-class pause/resume with durable persistence. LangGraph's `SqliteSaver` + `thread_id` is purpose-built for this.
- **Tailscale Funnel:** Exposes the endpoint to the public internet. Serve keeps it mesh-only.
- **Pushover:** Paid, not self-hostable. APNs direct requires app signing.

---

## 5. Security Model

### 5.1 Network Layer

- **Tailscale ACL:** `tag:ios-shortcut` can only reach `tag:ai-backend` on port 8443. No other traffic allowed.
- **Ollama binding:** `OLLAMA_HOST=127.0.0.1:11434`. Not reachable from the network, only from localhost.
- **No public exposure:** `tailscale serve` (not `funnel`). The endpoint is invisible outside the Tailnet.

### 5.2 Authentication

- **Primary:** `Tailscale-User-Login` header, injected by Tailscale serve. Cryptographically tied to the Tailscale identity.
- **Defense-in-depth:** Optional bearer token in the `Authorization` header. Not strictly necessary for solo use but prevents accidental exposure if ACLs are misconfigured.
- **No secrets on iPhone:** iOS Shortcuts cannot read the system Keychain. Any value hardcoded in a Shortcut is visible in plaintext and copied when the Shortcut is shared. All secrets stay server-side.

### 5.3 Prompt Injection Mitigations

- **Confirmation gates:** Destructive actions (file deletion, calendar modification, message sending) require explicit user confirmation via a follow-up ntfy notification.
- **Regex stripping:** Known injection patterns (e.g., "ignore previous instructions") are stripped before LLM input.
- **Tool schema constraints:** LangGraph tool definitions use strict Pydantic schemas. The LLM cannot invoke arbitrary system commands.
- **Daily token budget:** Hard cap on total tokens consumed per 24-hour window. Prevents runaway loops.

### 5.4 Tunnel Reliability

- **VPN On Demand:** iOS VPN On Demand rules keep the Tailscale tunnel active. Mitigates the known tunnel-drop issue (tailscale/tailscale#16240).
- **Warm-up pings:** A scheduled Shortcut automation pings the server every 30 minutes to keep the tunnel warm.

---

## 6. Memory & Compute Budget

### 6.1 Memory Allocation (32 GB Unified)

| Component | Estimate |
|-----------|----------|
| macOS + system services | ~8-10 GB |
| llama3.2:3b (router) | ~2 GB |
| qwen3:14b (worker) | ~10 GB |
| KV cache + FastAPI + LangGraph | ~10 GB headroom |
| **Total** | ~30-32 GB |

### 6.2 Ollama Configuration

```bash
OLLAMA_HOST=127.0.0.1:11434
OLLAMA_MAX_LOADED_MODELS=2
OLLAMA_NUM_PARALLEL=2
OLLAMA_FLASH_ATTENTION=1        # Disable for Gemma 3/4 models
OLLAMA_KEEP_ALIVE=-1            # Never unload (cold start mitigation)
```

### 6.3 Context Window

`num_ctx` must be set in the Modelfile, not at request time, due to Ollama's allocation behavior. Default 2048 is insufficient for agentic workloads.

```
# Modelfile.router
FROM llama3.2:3b
PARAMETER num_ctx 4096

# Modelfile.worker
FROM qwen3:14b
PARAMETER num_ctx 8192
```

---

## 7. iOS Shortcuts Design

### 7.1 Thin-Client Philosophy

Every Shortcut follows the same pattern:

1. **Capture** -- Dictate Text, clipboard, NFC payload, or hardcoded intent.
2. **POST** -- Send JSON to `/intent`.
3. **Display** -- Show the synchronous acknowledgment ("Got it, working on it...").
4. **Receive** -- Result arrives via ntfy push notification.

### 7.2 Trigger Types

| Trigger | Capture Method | Payload |
|---------|---------------|---------|
| **Action Button** | Dictate Text | Free-form text |
| **NFC tag** | NFC payload | Predefined intent string (e.g., `desk:start_focus`) |
| **Siri** | Voice input | Free-form text with `source: "siri"` |
| **Focus mode** | Automation | Predefined context payload (e.g., `focus:work_started`) |

### 7.3 Platform Quirks

- **`stream: false` is mandatory.** Include it in every request body. Streaming responses cause Shortcuts to hang or return empty data.
- **1-indexed arrays.** `Get Item from List` at index 1 returns the first element. Off-by-one bugs are the most common Shortcut failure mode.
- **No HTTP status codes.** The "Get Contents of URL" action does not expose status codes. Error detection must parse the response body for an `"error"` key.
- **Import Questions for secrets.** If a Shortcut must contain a server URL or token, use Import Questions so the value is prompted on install rather than hardcoded.

### 7.4 Conversation Persistence

- `conversation_id` is stored in **Data Jar** (a key-value store app for Shortcuts).
- On first invocation, the server generates a `conversation_id` and returns it in the 202 response.
- The Shortcut saves it to Data Jar. Subsequent invocations include it in the POST body.
- LangGraph uses `conversation_id` as the `thread_id` for `SqliteSaver`, enabling multi-turn conversations across separate Shortcut runs.

---

## 8. Multi-Agent Extension

Once the single-agent pipeline is stable, the architecture extends to multi-agent coordination.

### 8.1 Parallel Execution

- **claude --worktree:** Isolated git worktrees for parallel Claude Code sessions. Each agent works on a separate branch without conflicts.
- **parallel-code:** Mobile monitoring dashboard for concurrent agent sessions. Accessible via QR code over Wi-Fi or Tailscale.

### 8.2 Swarm Coordination

- **Bun/Hono claude-relay:** Lightweight relay server for Nostr-based inter-agent messaging. Agents publish events to Nostr relays; other agents subscribe and react.
- **TeammateTool inbox protocol:** Structured message passing between agents. Each agent has an inbox; messages are typed (request, response, status update).
- **claude-squad:** Manual TUI oversight for monitoring and intervening in multi-agent workflows from a terminal.

### 8.3 Mobile Monitoring

- **parallel-code dashboard:** Web UI showing active agents, their current tasks, token usage, and status. Accessible from iPhone over Tailscale.
- **ntfy channels:** Per-agent ntfy topics for granular notification control.

---

## 9. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **25-second background timeout** | Background Shortcuts killed mid-request | 202 Accepted + ntfy async pattern. Server responds immediately; result pushed later. |
| **Tailscale tunnel drops** (tailscale/tailscale#16240) | Requests fail silently | VPN On Demand rules. Warm-up pings every 30 min. Retry logic in Shortcut (up to 2 retries). |
| **Model cold start** | First request takes 30-60s to load model | `OLLAMA_KEEP_ALIVE=-1` (never unload). `launchd` plist sends a warm-up prompt on boot. |
| **Prompt injection** | Attacker-controlled input triggers unintended actions | Confirmation gates for destructive actions. Regex stripping. Tool schema constraints. |
| **Shortcut sharing leaks secrets** | Bearer tokens exposed in shared Shortcuts | Import Questions for all configurable values. No hardcoded secrets. |
| **`keep_alive` ignored on `/v1/chat/completions`** (ollama/ollama#11458) | Models unload unexpectedly | Use `/api/chat` or `/v1/messages` endpoints instead. Set `OLLAMA_KEEP_ALIVE` env var as fallback. |
| **`num_ctx` ignored at request time** | Context window too small for agent workloads | Set `num_ctx` in Modelfile. Create custom model variants. |
| **OOM under dual-model load** | System instability | Memory budget validated (Section 6). `OLLAMA_MAX_LOADED_MODELS=2` hard cap. Monitor via `vm_stat`. |

---

## 10. Implementation Phases

### Phase 1: Infrastructure (Week 1)

- [ ] Configure Tailscale ACLs (`tag:ios-shortcut`, `tag:ai-backend`)
- [ ] Set up `tailscale serve` HTTPS on port 8443
- [ ] Deploy FastAPI skeleton with `/intent` endpoint and health check
- [ ] Configure Ollama with Modelfiles for router (3B) and worker (14B)
- [ ] Validate dual-model loading and memory usage

### Phase 2: Orchestration (Week 2)

- [ ] Implement LangGraph router subgraph (intent classification)
- [ ] Implement LangGraph worker subgraph (task execution)
- [ ] Set up SqliteSaver for conversation persistence
- [ ] Implement job queue and status tracking
- [ ] Integrate ntfy push-back (result delivery, error notifications)
- [ ] Add token budget tracking and enforcement

### Phase 3: iOS Integration (Week 3)

- [ ] Build Action Button Shortcut (dictation -> POST -> display ack)
- [ ] Build NFC tag Shortcuts (desk context triggers)
- [ ] Implement Data Jar conversation persistence
- [ ] Configure VPN On Demand for tunnel reliability
- [ ] Build warm-up ping automation
- [ ] Test error handling (timeout, tunnel drop, server error)

### Phase 4: Multi-Agent & Monitoring (Week 4)

- [ ] Set up claude --worktree for parallel sessions
- [ ] Deploy parallel-code monitoring dashboard
- [ ] Implement Nostr-based swarm relay (stretch goal)
- [ ] Configure per-agent ntfy channels
- [ ] Build claude-squad integration for TUI oversight
- [ ] End-to-end testing of all trigger types

---

## 11. Success Criteria

| Criterion | Target |
|-----------|--------|
| Action Button -> dictation -> server response | < 30 seconds (foreground), async ntfy (background) |
| NFC tap -> context-specific workflow triggered | < 5 seconds to 202 acknowledgment |
| Multi-turn conversation persistence | Across Shortcut invocations, verified over 10+ turns |
| Secrets stored on iPhone | Zero |
| Concurrent model loading (3B + 14B) | No OOM, < 30 GB total memory usage |
| Tunnel reliability over 24 hours | > 99% uptime with VPN On Demand |
| Daily token budget enforcement | Hard stop at configured limit |

---

## Appendix: Reference Links

- [Tailscale Serve docs](https://tailscale.com/kb/1242/tailscale-serve)
- [Ollama API compatibility](https://github.com/ollama/ollama/blob/main/docs/openai.md)
- [LangGraph persistence](https://langchain-ai.github.io/langgraph/concepts/persistence/)
- [ntfy documentation](https://docs.ntfy.sh/)
- [iOS Shortcuts HTTP limitations](https://support.apple.com/guide/shortcuts/intro-to-web-api-actions-apd2e30c8c85/ios)
- [Ollama keep_alive issue #11458](https://github.com/ollama/ollama/issues/11458)
- [Tailscale tunnel drop issue #16240](https://github.com/tailscale/tailscale/issues/16240)
