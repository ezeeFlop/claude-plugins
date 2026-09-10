"""Wrap graphifyy's deterministic AST extraction into Spongram code-map dicts.

We reuse graphifyy (MIT, Safi Shamsi) for the heavy lifting (tree-sitter parse,
import resolution, call-graph), then normalise its output to a single `:Code`
label + `kind` so the server schema is FalkorDB-portable.
"""

from __future__ import annotations

from pathlib import Path

LANGUAGES: tuple[str, ...] = ("python", "javascript", "typescript", "rust", "go")
_SUFFIXES: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".rs": "rust",
    ".go": "go",
}


def _strip_parens(label: str) -> str:
    """Remove trailing () or leading . from graphifyy label conventions."""
    if label.endswith("()"):
        label = label[:-2]
    if label.startswith("."):
        label = label[1:]
    return label


def _infer_kinds(nodes: list[dict], edges: list[dict]) -> dict[str, str]:
    """Build a node-id → kind mapping using edge relations from graphifyy.

    graphifyy encodes semantics in edge relations:
      - file → symbol  via 'contains'  → symbol is function or class
      - class → method via 'method'    → target is a method
      - caller → callee via 'calls'    → target is a function

    We use a two-pass approach:
    1. Classify 'method' edge targets as 'method'.
    2. Files (id matches stripped basename of source_file) → 'file'.
    3. Remaining symbols: label without () → 'class'; label with () → 'function'.
    """
    kinds: dict[str, str] = {}

    # Pass 1: mark method targets
    for e in edges:
        if e.get("relation") == "method":
            kinds[str(e["target"])] = "method"

    # Pass 2: classify remaining nodes
    for n in nodes:
        nid = str(n.get("id") or "")
        if not nid:
            continue
        if nid in kinds:
            continue  # already classified as method

        raw_label = str(n.get("label") or "")
        # File node: graphifyy labels file nodes with the filename INCLUDING its
        # extension (e.g. "__init__.py", "cli.py"). The node id may be mangled —
        # graphifyy strips the dunder underscores so "__init__.py" gets id "init",
        # which never equals the stem "__init__". Matching on the LABEL suffix is
        # therefore the reliable discriminator (verified against graphifyy output).
        if any(raw_label.endswith(suf) for suf in _SUFFIXES):
            kinds[nid] = "file"
            continue

        # Symbol: classify by label shape
        if raw_label.endswith("()") or raw_label.startswith("."):
            kinds[nid] = "function"
        else:
            kinds[nid] = "class"

    return kinds


def _qualified_call_edges(
    root: Path, py_files: list[Path], nodes: list[dict], edges: list[dict]
) -> list[dict]:
    """Infer `calls` edges for qualified cross-module calls (``mod.func()``).

    graphifyy resolves direct-name calls (``helper()`` after ``from m import
    helper``) but NOT attribute-qualified ones (``m.helper()`` after ``import
    m`` / ``import pkg.m as alias``) — bench 2026-06-10 : l'appelant de
    ``enrich_search_nodes`` (``_code_map.enrich_search_nodes(...)`` dans
    mcp_router.py) manquait au graphe. Python-only, stdlib ``ast``, best
    effort : on n'émet une arête que si la cible résout sans ambiguïté vers
    un symbole du repo scanné. Confidence ``AST_INFERRED`` — distincte de
    ``INFERRED`` que graphifyy émet nativement pour ses inférences par
    annotations de types, pour rester traçable.
    """
    import ast

    by_file_label: dict[tuple[str, str], str] = {}
    file_stems: dict[str, list[tuple[str, str]]] = {}  # stem -> [(source_file, file_id)]
    for n in nodes:
        by_file_label[(n["source_file"], n["label"])] = n["id"]
        if n["kind"] == "file":
            file_stems.setdefault(Path(n["label"]).stem, []).append((n["source_file"], n["id"]))

    class _Visitor(ast.NodeVisitor):
        def __init__(self, alias_to_mod: dict[str, str], rel: str, this_file_id: str) -> None:
            self.alias_to_mod = alias_to_mod
            self.rel = rel
            self.this_file_id = this_file_id
            self.stack: list[str] = []
            self.calls: list[tuple[str, str]] = []  # (source_id, target_id)

        def _resolve(self, modbase: str, fname: str) -> str | None:
            hits = [
                h
                for src, _fid in file_stems.get(modbase, [])
                if (h := by_file_label.get((src, fname)))
            ]
            return hits[0] if len(hits) == 1 else None  # skip ambiguous stems

        def visit_FunctionDef(self, node):  # noqa: N802
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        visit_AsyncFunctionDef = visit_FunctionDef  # noqa: N815

        def visit_Call(self, node):  # noqa: N802
            f = node.func
            if (
                isinstance(f, ast.Attribute)
                and isinstance(f.value, ast.Name)
                and f.value.id in self.alias_to_mod
            ):
                target = self._resolve(self.alias_to_mod[f.value.id], f.attr)
                if target:
                    source = (
                        by_file_label.get((self.rel, self.stack[-1])) if self.stack else None
                    ) or self.this_file_id
                    if source != target:
                        self.calls.append((source, target))
            self.generic_visit(node)

    existing = {(e["source"], e["target"], e["relation"]) for e in edges}
    out: list[dict] = []
    for path in py_files:
        if path.suffix != ".py":
            continue
        try:
            rel = str(path.relative_to(root).as_posix())
        except ValueError:
            rel = str(path)
        this_file_id = by_file_label.get((rel, path.name))
        if this_file_id is None:
            continue  # file produced no node (empty / parse failure upstream)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue

        alias_to_mod: dict[str, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    # `import pkg.mod as alias` → alias.func() targets mod;
                    # bare `import pkg.mod` is used as pkg.mod.func() (2-level
                    # attribute) which we deliberately skip — single-segment
                    # `import mod` still resolves.
                    alias = a.asname or a.name.split(".")[0]
                    if a.asname or "." not in a.name:
                        alias_to_mod[alias] = a.name.split(".")[-1]
            elif isinstance(node, ast.ImportFrom):
                for a in node.names:
                    # `from pkg import mod` → mod.func() targets mod.
                    alias_to_mod[a.asname or a.name] = a.name

        visitor = _Visitor(alias_to_mod, rel, this_file_id)
        visitor.visit(tree)
        for source, target in visitor.calls:
            triple = (source, target, "calls")
            if triple not in existing:
                existing.add(triple)
                out.append(
                    {
                        "source": source,
                        "target": target,
                        "relation": "calls",
                        "confidence": "AST_INFERRED",
                    }
                )
    return out


def extract_repo(root: str | Path, languages: tuple[str, ...] = LANGUAGES) -> dict:
    """Return {nodes, edges} for all supported files under root.

    nodes: [{id, label, kind, source_file, source_location?}]
    edges: [{source, target, relation, confidence}]
    """
    from graphify import detect, extract  # lazy import — grammars load on demand

    # Resolve to an absolute root: graphifyy detect() returns ABSOLUTE file
    # paths even for a relative root, so every relative_to(root) below would
    # raise (and silently disable the AST post-pass) when called as
    # extract_repo(".") — which is exactly what the CLI does.
    root = Path(root).resolve()
    wanted_suffixes = {s for s, lang in _SUFFIXES.items() if lang in languages}

    # graphifyy's detect.detect() scans a directory and returns classified file lists.
    # We use only 'code' files and then filter to our wanted suffixes.
    detection = detect.detect(root)
    all_code_files = detection.get("files", {}).get("code", [])
    files = [p for p in all_code_files if Path(p).suffix.lower() in wanted_suffixes]

    if not files:
        return {"nodes": [], "edges": []}

    # graphifyy extract.extract() expects a LIST of Path objects.
    # Returns {"nodes": [...], "edges": [...]}.
    try:
        res = extract.extract([Path(f) for f in files])
    except Exception:
        return {"nodes": [], "edges": []}

    raw_nodes = res.get("nodes", [])
    raw_edges = res.get("edges", [])

    # graphifyy emits one "rationale" node per docstring/comment (file_type=
    # "rationale", label = the prose itself). Those are NOT structural code
    # entities — keeping them pollutes a structural code map (they land as bogus
    # classes). Drop every rationale node and any edge that touches one.
    rationale_ids = {str(n.get("id")) for n in raw_nodes if n.get("file_type") == "rationale"}
    if rationale_ids:
        raw_nodes = [n for n in raw_nodes if n.get("file_type") != "rationale"]
        raw_edges = [
            e
            for e in raw_edges
            if str(e.get("source")) not in rationale_ids
            and str(e.get("target")) not in rationale_ids
        ]

    # Drop EXTERNAL imported symbols (e.g. pathlib.Path, os.path.join). graphifyy
    # materializes these as nodes that NO scanned file defines: they appear only
    # as targets of imports/calls/references edges, never of a 'contains'/'method'
    # edge, and their label is not a filename. Keeping them pollutes a structural
    # map of YOUR code with phantom 'class' nodes (one per importing file). A node
    # is "defined here" iff it is a file node OR the target of a contains/method
    # edge; everything else is external and dropped, together with its edges.
    _file_ids = {
        str(n.get("id"))
        for n in raw_nodes
        if any(str(n.get("label") or "").endswith(suf) for suf in _SUFFIXES)
    }
    _defined_ids = set(_file_ids)
    for e in raw_edges:
        if e.get("relation") in ("contains", "method"):
            _defined_ids.add(str(e.get("target")))
    _external_ids = {
        str(n.get("id"))
        for n in raw_nodes
        if str(n.get("id") or "") and str(n.get("id")) not in _defined_ids
    }
    if _external_ids:
        raw_nodes = [n for n in raw_nodes if str(n.get("id")) not in _external_ids]
        raw_edges = [
            e
            for e in raw_edges
            if str(e.get("source")) not in _external_ids
            and str(e.get("target")) not in _external_ids
        ]

    # Build kind map using edge topology
    kinds = _infer_kinds(raw_nodes, raw_edges)

    nodes: list[dict] = []
    seen: set[str] = set()
    for n in raw_nodes:
        nid = str(n.get("id") or "")
        if not nid or nid in seen:
            continue
        seen.add(nid)

        raw_label = str(n.get("label") or nid)
        clean_label = _strip_parens(raw_label)

        rel = str(n.get("source_file") or "")
        try:
            rel = str(Path(rel).relative_to(root).as_posix())
        except ValueError:
            pass

        nodes.append(
            {
                "id": nid,
                "label": clean_label,
                "kind": kinds.get(nid, "function"),
                "source_file": rel,
                "source_location": n.get("source_location"),
            }
        )

    # Referential integrity: keep ONLY edges whose endpoints both survive as
    # real nodes. graphifyy emits import edges whose target is a bare external
    # module name (e.g. "pathlib") that has no node; without this guard the
    # store would MERGE those endpoints into phantom nodes on ingest.
    node_ids = {n["id"] for n in nodes}
    edges: list[dict] = []
    for e in raw_edges:
        src, tgt = e.get("source"), e.get("target")
        if not src or not tgt:
            continue
        if str(src) not in node_ids or str(tgt) not in node_ids:
            continue
        edges.append(
            {
                "source": str(src),
                "target": str(tgt),
                "relation": str(e.get("relation") or "uses"),
                "confidence": str(e.get("confidence") or "EXTRACTED"),
            }
        )

    # Post-pass: qualified cross-module calls (`mod.func()`) that graphifyy
    # does not resolve. Endpoints are existing node ids by construction.
    edges.extend(_qualified_call_edges(root, [Path(f) for f in files], nodes, edges))

    return {"nodes": nodes, "edges": edges}
