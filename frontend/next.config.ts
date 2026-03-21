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
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/:path*`,
      },
      {
        source: "/health",
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/health`,
      },
      {
        source: "/ws/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/ws/:path*`,
      },
    ];
  },
};

export default nextConfig;
