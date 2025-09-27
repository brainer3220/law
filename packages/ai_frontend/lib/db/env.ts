export function getPostgresUrl(): string {
  const { POSTGRES_URL } = process.env;

  if (!POSTGRES_URL) {
    throw new Error(
      "POSTGRES_URL environment variable is required to access the database"
    );
  }

  return POSTGRES_URL;
}
