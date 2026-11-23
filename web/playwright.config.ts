import { defineConfig } from "@playwright/test";

const frontend = "http://127.0.0.1:3100";
const backend = "http://127.0.0.1:5100";

export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  use: {
    baseURL: frontend,
    trace: "retain-on-failure",
    launchOptions: { executablePath: process.env.CAISSA_CHROMIUM_PATH || undefined },
  },
  webServer: [
    {
      command: "python e2e/serve_flask.py",
      url: backend + "/api/v1/rooms",
      env: { PYTHONPATH: "../src", SECRET_KEY: "browser-test-only", PORT: "5100",
        HOST: "127.0.0.1", ALLOWED_ORIGINS: frontend },
    },
    {
      command: "npm run dev -- --hostname 127.0.0.1 --port 3100",
      url: frontend,
      env: { CAISSA_BACKEND_URL: backend, NEXT_DIST_DIR: ".next-e2e" },
    },
  ],
});
