import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  resolve: {
    alias: {
      // Next 서버 전용 가드는 vitest(node) 환경에서 빈 모듈로 대체한다.
      "server-only": path.resolve(__dirname, "test/stub-server-only.ts"),
      "@": path.resolve(__dirname),
    },
  },
  test: {
    environment: "node",
    setupFiles: ["test/setup.ts"],
  },
});
