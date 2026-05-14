import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  outputFileTracingRoot: path.resolve(process.cwd(), "../.."),
  // Expose custom environment variables to the client
  env: {
    KIM_BYUN_NEXT_PUBLIC_SUPABASE_URL: process.env.KIM_BYUN_NEXT_PUBLIC_SUPABASE_URL,
    KIM_BYUN_NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.KIM_BYUN_NEXT_PUBLIC_SUPABASE_ANON_KEY,
  },
};

export default nextConfig;
