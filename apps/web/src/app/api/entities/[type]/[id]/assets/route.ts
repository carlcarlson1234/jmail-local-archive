import { NextRequest, NextResponse } from 'next/server';
import { listAssetsForEntity } from '@jmail/db/queries';

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ type: string; id: string }> }
) {
  try {
    const { type, id } = await params;
    const assets = await listAssetsForEntity(type, id);
    return NextResponse.json({ entityType: type, entityId: id, assets });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
