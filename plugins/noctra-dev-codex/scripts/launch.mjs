import { readFile } from "node:fs/promises";
import { connectionFor } from "../server/connection.js";
import { credentialStore, environmentName } from "./credential-store.mjs";

const root = new URL("../", import.meta.url);
try {
  const instance = JSON.parse(
    await readFile(new URL("instance.json", root), "utf8"),
  );
  const origin = new URL(
    connectionFor(instance, "nct_" + "x".repeat(32)).endpoint,
  ).origin;
  const variable = environmentName(origin);
  const key = process.env[variable] ?? (await credentialStore(origin).read());
  connectionFor(instance, key);
  // A key from another instance, or a generic ambient key, is never a fallback.
  delete process.env[variable];
  process.env.NOCTRA_MCP_API_KEY = key;
  await import("../server/main.js");
} catch {
  process.stderr.write(
    "Noctra credentials unavailable. Run this plugin's setup skill.\n",
  );
  process.exitCode = 2;
}
