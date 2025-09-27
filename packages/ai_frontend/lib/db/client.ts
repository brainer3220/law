import { drizzle } from "drizzle-orm/postgres-js";
import postgres, { type Options, type Sql } from "postgres";

import { getPostgresUrl } from "./env";

const ensureServerEnvironment = () => {
  if (typeof window !== "undefined") {
    throw new Error("Database client can only be used on the server");
  }
};

let client: Sql<Record<string, unknown>> | undefined;
let db: ReturnType<typeof drizzle> | undefined;

export const getPostgresClient = () => {
  ensureServerEnvironment();
  if (!client) {
    client = postgres(getPostgresUrl());
  }

  return client;
};

export const getDb = () => {
  ensureServerEnvironment();
  if (!db) {
    db = drizzle(getPostgresClient());
  }

  return db;
};

export const createScopedDb = (options?: Options<Record<string, unknown>>) => {
  ensureServerEnvironment();
  const scopedClient = postgres(getPostgresUrl(), options);
  return { db: drizzle(scopedClient), client: scopedClient };
};
