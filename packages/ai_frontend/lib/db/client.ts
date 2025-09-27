import "server-only";

import { drizzle } from "drizzle-orm/postgres-js";
import postgres, { type Options, type Sql } from "postgres";

import { getPostgresUrl } from "./env";

let client: Sql<Record<string, unknown>> | undefined;
let db: ReturnType<typeof drizzle> | undefined;

export const getPostgresClient = () => {
  if (!client) {
    client = postgres(getPostgresUrl());
  }

  return client;
};

export const getDb = () => {
  if (!db) {
    db = drizzle(getPostgresClient());
  }

  return db;
};

export const createScopedDb = (options?: Options<Record<string, unknown>>) => {
  const scopedClient = postgres(getPostgresUrl(), options);
  return { db: drizzle(scopedClient), client: scopedClient };
};
