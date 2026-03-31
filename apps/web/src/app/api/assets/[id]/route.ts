import { NextRequest, NextResponse } from 'next/server';
import { getAssetById } from '@jmail/db/queries';

export async function GET(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const asset = await getAssetById(parseInt(id));
    if (!asset) return NextResponse.json({ error: 'Not found' }, { status: 404 });
    return NextResponse.json(asset);
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
