import { config } from "dotenv";
import { migrate } from "drizzle-orm/postgres-js/migrator";

import { createScopedDb } from "./client";

config({
  path: ".env.local",
});

const runMigrate = async () => {
  const { db, client } = createScopedDb({ max: 1 });

  console.log("⏳ Running migrations...");

  const start = Date.now();
  await migrate(db, { migrationsFolder: "./lib/db/migrations" });
  const end = Date.now();

  console.log("✅ Migrations completed in", end - start, "ms");
  await client.end();
  process.exit(0);
};

runMigrate().catch((err) => {
  console.error("❌ Migration failed");
  console.error(err);
  process.exit(1);
});
