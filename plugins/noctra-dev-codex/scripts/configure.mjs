import { execFileSync } from "node:child_process";
import { readFile } from "node:fs/promises";
import { connectionFor } from "../server/connection.js";
import {
  credentialStore,
  environmentName,
  validateKey,
} from "./credential-store.mjs";

function terminalSecret() {
  if (!process.stdin.isTTY || !process.stdout.isTTY)
    throw new Error(
      "Run --terminal in your own terminal, or choose --gui on macOS",
    );
  process.stdout.write("Noctra API key (hidden): ");
  process.stdin.setRawMode(true);
  process.stdin.resume();
  process.stdin.setEncoding("utf8");
  return new Promise((resolve, reject) => {
    let value = "";
    const done = (error) => {
      process.stdin.off("data", receive);
      process.stdin.setRawMode(false);
      process.stdin.pause();
      process.stdout.write("\n");
      if (error) reject(new Error("Input cancelled or invalid"));
      else resolve(value);
    };
    const receive = (data) => {
      for (const character of data) {
        if (character === "\u0003" || character === "\u0004") return done(true);
        if (character === "\r" || character === "\n") return done(false);
        if (character === "\u007f" || character === "\b")
          value = value.slice(0, -1);
        else if (/^[A-Za-z0-9_-]$/.test(character)) value += character;
        else return done(true);
        if (value.length > 204) return done(true);
      }
    };
    process.stdin.on("data", receive);
  });
}

function guiSecret(origin) {
  if (process.platform !== "darwin")
    throw new Error("GUI setup requires macOS");
  const script = `on run argv
set answer to display dialog ("Clé API Noctra pour " & item 1 of argv) with title "Noctra — Codex" default answer "" with hidden answer buttons {"Annuler", "Enregistrer"} default button "Enregistrer" cancel button "Annuler"
return text returned of answer
end run`;
  return execFileSync("/usr/bin/osascript", ["-e", script, origin], {
    encoding: "utf8",
    timeout: 120_000,
    maxBuffer: 4096,
    stdio: ["ignore", "pipe", "pipe"],
  }).replace(/[\r\n]+$/, "");
}

try {
  if (process.env.NODE_TLS_REJECT_UNAUTHORIZED === "0") throw new Error();
  const option = process.argv[2];
  if (
    !["--gui", "--terminal", "--check"].includes(option) ||
    process.argv.length !== 3
  )
    throw new Error();
  const instance = JSON.parse(
    await readFile(new URL("../instance.json", import.meta.url), "utf8"),
  );
  const origin = new URL(
    connectionFor(instance, "nct_" + "x".repeat(32)).endpoint,
  ).origin;
  const store = credentialStore(origin);
  const key = validateKey(
    option === "--check"
      ? (process.env[environmentName(origin)] ?? (await store.read()))
      : option === "--terminal"
        ? await terminalSecret()
        : guiSecret(origin),
  );
  const response = await fetch(`${origin}/api/v1/me`, {
    headers: { Authorization: `Bearer ${key}` },
    redirect: "error",
    signal: AbortSignal.timeout(15_000),
  });
  if (!response.ok) throw new Error();
  await response.body?.cancel();
  if (option !== "--check") {
    await store.install();
    await store.write(key);
  }
  process.stdout.write(
    option === "--check"
      ? `Noctra connection verified for ${origin}; no campaign launched.\n`
      : `Noctra configured for ${origin}. Key saved in macOS Keychain. Open a new Codex thread.\n`,
  );
} catch {
  process.stderr.write(
    "Noctra setup failed or was cancelled. Check the instance, key and unlocked Keychain. Use --gui or --terminal to configure, --check to verify. No credential is logged.\n",
  );
  process.exitCode = 2;
}
