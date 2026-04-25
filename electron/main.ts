import { app, BrowserWindow, Menu, nativeImage } from "electron";
import fs from "fs";
import path from "path";
import { startSidecar, stopSidecar } from "./sidecar";

// Load .env into process.env for the main process. Vite's renderer-side
// env handling does not reach the main process, so CIH_USE_LOCAL_SIDECAR /
// CIH_API_BASE_URL would otherwise be undefined here.
function loadDotEnv(): void {
  const envPath = path.resolve(app.getAppPath(), ".env");
  let raw: string;
  try {
    raw = fs.readFileSync(envPath, "utf8");
  } catch {
    return;
  }
  for (const line of raw.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq < 0) continue;
    const key = trimmed.slice(0, eq).trim();
    let value = trimmed.slice(eq + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    if (key && process.env[key] === undefined) {
      process.env[key] = value;
    }
  }
}
loadDotEnv();

const APP_NAME = "Content Intelligence Hub";

// Override the app name so macOS menu bar and About window show it correctly
app.setName(APP_NAME);

let mainWindow: BrowserWindow | null = null;

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    icon: path.join(__dirname, "../../build/icon.png"),
    titleBarStyle: "hiddenInset",
    trafficLightPosition: { x: 16, y: 16 },
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (process.env.ELECTRON_RENDERER_URL) {
    mainWindow.loadURL(process.env.ELECTRON_RENDERER_URL);
  } else {
    mainWindow.loadFile(path.join(__dirname, "../renderer/index.html"));
  }
}

function showLicenses(): void {
  const win = new BrowserWindow({
    width: 600,
    height: 700,
    title: "Open Source Licenses",
    minimizable: false,
    maximizable: false,
  });

  const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; padding: 24px; background: #1a1a2e; color: #e0e0e0; }
  h1 { font-size: 18px; margin-bottom: 4px; color: #fff; }
  p.sub { font-size: 12px; color: #888; margin-bottom: 20px; }
  h2 { font-size: 14px; color: #a5b4fc; margin: 16px 0 8px; border-bottom: 1px solid #333; padding-bottom: 4px; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  td { padding: 4px 8px; border-bottom: 1px solid #2a2a3e; }
  td:first-child { font-weight: 500; color: #c4c4c4; }
  td:last-child { color: #888; text-align: right; }
</style></head><body>
<h1>${APP_NAME}</h1>
<p class="sub">Version ${app.getVersion()} &middot; Electron ${process.versions.electron} &middot; Node ${process.versions.node}</p>

<h2>Frontend (JavaScript)</h2>
<table>
  <tr><td>Electron</td><td>${process.versions.electron}</td></tr>
  <tr><td>React</td><td>19.2.4</td></tr>
  <tr><td>React DOM</td><td>19.2.4</td></tr>
  <tr><td>React Router DOM</td><td>7.13.1</td></tr>
  <tr><td>TanStack React Table</td><td>8.21.3</td></tr>
  <tr><td>Tailwind CSS</td><td>3.4.19</td></tr>
  <tr><td>Vite</td><td>7.3.1</td></tr>
  <tr><td>TypeScript</td><td>5.9.3</td></tr>
</table>

<h2>Sidecar (Python)</h2>
<table>
  <tr><td>FastAPI</td><td>0.135.1</td></tr>
  <tr><td>Uvicorn</td><td>0.41.0</td></tr>
  <tr><td>Anthropic SDK</td><td>0.84.0</td></tr>
  <tr><td>LangGraph</td><td>1.0.10</td></tr>
  <tr><td>LangChain Anthropic</td><td>1.3.4</td></tr>
  <tr><td>LangChain Core</td><td>1.2.17</td></tr>
  <tr><td>Sentence Transformers</td><td>5.2.3</td></tr>
  <tr><td>ONNX Runtime</td><td>1.24.3</td></tr>
  <tr><td>sqlite-vss</td><td>0.1.2</td></tr>
  <tr><td>Pydantic</td><td>2.12.5</td></tr>
  <tr><td>Pydantic Settings</td><td>2.13.1</td></tr>
  <tr><td>PyMuPDF</td><td>1.27.1</td></tr>
  <tr><td>python-docx</td><td>1.2.0</td></tr>
  <tr><td>Watchdog</td><td>6.0.0</td></tr>
</table>

<p class="sub" style="margin-top: 20px;">All libraries are MIT or Apache-2.0 licensed unless otherwise noted.</p>
</body></html>`;

  win.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(html)}`);
}

function buildMenu(): void {
  const template: Electron.MenuItemConstructorOptions[] = [
    {
      label: APP_NAME,
      submenu: [
        { label: `About ${APP_NAME}`, role: "about" },
        { label: "Open Source Licenses", click: showLicenses },
        { type: "separator" },
        { label: `Hide ${APP_NAME}`, role: "hide" },
        { label: "Hide Others", role: "hideOthers" },
        { label: "Show All", role: "unhide" },
        { type: "separator" },
        {
          label: `Restart ${APP_NAME}`,
          accelerator: "CmdOrCtrl+Shift+R",
          click: async () => {
            stopSidecar();
            try {
              await startSidecar();
            } catch (err) {
              console.error("Sidecar restart failed:", err);
            }
            if (mainWindow && !mainWindow.isDestroyed()) {
              mainWindow.reload();
            } else {
              createWindow();
            }
          },
        },
        { label: `Quit ${APP_NAME}`, role: "quit" },
      ],
    },
    {
      label: "Edit",
      submenu: [
        { role: "undo" },
        { role: "redo" },
        { type: "separator" },
        { role: "cut" },
        { role: "copy" },
        { role: "paste" },
        { role: "selectAll" },
      ],
    },
    {
      label: "View",
      submenu: [
        { role: "reload" },
        { role: "forceReload" },
        { role: "toggleDevTools" },
        { type: "separator" },
        { role: "resetZoom" },
        { role: "zoomIn" },
        { role: "zoomOut" },
        { type: "separator" },
        { role: "togglefullscreen" },
      ],
    },
    {
      label: "Window",
      submenu: [
        { role: "minimize" },
        { role: "zoom" },
        { type: "separator" },
        { role: "front" },
      ],
    },
  ];

  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

app.whenReady().then(async () => {
  const iconPath = path.join(__dirname, "../../build/icon.png");
  const icon = nativeImage.createFromPath(iconPath);
  app.dock?.setIcon(icon);

  app.setAboutPanelOptions({
    applicationName: APP_NAME,
    applicationVersion: "1.0.0",
    version: `Electron ${process.versions.electron}`,
    copyright: "© 2026",
    iconPath,
  });

  buildMenu();

  try {
    await startSidecar();
  } catch (err) {
    console.error("Sidecar start failed, continuing without it:", err);
  }
  createWindow();
});

app.on("window-all-closed", () => {
  stopSidecar();
  app.quit();
});

app.on("before-quit", () => {
  stopSidecar();
});
