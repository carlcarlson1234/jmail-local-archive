import { NextResponse } from 'next/server';

export async function GET() {
  try {
    const { db } = await import('@jmail/db');
    const result = await db.execute({ sql: 'SELECT 1 as ok' } as any);
    return NextResponse.json({ status: 'ok', database: 'connected', timestamp: new Date().toISOString() });
  } catch (error: any) {
    return NextResponse.json({ status: 'error', database: 'disconnected', error: error.message }, { status: 503 });
  }
}
