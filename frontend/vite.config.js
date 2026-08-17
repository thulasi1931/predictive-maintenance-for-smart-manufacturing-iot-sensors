import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/login": "http://127.0.0.1:5000",
      "/signup": "http://127.0.0.1:5000",
      "/forgot-password": "http://127.0.0.1:5000",
      "/reset-password": "http://127.0.0.1:5000",
      "/predict": "http://127.0.0.1:5000",
      "/history": "http://127.0.0.1:5000",
      "/forecast": "http://127.0.0.1:5000",
      "/alerts": "http://127.0.0.1:5000",
      "/work-orders": "http://127.0.0.1:5000",
      "/assets": "http://127.0.0.1:5000",
      "/notification-settings": "http://127.0.0.1:5000",
      "/email-test": "http://127.0.0.1:5000",
      "/model-metrics": "http://127.0.0.1:5000",
      "/summary": "http://127.0.0.1:5000",
      "/health": "http://127.0.0.1:5000",
    },
  },
});
