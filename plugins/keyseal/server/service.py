"""Keyseal publisher client. Only the official API receives the management credential."""

import base64
import hashlib
import http.client
import json
import mimetypes
import os
import re
import tomllib
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ORIGIN = "https://keyseal.io"
API = "/api/v1"
SLUG = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
PLATFORMS = (
    "macos-universal",
    "macos-arm64",
    "macos-x64",
    "windows-x64",
    "windows-arm64",
    "linux-x64",
    "linux-arm64",
    "any",
)


class Problem(Exception):
    """Messages contain no request headers, signed addresses or upstream response bodies."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def credential():
    key = os.environ.get("KEYSEAL_API_KEY")
    url = os.environ.get("KEYSEAL_URL", ORIGIN).rstrip("/")
    if not key:
        root = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
        if not root.is_absolute():
            raise Problem("Use an absolute XDG_CONFIG_HOME.")
        path = root / "keyseal" / "config.toml"
        try:
            with path.open("rb") as handle:
                if os.name == "posix" and os.fstat(handle.fileno()).st_mode & 0o077:
                    raise Problem("Set the Keyseal profile file permissions to 0600.")
                cfg = tomllib.load(handle)
            name = os.environ.get("KEYSEAL_PROFILE") or cfg["default_profile"]
            profile = cfg["profiles"][name]
            key = profile["api_key"]
            profile_url = profile["url"].rstrip("/")
        except (OSError, KeyError, ValueError, TypeError, AttributeError):
            raise Problem(
                "Configure KEYSEAL_API_KEY or a private Keyseal CLI profile."
            ) from None
        if profile_url != ORIGIN:
            raise Problem("The selected profile belongs to a different server.")
    if (
        url != ORIGIN
        or not isinstance(key, str)
        or not re.fullmatch(r"ksk_(?:live|test)_[a-zA-Z0-9]+", key)
    ):
        raise Problem("Check the Keyseal credential and its official origin.")
    return key


class Service:
    def __init__(self):
        self._key = credential()
        self._http = build_opener(NoRedirect())

    def call(self, method, path, data=None, *, public=False):
        if not path.startswith((API + "/", "/v1/")) or path.startswith("//"):
            raise Problem("Invalid service path.")
        headers = {"Accept": "application/json", "User-Agent": "Keyseal-publisher/1.0"}
        if not public:
            headers["Authorization"] = "Bearer " + self._key
        payload = None
        if data is not None:
            payload = json.dumps(data, separators=(",", ":")).encode()
            headers["Content-Type"] = "application/json"
        if method in ("POST", "PATCH"):
            headers["Idempotency-Key"] = str(uuid.uuid4())
        request = Request(ORIGIN + path, method=method, headers=headers, data=payload)
        try:
            with self._http.open(request, timeout=60) as response:
                return json.load(response)
        except HTTPError as exc:
            try:
                error = json.loads(exc.read(4096))["error"]["code"]
                code = (
                    error if re.fullmatch(r"[a-z_]{1,70}", error) else "request_failed"
                )
            except (KeyError, TypeError, ValueError):
                code = "request_failed"
            raise Problem(f"Keyseal HTTP {exc.code} ({code}).") from None
        except (OSError, URLError, ValueError):
            raise Problem(
                "Keyseal did not return a valid response. Retry after checking connectivity."
            ) from None


def require(value, message):
    if not value:
        raise Problem(message)


def slug(value):
    require(isinstance(value, str) and SLUG.fullmatch(value), "Invalid catalogue slug.")
    return value


def scope(api, args, write=False):
    org = api.call("GET", API + "/organization")
    require(
        org["slug"] == args["organization"]
        and org["environment"] == args["environment"],
        "The credential belongs to another organization or environment.",
    )
    if write and org["environment"] == "live":
        require(
            args.get("confirm_live") is True,
            "Confirm this Live operation with confirm_live.",
        )
    return org


def context(api):
    org = api.call("GET", API + "/organization")
    rows = api.call("GET", API + "/products")["products"]
    plans = api.call("GET", API + "/plans")["plans"]
    offers = [
        {
            k: row[k]
            for k in (
                "id",
                "slug",
                "product_id",
                "name",
                "kind",
                "seats",
                "public",
                "price",
                "free",
                "features",
                "update_months",
                "stripe",
            )
        }
        for row in plans
    ]
    return {
        "organization": org["slug"],
        "environment": org["environment"],
        "offers": offers,
        "products": [
            {k: row[k] for k in ("id", "name", "slug", "key_prefix", "ls_compat")}
            for row in rows
        ],
    }


def product_for(api, target):
    target = slug(target)
    products = api.call("GET", API + "/products")["products"]
    product = next((row for row in products if row["slug"] == target), None)
    require(product is not None, "The product does not exist in this scope.")
    return product


def diff(current, desired, immutable):
    delta = {}
    for k, v in desired.items():
        old = current.get(k)
        if isinstance(old, dict) and isinstance(v, dict):
            old = {field: old.get(field) for field in v}
        if old != v:
            require(k not in immutable, "An existing immutable field differs: " + k)
            delta[k] = v
    return delta


PRODUCT_FIELDS = {
    "slug",
    "name",
    "key_prefix",
    "description",
    "website_url",
    "image_url",
    "page_enabled",
    "offline_policy",
    "lease_days",
    "tax_code",
}
PLAN_FIELDS = {
    "slug",
    "name",
    "kind",
    "seats",
    "features",
    "update_months",
    "public",
    "price",
    "free",
}


def product(api, **args):
    apply = args["action"] == "apply"
    scope(api, args, write=apply)
    spec = args["product"]
    require(not (set(spec) - PRODUCT_FIELDS), "Unknown product fields.")
    target = slug(spec["slug"])
    require(
        re.fullmatch("[A-Z]{3}", spec["key_prefix"]),
        "Use three uppercase letters for the prefix.",
    )
    products = api.call("GET", API + "/products")["products"]
    cur = next((p for p in products if p["slug"] == target), None)
    flow = args["target"]
    if flow == "existing":
        require(
            cur and args.get("product_id") == cur["id"],
            "Specify the existing product ID from keyseal_context.",
        )
    if flow == "new" and cur:
        require(
            cur["key_prefix"] == spec["key_prefix"],
            "The slug is used by another product.",
        )
    require(
        not any(
            p["slug"] != target and p["key_prefix"] == spec["key_prefix"]
            for p in products
        ),
        "Another product already uses the prefix.",
    )
    changes = diff(cur, spec, {"slug", "key_prefix"}) if cur else spec
    if flow == "new" and cur and changes:
        raise Problem(
            "This product exists with different fields. Preview it with target existing and its ID."
        )
    plans = api.call("GET", API + "/plans")["plans"]
    work, seen = [], set()
    for cfg in args["plans"]:
        s = slug(cfg["slug"])
        require(
            s not in seen and not (set(cfg) - PLAN_FIELDS),
            "Duplicate plan slug or unknown plan field.",
        )
        seen.add(s)
        found = next((p for p in plans if p["slug"] == s), None)
        require(
            not found or (cur and found["product_id"] == cur["id"]),
            "An offer slug belongs to another product.",
        )
        desired = dict(cfg)
        if "price" in desired:
            old_price = (found or {}).get("price") or {}
            effective = {
                k: old_price[k]
                for k in ("tax_behavior", "interval")
                if old_price.get(k)
            }
            effective.update(desired["price"])
            effective.setdefault("tax_behavior", "inclusive")
            kind = (found or desired).get("kind")
            require(
                (kind == "subscription") == bool(effective.get("interval")),
                "Only a subscription price requires a month or year interval.",
            )
            desired["price"] = effective
        if not found and cur and cur.get("ls_compat") and flow == "new":
            raise Problem(
                "Adding an offer to an imported product requires its existing ID."
            )
        if not found:
            desired.setdefault("public", False)
            require(
                all(k in desired for k in ("name", "kind", "seats")),
                "New offers require name, kind and seats.",
            )
        delta = diff(found, desired, {"slug", "kind"}) if found else desired
        if flow == "new" and cur and found and delta:
            raise Problem(
                "An existing offer differs. Review its product ID and use target existing."
            )
        work.append((s, found, delta))
    report = {
        "product": target,
        "product_action": ("update" if changes else "keep") if cur else "create",
        "organization": args["organization"],
        "environment": args["environment"],
        "product_changes": changes,
        "plans": [
            {
                "slug": s,
                "action": ("update" if ch else "keep") if old else "create",
                "changes": ch,
            }
            for s, old, ch in work
        ],
    }
    if not apply:
        return report
    if not cur:
        cur = api.call("POST", API + "/products", changes)
    elif changes:
        cur = api.call("PATCH", API + "/products/" + cur["id"], changes)
    suffix = "?environment=test" if args["environment"] == "test" else ""
    for result, (s, old, delta) in zip(report["plans"], work):
        if not old:
            old = api.call("POST", API + "/plans", {"product_id": cur["id"], **delta})
        elif delta:
            old = api.call("PATCH", API + "/plans/" + old["id"], delta)
        result.update(
            id=old["id"],
            public=old["public"],
            stripe=old["stripe"],
            buy_url=f"{ORIGIN}/b/{args['organization']}/{s}{suffix}",
        )
    final = api.call("GET", API + "/products/" + cur["id"])
    path = f"/v1/keys/{args['organization']}/{target}?environment={args['environment']}"
    keys = api.call("GET", path, public=True)["keys"]
    require(
        keys
        and all(len(base64.b64decode(v, validate=True)) == 32 for v in keys.values()),
        "Product saved. Public Ed25519 keys could not be verified.",
    )
    report.update(
        product_id=final["id"],
        page_enabled=final["page_enabled"],
        keys_url=ORIGIN + path,
        public_keys=keys,
        product_url=f"{ORIGIN}/p/{args['organization']}/{target}{suffix}",
    )
    return report


def local_file(value):
    path = Path(value)
    require(
        path.is_absolute() and path.is_file() and not path.is_symlink(),
        "Pass an absolute path to the verified regular file.",
    )
    return path


def image(api, **args):
    scope(api, args, write=True)
    cur = product_for(api, args["product_slug"])
    path = local_file(args["path"])
    with path.open("rb") as handle:
        data = handle.read(512 * 1024 + 1)
    require(0 < len(data) <= 512 * 1024, "Use a PNG, JPEG or WebP image up to 512 KiB.")
    require(
        data.startswith((b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff"))
        or (data.startswith(b"RIFF") and data[8:12] == b"WEBP"),
        "Unsupported image format.",
    )
    out = api.call(
        "PUT",
        f"{API}/products/{cur['id']}/image",
        {"content_base64": base64.b64encode(data).decode()},
    )
    return {"product_id": cur["id"], "image_url": out["image_url"]}


def digest(handle):
    handle.seek(0)
    result = hashlib.file_digest(handle, "sha256").hexdigest()
    handle.seek(0)
    return result


def upload(address, handle, size, content_type):
    dest = urlsplit(address)
    require(
        dest.scheme == "https"
        and dest.netloc == "files.keyseal.io"
        and not dest.fragment,
        "Unexpected storage origin; upload stopped.",
    )
    conn = http.client.HTTPSConnection("files.keyseal.io", timeout=300)
    try:
        path = dest.path + ("?" + dest.query if dest.query else "")
        conn.request(
            "PUT",
            path,
            body=handle,
            headers={"Content-Length": str(size), "Content-Type": content_type},
        )
        res = conn.getresponse()
        require(
            200 <= res.status < 300,
            f"Storage HTTP {res.status}. Rerun the release to resume.",
        )
    except OSError:
        raise Problem(
            "Storage connection interrupted. Rerun the release to resume."
        ) from None
    finally:
        conn.close()


def release(api, **args):
    apply = args["action"] == "apply"
    scope(api, args, write=apply)
    cur = product_for(api, args["product_slug"])
    version = args["version"]
    require(re.fullmatch(r"[a-zA-Z0-9.+-]{1,64}", version), "Invalid release version.")
    base = f"{API}/products/{cur['id']}/releases"
    existing = next(
        (r for r in api.call("GET", base)["releases"] if r["version"] == version), None
    )
    files, platforms = [], set()
    for item in args["files"]:
        platform = item["platform"]
        require(
            platform in PLATFORMS and platform not in platforms,
            "Supply each supported platform once.",
        )
        platforms.add(platform)
        path = local_file(item["path"])
        with path.open("rb") as fh:
            size = os.fstat(fh.fileno()).st_size
            checksum = digest(fh)
        declared = {
            "filename": path.name,
            "platform": platform,
            "sha256": checksum,
            "size": size,
            "content_type": mimetypes.guess_type(path.name)[0]
            or "application/octet-stream",
        }
        prior = (
            next((f for f in existing["files"] if f["platform"] == platform), None)
            if existing
            else None
        )
        if prior:
            require(
                all(prior[f] == declared[f] for f in ("filename", "sha256", "size")),
                "This platform already contains a different file. Use a new version.",
            )
        files.append((path, declared, bool(prior and prior["status"] == "ready")))
    require(files, "Supply at least one release file.")
    report = {
        "version": version,
        "product": cur["slug"],
        "files": [meta for _, meta, _ in files],
    }
    if existing:
        require(
            existing["public"] is False,
            "This version has broader download coverage. Review its policy first.",
        )
        if args.get("publish"):
            extras = {f["platform"] for f in existing["files"]} - platforms
            require(
                not extras,
                "Include all existing release platforms before publication: "
                + ", ".join(sorted(extras)),
            )
    if not apply:
        return report
    if not existing:
        existing = api.call(
            "POST",
            base,
            {"version": version, "notes": args.get("notes", ""), "public": False},
        )
    require(
        existing["public"] is False,
        "This version has broader download coverage. Review its policy first.",
    )
    rid = existing["id"]
    for path, meta, done in files:
        if done:
            continue
        require(
            existing["status"] == "draft",
            "A published version is immutable here. Use a new version.",
        )
        with path.open("rb") as fh:
            require(
                os.fstat(fh.fileno()).st_size == meta["size"]
                and digest(fh) == meta["sha256"],
                "A release artifact changed; rebuild and retry.",
            )
            ticket = api.call("POST", f"{API}/releases/{rid}/files", meta)
            upload(ticket["upload_url"], fh, meta["size"], meta["content_type"])
            require(
                digest(fh) == meta["sha256"],
                "Artifact changed during upload; completion withheld.",
            )
        api.call("POST", f"{API}/files/{ticket['file']['id']}/complete")
    final = api.call("GET", f"{API}/releases/{rid}")
    require(
        all(f["status"] == "ready" for f in final["files"]),
        "A release file is still pending.",
    )
    if args.get("publish"):

        def verify_manifest(row):
            require(
                row["public"] is False, "Download coverage changed. Review the release."
            )
            keys = ("platform", "filename", "sha256", "size")
            actual = sorted(tuple(f[k] for k in keys) for f in row["files"])
            expected = sorted(tuple(f[k] for k in keys) for _, f, _ in files)
            require(
                actual == expected
                and all(f["status"] == "ready" for f in row["files"]),
                "The release manifest differs from the approved files. Review the version.",
            )

        verify_manifest(final)
        if final["status"] == "draft":
            final = api.call("POST", f"{API}/releases/{rid}/publish")
            verify_manifest(final)
    return {**report, "id": rid, "status": final["status"]}
