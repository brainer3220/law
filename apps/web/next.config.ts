import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Expose custom environment variables to the client
  env: {
    KIM_BYUN_NEXT_PUBLIC_SUPABASE_URL: process.env.KIM_BYUN_NEXT_PUBLIC_SUPABASE_URL,
    KIM_BYUN_NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.KIM_BYUN_NEXT_PUBLIC_SUPABASE_ANON_KEY,
  },
  webpack: (config) => {
    config.resolve.alias = {
      ...(config.resolve.alias ?? {}),
    };
    return config;
  },
};

export default nextConfig;
