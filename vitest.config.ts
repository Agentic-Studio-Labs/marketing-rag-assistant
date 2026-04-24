import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    exclude: [
      "**/node_modules/**",
      "**/dist/**",
      "**/out/**",
      "**/.claude/**",
      "**/.worktrees/**",
    ],
  },
  resolve: {
    alias: { "@": resolve(__dirname, "src") },
  },
});
