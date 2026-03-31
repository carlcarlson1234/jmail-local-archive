import { NextRequest, NextResponse } from 'next/server';
import { getEmailById } from '@jmail/db/queries';

export async function GET(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const email = await getEmailById(id);
    if (!email) return NextResponse.json({ error: 'Not found' }, { status: 404 });
    return NextResponse.json(email);
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
