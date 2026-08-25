import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Keep development artifacts separate from production builds. Running
  // `next build` while the acceptance server is open must not corrupt HMR.
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
};

export default nextConfig;
