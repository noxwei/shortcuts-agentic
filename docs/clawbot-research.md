# OpenClaw (formerly Clawdbot / Moltbot) Research

Research date: 2026-04-18

## Identity

The project is real. The naming history is confirmed:

- **Clawdbot** (original name)
- **Moltbot** (intermediate rename)
- **OpenClaw** (current name)

The Cloudflare community repo (`cloudflare/moltworker`) explicitly states: "Run OpenClaw, (formerly Moltbot, formerly Clawdbot) on Cloudflare Workers." The rename sequence appears to have been driven by trademark concerns (the "Claud" in "Clawdbot" was too close to Anthropic's Claude).

| Field | Value |
|-------|-------|
| GitHub | [openclaw/openclaw](https://github.com/openclaw/openclaw) |
| Website | [openclaw.ai](https://openclaw.ai) |
| Docs | [docs.openclaw.ai](https://docs.openclaw.ai) |
| Language | TypeScript (Node 24 / Node 22.16+) |
| License | MIT |
| Stars | ~360k |
| Forks | ~73k |
| Creator | Peter Steinberger ([@steipete](https://github.com/steipete)) — 18,673 commits |
| Latest release | v2026.4.15 (2026-04-16) |
| Release cadence | Weekly stable + beta prereleases |
| Skills registry | [ClawHub](https://clawhub.com) — 5,400+ community skills |

## What it is

OpenClaw is a **local-first personal AI assistant** you run on your own hardware. The core is a TypeScript **Gateway** daemon that acts as a control plane: it manages sessions, channels (messaging platforms), tools, agents, and events. The Gateway is the product — companion apps are optional.

It is **not** a model runtime. It calls external LLM providers (Anthropic/Claude, OpenAI, OpenRouter, custom) via API. It is an orchestration layer that routes messages from 24+ channels into agent sessions backed by those models.

## Architecture

```
iOS/Android Nodes ──┐
macOS App ──────────┤
CLI ────────────────┼──── WebSocket ────> Gateway (port 18789)
Web Admin ──────────┤                        │
Automations ────────┘                        ├── Agent sessions (LLM calls)
                                             ├── Channel connections
                                             │   (WhatsApp, Telegram, Slack, Discord,
                                             │    Signal, iMessage, Matrix, Nostr, etc.)
                                             ├── Tools (browser, canvas, cron, etc.)
                                             └── Skills (~/.openclaw/workspace/skills/)
```

- **Gateway**: Single-port daemon (default 18789). Exposes HTTP + WebSocket on the same port. Manages all state.
- **Agents**: LLM-backed sessions. Configurable model, workspace, tools, sandbox mode.
- **Channels**: 24+ messaging platforms. Each channel bridges inbound messages into agent sessions.
- **Nodes**: iOS/Android/macOS devices that connect via WebSocket, providing device capabilities (camera, canvas, voice, location).
- **Skills**: Modular prompt+tool bundles in the workspace. Community registry at ClawHub.

## Supported channels (24+)

WhatsApp, Telegram, Slack, Discord, Google Chat, Signal, iMessage, BlueBubbles, IRC, Microsoft Teams, Matrix, Feishu, LINE, Mattermost, Nextcloud Talk, Nostr, Synology Chat, Tlon, Twitch, Zalo, Zalo Personal, WeChat, QQ, WebChat.

## LLM provider support

- Anthropic / Claude (API key or Claude CLI)
- OpenAI
- OpenRouter (free model catalog scanning)
- Custom providers via `models.json`
- No explicit Ollama documentation found, but custom provider config likely supports it

## HTTP API (relevant for Shortcuts integration)

### OpenAI-compatible endpoints

The Gateway exposes OpenAI-compatible HTTP endpoints on port 18789:

- `GET /v1/models` — model discovery
- `POST /v1/chat/completions` — chat inference
- `POST /v1/responses` — response generation
- `POST /v1/embeddings` — embeddings
- `POST /tools/invoke` — tool execution

Auth: `Authorization: Bearer <token>` or gateway password.

### Webhook endpoints

Enable via config (`hooks.enabled: true`, `hooks.token`, `hooks.path: "/hooks"`):

- `POST /hooks/wake` — enqueue a system event for the main session
  - Params: `text` (required), `mode` (`now` | `next-heartbeat`)
- `POST /hooks/agent` — run an isolated agent turn
  - Params: `message` (required), `name`, `agentId`, `model`, `thinking`, `deliver`, `channel`, `to`, `timeoutSeconds`
- `POST /hooks/<name>` — custom hooks via `hooks.mappings` config

Auth: `Authorization: Bearer <hook-token>` header.

Example (curl):
```bash
curl -X POST http://127.0.0.1:18789/hooks/agent \
  -H 'Authorization: Bearer SECRET' \
  -H 'Content-Type: application/json' \
  -d '{"message":"Summarize inbox","name":"Email","model":"openai/gpt-5.4-mini"}'
```

This is directly callable from an iOS Shortcut via "Get Contents of URL."

## Tailscale integration

First-class Tailscale support with three modes:

1. **Serve** (tailnet-only): `tailscale serve` wraps the gateway with HTTPS + identity headers. Access via MagicDNS hostname.
2. **Funnel** (public): Exposes gateway publicly via `tailscale funnel`. Ports 443, 8443, 10000.
3. **Off** (default): No Tailscale automation; manual setup.

Config example (tailnet-only):
```json5
{ gateway: { bind: "loopback", tailscale: { mode: "serve" } } }
```

Auth can use Tailscale identity headers (`gateway.auth.allowTailscale: true`) for dashboard access, but API endpoints still require token auth.

There is also an Ansible playbook: [openclaw/openclaw-ansible](https://github.com/openclaw/openclaw-ansible) — "Automated, hardened Clawdbot installation with Tailscale VPN, UFW firewall, and Docker isolation."

## iOS integration

The iOS app is currently in **internal preview** (not on App Store). It:

- Connects as a "node" to the Gateway via WebSocket (LAN Bonjour discovery or Tailscale)
- Provides Canvas rendering, camera, screen capture, location, voice
- Requires operator approval via `openclaw devices approve`
- Voice: wake word detection + talk mode (best-effort in background due to iOS audio policies)

**No Shortcuts or Siri integration documented.** The iOS app is a node, not a Shortcuts action provider.

However, this does not matter for our use case. The Gateway HTTP API is the integration surface — Shortcuts call the webhook endpoints directly.

## Security model

- DM pairing by default: unknown senders get a pairing code, must be approved
- Sandbox mode for non-main sessions (Docker isolation)
- Tools run on host for main session (full access)
- CVE-2026-25253 exists (one-click RCE PoC published by ethiack) — check if patched in current release

---

## Integration assessment for iOS Shortcuts pipeline

### Can an iOS Shortcut trigger OpenClaw actions via HTTP?

**Yes, cleanly.** The `/hooks/agent` endpoint is purpose-built for this:

```
POST http://<tailscale-ip>:18789/hooks/agent
Authorization: Bearer <token>
Content-Type: application/json

{"message": "Do the thing", "deliver": true, "channel": "telegram", "to": "+1234567890"}
```

This runs an agent turn and optionally delivers the result to any connected channel. An iOS Shortcut using "Get Contents of URL" can do this trivially.

The `/hooks/wake` endpoint is also useful for event-driven triggers (e.g., "new email arrived" -> wake the agent).

### Does it overlap or complement the FastAPI + LangGraph + Ollama architecture?

**It overlaps significantly, but at a different layer.**

| Concern | Shortcuts-agentic (planned) | OpenClaw |
|---------|---------------------------|----------|
| Trigger layer | iOS Shortcuts -> FastAPI | iOS Shortcuts -> Gateway webhooks |
| Orchestration | LangGraph (Python) | Built-in agent sessions (TypeScript) |
| LLM runtime | Ollama (local) | External API (Claude, OpenAI, OpenRouter) |
| Channel routing | Custom relay | 24+ channels built-in |
| Tools | Custom Python tools | Skills ecosystem (5,400+ community) |
| Voice | Not planned | Built-in (wake word, TTS) |

Key differences:
- OpenClaw does **not** run local models via Ollama. It calls cloud APIs. If local inference is a hard requirement, OpenClaw does not replace Ollama.
- OpenClaw's orchestration is opinionated (single-agent sessions with tool calls). LangGraph offers multi-agent graphs, conditional routing, human-in-the-loop. More flexible but more complex.
- OpenClaw's channel support is vastly superior. Building WhatsApp/Telegram/Signal bridges from scratch is months of work that OpenClaw handles out of the box.

### Would it replace components?

- **The relay**: Yes. OpenClaw's channel system replaces any custom message relay entirely.
- **The orchestrator**: Partially. For simple "receive trigger -> call LLM -> return result" flows, OpenClaw's agent sessions suffice. For complex multi-step graphs with branching logic, LangGraph is more capable.
- **The trigger layer**: Partially. Webhooks replace the need for a custom FastAPI endpoint for Shortcuts triggers. But if you need custom business logic before the LLM call (database lookups, validation, multi-step preprocessing), a FastAPI layer in front still makes sense.

### Recommendation

**Use OpenClaw as the channel layer and agent runtime. Do not rebuild what it already does.**

Concrete plan:
1. Install OpenClaw on the Mac Mini, configure with `tailscale: { mode: "serve" }`.
2. Point iOS Shortcuts at `POST /hooks/agent` for direct agent invocations.
3. Connect WhatsApp/Telegram/Signal/iMessage channels as needed — this is OpenClaw's core strength.
4. For simple tasks (summarize, draft, lookup), OpenClaw's built-in agent sessions are sufficient.
5. For complex agentic workflows (multi-step pipelines, tool chains, conditional logic), either:
   - Write OpenClaw skills (SKILL.md + tool definitions) for the workflows, or
   - Keep a separate FastAPI + LangGraph service for complex orchestration and have OpenClaw call it as a tool, or have Shortcuts call it directly for those specific flows.
6. Ollama can still serve local embeddings/small models for tasks where you want zero cloud dependency. OpenClaw and Ollama are not mutually exclusive — they serve different purposes.

### Risks

- **CVE-2026-25253**: One-click RCE vulnerability. Verify it is patched before exposing to any network.
- **Node 24 dependency**: Requires a current Node.js runtime. Not onerous but adds to the stack.
- **Cloud LLM dependency**: OpenClaw calls external APIs. No offline/local-only mode for inference documented.
- **iOS app in preview**: The native iOS app is not yet public. But this is irrelevant — Shortcuts integration is via HTTP, not the app.
- **Complexity**: 360k stars, massive community, rapid release cadence. This is a fast-moving project. Staying current requires attention.

### Verdict

**Worth adding to the stack.** OpenClaw solves the hardest parts of the pipeline (channel bridging, agent session management, webhook triggers) and has first-class Tailscale support. It does not replace Ollama for local inference or LangGraph for complex orchestration, but it eliminates the need to build a custom relay, channel connectors, or trigger endpoint. The `/hooks/agent` API is exactly what an iOS Shortcut needs.
