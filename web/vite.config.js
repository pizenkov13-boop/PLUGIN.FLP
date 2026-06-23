import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
// base: "./"  → assets are referenced relatively, so the prod build works when
//               served from the localhost static server in plg_webview.py.
// strictPort  → dev server stays on 5173 so PLG_DEV_URL is predictable.
export default defineConfig({
    plugins: [react()],
    base: "./",
    server: {
        port: 5173,
        strictPort: true,
    },
    build: {
        outDir: "dist",
        emptyOutDir: true,
    },
});
