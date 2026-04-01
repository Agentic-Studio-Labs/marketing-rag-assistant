import { existsSync, readFileSync, unlinkSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { app, safeStorage } from "electron";

function encryptedKeyPath(): string {
  return join(app.getPath("userData"), "api-key.enc");
}

export function isEncryptionAvailable(): boolean {
  return safeStorage.isEncryptionAvailable();
}

export function getApiKey(): string | null {
  const path = encryptedKeyPath();
  if (!existsSync(path)) return null;
  if (!safeStorage.isEncryptionAvailable()) return null;
  try {
    const encrypted = readFileSync(path);
    return safeStorage.decryptString(encrypted);
  } catch {
    return null;
  }
}

export function setApiKey(key: string): void {
  if (!safeStorage.isEncryptionAvailable()) {
    throw new Error("Encryption is not available on this system");
  }
  const encrypted = safeStorage.encryptString(key);
  writeFileSync(encryptedKeyPath(), encrypted);
}

export function clearApiKey(): void {
  const path = encryptedKeyPath();
  if (existsSync(path)) {
    unlinkSync(path);
  }
}
