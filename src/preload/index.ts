import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("appInfo", {
  sidecarOrigin: "http://127.0.0.1:8420",
} as const);

contextBridge.exposeInMainWorld("electronAPI", {
  getApiKey: () =>
    ipcRenderer.invoke("apiKey:get") as Promise<{
      isSet: boolean;
      encryptionAvailable: boolean;
    }>,
  setApiKey: (key: string) =>
    ipcRenderer.invoke("apiKey:set", key) as Promise<{ ok: boolean }>,
  clearApiKey: () =>
    ipcRenderer.invoke("apiKey:clear") as Promise<{ ok: boolean }>,
});
