import { NextRequest, NextResponse } from 'next/server';
import { getPhotoById } from '@jmail/db/queries';

export async function GET(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const photo = await getPhotoById(id);
    if (!photo) return NextResponse.json({ error: 'Not found' }, { status: 404 });
    return NextResponse.json(photo);
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
