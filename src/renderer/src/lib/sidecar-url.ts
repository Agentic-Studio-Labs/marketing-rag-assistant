/** Base URL for the FastAPI sidecar (no trailing slash). */
export function resolveSidecarBase(
  viteUrl: string | undefined,
  windowOrigin: string | undefined,
): string {
  if (viteUrl) return viteUrl.replace(/\/$/, "");
  return windowOrigin ?? "http://127.0.0.1:8420";
}
