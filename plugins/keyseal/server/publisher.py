"""A stdio MCP server for both publisher plugins. Python 3.11+, standard library only."""

import json
import re
import sys

from service import PLATFORMS, Problem, Service, context, image, product, release

TEXT = {"type": "string", "minLength": 1}
FLAG = {"type": "boolean"}
SLUG = {**TEXT, "pattern": "^[a-z0-9][a-z0-9-]{0,63}$"}


def enum(*values):
    return {"type": "string", "enum": list(values)}


def number(minimum, maximum):
    return {"type": "integer", "minimum": minimum, "maximum": maximum}


def obj(properties, required=()):
    return {
        "type": "object",
        "properties": properties,
        "required": list(required),
        "additionalProperties": False,
    }


def array(items, limit, minimum=0):
    return {"type": "array", "items": items, "minItems": minimum, "maxItems": limit}


scope = {
    "organization": SLUG,
    "environment": enum("test", "live"),
    "confirm_live": FLAG,
}
action = enum("preview", "apply")
price = obj(
    {
        "amount": number(1, 99999999),
        "currency": {**TEXT, "pattern": "^[a-z]{3}$"},
        "interval": enum("month", "year"),
        "tax_behavior": enum("inclusive", "exclusive"),
    },
    ["amount", "currency"],
)
offer = obj(
    {
        "slug": SLUG,
        "name": TEXT,
        "kind": enum("perpetual", "perpetual_with_updates", "renewal", "subscription"),
        "seats": number(1, 1000000),
        "update_months": number(1, 1200),
        "features": array(TEXT, 50),
        "free": FLAG,
        "public": FLAG,
        "price": price,
    },
    ["slug"],
)
product_spec = obj(
    {
        "slug": SLUG,
        "name": TEXT,
        "key_prefix": {**TEXT, "pattern": "^[A-Z]{3}$"},
        "description": {"type": "string", "maxLength": 5000},
        "website_url": TEXT,
        "image_url": TEXT,
        "page_enabled": FLAG,
        "tax_code": TEXT,
        "lease_days": number(1, 3650),
        "offline_policy": enum("open", "closed"),
    },
    ["slug", "name", "key_prefix"],
)
artifact = obj({"platform": enum(*PLATFORMS), "path": TEXT}, ["platform", "path"])
TOOLS = {
    "keyseal_context": (
        context,
        "Verify the authenticated organization and environment and list its products and immutable IDs.",
        obj({}),
    ),
    "keyseal_product": (
        product,
        "Preview or apply an idempotent product and offer specification. Use an existing imported product ID to preserve licences. New offers default to private. Returns checkout addresses, eligibility status and public Ed25519 keys.",
        obj(
            {
                **scope,
                "target": enum("new", "existing"),
                "action": action,
                "product_id": TEXT,
                "product": product_spec,
                "plans": array(offer, 100),
            },
            ["organization", "environment", "action", "target", "product", "plans"],
        ),
    ),
    "keyseal_image": (
        image,
        "Upload an authorized local PNG, JPEG or WebP (up to 512 KiB) to the chosen product. Keyseal serves its own sanitized image.",
        obj(
            {**scope, "product_slug": SLUG, "path": TEXT},
            ["organization", "environment", "product_slug", "path"],
        ),
    ),
    "keyseal_release": (
        release,
        "Preview, upload and optionally publish the verified local builds of one version for eligible buyers. Rerunning reuses matching files. Supply all files before publishing.",
        obj(
            {
                **scope,
                "action": action,
                "product_slug": SLUG,
                "version": TEXT,
                "notes": {"type": "string"},
                "publish": FLAG,
                "files": array(artifact, len(PLATFORMS), 1),
            },
            [
                "organization",
                "environment",
                "action",
                "product_slug",
                "version",
                "files",
            ],
        ),
    ),
}


def validate(value, schema):
    kind = schema["type"]
    types = {
        "object": dict,
        "array": list,
        "boolean": bool,
        "integer": int,
        "string": str,
    }
    if type(value) is not types[kind] or (
        "enum" in schema and value not in schema["enum"]
    ):
        raise Problem("Invalid argument type or option.")
    if kind == "object":
        if set(value) - set(schema["properties"]) or set(schema["required"]) - set(
            value
        ):
            raise Problem("Unknown or missing argument. Check the tool schema.")
        for field in value:
            validate(value[field], schema["properties"][field])
    elif kind == "array":
        if not schema["minItems"] <= len(value) <= schema["maxItems"]:
            raise Problem("Unexpected number of entries.")
        for entry in value:
            validate(entry, schema["items"])
    elif kind == "string":
        if (
            not schema.get("minLength", 0)
            <= len(value)
            <= schema.get("maxLength", 4096)
        ):
            raise Problem("Invalid text length.")
        if "pattern" in schema and not re.fullmatch(schema["pattern"], value):
            raise Problem("Invalid field format.")
    elif kind == "integer" and not schema["minimum"] <= value <= schema["maximum"]:
        raise Problem("Number outside the supported range.")


def run_tool(params):
    try:
        fn, _, schema = TOOLS[params["name"]]
        args = params.get("arguments", {})
        validate(args, schema)
        value = fn(Service(), **args)
        return {
            "content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}]
        }
    except Problem as exc:
        message = str(exc)
    except (ValueError, KeyError, TypeError, OSError):
        message = "Operation could not finish. Check the input, file and current product state."
    return {"isError": True, "content": [{"type": "text", "text": message}]}


def dispatch(message):
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        return {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32600, "message": "Invalid Request"},
        }
    if "id" not in message:
        return None
    method = message.get("method")
    reply = {"jsonrpc": "2.0", "id": message["id"]}
    params = message.get("params", {})
    if not isinstance(params, dict):
        return {**reply, "error": {"code": -32602, "message": "Invalid params"}}
    if method == "initialize":
        versions = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
        protocol = params.get("protocolVersion")
        result = {
            "protocolVersion": protocol if protocol in versions else versions[0],
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "keyseal-publisher", "version": "1.0.1"},
        }
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {
            "tools": [
                {"name": name, "description": desc, "inputSchema": schema}
                for name, (_, desc, schema) in TOOLS.items()
            ]
        }
    elif method == "tools/call":
        result = run_tool(params)
    else:
        return {**reply, "error": {"code": -32601, "message": "Method not found"}}
    return {**reply, "result": result}


if __name__ == "__main__":
    for line in sys.stdin:
        try:
            reply = dispatch(json.loads(line))
        except (ValueError, TypeError):
            reply = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"},
            }
        if reply is not None:
            print(json.dumps(reply, separators=(",", ":")), flush=True)
