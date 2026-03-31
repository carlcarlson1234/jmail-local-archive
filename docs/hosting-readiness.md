# Hosting Readiness

## What Is Already Deployment-Ready

- **Next.js app** — standard App Router, can deploy to Vercel, Railway, Fly.io, etc.
- **API routes** — all at `/api/*`, no special server dependencies
- **Database schema** — standard PostgreSQL, works with any managed Postgres
- **Environment config** — all settings via env vars, no hardcoded paths
- **Storage abstraction** — `StorageProvider` interface ready for cloud swap

## What Must Change to Host Online

### 1. Storage Backend
**Current:** Local filesystem (`data/raw/jmail/`, `data/raw-assets/`)
**Target:** S3, R2, or B2

Steps:
1. Implement `S3StorageProvider` or `R2StorageProvider` in `src/lib/storage/`
2. Upload raw files to cloud bucket
3. Set env vars for bucket credentials
4. The rest of the app uses the `StorageProvider` interface unchanged

### 2. Database
**Current:** Local PostgreSQL on port 5432
**Target:** Managed PostgreSQL (Supabase, Neon, RDS, etc.)

Steps:
1. Provision managed PostgreSQL instance
2. Run the schema creation SQL
3. Run the ingestion pipeline pointing to the remote database
4. Update `DATABASE_URL` env var

### 3. App Deployment
**Current:** `pnpm dev` on localhost:3001
**Target:** Cloud platform

Steps for Vercel:
1. Connect repo to Vercel
2. Set root directory to `apps/web`
3. Set env vars: `DATABASE_URL`
4. Deploy

Steps for Railway/Fly.io:
1. Add Dockerfile or use buildpacks
2. Set env vars
3. Deploy

### 4. Data Ingestion
Currently runs locally via Python scripts. For cloud:
- Run ingestion as a one-time job or scheduled task
- Can run from any machine with database access
- No changes needed to ingestion scripts — they use `DATABASE_URL`

## Recommended First Deployment Path

1. **Neon or Supabase** for managed PostgreSQL (free tier available)
2. **Vercel** for Next.js app (free tier sufficient)
3. **Cloudflare R2** for raw file storage (free egress)
4. Run ingestion locally pointing to remote database

## Cost Considerations

- **Database:** ~500MB-1GB for structured data. Most managed Postgres free tiers cover this.
- **Storage:** ~2-3GB for raw files. R2/B2 are very cheap for this volume.
- **Compute:** Next.js server functions are lightweight. Free tier usually sufficient.

## Timeline Estimate

Migrating from local to hosted: **2-4 hours** for someone familiar with the codebase.
