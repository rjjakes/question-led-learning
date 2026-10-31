import { defineConfig, mergeConfig } from "vitest/config"

import viteConfig from "./vite.config.ts"

// After NVIDIA's RAG Blueprint frontend (vitest.config.ts)
export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      globals: true,
      environment: "jsdom",
      setupFiles: ["./src/testing/setup-tests.ts"],
    },
  })
)
