import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  server: {
    port: 5174,
    proxy: {
      "/search": "http://127.0.0.1:8002",
      "/graph": "http://127.0.0.1:8002",
      "/cohort": "http://127.0.0.1:8002",
      "/health": "http://127.0.0.1:8002",
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
