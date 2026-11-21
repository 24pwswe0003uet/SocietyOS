# SocietyOS AI — Deployment Guide

## Quick Start (Development)

```bash
# 1. Start PostgreSQL with pgvector
sudo service postgresql start

# 2. Create database
sudo -u postgres createdb societyos
sudo -u postgres psql -d societyos -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 3. Backend
cd backend
cp ../.env.example .env  # Edit with your values
pip install -r requirements.txt
PYTHONPATH=. python -m alembic upgrade head
PYTHONPATH=. uvicorn app.main:app --reload --port 8000

# 4. Frontend
cd frontend
cp ../.env.example .env.local  # Set NEXT_PUBLIC_API_URL
npm install
npm run dev
```

## Docker Deployment

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with production values (especially JWT_SECRET_KEY and DB_PASSWORD)

# 2. Build and run
docker-compose up -d --build

# 3. Verify
curl http://localhost:8000/api/v1/health
curl http://localhost:3000
```

## Production Checklist

- [ ] Generate a random JWT_SECRET_KEY: `openssl rand -hex 32`
- [ ] Set a strong DB_PASSWORD
- [ ] Configure GEMINI_API_KEY (get from Google AI Studio)
- [ ] Set CORS_ORIGINS to your production domain
- [ ] Enable HTTPS via reverse proxy (nginx/caddy)
- [ ] Configure database backups
- [ ] Set APP_ENV=production and DEBUG=false
- [ ] Review rate limiting thresholds for your traffic

## Architecture

```
                    ┌─────────────┐
                    │   Nginx/    │
                    │   Caddy     │  HTTPS termination
                    └──────┬──────┘
                           │
              ┌────────────┴────────────┐
              │                         │
        ┌─────▼─────┐           ┌──────▼──────┐
        │  Frontend  │           │   Backend   │
        │  Next.js   │           │   FastAPI   │
        │  :3000     │           │   :8000     │
        └────────────┘           └──────┬──────┘
                                        │
                           ┌────────────┴────────────┐
                           │                         │
                    ┌──────▼──────┐          ┌──────▼──────┐
                    │  PostgreSQL │          │    Redis    │
                    │  + pgvector │          │  (sessions) │
                    │  :5432      │          │  :6379      │
                    └─────────────┘          └─────────────┘
```

## Database Migrations

```bash
# Run all pending migrations
cd backend && PYTHONPATH=. python -m alembic upgrade head

# Check current version
PYTHONPATH=. python -m alembic current

# Create a new migration
PYTHONPATH=. python -m alembic revision --autogenerate -m "description"
```

## Backup & Recovery

```bash
# Backup
pg_dump -U postgres societyos > backup_$(date +%Y%m%d).sql

# Restore
psql -U postgres -d societyos < backup_20261120.sql

# Backup with pgvector data
pg_dump -U postgres --format=custom societyos > backup.dump
pg_restore -U postgres -d societyos backup.dump
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| DATABASE_URL | Yes | localhost | PostgreSQL connection string |
| JWT_SECRET_KEY | Yes | (dev default) | JWT signing key — generate random |
| GEMINI_API_KEY | No | (empty) | Google AI API key — fallbacks used without |
| GEMINI_MODEL | No | gemini-2.0-flash | Gemini model for generation |
| EMBEDDING_MODEL | No | text-embedding-004 | Model for semantic embeddings |
| EMBEDDING_DIMENSIONS | No | 768 | Vector dimensions (must match model) |
| CORS_ORIGINS | Yes | localhost:3000 | Allowed frontend origins |
| APP_ENV | No | development | development/production |
| REDIS_URL | No | localhost:6379 | Redis for sessions |
| UPLOAD_DIR | No | ./uploads | File upload storage path |
| MAX_UPLOAD_SIZE_MB | No | 50 | Maximum upload size |

## Known Limitations

1. **AI dependency**: Without GEMINI_API_KEY, all AI features use rule-based fallbacks. Quality is significantly lower.
2. **Share tokens**: Currently in-memory — lost on server restart. Production should use Redis or DB.
3. **File storage**: Local filesystem only. Production should use S3/GCS.
4. **Vector search quality**: Fallback embeddings (without API key) are pseudo-random — similarity search won't find semantically related events.
5. **Single-instance rate limiter**: In-memory bucket won't work across multiple workers. Use Redis rate limiting in production.
6. **No email notifications**: Approval and task notifications are dashboard-only.
