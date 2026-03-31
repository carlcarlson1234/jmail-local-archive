import { NextRequest, NextResponse } from 'next/server';
import { getMessageById } from '@jmail/db/queries';

export async function GET(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const msg = await getMessageById(id);
    if (!msg) return NextResponse.json({ error: 'Not found' }, { status: 404 });
    return NextResponse.json(msg);
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
