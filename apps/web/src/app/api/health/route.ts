import { NextResponse } from 'next/server';
import postgres from 'postgres';

export async function GET() {
  try {
    const sql = postgres(process.env.DATABASE_URL || 'postgresql://jmail:jmail_local@localhost:5432/jmail');
    const result = await sql`SELECT 1 as ok`;
    await sql.end();
    return NextResponse.json({ status: 'ok', database: 'connected', timestamp: new Date().toISOString() });
  } catch (error: any) {
    return NextResponse.json({ status: 'error', database: 'disconnected', error: error.message }, { status: 503 });
  }
}
