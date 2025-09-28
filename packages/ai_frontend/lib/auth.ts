const FALLBACK_AUTH_SECRET = "development-auth-secret";

function isProduction() {
  return process.env.NODE_ENV === "production";
}

export function getAuthSecret(): string {
  const rawEnvSecret = process.env.AUTH_SECRET;

  if (rawEnvSecret !== undefined) {
    if (
      rawEnvSecret.length > 0 &&
      (rawEnvSecret !== rawEnvSecret.trim())
    ) {
      console.warn(
        "AUTH_SECRET environment variable contains leading or trailing whitespace. This may indicate a configuration error."
      );
    }
    const envSecret = rawEnvSecret.trim();
    if (envSecret.length > 0) {
      return envSecret;
    }
  }

  if (isProduction()) {
    throw new Error(
      "AUTH_SECRET environment variable is required when running in production"
    );
  }

  return FALLBACK_AUTH_SECRET;
}
