---
description: List your NeoRAG knowledge bases and their document counts.
---

List the user's NeoRAG knowledge bases using the `read_knowledge_bases` MCP tool.
Present a compact table: KB name, id, visibility, and (if available) document
count. If the user passes an argument, treat it as a name filter and only show
matching knowledge bases. Do not ingest or query anything — this is read-only.
