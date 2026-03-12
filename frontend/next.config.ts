import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Proxy API calls to the HealthOS backend
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:4090"}/api/:path*`,
      },
      {
        source: "/health",
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:4090"}/health`,
      },
      {
        source: "/ws/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:4090"}/ws/:path*`,
      },
    ];
  },
};

export default nextConfig;
