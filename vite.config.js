import { defineConfig } from "vite";
import path from "node:path";
import fs from "node:fs";

const frontendPath = (entry) => path.resolve(import.meta.dirname, "frontend", entry);

function copyStaticAssetsPlugin() {
  return {
    name: "copy-static-assets",
    closeBundle() {
      const outDir = path.resolve(import.meta.dirname, "dist");
      const jsSrc = frontendPath("js");
      const jsDest = path.resolve(outDir, "js");
      if (fs.existsSync(jsSrc)) {
        fs.cpSync(jsSrc, jsDest, { recursive: true });
        console.log("Copied frontend/js -> dist/js");
      }
      const cssSrc = frontendPath("css");
      const cssDest = path.resolve(outDir, "css");
      if (fs.existsSync(cssSrc)) {
        fs.cpSync(cssSrc, cssDest, { recursive: true });
        console.log("Copied frontend/css -> dist/css");
      }
    },
  };
}

// Vanilla HTML multi-page app. Vite is used only as the static dev/build server.
export default defineConfig(({ mode }) => ({
  root: frontendPath(""),
  base: process.env.FIGMA_PUBLIC_URL ? `${process.env.FIGMA_PUBLIC_URL}/` : "/",
  plugins: [copyStaticAssetsPlugin()],
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
    host: "0.0.0.0",
    port: 3000,
    strictPort: true,
    watch: { ignored: ["**/.figma/**", "**/backend/**", "**/__pycache__/**"] },
  },
  preview: {
    host: "0.0.0.0",
    port: 3000,
  },
}));
