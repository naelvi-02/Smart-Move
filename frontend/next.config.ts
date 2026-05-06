import path from "node:path";
import type { NextConfig } from "next";

const workspaceRoot = path.basename(process.cwd()) === 'frontend'
  ? process.cwd()
  : path.join(process.cwd(), 'frontend');

const nextConfig: NextConfig = {
  output: 'export',
  images: {
    unoptimized: true,
  },
  turbopack: {
    root: workspaceRoot,
  },
  trailingSlash: true,
};

export default nextConfig;
