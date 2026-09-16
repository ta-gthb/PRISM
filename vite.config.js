import { defineConfig } from "vite";
import path from "node:path";

const frontendPath = (entry) => path.resolve(import.meta.dirname, "frontend", entry);

// Vanilla HTML multi-page app. Vite is used only as the static dev/build server.
export default defineConfig(({ mode }) => ({
  root: frontendPath(""),
  base: process.env.FIGMA_PUBLIC_URL ? `${process.env.FIGMA_PUBLIC_URL}/` : "/",
  build: {
    outDir: path.resolve(import.meta.dirname, "dist"),
    emptyOutDir: true,
    sourcemap: mode === "development" ? "inline" : false,
    minify: mode !== "development",
    rollupOptions: {
      input: {
        main: frontendPath("index.html"),
        inspector: frontendPath("pages/inspector.html"),
        supervisor: frontendPath("pages/supervisor.html"),
        admin: frontendPath("pages/admin.html"),
        manufacturer: frontendPath("pages/manufacturer.html"),
        consumer: frontendPath("pages/consumer.html"),
      },
    },
  },
  server: {
    host: process.env.FIGMA_DEV_SERVER_HOST || "0.0.0.0",
    port: Number.parseInt(process.env.PORT || "8443", 10),
    strictPort: true,
    watch: { ignored: ["**/.figma/**", "**/backend/**", "**/__pycache__/**"] },
  },
  preview: {
    host: process.env.FIGMA_DEV_SERVER_HOST || "0.0.0.0",
    port: Number.parseInt(process.env.PORT || "8443", 10),
  },
}));
