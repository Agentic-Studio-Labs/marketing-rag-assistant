import { spawn, type ChildProcess } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { app, BrowserWindow, ipcMain, shell } from "electron";
import {
  clearApiKey,
  getApiKey,
  isEncryptionAvailable,
  setApiKey,
} from "./api-key-store";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

function devProjectRoot(): string {
  return join(__dirname, "..", "..");
}

function sidecarDirectory(): string {
  if (app.isPackaged) {
    return join(process.resourcesPath, "sidecar");
  }
  return join(devProjectRoot(), "sidecar");
}

function sidecarProcessEnv(): NodeJS.ProcessEnv {
  const base: NodeJS.ProcessEnv = { ...process.env, PYTHONUNBUFFERED: "1" };
  if (app.isPackaged) {
    base.RAG_DB_PATH = join(app.getPath("userData"), "rag.db");
  }
  const storedKey = getApiKey();
  if (storedKey) {
    base.ANTHROPIC_API_KEY = storedKey;
  }
  return base;
}

let sidecarProc: ChildProcess | null = null;
let mainWindow: BrowserWindow | null = null;

function preloadScriptPath(): string {
  const base = join(__dirname, "../preload");
  const mjs = join(base, "index.mjs");
  const js = join(base, "index.js");
  if (existsSync(mjs)) {
    return mjs;
  }
  return js;
}

function pythonBinary(): string {
  const sidecarDir = sidecarDirectory();
  const venvBin = process.platform === "win32" ? "Scripts" : "bin";
  const venvPython = join(
    sidecarDir,
    ".venv",
    venvBin,
    process.platform === "win32" ? "python.exe" : "python3",
  );
  if (existsSync(venvPython)) return venvPython;
  return process.platform === "win32" ? "python" : "python3";
}

async function waitForSidecar(url: string, maxAttempts = 60): Promise<void> {
  for (let i = 0; i < maxAttempts; i++) {
    try {
      const r = await fetch(`${url}/health`, {
        signal: AbortSignal.timeout(1000),
      });
      if (r.ok) return;
    } catch {
      /* retry */
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`Sidecar did not become ready at ${url}`);
}

function startSidecar(): void {
  if (sidecarProc) return;
  const sidecarDir = sidecarDirectory();
  sidecarProc = spawn(
    pythonBinary(),
    ["-m", "uvicorn", "api:app", "--host", "127.0.0.1", "--port", "8420"],
    {
      cwd: sidecarDir,
      env: sidecarProcessEnv(),
      stdio: "inherit",
    },
  );
  const proc = sidecarProc;
  proc.on("exit", (code) => {
    if (sidecarProc === proc) sidecarProc = null;
    if (code !== 0 && code !== null) {
      console.error(`Sidecar exited with code ${code}`);
    }
  });
}

function stopSidecar(): void {
  if (!sidecarProc) return;
  sidecarProc.kill("SIGTERM");
  sidecarProc = null;
}

async function restartSidecar(): Promise<void> {
  stopSidecar();
  startSidecar();
  try {
    await waitForSidecar("http://127.0.0.1:8420");
  } catch (e) {
    console.error(e);
  }
}

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1080,
    height: 760,
    minWidth: 720,
    minHeight: 520,
    title: "Marketing RAG Assistant",
    webPreferences: {
      preload: preloadScriptPath(),
      contextIsolation: true,
      sandbox: false,
    },
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  mainWindow.webContents.setWindowOpenHandler((details) => {
    shell.openExternal(details.url);
    return { action: "deny" };
  });

  const devUrl =
    process.env.ELECTRON_RENDERER_URL ??
    process.env.ELECTRON_VITE_DEV_SERVER_URL;
  if (devUrl) {
    void mainWindow.loadURL(devUrl);
    mainWindow.webContents.openDevTools({ mode: "detach" });
  } else {
    void mainWindow.loadFile(join(__dirname, "../renderer/index.html"));
  }
}

function registerIpcHandlers(): void {
  ipcMain.handle("apiKey:get", () => {
    return {
      isSet: getApiKey() !== null,
      encryptionAvailable: isEncryptionAvailable(),
    };
  });

  ipcMain.handle("apiKey:set", async (_event, key: string) => {
    setApiKey(key);
    await restartSidecar();
    try {
      await fetch("http://127.0.0.1:8420/api/audit/key-change", {
        method: "POST",
      });
    } catch {
      /* sidecar may still be starting */
    }
    return { ok: true };
  });

  ipcMain.handle("apiKey:clear", async () => {
    clearApiKey();
    await restartSidecar();
    try {
      await fetch("http://127.0.0.1:8420/api/audit/key-change", {
        method: "POST",
      });
    } catch {
      /* sidecar may still be starting */
    }
    return { ok: true };
  });
}

app.whenReady().then(async () => {
  registerIpcHandlers();
  startSidecar();
  try {
    await waitForSidecar("http://127.0.0.1:8420");
  } catch (e) {
    console.error(e);
  }
  createWindow();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    stopSidecar();
    app.quit();
  }
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    if (!sidecarProc) startSidecar();
    createWindow();
  }
});

app.on("before-quit", () => {
  stopSidecar();
});
