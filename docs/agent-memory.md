# Agent memory

Rogue Collage keeps durable artist preferences and working conventions in `runtime-data/memory.md` (or `memory.md` beneath `COLLAGE_DATA_DIR` when configured). The service creates a basic template on startup if the file does not exist. Existing content is preserved.

Open **Settings → Agent → Memory**, edit the Markdown, and use its save action. You can also edit the local file directly. Saved content is included in every subsequent planning request through either the LLM API or ACPX connector. It is therefore sent to the selected assistant provider along with the conversation; keep credentials out of it.

This is an explicit, manually maintained memory file. The agent does not automatically rewrite it, extract memories from chat, or maintain an external memory database. Store lasting preferences and useful conventions; leave temporary task progress, job IDs and current selections in the active conversation/project.

The design borrows the small, curated Markdown memory pattern from [Hermes Agent's official persistent-memory documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory/). Rogue Collage combines preferences and conventions into one editable file, refreshes it on each planning request, and does not copy Hermes's character caps or automatic memory-writing tools.

## HTTP API

- `GET /api/agent/memory` returns `{ "content": "...Markdown..." }`.
- `PUT /api/agent/memory` accepts and returns the same shape. Saving replaces the file atomically.

Memory is local service state, shared by this installation's projects. It is not a project ZIP asset. Back up the file separately when moving the installation.
