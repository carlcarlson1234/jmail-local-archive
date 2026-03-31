import { NextRequest, NextResponse } from 'next/server';
import { searchAll } from '@jmail/db/queries';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const q = searchParams.get('q') || '';
    const type = (searchParams.get('type') || 'all') as any;
    const limit = Math.min(parseInt(searchParams.get('limit') || '20'), 100);
    const offset = parseInt(searchParams.get('offset') || '0');

    if (!q.trim()) {
      return NextResponse.json({ results: [], query: '', total: 0 });
    }

    const results = await searchAll({ query: q, type, limit, offset });
    return NextResponse.json({ results, query: q, type, limit, offset });
  } catch (error: any) {
    return NextResponse.json({ error: error.message, results: [] }, { status: 500 });
  }
}
