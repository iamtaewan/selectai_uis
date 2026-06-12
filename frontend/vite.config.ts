// Vite 설정 — React + Tailwind v4 + /api 프록시 (architecture.md §6.1)
// 스캐폴딩 공유 설정 파일 — 구현 에이전트 수정 금지.
// vitest 설정(test 필드)을 함께 두기 위해 vitest/config의 defineConfig 사용.
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // 로컬에서도 배포(nginx)와 동일한 경로 구조 — /api → FastAPI(8000)
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
  },
});
