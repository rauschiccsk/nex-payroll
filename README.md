# NEX Payroll

**ICC Automated Accounting** — Payroll management system s AI-powered functionalities.

## Quick Start

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env — set DATABASE_URL, PAYROLL_ENCRYPTION_KEY, PAYROLL_JWT_SECRET

# 2. Start services
docker compose up -d

# 3. Access
Backend API: http://localhost:9172/docs
Frontend: http://localhost:9173
Database: localhost:9174
```

## Port Assignment (ICC Port Registry)
- **9172** — Backend API (FastAPI)
- **9173** — Frontend (Nginx)
- **9174** — PostgreSQL 16

## Development

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 9172
```

### Frontend
```bash
cd frontend
npm install
npm run dev  # Vite dev server on 9173
```

## Environment Variables
See `.env.example` for required configuration.

## CI/CD
GitHub Actions self-hosted runner on ANDROS Ubuntu.
Pipeline: Lint → Test → Build Docker Image

## License
Proprietary — ICC s.r.o.
