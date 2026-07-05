---
description: Ask a question against a NeoRAG knowledge base (grounded RAG answer with sources).
argument-hint: [question]
---

Answer the user's question — `$ARGUMENTS` — grounded in their NeoRAG corpus.

1. If the target knowledge base is ambiguous, list KBs with `read_knowledge_bases`
   and ask which one (or use the obvious one if there is only a single match).
2. Retrieve grounding context with `retrieve_sources` (retrieval only) for the
   chosen KB, then synthesize the answer yourself with explicit citations to the
   returned sources. Use `create_query` instead if the user wants NeoRAG's own
   generated answer.
3. Never assert anything that is not supported by the retrieved sources.
