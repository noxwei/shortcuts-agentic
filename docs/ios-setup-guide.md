# iOS Setup Guide

## Control Center Widget (S-7)
1. Open Settings > Control Center
2. Tap + next to "Shortcuts"
3. Select "Quick Ask" as the shortcut to run
4. The widget appears in Control Center -- one tap to ask a question

## Disable Siri When Locked (X-4)
For shortcuts that invoke tools (Action Button, AI Research Assistant):
1. Open Shortcuts app
2. Long-press the shortcut > Details
3. Disable "Show When Run" if you don't want UI
4. Go to Settings > Siri & Search > [shortcut name] > disable "Use with Lock Screen"

## Import Questions for Sharing (X-5)
Before sharing any shortcut via iCloud link:
1. Open the shortcut in Shortcuts editor
2. Tap the (i) info button
3. Under "Setup", add Import Questions for the API Token variable
4. This ensures recipients are prompted to enter their own token

## VPN On Demand (X-6)
1. Open Tailscale app on iPhone
2. Go to Settings (gear icon)
3. Enable "Connect on Demand" / "VPN On Demand"
4. This ensures the Tailscale tunnel is always up when Shortcuts fire HTTP requests
5. Test: run "Status Check" shortcut -- if it returns "ok", the tunnel is working
