import { describe, expect, it } from "vitest";
import { resolveSidecarBase } from "./sidecar-url";

describe("resolveSidecarBase", () => {
  it("strips trailing slash from Vite env URL", () => {
    expect(resolveSidecarBase("http://127.0.0.1:8420/", undefined)).toBe(
      "http://127.0.0.1:8420",
    );
  });
  it("falls back to window or default", () => {
    expect(resolveSidecarBase(undefined, "http://custom")).toBe(
      "http://custom",
    );
    expect(resolveSidecarBase(undefined, undefined)).toBe(
      "http://127.0.0.1:8420",
    );
  });
});
