---
name: neorag
description: SPT NeoRAG — enterprise RAG over your own knowledge bases (documents, semantic + hybrid + knowledge-graph retrieval). Use when the user wants to search their NeoRAG knowledge bases, ingest documents, ask questions grounded in their corpus, or manage KBs/documents. All access goes through the neorag MCP tools; the instance URL and API key come from the plugin configuration (never hardcode a key).
---

# NeoRAG — enterprise RAG in Claude Code

You have access to **SPT NeoRAG** by **Sponge Theory**: an enterprise RAG platform
exposing knowledge bases, document ingestion, semantic/hybrid/knowledge-graph
retrieval, and structured extraction. The MCP server is declared in this plugin's
`.mcp.json` and authenticated over HTTPS with the NeoRAG instance URL and API key
the user entered when enabling the plugin (Claude Code native configuration).
**No credential is baked into this plugin** and no key ever appears in tool
arguments — the transport adds the `Authorization: Bearer` header for you.

## Core concepts

- **Knowledge base (KB)** — a collection of documents with its own embedding,
  chunking and retrieval configuration. Everything is scoped to a KB.
- **Document** — an ingested file or scraped page, chunked and embedded.
- **Query / retrieval** — ask a question against a KB (generation) or fetch raw
  matching chunks (retrieval only). Multiple strategies: hybrid, knowledge-graph,
  adaptive, conversational.

## Typical workflow

1. **Identify the KB.** List with `read_knowledge_bases`; read one with
   `read_knowledge_base`. Create with `create_kb` only if the user asks.
2. **Add content** (only when asked):
   - `upload_document` / `create_document` — ingest a file into a KB.
   - `scrape_web_page` / `scrape_web_pages_batch` — ingest web content.
   - Check ingestion progress with `read_document_tasks` / `read_task`.
3. **Ask questions:**
   - `create_query` — full RAG answer (retrieval + generation) grounded in a KB.
   - `stream_query` — same, streamed.
   - `retrieve_sources` — retrieval only: returns the matching chunks/sources
     without generating an answer. Prefer this when you (Claude) will do the
     reasoning yourself and just need grounded context.
   - `get_query_strategies` — discover available strategies before choosing one.
4. **Knowledge graph** (KBs with a graph built): `search_graph_entities`,
   `get_graph_entity_relationships`, `find_paths_between_graph_entities`,
   `get_full_knowledge_graph` — for entity/relationship questions rather than
   plain semantic search.

## Guidance

- Prefer `retrieve_sources` when the user wants you to synthesize an answer with
  citations; prefer `create_query` when they want NeoRAG's own generated answer.
- Always cite the source documents/chunks returned — never invent content that
  isn't in the retrieved context.
- Inspect a document with `read_document`, `read_document_content`,
  `read_document_chunks` before claiming what it contains.
- Destructive tools (`delete_kb`, `delete_document`, `delete_api_key`, and the
  knowledge-graph delete endpoints) require explicit user confirmation — never
  call them speculatively.
- Who am I / account context: `read_users_me`, `read_current_user`.

## Privacy

All data stays within the user's own NeoRAG instance. The API key is stored in
Claude Code's native `userConfig` (masked, system keychain) and is sent only to
that instance over HTTPS.
