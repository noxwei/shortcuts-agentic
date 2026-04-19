# Cherri Viability Assessment

**Project:** shortcuts-agentic
**Date:** 2026-04-18
**Subject:** Cherri (cherrilang.org) — a programming language that compiles to signed .shortcut files

---

## 1. What Cherri Is

Cherri is a Go-based programming language that compiles `.cherri` source files directly into signed `.shortcut` binary plist files. It provides a 1-to-1 mapping to Shortcut actions with Go/Ruby-inspired syntax, type inference, function scoping, file includes, and copy/paste macros.

- **Version:** 2.1.1 (March 30, 2026)
- **Health:** 1.4k GitHub stars, 2,010 commits, 44 releases, 7 open issues — actively maintained
- **Tooling:** CLI compiler, macOS IDE app (Swift, v1.2), VS Code extension, online playground
- **Coverage:** 23+ action categories including network, scripting, cryptography, and web
- **Signing:** Native macOS signing, HubSign fallback, shortcut-signing-server compatible
- **Distribution:** AirDrop, open .shortcut file, iCloud link (no OTA push)

---

## 2. Relevance to shortcuts-agentic

The shortcuts-agentic architecture is a thin-client pattern: Shortcuts POST JSON to a single `/intent` endpoint on the Mac Mini over Tailscale. The Shortcut itself is intentionally simple — it gathers context (text input, clipboard, location), constructs a JSON body, calls `Get Contents of URL`, and displays the response or subscribes to ntfy for async results.

Cherri does not change what Shortcuts can do. It changes how you author, version, and deploy them.

This is a maintainability tool, not a capability tool. That distinction matters.

---

## 3. Key Advantages

### Version control
`.cherri` files are plain text. They go in git. You get diffs, blame, branch-per-feature, and PR review for your Shortcuts. Compare this to the current state: opaque iCloud-synced plist blobs with no history and no way to diff two versions.

### Reproducible builds
`cherri file.cherri` produces a deterministic signed `.shortcut`. No manual editing in the Shortcuts app, no "I think I changed that action last week." CI can compile and verify.

### Parameterized compilation
Includes and macros allow compile-time substitution. Practical uses:
- Swap endpoint URLs between dev (`http://localhost:8443`) and prod (`https://mac-mini.tail1234.ts.net`)
- Inject bearer tokens per environment
- Toggle debug logging actions on/off

### Raw action support
The `#define` and raw action syntax means custom actions (Sindre Sorhus Actions, Scriptable intents, third-party app intents) can be invoked without waiting for Cherri to add first-class support.

### Modular Shortcut libraries
Function scoping and file includes allow factoring out common patterns — the JSON body construction, the ntfy subscription flow, the error display logic — into reusable modules. Write the "call /intent and handle response" pattern once, include it everywhere.

### Type safety
Type inference catches mismatched variable types before you deploy to the phone. This eliminates a class of silent runtime failures that are painful to debug in the Shortcuts app.

---

## 4. Risks and Limitations

### Distribution gap (high impact)
There is no way to OTA-push a compiled `.shortcut` to an iPhone from the CLI. You must AirDrop it, open the file manually, or share via iCloud link. This is the single biggest friction point. Every recompile requires a manual install step.

Mitigation: `open file.shortcut` on macOS opens the Shortcuts app and prompts import. For iPhone, AirDrop from the Mac Mini is the least-friction path. A GitHub Release artifact workflow could also host `.shortcut` files for download.

### Signing complexity (medium impact)
Native signing requires macOS. If you ever need to compile on Linux (e.g., GitHub Actions on ubuntu runners), you need HubSign or a signing server. The macOS-only path is fine for this project since the Mac Mini is the build machine.

### Learning curve (medium impact)
Cherri is another DSL to learn and maintain. For a team of one, the question is whether the time spent learning Cherri pays back in reduced time wrangling the Shortcuts GUI. For 2-3 simple Shortcuts, it probably does not. For 5+ Shortcuts with shared patterns, it does.

### No package manager (low impact)
Planned but not shipped. For this project, file includes within the repo are sufficient. A package manager would matter if you needed to consume community-maintained action libraries.

### Network action coverage (must verify)
The entire shortcuts-agentic architecture depends on `Get Contents of URL` with JSON body, custom headers (Authorization bearer), and POST method. This must be verified against Cherri's network action support before adoption. If Cherri cannot express custom headers or JSON body construction, it is a blocker.

### Playground expiry (irrelevant)
The 5-day playground link expiry does not matter. Source lives in git; the playground is for experimentation only.

---

## 5. Integration Pattern

If adopted, Cherri fits into the build pipeline as follows:

```
shortcuts-agentic/
  shortcuts/
    common/
      intent-call.cherri      # shared: POST to /intent, handle response
      ntfy-subscribe.cherri   # shared: subscribe to ntfy topic
      error-display.cherri    # shared: show error alert
    action-button.cherri      # Action Button trigger
    nfc-tag.cherri            # NFC tap trigger
    siri-query.cherri         # Siri voice trigger
  Makefile
```

**Makefile targets:**

```makefile
CHERRI := cherri
SHORTCUT_DIR := build/shortcuts
ENV ?= prod

shortcuts: $(SHORTCUT_DIR)/action-button.shortcut $(SHORTCUT_DIR)/nfc-tag.shortcut

$(SHORTCUT_DIR)/%.shortcut: shortcuts/%.cherri shortcuts/common/*.cherri
	$(CHERRI) $< -o $@

install: shortcuts
	open $(SHORTCUT_DIR)/*.shortcut

clean:
	rm -rf $(SHORTCUT_DIR)
```

**Environment parameterization** would use Cherri macros or a preprocessing step to inject the correct endpoint URL and bearer token at compile time.

**CI integration:** A GitHub Action on the `master` branch compiles all `.cherri` files on a macOS runner and attaches the signed `.shortcut` files as release artifacts.

---

## 6. Decision Framework

| Condition | Recommendation |
|---|---|
| 1-2 simple Shortcuts, no parameterization needed | Skip Cherri. Use the visual editor. |
| 3+ Shortcuts with shared patterns (e.g., all call /intent) | Adopt Cherri. The modular includes pay for themselves. |
| Need dev/prod endpoint switching | Adopt Cherri. Parameterized builds are the cleanest solution. |
| Need CI-compiled Shortcuts on push | Adopt Cherri. No alternative provides this. |
| Frequently iterating on Shortcut logic | Adopt Cherri. Text editor + recompile beats the Shortcuts GUI drag-and-drop. |

---

## 7. Verdict

**Adopt Cherri, but not on day one.**

Phase 1 of shortcuts-agentic (the tech proposal's "Hello World" milestone) should build the first Shortcut manually in the Shortcuts app. This validates the `/intent` endpoint, the Tailscale TLS path, and the ntfy async pattern without introducing a second new tool.

Phase 2 — when the architecture is proven and you are building out additional Shortcuts (Action Button, NFC, Siri, Focus automations) — is the right time to adopt Cherri. At that point you have:
- Multiple Shortcuts sharing the same POST-to-/intent pattern
- A need for dev/prod endpoint switching
- Enough Shortcut logic that version control becomes valuable

Before adopting, verify one thing: that Cherri's network actions support `Get Contents of URL` with custom headers, POST method, and JSON request body. If that works, Cherri is a clear win for maintainability at scale.

The tool is mature (44 releases, active maintenance), the risk is low (you can always fall back to the visual editor), and the upside — git-tracked, reproducible, parameterized Shortcuts — directly addresses the pain points of managing multiple Shortcuts in a serious automation pipeline.
