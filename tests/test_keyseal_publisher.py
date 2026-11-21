"""Exercise catalogue reconciliation and the Live guard without a network connection."""

import base64
import hashlib
import tempfile
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins/keyseal/server"))
import publisher
import service


class Catalogue:
    def __init__(self):
        self.products = {}
        self.plans = {}
        self.writes = []

    def call(self, method, path, data=None, *, public=False):
        if path.endswith("/organization"):
            return {"slug": "studio", "environment": "live"}
        if path.startswith("/v1/keys/"):
            assert public
            return {"keys": {"example": base64.b64encode(bytes(range(32))).decode()}}
        kind = path.split("/")[3]
        rows = getattr(self, kind)
        if method == "GET":
            if path.endswith("/" + kind):
                return {kind: list(rows.values())}
            return rows[path.rsplit("/", 1)[-1]]
        self.writes.append((method, path))
        identifier = str(len(rows) + 1) if method == "POST" else path.rsplit("/", 1)[-1]
        rows[identifier] = {
            **rows.get(identifier, {}),
            "id": identifier,
            "stripe": {"synced": False},
            "page_enabled": False,
            **data,
        }
        return rows[identifier]


class PublisherTest(unittest.TestCase):
    def setUp(self):
        self.api = Catalogue()
        self.args = dict(
            action="apply",
            environment="live",
            organization="studio",
            target="new",
            confirm_live=True,
            product=dict(slug="pencil", key_prefix="PEN", name="Pencil"),
            plans=[dict(slug="personal", name="Personal", kind="perpetual", seats=1)],
        )

    def test_retry_same_product_and_offer(self):
        first = service.product(self.api, **self.args)
        second = service.product(self.api, **self.args)
        self.assertEqual(first["product_id"], second["product_id"])
        self.assertFalse(first["plans"][0]["public"])
        self.assertEqual(second["plans"][0]["action"], "keep")
        self.assertEqual(len(self.api.writes), 2)

    def test_preview_and_unconfirmed_or_mistargeted_live(self):
        preview = service.product(
            self.api, **{**self.args, "action": "preview", "confirm_live": False}
        )
        self.assertEqual(preview["plans"][0]["changes"]["seats"], 1)
        for override in (
            {"confirm_live": False},
            {"environment": "test"},
            {"organization": "other"},
        ):
            with self.assertRaises(service.Problem):
                service.product(self.api, **{**self.args, **override})
        self.assertEqual(self.api.writes, [])

    def test_offer_slug_collision_checked_before_writes(self):
        self.api.plans["unrelated"] = {"slug": "personal", "product_id": "other"}
        with self.assertRaises(service.Problem):
            service.product(self.api, **self.args)
        self.assertFalse(self.api.writes)

    def test_existing_identity_and_price_are_preserved_on_replay(self):
        result = service.product(self.api, **self.args)
        self.args["plans"][0]["seats"] = 5
        with self.assertRaises(service.Problem):
            service.product(self.api, **self.args)
        with self.assertRaises(service.Problem):
            service.product(
                self.api, **{**self.args, "target": "existing", "product_id": "other"}
            )
        service.product(
            self.api,
            **{**self.args, "target": "existing", "product_id": result["product_id"]},
        )
        self.assertEqual(len(self.api.writes), 3)

    def test_price_update_keeps_existing_interval_and_tax(self):
        self.args["plans"][0].update(
            kind="subscription",
            price={
                "amount": 3200,
                "currency": "eur",
                "interval": "month",
                "tax_behavior": "exclusive",
            },
        )
        row = service.product(self.api, **self.args)
        self.args["plans"][0]["price"] = {"amount": 4100, "currency": "eur"}
        result = service.product(
            self.api,
            **{**self.args, "target": "existing", "product_id": row["product_id"]},
        )
        self.assertEqual(
            result["plans"][0]["changes"]["price"],
            {
                "amount": 4100,
                "currency": "eur",
                "interval": "month",
                "tax_behavior": "exclusive",
            },
        )

    def test_new_mode_preserves_imported_product(self):
        service.product(self.api, **self.args)
        self.api.products["1"]["ls_compat"] = True
        self.args["plans"][0]["slug"] = "new-offer"
        with self.assertRaises(service.Problem):
            service.product(self.api, **self.args)
        self.assertEqual(len(self.api.writes), 2)

    def test_publication_rechecks_manifest_and_coverage(self):
        service.product(self.api, **self.args)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "build.zip"
            path.write_bytes(b"build")
            meta = {
                "platform": "any",
                "filename": path.name,
                "size": 5,
                "sha256": hashlib.sha256(b"build").hexdigest(),
                "status": "ready",
            }
            base = {
                "id": "one",
                "version": "1",
                "public": False,
                "status": "draft",
                "files": [meta],
            }
            rel = dict(
                product_slug="pencil",
                version="1",
                action="apply",
                environment="live",
                organization="studio",
                confirm_live=True,
                publish=True,
                files=[{"platform": "any", "path": str(path)}],
            )
            for changed in (
                {"public": True},
                {"files": [meta, {**meta, "platform": "linux-arm64"}]},
                {"files": [{**meta, "sha256": "0" * 64}]},
            ):

                def call(method, route, *args):
                    if route.endswith("/releases"):
                        return {"releases": [base]}
                    if route.endswith("/releases/one"):
                        return {**base, **changed}
                    self.assertEqual(method, "GET")
                    return self.api.call(method, route, *args)

                with (
                    patch.object(service, "scope"),
                    patch.object(
                        service,
                        "product_for",
                        return_value={"slug": "pencil", "id": "1"},
                    ),
                    self.assertRaises(service.Problem),
                ):
                    service.release(
                        type("Adapter", (), {"call": staticmethod(call)})(), **rel
                    )

    def test_upload_destination_and_tool_arguments(self):
        with patch("http.client.HTTPSConnection") as connect:
            for url in (
                "https://example.org/upload",
                "https://files.keyseal.io@example.org/path",
            ):
                with self.assertRaises(service.Problem):
                    service.upload(url, None, 0, "application/octet-stream")
            connect.assert_not_called()
        with self.assertRaises(service.Problem):
            publisher.validate(
                {**self.args, "server": "https://example.org"},
                publisher.TOOLS["keyseal_product"][2],
            )
        self.assertIsNone(
            publisher.dispatch(
                {"jsonrpc": "2.0", "method": "notifications/initialized"}
            )
        )


if __name__ == "__main__":
    unittest.main()
