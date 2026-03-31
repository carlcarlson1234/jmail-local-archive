import { NextRequest, NextResponse } from 'next/server';
import { getConversationBySlug } from '@jmail/db/queries';

export async function GET(_req: NextRequest, { params }: { params: Promise<{ slug: string }> }) {
  try {
    const { slug } = await params;
    const conv = await getConversationBySlug(slug);
    if (!conv) return NextResponse.json({ error: 'Not found' }, { status: 404 });
    return NextResponse.json(conv);
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
