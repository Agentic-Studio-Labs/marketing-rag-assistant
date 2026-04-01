import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactElement,
} from "react";

interface Props {
  isKeySet: boolean;
  encryptionAvailable: boolean;
  onClose: () => void;
  onSaved: () => void;
}

export function ApiKeyDialog({
  isKeySet,
  encryptionAvailable,
  onClose,
  onSaved,
}: Props): ReactElement {
  const [key, setKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const backdropRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSave = useCallback(async () => {
    const trimmed = key.trim();
    if (!trimmed) return;
    if (!trimmed.startsWith("sk-ant-")) {
      setError("Key should start with sk-ant-");
      return;
    }
    setError(null);
    setSaving(true);
    try {
      await window.electronAPI?.setApiKey(trimmed);
      onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save key");
    } finally {
      setSaving(false);
    }
  }, [key, onSaved]);

  const handleClear = useCallback(async () => {
    setSaving(true);
    try {
      await window.electronAPI?.clearApiKey();
      setKey("");
      onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to clear key");
    } finally {
      setSaving(false);
    }
  }, [onSaved]);

  const handleBackdropClick = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === backdropRef.current) onClose();
    },
    [onClose],
  );

  return (
    <div
      ref={backdropRef}
      onClick={handleBackdropClick}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
    >
      <div className="w-full max-w-md rounded-2xl border border-zinc-700 bg-zinc-900 p-6 shadow-2xl">
        <h2 className="text-base font-semibold text-zinc-100">API Key</h2>
        <p className="mt-1 text-sm text-zinc-400">
          Stored securely in macOS Keychain. Never sent to the renderer.
        </p>

        {!encryptionAvailable ? (
          <div className="mt-4 rounded-lg border border-amber-900/60 bg-amber-950/40 px-4 py-3 text-sm text-amber-100">
            Encryption is not available on this system. The key cannot be stored
            securely.
          </div>
        ) : null}

        <div className="mt-4 flex items-center gap-2">
          <span
            className={`h-2.5 w-2.5 rounded-full ${isKeySet ? "bg-emerald-500" : "bg-zinc-600"}`}
          />
          <span className="text-sm text-zinc-300">
            {isKeySet ? "Key stored" : "Not set"}
          </span>
        </div>

        <div className="mt-4">
          <input
            ref={inputRef}
            type="password"
            value={key}
            onChange={(e) => {
              setKey(e.target.value);
              setError(null);
            }}
            onKeyDown={(e) => e.key === "Enter" && void handleSave()}
            placeholder="sk-ant-…"
            className="w-full rounded-xl border border-zinc-700 bg-zinc-800 px-4 py-3 text-sm text-zinc-100 outline-none transition placeholder:text-zinc-500 focus:border-emerald-700/50 focus:ring-2 focus:ring-emerald-700/30"
            disabled={saving || !encryptionAvailable}
            aria-label="Anthropic API key"
          />
        </div>

        {error ? <p className="mt-2 text-sm text-red-400">{error}</p> : null}

        <div className="mt-5 flex justify-end gap-2">
          {isKeySet ? (
            <button
              type="button"
              onClick={() => void handleClear()}
              disabled={saving}
              className="rounded-lg px-4 py-2 text-sm text-red-400 transition hover:bg-red-950/40 disabled:opacity-40"
            >
              Clear key
            </button>
          ) : null}
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-4 py-2 text-sm text-zinc-400 transition hover:bg-zinc-800"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => void handleSave()}
            disabled={saving || !key.trim() || !encryptionAvailable}
            className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
