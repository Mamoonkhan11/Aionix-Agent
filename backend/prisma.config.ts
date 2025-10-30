import "dotenv/config"; // ✅ loads .env automatically
import { defineConfig, env } from "prisma/config";

export default defineConfig({
  schema: "./prisma/schema.prisma", // ✅ added ./ for explicit path
  migrations: {
    path: "./prisma/migrations", // ✅ consistent path
  },
  engine: "classic", // optional, fine
  datasource: {
    url: env("DATABASE_URL"), // ✅ now .env will be loaded correctly
  },
});
