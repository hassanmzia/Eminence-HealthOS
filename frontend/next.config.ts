import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Use polling for file watching inside Docker containers (avoids EMFILE errors)
  webpack: (config, { dev }) => {
    if (dev) {
      config.watchOptions = {
        poll: 1000,
        aggregateTimeout: 300,
        ignored: /node_modules/,
      };
    }
    return config;
  },
  // Proxy API calls to the HealthOS backend
  // Use API_URL (server-side, Docker-internal) for rewrites, not the public NEXT_PUBLIC_API_URL
  async rewrites() {
    const apiBase = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${apiBase}/api/:path*`,
      },
      {
        source: "/health",
        destination: `${apiBase}/health`,
      },
      {
        source: "/ws/:path*",
        destination: `${apiBase}/ws/:path*`,
      },
    ];
  },
};

export default nextConfig;
