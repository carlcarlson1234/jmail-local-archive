import { NextRequest, NextResponse } from 'next/server';
import { getPersonById } from '@jmail/db/queries';

export async function GET(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const person = await getPersonById(id);
    if (!person) return NextResponse.json({ error: 'Not found' }, { status: 404 });
    return NextResponse.json(person);
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
