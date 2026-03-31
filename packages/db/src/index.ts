import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import * as schema from './schema';

const connectionString = process.env.DATABASE_URL || 'postgresql://jmail:jmail_local@localhost:5432/jmail';

const queryClient = postgres(connectionString);
export const db = drizzle(queryClient, { schema });

export * from './schema';
export type Database = typeof db;
