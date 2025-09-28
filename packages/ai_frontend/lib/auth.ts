const FALLBACK_AUTH_SECRET = "development-auth-secret";

function isProduction() {
  return process.env.NODE_ENV === "production";
}

export function getAuthSecret(): string {
  const envSecret = process.env.AUTH_SECRET?.trim();

  if (envSecret && envSecret.length > 0) {
    return envSecret;
  }

  if (isProduction()) {
    throw new Error(
      "AUTH_SECRET environment variable is required when running in production"
    );
  }

  return FALLBACK_AUTH_SECRET;
}
