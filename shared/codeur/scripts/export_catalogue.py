"""Export the public business API contract without starting the app or its schedulers.

The committed catalogue is an allowlist: a new route is only exposed after rebuilding
and reviewing it. --check detects drift in route coverage AND parameter schemas.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import sys
import tempfile

MCP_ROOT = Path(__file__).resolve().parents[1]
ROOT = Path(os.environ.get("CODEUR_SOURCE_ROOT", MCP_ROOT.parent)).resolve()
if not (ROOT / "src" / "api.py").is_file():
    sys.exit("Set CODEUR_SOURCE_ROOT to a checkout of ezeeFlop/codeur to export or check the API catalogue.")
sys.path.insert(0, str(ROOT))

# Imports must never open the developer's database or start telemetry.
os.environ["LANGFUSE_ENABLED"] = "false"
os.environ["POLL_INTERVAL_MINUTES"] = "0"
os.environ["MAILING_TICK_MINUTES"] = "0"

EXCLUDED = {
    ("POST", "/api/auth/login"): "Browser session management is unavailable to machine credentials.",
    ("POST", "/api/auth/logout"): "Browser session management is unavailable to machine credentials.",
    ("GET", "/api/mcp-keys"): "Credential administration requires a browser session.",
    ("POST", "/api/mcp-keys"): "Credential administration requires a browser session.",
    ("DELETE", "/api/mcp-keys/{key_id}"): "Credential administration requires a browser session.",
    ("POST", "/api/devis/{devis_id}/generate/stream"): "Use devis.generate_devis_content with a background job.",
}
DOMAINS = {
    "fetch": "missions", "score": "missions", "workflow": "missions",
    "generate": "missions", "health": "diagnostic", "stats": "diagnostic",
    "dashboard": "diagnostic", "mcp": "diagnostic",
}
KEYWORDS = {
    "missions": "prospection RSS scoring proposition veille",
    "customers": "clients contacts entreprise",
    "affaires": "CRM pipeline opportunités notes commercial",
    "devis": "quote chiffrage document PDF versions pièces jointes relance",
    "invoices": "factures facturation acompte avoir paiement émission relance",
    "time-entries": "temps jours régie prestation saisie",
    "expenses": "frais dépenses justificatifs débours",
    "purchase-orders": "bons commande BC extraction",
    "exports": "comptabilité FEC TVA CSV téléchargement",
    "prospects": "contacts import CSV XLSX tags conversion",
    "prospect-tags": "étiquettes segments prospects tags",
    "campaigns": "campagnes newsletter mailing email envoi statistiques planification design",
    "campaign-templates": "modèles templates newsletter",
    "companies": "entreprises société active identité",
    "knowledge-base": "base connaissances références compétences équipe",
    "settings": "paramètres réglages configuration logo",
    "ai": "IA modèles fournisseurs test",
    "emails": "journal emails suivi envois",
    "media": "images logo campagne téléchargement",
    "diagnostic": "santé diagnostic statistiques tableau bord",
}


def refs(value):
    if isinstance(value, dict):
        if "$ref" in value:
            yield value["$ref"].split("/")[-1]
        for child in value.values():
            yield from refs(child)
    elif isinstance(value, list):
        for child in value:
            yield from refs(child)


def build_catalogue():
    from fastapi.routing import APIRoute
    from src.api import app
    import src.models as models

    spec = app.openapi()
    definitions = spec.get("components", {}).get("schemas", {})
    routes = {(method, r.path): r for r in app.routes if isinstance(r, APIRoute)
              for method in r.methods}
    operations = []
    excluded = []
    for path, path_item in spec["paths"].items():
        if not (path.startswith("/api/") or path.startswith("/media/")):
            continue
        for method, item in path_item.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            route = routes[(method.upper(), path)]
            if (method.upper(), path) in EXCLUDED:
                excluded.append({"method": method.upper(), "path": path,
                                 "reason": EXCLUDED[(method.upper(), path)]})
                continue
            domain = path.split("/")[2] if path.startswith("/api/") else "media"
            domain = DOMAINS.get(domain, domain)
            props, required = {}, []
            for location in ("path", "query"):
                params = [p for p in item.get("parameters", []) if p["in"] == location]
                if params:
                    needed = [p["name"] for p in params if p.get("required")]
                    props[location] = {"type": "object", "additionalProperties": False,
                                       "properties": {p["name"]: p["schema"] for p in params}}
                    if needed:
                        props[location]["required"] = needed
                        required.append(location)
            content_type = None
            if "requestBody" in item:
                body = item["requestBody"]
                content_type, content = next(iter(body["content"].items()))
                schema = copy.deepcopy(content["schema"])
                # Several existing routes accept dict and validate inside the handler.
                # Describe their actual model so agents can build complete requests.
                model_name = {"invoices": "Invoice", "expenses": "Expense",
                              "time-entries": "TimeEntry", "affaires": "Affaire",
                              "settings": "Settings"}.get(domain)
                if schema.get("type") == "object" and not schema.get("properties") and model_name:
                    if route.name.startswith(("create_", "update_")):
                        schema = getattr(models, model_name).model_json_schema()
                        definitions.update(schema.pop("$defs", {}))
                        if route.name.startswith("update_"):
                            schema.pop("required", None)
                props["body"] = schema
                if body.get("required"):
                    required.append("body")
            schema = {"type": "object", "properties": props, "additionalProperties": False}
            if required:
                schema["required"] = required
            selected = {}
            todo = list(refs(schema))
            while todo:
                name = todo.pop()
                if name in selected:
                    continue
                selected[name] = definitions[name]
                todo.extend(refs(selected[name]))
            if selected:
                schema["$defs"] = selected
            schema = json.loads(json.dumps(schema).replace("#/components/schemas/", "#/$defs/"))
            # These GETs have business effects in the existing API (expiry, event sync).
            effectful_get = (domain == "devis" and route.name in {"list_devis", "get_devis"}) or (
                domain in {"campaigns", "emails"} and (path.endswith("/stats") or domain == "emails"))
            access = "read" if method == "get" and not effectful_get else "write"
            download = method == "get" and (
                domain in {"exports", "media"} or path.endswith(("/pdf", ".pdf", "/file", "/justification"))
                or path == "/api/devis/{devis_id}/attachments/{att_id}")
            if download:
                access = "download"
            operations.append({
                "id": f"{domain}.{route.name}", "domain": domain,
                "method": method.upper(), "path": path, "access": access,
                "summary": item.get("summary", route.name),
                "description": item.get("description", ""),
                "keywords": KEYWORDS.get(domain, ""),
                "content_type": content_type, "input_schema": schema,
                "business_effects_on_read": effectful_get,
            })
    ids = [o["id"] for o in operations]
    if len(ids) != len(set(ids)):
        raise RuntimeError("Duplicate operation identifiers")
    return {"format": 1, "operations": sorted(operations, key=lambda o: o["id"]),
            "excluded": excluded}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="codeur-catalogue-") as tmp:
        os.environ["CODEUR_DB_PATH"] = str(Path(tmp) / "catalogue.db")
        data = build_catalogue()
    output = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    target = MCP_ROOT / "src" / "catalogue.json"
    if args.check:
        if not target.exists() or target.read_text() != output:
            sys.exit("Catalogue out of date. Run npm run catalogue in mcp/ and review the diff.")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(output)
    print(f"{len(data['operations'])} operations; {len(data['excluded'])} documented exclusions")
