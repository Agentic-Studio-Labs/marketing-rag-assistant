import { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthProvider";

function readTokenFromHash(): string | null {
  const raw = window.location.hash.replace(/^#/, "");
  const qi = raw.indexOf("?");
  if (qi === -1) return null;
  const qs = new URLSearchParams(raw.slice(qi + 1));
  return qs.get("token") ?? qs.get("magic_token");
}

export default function Login() {
  const {
    requestMagicLink,
    completeMagicLink,
    requestedEmail,
    lastMagicLink,
    loading,
  } = useAuth();
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const t = readTokenFromHash();
    if (t) setToken(t);
  }, []);

  async function handleRequest(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setMessage("");
    try {
      const response = await requestMagicLink(email);
      setMessage(`Magic link issued for ${response.email}.`);
      if (response.dev_magic_link_token) {
        setToken(response.dev_magic_link_token);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleComplete(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await completeMagicLink(token.trim());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div className="min-h-screen bg-background text-foreground flex items-center justify-center p-6">
      <div className="w-full max-w-xl rounded-xl border border-border bg-card p-8 space-y-8 shadow-sm">
        <div>
          <h1 className="text-2xl font-semibold">Operator Sign In</h1>
          <p className="text-sm text-muted-foreground mt-2">
            This desktop build is configured for cloud mode and requires a
            magic-link session.
          </p>
        </div>

        <form onSubmit={handleRequest} className="space-y-3">
          <div>
            <label className="text-sm font-medium block mb-2" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
              placeholder="you@company.com"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !email.trim()}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
          >
            {loading ? "Requesting..." : "Send Magic Link"}
          </button>
        </form>

        <form
          onSubmit={handleComplete}
          className="space-y-3 border-t border-border pt-6"
        >
          <div>
            <label className="text-sm font-medium block mb-2" htmlFor="token">
              Magic Link Token
            </label>
            <textarea
              id="token"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm min-h-28"
              placeholder="Paste the signed token (from email, dev console, or a cih:// / app deep link)."
            />
          </div>
          <button
            type="submit"
            disabled={loading || !token.trim()}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
          >
            {loading ? "Signing In..." : "Complete Sign In"}
          </button>
        </form>

        {(requestedEmail || lastMagicLink || message || error) && (
          <div className="rounded-md border border-border bg-muted/30 p-4 space-y-2 text-sm">
            {requestedEmail && (
              <p className="text-muted-foreground">
                Latest email request:{" "}
                <span className="font-medium text-foreground">
                  {requestedEmail}
                </span>
              </p>
            )}
            {lastMagicLink && (
              <div>
                <p className="font-medium">Development token</p>
                <p className="text-xs text-muted-foreground break-all mt-1">
                  {lastMagicLink}
                </p>
              </div>
            )}
            {message && <p className="text-emerald-600">{message}</p>}
            {error && <p className="text-red-500">{error}</p>}
          </div>
        )}
      </div>
    </div>
  );
}
