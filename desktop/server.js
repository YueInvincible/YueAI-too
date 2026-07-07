import http from "node:http";
import { spawn } from "node:child_process";
import { readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import readline from "node:readline";
import { fileURLToPath } from "node:url";

const host = "127.0.0.1";
const port = Number(process.env.PORT || 1420);
const root = path.dirname(fileURLToPath(import.meta.url));
const workspaceRoot = path.dirname(root);
const srcRoot = path.join(workspaceRoot, "src");
const configuredCorePath = process.env.YUE_CORE_CONFIG
  ? path.resolve(process.env.YUE_CORE_CONFIG)
  : path.join(workspaceRoot, "config.demo.local.toml");
const defaultCoreConfigPath = existsSync(configuredCorePath) ? configuredCorePath : null;
const pythonCommand = process.env.YUE_PYTHON || "python";
const pythonPathDelimiter = path.delimiter;

function mergePythonPath(nextEntry, currentValue) {
  const entries = [nextEntry, ...(currentValue ? String(currentValue).split(pythonPathDelimiter) : [])]
    .map((item) => String(item).trim())
    .filter(Boolean);
  return [...new Set(entries)].join(pythonPathDelimiter);
}

const contentTypes = new Map([
  [".html", "text/html; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".css", "text/css; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
]);

class CoreBridge {
  constructor() {
    this.child = null;
    this.startPromise = null;
    this.pending = new Map();
    this.events = [];
    this.stderr = [];
    this.exited = false;
    this.lastLaunch = null;
  }

  async ensureStarted() {
    if (this.child && !this.exited) {
      return;
    }
    if (this.startPromise) {
      return this.startPromise;
    }
    this.startPromise = new Promise((resolve, reject) => {
      const args = ["-m", "yue_core"];
      if (defaultCoreConfigPath) {
        args.push("--config", defaultCoreConfigPath);
      }
      args.push("serve");
      const childEnv = {
        ...process.env,
        PYTHONPATH: mergePythonPath(srcRoot, process.env.PYTHONPATH),
      };
      this.lastLaunch = {
        command: pythonCommand,
        args: [...args],
        cwd: workspaceRoot,
        pythonPath: childEnv.PYTHONPATH,
      };
      const child = spawn(pythonCommand, args, {
        cwd: workspaceRoot,
        env: childEnv,
        stdio: ["pipe", "pipe", "pipe"],
        windowsHide: true,
      });
      this.child = child;
      this.exited = false;

      const completeStartup = () => {
        if (this.startPromise) {
          resolve();
          this.startPromise = null;
        }
      };

      const failStartup = (error) => {
        if (this.startPromise) {
          reject(error);
          this.startPromise = null;
        }
      };

      child.once("spawn", completeStartup);
      child.once("error", (error) => {
        this.stderr.push(`Spawn failed: ${error instanceof Error ? error.message : String(error)}`);
        failStartup(error);
      });
      child.once("exit", (code, signal) => {
        this.exited = true;
        const error = new Error(
          `Core bridge exited${code !== null ? ` with code ${code}` : ""}${signal ? ` (${signal})` : ""}`,
        );
        for (const { reject } of this.pending.values()) {
          reject(error);
        }
        this.pending.clear();
      });

      readline
        .createInterface({ input: child.stdout })
        .on("line", (line) => {
          this.handleLine(line);
        });

      readline
        .createInterface({ input: child.stderr })
        .on("line", (line) => {
          this.stderr.push(line);
          if (this.stderr.length > 50) {
            this.stderr.shift();
          }
        });
    });
    return this.startPromise;
  }

  handleLine(line) {
    const trimmed = String(line).trim();
    if (!trimmed) {
      return;
    }
    let message;
    try {
      message = JSON.parse(trimmed);
    } catch {
      this.stderr.push(`Invalid JSONL from core: ${trimmed}`);
      return;
    }
    if (message.event) {
      this.events.push(message.event);
      if (this.events.length > 500) {
        this.events.shift();
      }
      return;
    }
    if (!message.id) {
      return;
    }
    const pending = this.pending.get(message.id);
    if (!pending) {
      return;
    }
    this.pending.delete(message.id);
    if (message.ok) {
      pending.resolve(message.result);
      return;
    }
    pending.reject(new Error(message.error || "Bridge request failed"));
  }

  async request(payload) {
    await this.ensureStarted();
    if (!this.child || !this.child.stdin || this.exited) {
      throw new Error("Core bridge is not running");
    }
    const id = `browser-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    const envelope = {
      id,
      method: payload.method,
      params: payload.params || {},
    };
    const timeoutMs = Number(payload.timeout_ms || payload.timeoutMs || 15000);
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`Bridge request timed out after ${timeoutMs}ms`));
      }, timeoutMs);
      this.pending.set(id, {
        resolve: (value) => {
          clearTimeout(timer);
          resolve(value);
        },
        reject: (error) => {
          clearTimeout(timer);
          reject(error);
        },
      });
      this.child.stdin.write(`${JSON.stringify(envelope)}\n`);
    });
  }

  runtimeInfo() {
    return {
      mode: "browser-preview",
      core_transport: "jsonl-http-bridge",
      process_started: Boolean(this.child) && !this.exited,
      pending_requests: this.pending.size,
      queued_events: this.events.length,
      note: defaultCoreConfigPath
        ? `Browser preview using ${path.basename(defaultCoreConfigPath)}`
        : "Browser preview using default YueCore settings",
      last_error: this.stderr.length > 0 ? this.stderr[this.stderr.length - 1] : null,
      launch: this.lastLaunch,
      diagnostic_enabled: false,
    };
  }

  drainEvents() {
    const events = [...this.events];
    this.events.length = 0;
    return events;
  }

  async shutdown() {
    if (!this.child || this.exited) {
      return { stopped: false };
    }
    const child = this.child;
    this.child = null;
    this.exited = true;
    child.kill();
    return { stopped: true };
  }
}

const bridge = new CoreBridge();

async function readJson(request) {
  const chunks = [];
  for await (const chunk of request) {
    chunks.push(chunk);
  }
  if (chunks.length === 0) {
    return {};
  }
  return JSON.parse(Buffer.concat(chunks).toString("utf-8"));
}

function writeJson(response, statusCode, payload) {
  response.writeHead(statusCode, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
  });
  response.end(JSON.stringify(payload));
}

const server = http.createServer(async (request, response) => {
  const url = new URL(request.url || "/", `http://${host}:${port}`);

  if (url.pathname === "/api/bridge/runtime" && request.method === "GET") {
    await bridge.ensureStarted().catch(() => null);
    writeJson(response, 200, bridge.runtimeInfo());
    return;
  }

  if (url.pathname === "/api/bridge/events" && request.method === "GET") {
    writeJson(response, 200, { events: bridge.drainEvents() });
    return;
  }

  if (url.pathname === "/api/bridge/request" && request.method === "POST") {
    try {
      const payload = await readJson(request);
      const result = await bridge.request(payload);
      writeJson(response, 200, { ok: true, result });
    } catch (error) {
      writeJson(response, 500, {
        ok: false,
        error: error instanceof Error ? error.message : String(error),
      });
    }
    return;
  }

  if (url.pathname === "/api/bridge/shutdown" && request.method === "POST") {
    writeJson(response, 200, await bridge.shutdown());
    return;
  }

  const relative = url.pathname === "/" ? "/index.html" : url.pathname;
  const target = path.normalize(path.join(root, relative));
  if (!target.startsWith(root)) {
    response.writeHead(403).end("Forbidden");
    return;
  }
  try {
    const body = await readFile(target);
    response.writeHead(200, {
      "Content-Type": contentTypes.get(path.extname(target)) || "application/octet-stream",
    });
    response.end(body);
  } catch {
    response.writeHead(404).end("Not found");
  }
});

server.listen(port, host, () => {
  console.log(`Yue Desktop preview: http://${host}:${port}`);
});
