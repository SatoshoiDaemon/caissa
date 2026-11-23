import type { NextConfig } from "next";

const backend = (process.env.CAISSA_BACKEND_URL ?? "http://127.0.0.1:5000").replace(/\/$/, "");
const config: NextConfig = {
  skipTrailingSlashRedirect: true,
  distDir: process.env.NEXT_DIST_DIR || ".next",
  async rewrites() {
    return [
      { source: "/api/v1/:path*", destination: backend + "/api/v1/:path*" },
      { source: "/socket.io", destination: backend + "/socket.io/" },
    ];
  },
};

export default config;
