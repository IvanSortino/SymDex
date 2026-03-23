# Search ROI Summary Design

Status: shipped
Date: 2026-03-22

## Goal

After SymDex returns a useful search result, show the agent and the human roughly how much reading and token spend were avoided.

## Shipped Output Shape

Successful search-oriented commands print an approximate ROI footer that includes:

- lines searched
- tokens that would likely have been spent without SymDex
- tokens used with SymDex
- tokens saved

The footer is intentionally approximate and uses a default tokenizer profile rather than pretending to be billing-grade accounting.

Example:

```text
Without SymDex: ~7,500 tokens
With SymDex: ~200 tokens
Saved: ~7,300 tokens
You are in good hands.
```

## Design Choices

- one default tokenizer profile for consistency
- explicit approximation language instead of false precision
- playful closing line kept short so it adds personality without clutter
- same metric family reused in CLI output and MCP payloads
