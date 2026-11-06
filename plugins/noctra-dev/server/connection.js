import { readFile } from "node:fs/promises";
import { isIP } from "node:net";
export function connectionFor(instance, apiKey) {
    if (!instance || typeof instance !== "object" || Array.isArray(instance)) {
        throw new Error("invalid_instance");
    }
    const spec = instance;
    if (Object.keys(spec).some((key) => !["api_url", "development"].includes(key)) ||
        typeof spec.api_url !== "string" ||
        spec.api_url.length > 2048 ||
        /[\s\x00-\x1f\x7f\\]/u.test(spec.api_url) ||
        (spec.development !== undefined && typeof spec.development !== "boolean")) {
        throw new Error("invalid_instance");
    }
    const url = new URL(spec.api_url);
    const host = url.hostname.replace(/^\[|\]$/g, "");
    const loopback = host === "localhost" ||
        host === "::1" ||
        (isIP(host) === 4 && host.startsWith("127."));
    if ((url.protocol !== "https:" &&
        !(url.protocol === "http:" && spec.development === true && loopback)) ||
        url.username ||
        url.password ||
        url.search ||
        url.hash ||
        url.pathname !== "/") {
        throw new Error("invalid_instance");
    }
    if (typeof apiKey !== "string" ||
        !/^nct_[A-Za-z0-9_-]{20,200}$/.test(apiKey)) {
        throw new Error("invalid_key");
    }
    return Object.freeze({ endpoint: new URL("/mcp", url).href, apiKey });
}
export async function loadConnection(root, environment) {
    if (environment.NODE_TLS_REJECT_UNAUTHORIZED === "0") {
        throw new Error("tls_verification_required");
    }
    const bytes = await readFile(new URL("instance.json", root));
    if (bytes.length > 4096)
        throw new Error("invalid_instance");
    return connectionFor(JSON.parse(bytes.toString("utf8")), environment.NOCTRA_MCP_API_KEY);
}
