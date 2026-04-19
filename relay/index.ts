import { Hono } from "hono";
import { cors } from "hono/cors";

// --- Types ---

interface NostrEvent {
  id: string;
  pubkey: string;
  created_at: number;
  kind: number;
  tags: string[][];
  content: string;
  sig: string;
}

interface Subscription {
  id: string;
  filters: NostrFilter[];
}

interface NostrFilter {
  ids?: string[];
  authors?: string[];
  kinds?: number[];
  since?: number;
  until?: number;
  limit?: number;
  [key: string]: any; // tag filters like #e, #p
}

// --- In-memory store ---

const MAX_EVENTS = 1000;
const events: NostrEvent[] = [];

function storeEvent(event: NostrEvent): boolean {
  // Deduplicate by id
  if (events.some((e) => e.id === event.id)) return false;
  events.push(event);
  // Evict oldest when over limit
  while (events.length > MAX_EVENTS) {
    events.shift();
  }
  return true;
}

function matchesFilter(event: NostrEvent, filter: NostrFilter): boolean {
  if (filter.ids && !filter.ids.includes(event.id)) return false;
  if (filter.authors && !filter.authors.includes(event.pubkey)) return false;
  if (filter.kinds && !filter.kinds.includes(event.kind)) return false;
  if (filter.since && event.created_at < filter.since) return false;
  if (filter.until && event.created_at > filter.until) return false;
  return true;
}

function queryEvents(filter: NostrFilter): NostrEvent[] {
  const matched = events.filter((e) => matchesFilter(e, filter));
  // Sort newest first
  matched.sort((a, b) => b.created_at - a.created_at);
  const limit = filter.limit ?? 100;
  return matched.slice(0, limit);
}

// --- WebSocket subscription management ---

const subscriptions = new Map<WebSocket, Map<string, NostrFilter[]>>();

function addSubscription(ws: WebSocket, subId: string, filters: NostrFilter[]) {
  if (!subscriptions.has(ws)) {
    subscriptions.set(ws, new Map());
  }
  subscriptions.get(ws)!.set(subId, filters);
}

function removeSubscription(ws: WebSocket, subId: string) {
  subscriptions.get(ws)?.delete(subId);
}

function removeAllSubscriptions(ws: WebSocket) {
  subscriptions.delete(ws);
}

function broadcastEvent(event: NostrEvent) {
  for (const [ws, subs] of subscriptions) {
    for (const [subId, filters] of subs) {
      if (filters.some((f) => matchesFilter(event, f))) {
        try {
          ws.send(JSON.stringify(["EVENT", subId, event]));
        } catch {
          // Client disconnected, will be cleaned up
        }
      }
    }
  }
}

// --- NIP-01 WebSocket handler ---

function handleMessage(ws: WebSocket, data: string | Buffer) {
  let msg: any[];
  try {
    msg = JSON.parse(typeof data === "string" ? data : data.toString());
  } catch {
    ws.send(JSON.stringify(["NOTICE", "invalid JSON"]));
    return;
  }

  if (!Array.isArray(msg) || msg.length < 2) {
    ws.send(JSON.stringify(["NOTICE", "invalid message format"]));
    return;
  }

  const type = msg[0];

  switch (type) {
    case "EVENT": {
      const event = msg[1] as NostrEvent;
      if (!event?.id || !event?.kind) {
        ws.send(JSON.stringify(["NOTICE", "invalid event"]));
        return;
      }
      const stored = storeEvent(event);
      // NIP-01: send OK
      ws.send(JSON.stringify(["OK", event.id, stored, stored ? "" : "duplicate:"]));
      if (stored) {
        broadcastEvent(event);
        console.log(`[nostr] Event ${event.id.slice(0, 8)} kind=${event.kind} stored & broadcast`);
      }
      break;
    }

    case "REQ": {
      const subId = msg[1] as string;
      const filters = msg.slice(2) as NostrFilter[];
      addSubscription(ws, subId, filters);
      // Send matching stored events
      for (const filter of filters) {
        for (const event of queryEvents(filter)) {
          ws.send(JSON.stringify(["EVENT", subId, event]));
        }
      }
      // NIP-01: EOSE (End of Stored Events)
      ws.send(JSON.stringify(["EOSE", subId]));
      break;
    }

    case "CLOSE": {
      const subId = msg[1] as string;
      removeSubscription(ws, subId);
      break;
    }

    default:
      ws.send(JSON.stringify(["NOTICE", `unknown message type: ${type}`]));
  }
}

// --- Hono HTTP API ---

const app = new Hono();

app.use("*", cors());

app.get("/health", (c) =>
  c.json({
    status: "ok",
    events: events.length,
    connections: subscriptions.size,
    uptime: process.uptime(),
  })
);

// POST /relay/broadcast — publish a Nostr event (for FastAPI to call)
app.post("/relay/broadcast", async (c) => {
  const body = await c.req.json<NostrEvent>();
  if (!body.id || !body.kind) {
    return c.json({ error: "missing id or kind" }, 400);
  }
  // Set created_at if not provided
  if (!body.created_at) {
    body.created_at = Math.floor(Date.now() / 1000);
  }
  // Default empty fields
  body.pubkey = body.pubkey || "fastapi-swarm";
  body.tags = body.tags || [];
  body.content = body.content || "";
  body.sig = body.sig || "";

  const stored = storeEvent(body);
  if (stored) {
    broadcastEvent(body);
    console.log(`[http] Broadcast event ${body.id.slice(0, 8)} kind=${body.kind}`);
  }
  return c.json({ ok: true, stored, id: body.id });
});

// GET /relay/events — list recent events, optional ?kind= filter
app.get("/relay/events", (c) => {
  const kindParam = c.req.query("kind");
  const limitParam = c.req.query("limit");
  const filter: NostrFilter = {};
  if (kindParam) filter.kinds = [Number(kindParam)];
  filter.limit = limitParam ? Number(limitParam) : 50;
  return c.json(queryEvents(filter));
});

// --- Server ---

const PORT = Number(process.env.RELAY_PORT || 8201);

console.log(`[relay] Agent coordination relay starting on http://0.0.0.0:${PORT}`);
console.log(`[relay] WebSocket: ws://0.0.0.0:${PORT}/ws`);

export default {
  port: PORT,
  hostname: "0.0.0.0",
  fetch(req: Request, server: any): Response | Promise<Response> {
    const url = new URL(req.url);
    // Upgrade WebSocket at /ws
    if (
      url.pathname === "/ws" &&
      req.headers.get("upgrade")?.toLowerCase() === "websocket"
    ) {
      const success = server.upgrade(req);
      if (success) return undefined as any;
      return new Response("WebSocket upgrade failed", { status: 400 });
    }
    return app.fetch(req, server);
  },
  websocket: {
    maxPayloadLength: 64 * 1024, // 64KB
    open(ws: any) {
      console.log(`[nostr] WS connected (${subscriptions.size + 1} clients)`);
    },
    close(ws: any) {
      removeAllSubscriptions(ws);
      console.log(`[nostr] WS disconnected (${subscriptions.size} clients)`);
    },
    message(ws: any, data: string | Buffer) {
      handleMessage(ws, data);
    },
  },
};
