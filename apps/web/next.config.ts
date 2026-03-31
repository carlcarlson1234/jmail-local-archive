import type { NextConfig } from "next";
import path from "path";
import dotenv from "dotenv";

// Load .env from project root (two levels up from apps/web)
dotenv.config({ path: path.resolve(__dirname, "../../.env") });

const nextConfig: NextConfig = {
  transpilePackages: ["@jmail/db"],
  serverExternalPackages: ["postgres"],
};

export default nextConfig;
