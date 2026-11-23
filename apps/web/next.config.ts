import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // E2E and local probes use 127.0.0.1 while Next binds localhost; allow the
  // loopback dev origin so HMR/dev resources are not blocked (dev only).
  allowedDevOrigins: ["127.0.0.1"],
};

export default nextConfig;
