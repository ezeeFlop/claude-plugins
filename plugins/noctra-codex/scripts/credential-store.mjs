import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { lstat, mkdir, readFile, link, unlink, open } from "node:fs/promises";
import { homedir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const digest = (bytes) => createHash("sha256").update(bytes).digest("hex");
export const instanceIdentity = (origin) => digest(new URL(origin).origin);
export const environmentName = (origin) =>
  `NOCTRA_API_KEY_${instanceIdentity(origin).slice(0, 24).toUpperCase()}`;

export function validateKey(value) {
  if (typeof value !== "string" || !/^nct_[A-Za-z0-9_-]{20,200}$/.test(value))
    throw new Error("Invalid Noctra API key");
  return value;
}

// Injection is for tests: production always verifies the packaged binary and
// stable user-owned path. No process output is ever included in diagnostics.
export function credentialStore(
  origin,
  {
    directory = fileURLToPath(new URL("./", import.meta.url)),
    home = homedir(),
    platform = process.platform,
    run = execFileSync,
  } = {},
) {
  const account = instanceIdentity(origin);
  const parent = path.join(home, ".noctra", "codex-keychain", "v1");
  const target = path.join(parent, "noctra-keychain");

  async function expectedHash() {
    const metadata = JSON.parse(
      await readFile(path.join(directory, "keychain-helper.json"), "utf8"),
    );
    if (!/^[a-f0-9]{64}$/.test(metadata.sha256))
      throw new Error("Invalid helper inventory");
    return metadata.sha256;
  }

  async function privateDirectory(create) {
    for (const part of [".noctra", "codex-keychain", "v1"]) {
      const current =
        part === ".noctra"
          ? path.join(home, part)
          : part === "codex-keychain"
            ? path.join(home, ".noctra", part)
            : parent;
      if (create)
        await mkdir(current, { mode: 0o700 }).catch((error) => {
          if (error.code !== "EEXIST") throw error;
        });
      const stat = await lstat(current);
      if (
        !stat.isDirectory() ||
        stat.isSymbolicLink() ||
        stat.uid !== process.getuid() ||
        stat.mode & 0o022
      )
        throw new Error("Unsafe helper directory");
    }
  }

  async function verified(filename) {
    const stat = await lstat(filename);
    return (
      stat.isFile() &&
      !stat.isSymbolicLink() &&
      stat.uid === process.getuid() &&
      !(stat.mode & 0o022) &&
      digest(await readFile(filename)) === (await expectedHash())
    );
  }

  async function install() {
    if (platform !== "darwin") throw new Error("Keychain setup requires macOS");
    await privateDirectory(true);
    try {
      if (await verified(target)) return;
      throw new Error("Preserve the existing helper; reinstall explicitly");
    } catch (error) {
      if (error.code !== "ENOENT") throw error;
    }
    const bytes = await readFile(path.join(directory, "keychain-helper"));
    if (digest(bytes) !== (await expectedHash()))
      throw new Error("Packaged helper is corrupt");
    const temporary = path.join(
      parent,
      `.install-${process.pid}-${Date.now()}`,
    );
    const file = await open(temporary, "wx", 0o700);
    try {
      await file.writeFile(bytes);
      await file.close();
      await link(temporary, target).catch(async (error) => {
        if (error.code !== "EEXIST" || !(await verified(target))) throw error;
      });
    } finally {
      await file.close().catch(() => {});
      await unlink(temporary).catch(() => {});
    }
  }

  async function perform(operation, value, interactive = false) {
    try {
      if (platform !== "darwin") throw new Error();
      await privateDirectory(false);
      if (!(await verified(target))) throw new Error();
      const request = { account, operation };
      if (value !== undefined) request.value = validateKey(value);
      const output = run(target, interactive ? ["--interactive"] : [], {
        input: JSON.stringify(request),
        encoding: "utf8",
        timeout: interactive ? 120_000 : 10_000,
        maxBuffer: 16_384,
        stdio: ["pipe", "pipe", "pipe"],
      });
      const reply = JSON.parse(output);
      if (reply.status === -25300 && operation === "read") return null;
      if (reply.status !== 0) throw new Error();
      return operation === "read" ? validateKey(reply.value) : undefined;
    } catch {
      throw new Error("Noctra Keychain unavailable. Unlock it and run setup.");
    }
  }

  return {
    install,
    read: () => perform("read"),
    write: (value) => perform("write", value, true),
  };
}
