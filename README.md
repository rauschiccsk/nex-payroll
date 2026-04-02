# NEX Payroll

Automated payroll management system with AI-assisted features. Built with FastAPI (backend), React/TypeScript (frontend), and PostgreSQL.

## Architecture

| Service  | Technology            | Port |
|----------|-----------------------|------|
| Backend  | FastAPI / Python 3.12 | 9172 |
| Frontend | React / Nginx         | 9173 |
| Database | PostgreSQL 16         | 9174 |

## Prerequisites

- Docker & Docker Compose
- (Optional) Python 3.12+ with Poetry, Node.js 20+ for local development

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/rauschiccsk/nex-payroll.git && cd nex-payroll

# 2. Create environment file
cp .env.example .env
# Edit .env — set PAYROLL_ENCRYPTION_KEY and PAYROLL_JWT_SECRET

# 3. Start all services
docker compose up -d

# 4. Verify
curl http://localhost:9172/health   # backend
curl http://localhost:9173          # frontend
```

## Environment Variables

| Variable                 | Description                          | Example                                          |
|--------------------------|--------------------------------------|--------------------------------------------------|
| `DATABASE_URL`           | PostgreSQL connection string         | `postgresql://payroll:secret@db:5432/payroll`    |
| `PAYROLL_ENCRYPTION_KEY` | Fernet key for sensitive data        | *(generate with Python cryptography)*            |
| `PAYROLL_JWT_SECRET`     | Secret for JWT token signing         | *(random 64-char string)*                        |
| `OLLAMA_URL`             | Ollama API endpoint for AI features  | `http://host.docker.internal:11434`              |

## Development

### Backend

```bash
cd backend
poetry install
poetry run uvicorn app.main:app --reload --port 9172
```

### Frontend

```bash
cd frontend
npm install
npm run dev -- --port 9173
```

### Running Tests

```bash
# Backend
cd backend && poetry run pytest -v

# Frontend
cd frontend && npm test
```

## Project Structure

```
nex-payroll/
├── backend/              # FastAPI application
│   ├── app/              # Application package
│   ├── tests/            # Backend tests
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/             # React/TypeScript application
│   ├── src/              # Source code
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md
```

## License

Proprietary — ICC s.r.o.
